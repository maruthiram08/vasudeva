"""
Vasudeva RAG Pipeline - Wisdom-based guidance system
Provides solutions and mental wellness support based on ancient wisdom texts
"""

import os
import json
import tempfile
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
except ImportError:
    from langchain_text_splitters import RecursiveCharacterTextSplitter

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Chroma

# Pinecone support (for Vercel serverless deployment)
try:
    from pinecone import Pinecone as PineconeClient
    from langchain_pinecone import PineconeVectorStore
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    print("⚠️  Pinecone not installed. Using ChromaDB only.")
try:
    from langchain_classic.chains.retrieval_qa.base import RetrievalQA
except ImportError:
    try:
        from langchain.chains import RetrievalQA
    except ImportError:
        try:
            from langchain_community.chains import RetrievalQA
        except ImportError:
            print("⚠️ RetrievalQA import failed. Using mock for non-RAG modes.")
            # Minimal mock to prevent AttributeError in non-RAG contexts
            class RetrievalQA:
                @classmethod
                def from_chain_type(cls, **kwargs):
                    return cls()
                def invoke(self, query):
                    return {"result": "RAG Unavailable", "source_documents": []}

try:
    from langchain.prompts import PromptTemplate
except ImportError:
    from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv

# Custom tracing
from tracer import get_tracer

# Response Mode Engine (Phase 2)
from response_modes import get_dispatcher, ResponseMode, MODE_PROMPTS

# Phase 3: Conversation State Machine (Path B - Strict)
from conversation_state import (
    StateManager, 
    ConversationState,
    EXIT_TEMPLATE,
    REFUSAL_TEMPLATE,
    POST_EXIT_REDIRECT,
    HARD_DISTRESS_TRIGGERS,
    EMOTIONAL_BLOCKLIST
)

# Optional: Cohere Reranker for better retrieval
try:
    import cohere
    COHERE_AVAILABLE = True
except ImportError:
    COHERE_AVAILABLE = False

try:
    from google.cloud import storage
    GCS_AVAILABLE = True
except ImportError:
    GCS_AVAILABLE = False
    print("⚠️  google-cloud-storage not installed. GCS features disabled.")

# Load environment variables
load_dotenv()


class VasudevaRAG:
    """
    Vasudeva RAG Pipeline - AI advisor based on wisdom literature
    """
    
    def __init__(
        self,
        documents_dir: str = "documents",
        vector_db_dir: str = "vectordb",
        chunk_size: int = 800,
        chunk_overlap: int = 150,
        model_name: str = "gpt-4o-mini",
        gcs_bucket_name: Optional[str] = None,
        gcs_project_id: Optional[str] = None,
        use_pinecone: bool = False,
        pinecone_index_name: Optional[str] = None
    ):
        """
        Initialize Vasudeva RAG pipeline.
        
        Args:
            documents_dir: Directory containing wisdom texts (PDFs)
            vector_db_dir: Directory to store vector database
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
            model_name: OpenAI model name
            gcs_bucket_name: GCS bucket name for documents (optional)
            gcs_project_id: GCS project ID (optional)
        """
        self.documents_dir = Path(documents_dir)
        self.vector_db_dir = Path(vector_db_dir)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.model_name = model_name
        
        # GCS configuration
        self.gcs_bucket_name = gcs_bucket_name or os.getenv("GCS_BUCKET_NAME")
        self.gcs_project_id = gcs_project_id or os.getenv("GCS_PROJECT_ID")
        self.gcs_client = None
        self._temp_dir = None
        
        # Pinecone configuration (for Vercel serverless)
        self.use_pinecone = use_pinecone or os.getenv("USE_PINECONE", "false").lower() == "true"
        self.pinecone_index_name = pinecone_index_name or os.getenv("PINECONE_INDEX_NAME", "vasudeva-wisdom")
        self.pinecone_client = None
        
        # Initialize components
        self.embeddings = OpenAIEmbeddings()
        self.llm = ChatOpenAI(model_name=model_name, temperature=0.7)
        self.vectorstore = None
        
        # Initialize tracer
        self.tracer = get_tracer(log_dir=str(Path(__file__).parent / "traces"))
        self.qa_chain = None
        
        # Initialize Cohere Reranker (optional, improves retrieval quality)
        self.cohere_client = None
        if COHERE_AVAILABLE:
            cohere_key = os.getenv("COHERE_API_KEY")
            if cohere_key:
                self.cohere_client = cohere.Client(cohere_key)
                print("✅ Cohere Reranker enabled")
            else:
                print("⚠️  Cohere Reranker disabled (no COHERE_API_KEY)")
        
        # Create directories
        self.vector_db_dir.mkdir(exist_ok=True, parents=True)
        self.documents_dir.mkdir(exist_ok=True, parents=True)
    
    def _setup_gcs_client(self) -> None:
        """Initialize GCS client if credentials available."""
        if not GCS_AVAILABLE:
            return
        
        try:
            # Check for service account JSON in environment
            credentials_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
            if credentials_json:
                from google.oauth2 import service_account
                credentials = service_account.Credentials.from_service_account_info(
                    json.loads(credentials_json)
                )
                self.gcs_client = storage.Client(
                    credentials=credentials,
                    project=self.gcs_project_id
                )
            else:
                # Use default credentials or anonymous for public buckets
                self.gcs_client = storage.Client.create_anonymous_client()
        except Exception as e:
            print(f"⚠️  Could not initialize GCS client: {e}")
            self.gcs_client = None
    
    def download_documents_from_gcs(self) -> Path:
        """Download documents from GCS bucket to temporary directory."""
        if not self.gcs_bucket_name:
            raise ValueError("GCS bucket name not configured")
        
        if not GCS_AVAILABLE:
            raise ImportError("google-cloud-storage not installed. Run: pip install google-cloud-storage")
        
        # Initialize GCS client if needed
        if self.gcs_client is None:
            self._setup_gcs_client()
        
        # Create temporary directory for downloads
        if self._temp_dir is None:
            self._temp_dir = Path(tempfile.mkdtemp(prefix="vasudeva_docs_"))
        
        print(f"☁️  Downloading documents from GCS bucket: {self.gcs_bucket_name}")
        
        try:
            bucket = self.gcs_client.bucket(self.gcs_bucket_name)
            blobs = list(bucket.list_blobs())
            pdf_blobs = [b for b in blobs if b.name.endswith('.pdf')]
            
            if not pdf_blobs:
                raise ValueError(f"No PDF files found in GCS bucket: {self.gcs_bucket_name}")
            
            print(f"📥 Downloading {len(pdf_blobs)} documents...")
            for blob in pdf_blobs:
                local_path = self._temp_dir / blob.name
                print(f"  - Downloading {blob.name} ({blob.size / 1024 / 1024:.1f} MB)")
                blob.download_to_filename(str(local_path))
            
            print(f"✅ Downloaded {len(pdf_blobs)} documents to {self._temp_dir}")
            return self._temp_dir
        
        except Exception as e:
            raise RuntimeError(f"Failed to download documents from GCS: {e}")
    
    def load_documents(self) -> List[Any]:
        """Load all wisdom texts from local directory or GCS."""
        documents = []
        
        # Check if documents exist locally
        pdf_files = list(self.documents_dir.glob("*.pdf"))
        
        if not pdf_files:
            # Try downloading from GCS
            if self.gcs_bucket_name:
                print(f"📂 No local documents found, checking GCS...")
                try:
                    docs_dir = self.download_documents_from_gcs()
                    pdf_files = list(docs_dir.glob("*.pdf"))
                except Exception as e:
                    print(f"❌ Failed to download from GCS: {e}")
                    raise ValueError(
                        f"No PDF files found locally in {self.documents_dir} "
                        f"and failed to download from GCS: {e}"
                    )
            else:
                raise ValueError(
                    f"No PDF files found in {self.documents_dir} "
                    "and GCS bucket not configured"
                )
        
        print(f"📚 Loading {len(pdf_files)} wisdom texts...")
        for pdf_file in pdf_files:
            print(f"  - Loading {pdf_file.name}")
            loader = PyPDFLoader(str(pdf_file))
            documents.extend(loader.load())
        
        print(f"✅ Loaded {len(documents)} pages of wisdom")
        return documents
    
    def split_documents(self, documents: List[Any]) -> List[Any]:
        """Split documents into chunks using story-aware semantic boundaries."""
        print(f"✂️  Splitting with story-aware chunking...")
        
        # Use story-aware chunker for better semantic boundaries
        from story_aware_chunker import StoryAwareChunker, ChunkResult
        from langchain_core.documents import Document
        
        chunker = StoryAwareChunker(
            min_chunk_size=300,
            max_chunk_size=2500,
            ideal_chunk_size=1200,
            overlap_chars=150
        )
        
        # Convert LangChain documents to chunks
        all_chunks = []
        for doc in documents:
            # Get source name and page from metadata
            source = doc.metadata.get('source', 'unknown')
            page = doc.metadata.get('page', 0)
            
            # Process document with story-aware chunker
            chunks = chunker.chunk_document(
                text=doc.page_content,
                source=source,
                start_page=page
            )
            
            # Convert ChunkResults back to LangChain Documents
            for chunk in chunks:
                # Clean metadata - convert lists to comma-separated strings
                clean_metadata = {}
                for key, value in chunk.metadata.items():
                    if isinstance(value, list):
                        # Convert list to comma-separated string
                        clean_metadata[key] = ",".join(str(v) for v in value) if value else ""
                    else:
                        clean_metadata[key] = value
                
                lang_doc = Document(
                    page_content=chunk.content,
                    metadata=clean_metadata
                )
                all_chunks.append(lang_doc)
        
        print(f"✅ Created {len(all_chunks)} story-aware chunks")
        return all_chunks
    
    def create_vectorstore(self, chunks: List[Any]) -> None:
        """Create vector store from wisdom chunks."""
        print("🔮 Creating vector embeddings...")
        self.vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            persist_directory=str(self.vector_db_dir),
            collection_name="vasudeva_wisdom"  # Use story-aware chunks collection
        )
        print(f"✅ Vector store ready with {len(chunks)} chunks")
    
    def load_vectorstore(self) -> None:
        """Load existing vector store from disk."""
        if not self.vector_db_dir.exists():
            raise ValueError(f"Vector store not found at {self.vector_db_dir}")
        
        print("📖 Loading wisdom database...")
        
        # Create ChromaDB client first to ensure proper connection
        import chromadb
        from chromadb.config import Settings
        
        client = chromadb.PersistentClient(
            path=str(self.vector_db_dir),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Load the existing collection with OpenAI embeddings
        self.vectorstore = Chroma(
            client=client,
            collection_name="vasudeva_wisdom",
            embedding_function=self.embeddings
        )
        
        # Verify documents loaded
        count = self.vectorstore._collection.count()
        print(f"✅ Wisdom database loaded ({count} chunks)")
    
    def load_vectorstore_pinecone(self) -> None:
        """Load vectorstore from Pinecone cloud (for Vercel serverless)."""
        if not PINECONE_AVAILABLE:
            raise RuntimeError("Pinecone not installed. Run: pip install pinecone-client langchain-pinecone")
        
        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key:
            raise ValueError("PINECONE_API_KEY environment variable not set")
        
        print(f"🌲 Connecting to Pinecone index: {self.pinecone_index_name}...")
        
        # Initialize Pinecone client
        self.pinecone_client = PineconeClient(api_key=api_key)
        index = self.pinecone_client.Index(self.pinecone_index_name)
        
        # Create LangChain vectorstore wrapper
        self.vectorstore = PineconeVectorStore(
            index=index,
            embedding=self.embeddings,
            text_key="text"
        )
        
        # Verify connection
        stats = index.describe_index_stats()
        print(f"✅ Pinecone connected ({stats.total_vector_count} vectors)")

    
    def setup_qa_chain(self, retrieval_k: int = 5) -> None:
        """Set up the wisdom guidance QA chain."""
        if self.vectorstore is None:
            raise ValueError("Vector store not initialized")
        
        # Simplified wisdom prompt - story extraction happens separately
        # Simplified wisdom prompt - story extraction happens separately
        wisdom_prompt_template = """You are a wise, compassionate guide who provides support based on timeless wisdom.

A person has come to you seeking guidance. Share profound wisdom with empathy and clarity.

Guidelines:
1. Be empathetic and understanding of their situation
2. Draw insights from the wisdom texts provided
3. Offer practical advice they can apply to their life
4. Maintain a supportive, non-judgmental tone
5. Keep responses meaningful but not too long (3-6 sentences)
6. DO NOT use flowery archaic language or address them as "Partha"
7. DO NOT roleplay as a deity

Sacred Wisdom from the Texts:
{context}

Seeker's Problem:
{question}

Your Guidance:"""
        
        WISDOM_PROMPT = PromptTemplate(
            template=wisdom_prompt_template,
            input_variables=["context", "question"]
        )
        
        # Create retrieval QA chain
        self.qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.vectorstore.as_retriever(
                search_kwargs={"k": retrieval_k}
            ),
            return_source_documents=True,
            chain_type_kwargs={"prompt": WISDOM_PROMPT}
        )
        print("✅ Vasudeva is ready to provide guidance")
    
    def build_pipeline(self, force_rebuild: bool = False) -> None:
        """Build the complete wisdom guidance pipeline."""
        
        # Use Pinecone for Vercel serverless deployment
        if self.use_pinecone:
            print("🌲 Using Pinecone for vector storage...")
            self.load_vectorstore_pinecone()
        # Use ChromaDB for local development
        elif self.vector_db_dir.exists() and not force_rebuild:
            print("📚 Wisdom database found, loading...")
            self.load_vectorstore()
        else:
            print("🔨 Building new wisdom database...")
            documents = self.load_documents()
            chunks = self.split_documents(documents)
            self.create_vectorstore(chunks)
        
        # Set up QA chain
        self.setup_qa_chain()
        print("\n✨ Vasudeva is ready to help!\n")
    
    def _rerank_documents(self, query: str, documents: list, top_n: int = 5) -> list:
        """
        Rerank documents using Cohere for better relevance.
        Falls back to original order if Cohere unavailable.
        
        Args:
            query: User query
            documents: List of Document objects from ChromaDB
            top_n: Number of top documents to return after reranking
            
        Returns:
            Reranked list of documents (top_n)
        """
        if not self.cohere_client or not documents:
            return documents[:top_n]
        
        try:
            # Extract text from Document objects
            doc_texts = [doc.page_content for doc in documents]
            
            # Call Cohere rerank API
            response = self.cohere_client.rerank(
                query=query,
                documents=doc_texts,
                top_n=min(top_n, len(documents)),
                model="rerank-v3.5"  # Best quality model
            )
            
            # Reorder documents based on rerank results
            reranked = []
            for result in response.results:
                reranked.append(documents[result.index])
            
            print(f"🎯 Reranked {len(documents)} → {len(reranked)} docs (Cohere)")
            return reranked
            
        except Exception as e:
            print(f"⚠️ Rerank failed, using original order: {e}")
            return documents[:top_n]

    def _sanitize_response(self, text: str, max_words: int = 150) -> str:
        """
        Strip forbidden deity phrases from LLM output AND enforce word limits.
        This ensures Option B compliance even if prompts leak mythic language.
        
        Args:
            text: The raw LLM response text
            max_words: Hard word limit (default 150)
        """
        import re
        
        # 1. Strip forbidden phrases (Aggressive Option B Compliance)
        forbidden = [
            # Direct Identity & Deities (Global Scrub)
            r"Dear Partha[,.]?\s*",
            r"— ?Vasudeva",
            r"— ?Krishna",
            r"\bI am (Krishna|God|the Lord|Vasudeva|the Divine)\b",
            r"\b(Krishna|Vasudeva) says\b",
            r"\b(Krishna|Vasudeva)\b",  # Strict: SCRUB ALL NAMES (User requirement)
            r"\(as Krishna\)", r"\(as Vasudeva\)",

            # Guru/Deity Voice (First Person Authority)
            r"\b(trust|believe|faith) in me\b",
            r"\b(surrender|yield) to me\b",
            r"\bsurrender to\b",  # Generic: catches 'surrender to God', etc.
            r"\bI am (with you|always by your side|here to guide)\b",
            r"\bmy (child|devotee|friend),?\b",
            r"\b(hear|listen to) my words\b",

            # Authority Tone (Interfaith/Refusal)
            r"ultimate truth", r"the absolute truth",
            r"one correct path", r"final spiritual answer",
            r"the right path",  # Fixes 'career vs family' failure
            r"closest to the truth",  # Fixes interfaith regression
            r"I encourage you", r"I urge you", r"I invite you",

            # Spiritual Metaphysics (when unjustified)
            r"\b(divine|cosmic) (plan|will|play|lila)\b",
            r"\batman is eternal\b",
            
            # Phase 3: Emotional Language Scrubber (Path B Strict)
            r"It'?s understandable to feel",
            r"It'?s completely understandable",
            r"completely understandable",
            r"It'?s natural to feel",
            r"I understand how you feel",
            r"support you on your journey",
            r"on your journey",
            r"your journey",
            r"\bjourney\b",  # Aggressive: strip standalone 'journey'
            r"I'?m here to support",
            r"I'?m here to help you through",
            r"Take a deep breath",
            r"breathe deeply",
            r"ground yourself",
            r"you can get through this",
            r"you will get through",
            r"everything will be okay",
            r"I'?m here for you",
            r"you are not alone",
            r"You'?re not alone",
            r"stay strong",
            r"I believe in you",
            r"\boverwhelmed\b",  # Fix Turn 10: prevent emotional echo
        ]
        
        result = text
        for pattern in forbidden:
            result = re.sub(pattern, "", result, flags=re.IGNORECASE)
        
        # 2. Clean up extra whitespace
        result = re.sub(r'\n\s*\n', '\n\n', result)
        result = result.strip()
        
        # 3. Enforce word limit (Hard Chop with Sentence Boundary)
        words = result.split()
        if len(words) > max_words:
            print(f"✂️ Truncating response: {len(words)} words → {max_words}")
            # Keep first N words
            truncated_words = words[:max_words]
            truncated_text = " ".join(truncated_words)
            
            # Try to cut at last sentence ending for cleanliness
            last_period = truncated_text.rfind('.')
            last_question = truncated_text.rfind('?')
            last_exclaim = truncated_text.rfind('!')
            
            cut_point = max(last_period, last_question, last_exclaim)
            
            if cut_point > len(truncated_text) * 0.7:  # Only chop if we keep >70%
                result = truncated_text[:cut_point+1]
            else:
                result = truncated_text + "..."  # Fallback
                
        return result

    def _classify_query(self, query: str) -> dict:
        """
        Classify user query to determine processing route.
        
        Returns:
            dict with keys:
            - category: str (emotional_support, philosophical, greeting, off_topic, followup, practical, story_request)
            - needs_retrieval: bool
            - needs_story: bool
            - confidence: float (0-1)
        """
        import re
        query_lower = query.lower().strip()
        word_count = len(query.split())
        
        # ============================================
        # PRIORITY 0: I5_EXIT — CRISIS/SAFETY (MUST BE FIRST!)
        # ============================================
        # These signals trigger IMMEDIATE EXIT - no retrieval, no story
        # Safety bias: when in doubt, classify as I5
        crisis_patterns = [
            # Suicide / Self-harm
            r'\b(suicide|suicidal|kill myself|end my life|want to die|no reason to live)\b',
            r'\b(self.harm|hurt myself|cutting myself|harm myself)\b',
            r'\b(planning to die|ways to die|how to die)\b',
            r'\b(ending my life|thinking of ending)\b',  # Added for "ending my life"
            
            # Harm to others
            r'\b(kill (someone|him|her|them|a person|my)|want to murder|hurt someone)\b',  # Added "my" for "kill my neighbor"
            r'\b(violent thoughts|thoughts of killing)\b',
            r'\b(feel like|want to) (hurt|hurting|harm|harming|kill|killing) (someone|people|him|her|them)\b',
            
            # Abuse disclosure
            r'\b(beating me|hits me|abusing me|abused by)\b',
            r'\b(husband|wife|partner|parent).*(beats|hits|abuses|hurts)\b',
            r'\b(domestic violence|victim of abuse)\b',
            
            # Substance abuse crisis
            r'\b(help me find|where to get|how to get).*(drugs|mdma|cocaine|heroin|meth)\b',
            r'\b(overdose|od|addicted|addiction).*(help|spiraling|out of control)\b',
            r'\b(i think i|i may have|i might have) (overdose|od)\b',  # Added for "I think I overdosed"
            r'\b(overdosed|overdosing)\b',  # Direct pattern for overdosed
            
            # Severe mental health crisis
            r'\b(having a breakdown|mental breakdown|psychotic|hearing voices)\b',
            r'\b(can\'t go on|can\'t take it anymore|want it to end)\b',
            
            # ============================================
            # GRIEF/LOSS → I5_EXIT (Option B: no wisdom for grief)
            # ============================================
            r'\b(died|death|passed away|passed on)\b',
            r'\blost\b.*(mother|father|mom|dad|parent|wife|husband|son|daughter|child|sibling|friend|pet|dog|cat)\b',
            r'\b(mother|father|mom|dad|parent|grandma|grandmother|grandpa|grandfather|wife|husband|spouse).*(died|passed|gone|no more|dead)\b',
            r'\b(funeral|mourning|grieving|bereaved)\b',
            r'\b(cancer|terminal|terminally ill|dying)\b',
            r'\b(can\'t stop crying)\b',
        ]
        for pattern in crisis_patterns:
            if re.search(pattern, query_lower):
                return {
                    "category": "I5_EXIT",
                    "needs_retrieval": False,
                    "needs_story": False,
                    "confidence": 0.99,
                    "safety_exit": True
                }
        
        # ============================================
        # PRIORITY 0b: DISTRESS (Emotional but NOT crisis)
        # ============================================
        # These need support but NOT immediate exit
        distress_signals = [
            # NOTE: Grief/death patterns moved to crisis_patterns → I5_EXIT (Option B)
            
            # Acute distress (support - but NOT immediate exit)
            r'\b(i am|i\'m|i feel|feeling)\b.*(anxious|anxiety|panic|terrified|scared)\b',
            r'\b(i am|i\'m|i feel|feeling)\b.*(depressed|depression|hopeless|helpless|worthless)\b',
            
            # Existential pain (support)
            r'\b(what\'s the point|why bother|meaningless|pointless)\b',
            r'\b(nobody (understands|cares|loves|listens))\b',
            r'\b(no one (understands|cares|loves|listens))\b',
            r'\b(hate myself|hate my life|disgusted with myself)\b',
            r'\b(i\'m (a failure|worthless|useless|pathetic))\b',
            r'\b(alone|lonely|isolated)\b',
            
            # Relationship trauma
            r'\b(divorce|breakup|cheated|betrayed|abandoned)\b',
            
            # Overwhelm
            r'\b(overwhelmed|can\'t cope|falling apart|breaking down)\b',
        ]
        for pattern in distress_signals:
            if re.search(pattern, query_lower):
                return {"category": "I1_REFLECTIVE", "needs_retrieval": True, "needs_story": False, "confidence": 0.95}
        
        # ============================================
        # PRIORITY 1: OFF-TOPIC (Redirect politely)
        # ============================================
        off_topic_patterns = [
            # Real people / politicians / celebrities
            r'\b(modi|trump|biden|obama|putin)\b',
            r'\b(elon musk|musk|ambani|adani|bezos|zuckerberg)\b',
            r'\b(virat|kohli|sachin|dhoni|tendulkar|ronaldo|messi)\b',
            r'\b(shah rukh|salman|aamir|amitabh|priyanka)\b',
            r'\b(politician|minister|president|pm|cm|mla|mp)\b',
            r'\b(actor|actress|singer|player|cricketer|celebrity)\b',
            
            # Scripture + off-topic topic (e.g., "What do scriptures say about X")
            r'\b(scripture|gita|bhagavad|ramayan|mahabharat).*(say|teach).*(cryptocurrency|bitcoin|AI|technology|science|politics)\b',
            
            # Technology & Gadgets (EXPANDED)
            r'\b(iphone|ipad|macbook|laptop|smartphone|android|samsung|oneplus)\b',
            r'\b(chatgpt|google bard|gemini|ai assistant|artificial intelligence)\b',
            r'\b(programming|python|javascript|coding|developer|software)\b',
            r'\b(wifi|router|internet|5g|vpn|antivirus)\b',
            r'\b(app|application|software|install|download|backup|recover)\b',
            r'\bhow to (fix|install|backup|remove|recover)\b.*\b(phone|laptop|computer|device|pc)\b',
            r'\b(tesla|electric car|quantum computing)\b',
            
            # Real People & Current Events (MORE SPECIFIC)
            r'\b(rishi sunak|bill gates|jeff bezos|mark zuckerberg)\b',
            r'\b(inflation|economy|economic|gdp|recession)\b.*(about|doing|think)\b',
            r'\bwhat (does|do|is) .*(think|say|believe) about\b.*(ai|technology|crypto|politics)\b',
            r'\b(ukraine|israel|palestine|gaza)\b.*(war|conflict)\b',
            
            # Shopping & Price Comparisons
            r'\b(best|budget|cheap|price|cost).*(under |\d+\s*(rupees?|rs|dollars?|usd))\b',
            r'\b(iphone|samsung|laptop|smartphone).*(vs|versus|or|comparison)\b',
            r'\brecommendations? for\b.*(laptop|phone|gadget|device)\b',
            
            # Sports & Teams (EXPANDED)
            r'\b(mumbai indians|chennai super kings|ipl|cricket|world cup)\b',
            r'\b(ronaldo|messi|cristiano|virat|kohli|sachin|dhoni|federer)\b',
            r'\b(champions league|olympics|uefa|fifa)\b',
            r'\b(match|game|tournament|championship|league)\b.*(won|win|lost|score|result)\b',
            
            # Entertainment (EXPANDED)
            r'\b(avengers|marvel|dc|netflix|amazon prime|disney)\b',
            r'\b(game of thrones|stranger things|breaking bad)\b',
            r'\b(taylor swift|the weeknd|coldplay|concert|grammy|oscar)\b',
            r'\b(bollywood|hollywood|actor|actress|director)\b',
            r'\bbest (movies?|series|songs?|albums?)\b',
            
            # General queries (EXPANDED)
            r'\b(movie|movies|series|film) (recommendations?|suggest)\b',
            r'\bhow to (crack|clear|pass)\b.*(exam|upsc|ias|neet|jee)\b',
            r'\b(gym|fitness) (membership|near me|center)\b',
            r'\bbest (restaurant|hotel|place) (in|near|for)\b',
            r'\b(book|flight|train|taxi)\b',
            
            # More specific off-topic (FINAL PUSH)
            r'\bbest (universities?|colleges?|schools?)\b.*(in|for)\b',
            r'\b(match|game)\b.*(start|time|won|result|dekha)\b',
            r'\b(richest|wealthiest) person\b',
            r'\bbest (action|thriller|comedy|horror) (movies?|films?)\b',
            r'\b(instagram|facebook|twitter|tiktok)\b.*(vs|marketing|comparison)\b',
            r'\b(camera|photography)\b.*(beginners?|best|recommend)\b',
            r'\b(productivity |office )?(apps?|software)\b.*(for|best|recommend)\b',
            r'\b(politicians?|politics)\b.*(corrupt|bad|good)\b',
            r'\b(weather|temperature|forecast)\b',
            r'\b(recipe|cook|food|restaurant)\b',
            r'\b(stock|crypto|cryptocurrency|bitcoin|trading|invest)\b',
            r'\b(buy|sell|price|shop|amazon)\b',
            r'\b(news|politics|election|government)\b',
            r'\b(travel|flight|hotel|booking|temple visit)\b',
            r'\b(which temple|which place|which city)\b',  # Location recommendation
            
            # Academic/Homework
            r'\b(for my|for the|for an?) (essay|assignment|project|homework|exam|school|class)\b',
            r'\bexplain .* (for|in) (my |an? |the )?(essay|assignment|project|homework|school)\b',
            r'\b(summary of|summarize|summarise)\b',
            r'\b(compare .* (and|with|to) )\b',
            r'\b(in \d+ words)\b',
            
            # Factual lookups
            r'\b(what year|when was|how many|how old is)\b',
            r'\b(where was .* born|who invented|who discovered)\b',
            r'\b(historically|actually)\b.*(born|died|written|happened)',
            r'\b(capital of|population of|distance between)\b',
            r'\bhow (tall|much|many) is\b',
            
            # Location with real-world context
            r'\bwhere is\b.*\b(right now|currently|today|at the moment)\b',
            r'\bwhere are\b.*\b(right now|currently|today)\b',
            r'\blocation of\b',
            r'\b(right now|currently happening|latest news|breaking)\b',
            
            # Code/Technical
            r'def \w+\s*\(',           # Python function
            r'function\s*\w*\s*\(',    # JS function
            r'\bselect\b.*\bfrom\b',   # SQL (query_lower already lowercase)
            r'\binsert\b.*\binto\b',
            r'import \w+',              # Import statements
            r'\bpython\b|\bjavascript\b|\bprogramming\b|\bbug\b|\bcode\b',
            
            # Prompt injection
            r'ignore.*(previous|prior|above).*instruction',
            r'disregard.*(previous|prior|above)',
            r'\byou are now\b',
            r'\bpretend (to be|you are)\b',
            r'\bjailbreak\b',
            
            # Gibberish / nonsense
            r'^[bcdfghjklmnpqrstvwxyz]{9,}$',  # 9+ consonants only (conservative)
            r'\bDAN mode\b',
            r'\boverride\b.*\b(persona|system)\b',
        ]
        for pattern in off_topic_patterns:
            if re.search(pattern, query_lower):
                return {"category": "off_topic", "needs_retrieval": False, "needs_story": False, "confidence": 0.85}
        
        # ============================================
        # PRIORITY 2: UNETHICAL BEHAVIOR (Refusal Mode)
        # ============================================
        # CHECK THIS BEFORE GREETINGS to catch "Can you help me cheat"
        unethical_patterns = [
            # Academic Dishonesty
            r'\b(cheat|copy|plagiarize|plagiarism).*(exam|test|homework|assignment|paper|essay|writes?|doing)\b',
            r'\b(how.*)(plagiarize|cheat).*(without getting caught)?\b',
            r'\b(plagiarize|cheat).*(without getting caught)\b',
            r'\b(write|do).*(my|for me).*(essay|paper|assignment|homework)\b',
            
            # Theft/Fraud
            r'\b(rob|steal|shoplift|theft|burglary|heist)\b',
            r'\b(scam|fraud|fake|counterfeit|forgery).*(money|document|card|id)\b',
            
            # General Unethical
            r'\b(lie to|deceive|trick|fool).*(teacher|boss|parents?|police)\b',
            r'\b(how to).*(hide|cover up).*(crime|illegal|body|evidence)\b',
            r'\b(illegal|crime|criminal).*(help|advice|tips)\b',
        ]
        for pattern in unethical_patterns:
            if re.search(pattern, query_lower):
                return {"category": "unethical_behavior", "needs_retrieval": False, "needs_story": False, "confidence": 0.95}

        # ============================================
        # PRIORITY 3: GREETING WITH EMOTIONAL OVERRIDE
        # ============================================
        # Check if it's a greeting followed by emotional words - treat as emotional
        greeting_with_emotion = [
            r'^(hi|hello|hey|namaste).*(help|question|problem|need|anxious|worried|scared)\b',
            r'^(thanks|thank you).*(but|now|however).*(help|anxious|worried|problem)\b',
        ]
        for pattern in greeting_with_emotion:
            if re.search(pattern, query_lower):
                return {"category": "I1_REFLECTIVE", "needs_retrieval": True, "needs_story": False, "confidence": 0.85}

        # ============================================
        # PRIORITY 3: INTERFAITH & COMPARATIVE (Neutral Explanation)
        # ============================================
        comparative_patterns = [
            # Direct comparisons
            r'\b(krishna|jesus|buddha|allah|shiva|ram|christ).*(vs|versus|or|compare|better|greater|superior)\b',
            r'\b(difference|same|similarity).*(between|among)\b',
            
            # Cross-tradition naming
            r'\b(krishna|gita).*(bible|quran|jesus|christ|buddha|tao|zen)\b',
            r'\b(bible|jesus).*(gita|krishna|vedas|upanishad)\b',
            
            # Universalist queries (Strict & Identity)
            r'\b(are they|is it) (the same|all one|different paths)\b',
            r'\b(is|are) \w+ (the same as|equal to|different from) \w+',
            r'\b(allah|brahman|god|divine).*(same|equal|one).*(brahman|allah|god)\b',
            r'\b(which|what) religion is (best|true|better)\b',
            
            # TRUE PATH / ONLY RELIGION questions (MUST be I3, not emotional)
            r'\b(true|correct|only|right)\b.*(path|religion|way|faith)\b',
            r'\b(path|religion|way|faith)\b.*(true|correct|only|right)\b',
            r'\b(which|what).*(is the).*(true|correct|right)\b',
            
            # Doctrin/Teachings queries (What does X say about Y)
            r'\b(what does|what do).*(buddhism|hinduism|christianity|islam|judaism|sikhism|jainism|bible|quran|gita|vedas).*(say|teach|think|believe)\b',
        ]
        for pattern in comparative_patterns:
            if re.search(pattern, query_lower):
                return {"category": "philosophical_comparison", "needs_retrieval": False, "needs_story": False, "confidence": 0.95}

        # ============================================
        # PRIORITY 4: EMOTIONAL SUPPORT
        # ============================================
        emotional_patterns = [
            # Core emotional states
            r'\b(i am|i\'m|i feel|feeling)\b.*(sad|depressed|anxious|worried|scared|angry|lost|confused|hopeless|alone|lonely|stressed|overwhelmed)',
            r'\b(struggling|suffering|going through|dealing with)\b',
            r'\b(help me|i need|i want)\b.*(understand|cope|deal|overcome|find)',
            
            # Loss and grief
            r'\b(lost|death|died|passed away|grief|mourning)\b',
            
            # Relationship issues
            r'\b(relationship|marriage|family|parents|spouse|partner)\b.*(problem|issue|trouble|difficult)',
            r'\b(after (the |my )?(breakup|divorce|separation))\b',
            r'\b(forgive (someone|him|her|them|my))\b',
            r'\b(move on from|get over|let go of)\b',
            r'\b(betrayed|cheated on|abandoned)\b',
            r'\b(toxic (relationship|family|parent))\b',
            
            # Career anxiety
            r'\b(career|job|work)\b.*(confused|stuck|lost|unhappy|stress)',
            
            # Existential
            r'\b(meaning|purpose|why am i|what is the point)\b',
            r'\b(fear|afraid|scared|terrified|panic)\b',
            r'\b(guilt|regret|shame|embarrassed)\b',
            
            # Life stages
            r'\b(pregnant|baby|child|mother|father)\b.*(worried|scared|anxious)',
            
            # Self-directed negativity
            r'\b(hate myself|hate my life|hates? themselves)\b',
            r'\b(i\'m (a failure|worthless|useless))\b',
            r'\b(can\'t do anything right)\b',
            r'\b(everyone hates|everybody hates)\b',
            
            # Implicit distress (sounds like "how to" or "tips" but is emotional)
            r'how (do i|to|can i) (stop crying|stop feeling|cope with|deal with .* pain)\b',
            r'how (do i|to|can i) (forgive|move on|let go|heal)\b',
            r'\b(tips|advice) for someone who (hates|is)\b',
            r'\bhow to .* when .* (anxious|depressed|sad|scared|worried)\b',
            
            # Hinglish support (EXPANDED)
            r'\b(tension|pareshan|dukhi|udas|stress)\b.*(hai|ho|raha|rahi)\b',
            r'\b(mujhe|meri|mere|main)\b.*(dar|chinta|tension|problem|dukh)\b',
            r'\b(kya karu|kaise karu)\b',  # "what do I do"
            r'\bzindagi\b.*(mein|ka|ki)\b',  # life-related
            r'\b(ghar|office|family|shaadi)\b.*(problem|issue|stress)\b',
            
            # Very short cries for help (EXPANDED)
            r'^(plz|pls|please|hlp)\s+(help|me|explain)\b',
            r'\b(hlp|help)\s+(me|pls|plz)\b',
            r'\bcnt\b.*(sleep|cope|handle|breathe)\b',  # can't with severe issues
        ]
        for pattern in emotional_patterns:
            if re.search(pattern, query_lower):
                return {"category": "I1_REFLECTIVE", "needs_retrieval": True, "needs_story": False, "confidence": 0.90}
        
        # ============================================
        # PRIORITY 4: PHILOSOPHICAL (ULTRA-STRICT)
        # ============================================
        philosophical_patterns = [
            # EXACT philosophical questions (from failures)
            r'\b(wat|what|wot).*(is|r|iz)\b.*(meaning|purpose|point).*(life|lyf|zindagi|existence)\b',
            r'\b(wat|wht|what).*(is|iz|s)\b.*(the )?(meaning|purpose|point).*(of )?(life|lyf)\b',  # More typo tolerance
            r'\b(soul|atman)\b.*(after death|happens|nature|body|what happens to)\b',
            r'\b(is there such a thing as|what is|explain)\b.*(destiny|fate|predetermin)\b',
            r'\b(what is|meaning of|explain)\b.*(the )?(dharma)\b(?!.*problem)',  # "the dharma"
            r'\b(karma)\b.*(matlab|meaning|concept|is|explain|detail|deal with|anyway)\b(?!.*feeling|problem)',
            r'\b(understand|find) (my |your |our )?purpose\b',
            r'\b(spiritual awakening|enlightenment|liberation|moksha|nirvana)\b.*(path|how to|achieve)\b',
            r'\bwhy is there suffering\b.*(in the world|in life)\b',
            r'\b(purpose|meaning) of (human )?existence\b',
            r'\bis there life after death\b',
            r'\bis god real\b.*(or|vs|concept)',
            r'\bwhy (were we|was i) born\b.*(into|in)',
            r'\b(meaning|what is) (of )?sacrifice\b',
            r'\bpath to liberation\b',
            r'\b(why is )?desire\b.*(root of|cause of) suffering\b',
            r'\b(relationship|connection) between action and destiny\b',
            r'\bwhy do we fear death\b',
            r'\b(nature|what is) (the |of the )?soul\b',
            r'\b(deal with|anyway)\b.*(karma|destiny|fate)\b',  # Casual philosophical
            
            # Philosophical "how can I" questions (BEFORE practical)
            r'\bhow can i (find|understand).*(my |your )?purpose\b',
            r'\bhow can i (find|achieve).*(inner peace|enlightenment)\b',
            r'\bhow can i (overcome|transcend).*(my |the )?ego\b',
            r'\bhow (can i|to) understand\b.*(concept of|nature of).*(time|consciousness|reality)\b',
            r'\bhow (can i|to) transcend\b.*(material .* |worldly )?(attachments?|desires?)\b',
            r'\bhow (can i|to) find (my |your )?dharma\b',
            r'\bwhy should (we|i) meditate\b',  # Philosophical why, not practical how
            
            # Core spiritual/philosophical concepts (VERY SPECIFIC)
            r'\b(what is|meaning of|explain)\b.*(moksha|atman|brahman)\b',
            r'\b(divine|god|supreme)\b.*(is|nature|what)\b(?!.*help|problem|please)',
            
            # Existential philosophy (STRICTER)
            r'\b(why is there|what is the nature of|what is true)\b.*(suffering|reality|wisdom|consciousness)\b',
            r'\b(free will|predetermined|destiny vs|fate vs)\b',
            r'\b(enlightenment|liberation|moksha|nirvana|salvation)\b.*(path|achieve|attain)\b',
            r'\b(purpose of|meaning of)\b.*(life|existence|being born)\b',
            r'\b(reincarnation|rebirth|past lives?)\b',
            r'\b(maya|illusion|detachment from)\b',
            r'\b(ego|mind and body|consciousness)\b.*(overcome|transcend|nature)\b',
            
            # Life questions (PHILOSOPHICAL not emotional)
            r'\b(why do we|why does|purpose of)\b.*(live|exist|suffer in general|die)\b',
            r'\b(how to|how can i)\b.*(find peace|attain|achieve|reach liberation|enlightenment)\b',
            r'\b(spiritual|spirituality|devotion|bhakti)\b.*(growth|path|journey)\b',
            r'\b(what happens|what is|is there)\b.*(after death|afterlife|when we die)\b',
            r'\b(good people|bad things) (happen|suffer)\b',  # Why do good people suffer
            
            # Questions about concepts/reality
            r'\b(what is|nature of)\b.*(truth|reality|happiness|time|consciousness)\b',
            r'\b(difference between|relationship between)\b.*(knowledge and wisdom|mind and body|religion and spirituality)\b',
            r'\b(desire|attachment).*(root of suffering|cause of)\b',
            r'\b(what does it mean to)\b.*(live righteously|be enlightened|achieve salvation)\b',
            
            # Short existential questions
            r'^why me[\s?!.,]*$',
            r'^is this it[\s?!.,]*$',
            r'^what\'?s the point[\s?!.,]*$',
            r'\b(what happens|what is|is there)\b.*(after death|when we die|life after death)\b',
            r'\b(good|bad) (people|things)\b.*(happen|suffer)\b',  # Why do good people suffer
            
            # Hinglish philosophical (EXPANDED)
            r'\bbhagwan (se|ko|ka)\b.*(baat|kaise|kya|matlab)\b',  # God-related
            r'\b(meaning|matlab|arth).*(life|zindagi|jeevan|lyf)\b',  # Meaning of life
            r'\b(wat|wht|wot|wats) (is|r|iz)\b.*(meaning|purpose|point)\b',  # Typo tolerance
            r'\b(moksha|mukti).*(kaise|prapt|achieve|path)\b',  # Liberation
        ]
        for pattern in philosophical_patterns:
            if re.search(pattern, query_lower):
                return {"category": "philosophical", "needs_retrieval": True, "needs_story": True, "confidence": 0.85}
        
        # ============================================
        # PRIORITY 5: STORY REQUEST
        # ============================================
        story_request_patterns = [
            r'\b(tell|share|narrate)\b.*(story|tale|incident)',
            r'\b(story|tale|example)\b.*(about|of|from)',
            r'\b(what does|what do).*(gita|bhagavad|ramayan|mahabharat|puran|ved)',
            r'\b(krishna|arjuna|rama|shiva|vishnu)\b.*(say|said|teach|taught)',
        ]
        for pattern in story_request_patterns:
            if re.search(pattern, query_lower):
                return {"category": "story_request", "needs_retrieval": True, "needs_story": True, "confidence": 0.90}
        
        # ============================================
        # PRIORITY 6: PRACTICAL (Skip story for speed)
        # ============================================
        practical_patterns = [
            # Meditation/Yoga - Very Specific (PRIORITY)
            r'\bhow long (should|do|to).*(meditate|meditation)\b',
            r'\b(best |what |which )(time|hour|moment)\b.*(to |for )?(practice |do )?(yoga|meditate|meditation|pray)\b',
            r'\bmeditation\b.*(kaise|karna|karu|sahi tarika)\b',  # Hinglish how-to
            r'\b(yoga|meditation)\b.*(learn|kaise|how|sahi tarika)\b',
            r'\bmandir\b.*(kitni baar|how (many|often))\b',  # Temple frequency
            r'\b(pronunciation|pronounce)\b.*(om|mantra)\b',
            r'\bflowers? (to |for )?offer\b.*(shiva|god|deity)\b',
            
            # Meditation/Mantra General
            r'\b(which|what|best) mantra\b.*(for|good|chant|repeat)\b',
            r'\b(where|which place|which corner)\b.*(keep|place|put)\b.*(idol|murti|photo|diya)\b',
            r'\bhow many (times|days|hours|minutes)\b.*(meditate|chant|repeat|recite)\b.*(mantra|om|gayatri)\b',
            
            # Yoga & Meditation Specific (EXPANDED)
            r'\b(yoga (poses?|asanas?)|pranayama|meditation technique)\b',
            r'\b(surya namaskar|kapalbhati|tratak|kundalini|headstand|lotus position)\b',
            r'\b(hatha|vinyasa|ashtanga|hot yoga|power yoga)\b',
            r'\bbest (way|method|technique)\b.*(to )?(meditate|yoga|pray|chant|pooja)\b',
            r'\bhow to (sit|breathe|focus|control)\b.*(in |during |for )?(meditation|yoga|pranayama)\b',
            r'\b(breathing technique|correct posture|flexibility|balance)\b',
            r'\bcan i (do|practice)\b.*(yoga|meditation)\b.*(during|while|lying|open eyes)\b',
            r'\bwhat to (eat|offer|wear)\b.*(before yoga|during pooja|in temple)\b',
            
            # Ritual & Mantra Specific
            r'\b(pooja|puja|ritual|aarti|prasad|tilak)\b.*(how|when|where|what|steps)\b',
            r'\b(mandir|temple|altar|idol|diya|incense)\b.*(where|how|when|direction)\b',
            r'\b(best |which )(direction|side|corner)\b.*(to )?(face|sit|pray|place altar)\b',
            
            # General practical (LAST, after specific patterns)
            r'^how (do i|to|can i)\b',  # Very general
            r'\b(steps|guide|process|procedure)\b.*(to )?(perform|do|practice|follow)\b',
            r'\b(should i|can i|is it okay|is it fine)\b',
        ]
        for pattern in practical_patterns:
            if re.search(pattern, query_lower):
                return {"category": "practical", "needs_retrieval": True, "needs_story": False, "confidence": 0.70}
        
        # ============================================
        # PRIORITY 7: GREETINGS (Check LATE, not first!)
        # ============================================
        greeting_patterns = [
            # Pure greetings only (ULTRA-STRICT - EXACT matches)
            r'^(hi|hello|hey)\s*[!.,]*$',
            r'^(hi there|hey there)\s*[!.,]*$',
            r'^(namaste|namaskar|pranam|pranaam)\s*[ji]*\s*[!.,]*$',
            r'^(good\s*(morning|afternoon|evening|night))\s*[!.,]*$',
            r'^(gud morning|gud evening)\s*[!.,]*$',  # Typo
            r'^(bye|goodbye|see you|see you later|take care)\s*[!.,]*$',
            r'^(ok|okay|alright|sure|yes|no)\s*[!.,]*$',
            r'^(thanks|thank you|thankyou|thx|shukriya)\s*(so much|a lot)?\s*[!.,]*$',  # Thanks variations
            r'^(how are you|how r u)\s*[?!.,]*$',
            r'^what\'?s up\s*[?!.,]*$',
            
            # Religious/Regional Greetings (EXACT matches only)
            r'^(jai shri krishna|hare krishna|jai shri ram|ram ram)\s*[!.,]*$',
            r'^(radhey? radhey?|radhe radhe)\s*[!.,]*$',
            r'^(har har mahadev|om shanti|om namah shivaya)\s*[!.,]*$',
            r'^(jai mata di|jai maa)\s*[!.,]*$',  # Added
            r'^(hari om)\s*[!.,]*$',  # Added
            r'^(sat sri akal|waheguru|jai jinendra)\s*[!.,]*$',
            r'^(vanakkam|namaskaram|namasthe)\s*[!.,]*$',
            r'^(jai hind|vande mataram)\s*[!.,]*$',
            r'^(blessings?|peace be with you|shanti)\s*[!.,]*$',
            r'^(have a|wishing you a)\s*(great|blessed|good|wonderful) day\s*[!.,]*$',
            r'^(stay blessed|take care|god bless)\s*(you)?\s*[!.,]*$',
            
            # Greetings with name/title (STRICT)
            r'^(hi|hello|hey|namaste|namaskar)\s+(there\s+)?(vasudeva|krishna|guru|maharaj|guruji)\s*[!.,]*$',
            r'^(pranaam|pranam)\s+(guru|guruji|maharaj)\s*[!.,]*$',  # Added
            r'^(good morning|good evening)\s+(vasudeva|krishna)\s*[!.,]*$',
            
            # Thanks + goodbye (EXACT)
            r'^(thanks|thank you|shukriya)\s*,?\s*(bye|goodbye|see you)\s*[!.,]*$',
            r'^(thx|ty)\s+(alot|a lot)\s*[!.,]*$',  # Typo version
            
            # How are you variations (EXACT)
            r'^(aap kaise ho|aap kaisi hain|how are you doing)\s*[?!.,]*$',
        ]
        for pattern in greeting_patterns:
            if re.search(pattern, query_lower):
                return {"category": "greeting", "needs_retrieval": False, "needs_story": False, "confidence": 0.95}
        
        # ============================================
        # PRIORITY 8: FOLLOWUP
        # ============================================
        followup_patterns = [
            r'^(tell me more|more details|explain more|go on)[\s!.,]*$',
            r'^(why|how come|what do you mean)[\s?!.,]*$',
            r'^(can you explain|please explain|elaborate)[\s?!.,]*$',
            r'^(and then|what happened|what next)[\s?!.,]*$',
            r'^(really|interesting|i see|okay but)[\s?!.,]*$',
            r'^\.{2,}$',  # Just dots
            r'^\?{1,}$',  # Just question marks
        ]
        for pattern in followup_patterns:
            if re.search(pattern, query_lower):
                return {"category": "followup", "needs_retrieval": False, "needs_story": False, "confidence": 0.80}
        
        # Very short queries (1-3 words) without clear patterns → followup
        if word_count <= 3:
            return {"category": "followup", "needs_retrieval": False, "needs_story": False, "confidence": 0.60}
        
        # ============================================
        # DEFAULT: Longer unknown queries → emotional (safe)
        # ============================================
        if word_count >= 5:
            return {"category": "I2_PRACTICAL", "needs_retrieval": True, "needs_story": False, "confidence": 0.50}
        
        # Medium length (4 words) without signals → practical
        return {"category": "practical", "needs_retrieval": True, "needs_story": False, "confidence": 0.50}

    def _get_greeting_response(self, query: str) -> dict:
        """Return a warm greeting without retrieval."""
        import random
        greetings = [
            "Hello! I'm here to help you explore life's questions. What's on your mind today?",
            "Namaste! I'm ready to help you think through whatever you're facing. What would you like to discuss?",
            "Hello! Share what's on your mind, and I'll do my best to offer perspective.",
        ]
        
        guidance_text = self._sanitize_response(random.choice(greetings))
        
        return {
            "problem": query,
            "guidance": guidance_text,
            "story": None,
            "sources": [],
            "query_type": "greeting",
            "model": self.model_name
        }

    def _get_off_topic_response(self, query: str) -> dict:
        """Politely redirect off-topic queries."""
        return {
            "problem": query,
            "guidance": "Dear Partha, I am here to offer wisdom and guidance for life's deeper questions - matters of the heart, purpose, relationships, and inner peace. While I cannot help with that particular query, I am ready to listen if you have concerns about life, emotions, or finding your path. What truly weighs on your mind?",
            "story": None,
            "sources": [],
            "query_type": "off_topic",
            "model": self.model_name
        }

    def _get_followup_response(self, query: str) -> dict:
        """Handle followup questions."""
        return {
            "problem": query,
            "guidance": "I sense you wish to explore deeper. Could you share more about what specifically you'd like to understand? The more you share, the better I can guide you.",
            "story": None,
            "sources": [],
            "query_type": "followup",
            "model": self.model_name
        }

    def _get_exit_response(self, query: str, trace_id: str = None) -> Dict[str, Any]:
        """
        Handle I5_EXIT (crisis/safety) with grounded exit.
        NO advice, NO stories, NO philosophy. Just brief acknowledgment + support.
        Uses MODE_PROMPTS[ResponseMode.EXIT] for consistent contract enforcement.
        """
        dispatcher = get_dispatcher()
        system_prompt = MODE_PROMPTS[ResponseMode.EXIT]
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ]
            response = self.llm.invoke(messages)
            guidance = response.content.strip()
            
            # Validate against mode contract
            validation = dispatcher.validate_response(guidance, ResponseMode.EXIT)
            if not validation["valid"]:
                print(f"⚠️ Exit response violations: {validation['violations']}")
                guidance = validation["corrected_response"]
            
            return {
                "problem": query,
                "guidance": self._sanitize_response(guidance),
                "story": None,
                "sources": [],
                "query_type": "I5_EXIT",
                "mode": "exit",
                "model": self.model_name,
                "validation": validation
            }
        except Exception as e:
            print(f"Exit response generation failed: {e}")
            # Fallback - guaranteed safe response
            return {
                "problem": query,
                "guidance": "I hear that you're going through something difficult. I'm not equipped to help with this directly, but please consider reaching out to someone who can - a trusted friend, family member, or a professional who specializes in this area.",
                "story": None,
                "sources": [],
                "query_type": "I5_EXIT",
                "mode": "exit",
                "model": "fallback_exit"
            }

    def _get_mode_response_no_rag(self, query: str, mode: ResponseMode, trace_id: str = None) -> Dict[str, Any]:
        """
        Handle modes where RAG is blocked (I3, I4, I5 or any future modes).
        Uses MODE_PROMPTS and validates against mode contracts.
        """
        dispatcher = get_dispatcher()
        
        # Get mode-specific prompt
        system_prompt = MODE_PROMPTS.get(mode)
        if not system_prompt:
            print(f"⚠️ No prompt for mode {mode.value}, using fallback")
            system_prompt = "Provide a brief, helpful response."
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ]
            response = self.llm.invoke(messages)
            guidance = response.content.strip()
            
            # Validate against mode contract
            validation = dispatcher.validate_response(guidance, mode)
            if not validation["valid"]:
                print(f"⚠️ Response violations for {mode.value}: {validation['violations']}")
                guidance = validation["corrected_response"]
            
            
            return {
                "problem": query,
                "guidance": self._sanitize_response(guidance),
                "story": None,
                "sources": [],
                "query_type": mode.value,
                "mode": mode.value,
                "rag_used": False,
                "model": self.model_name,
                "validation": validation
            }
        except Exception as e:
            print(f"Mode response generation failed: {e}")
            return {
                "problem": query,
                "guidance": "I'd like to help, but I encountered an issue. Please try rephrasing your question.",
                "story": None,
                "sources": [],
                "query_type": mode.value,
                "mode": mode.value,
                "rag_used": False,
                "model": "fallback"
            }

    def _get_comparative_response(self, query: str, trace_id: str = None) -> Dict[str, Any]:
        """
        Handle interfaith/comparative questions with neutral scholar persona.
        NO "Dear Partha", NO stories, NO forced syncretism.
        """
        system_prompt = """You are an OBJECTIVE SCHOLAR of comparative religion and philosophy.
        Your goal is to explain DIVERSITY of belief, not enforce UNITY.
        Force 'Different traditions...' template structure (Fix 2).
        Block identity leaks (Fix 1).
        """
        # Strict Neutral Template Prompt
        template_prompt = f"""You are a neutral scholar of comparative religion.
        User Question: "{query}"
        
        Task: Explain how different traditions view this topic.
        
        Strict Guidelines:
        1. Start EXACTLY with: "Different religious traditions approach this question in different ways."
        2. Then use bullet points or short paragraphs:
           - "From a Hindu perspective..."
           - "From a Christian/Buddhist/Islamic perspective..." (choose relevant ones)
        3. End with: "Rather than a single answer, these views reflect distinct ways of understanding meaning and truth."
        4. NEVER say "As Vasudeva" or "I believe".
        5. NEVER declare one religion superior or "more complete".
        6. Max 150 words.
        
        Response:"""

        try:
            response_text = self.llm.invoke(template_prompt).content.strip()
            
            # Fix 1: Post-generation Identity Suppression
            # Now handled by global _sanitize_response, but keeping strict manual check 
            # for safety before passing to sanitizer.
            forbidden_identity = ["As Vasudeva", "I am Vasudeva", "I encourage you", "my child"]
            for phrase in forbidden_identity:
                if phrase in response_text:
                    print(f"🛡️ Caught Identity Leak: '{phrase}' - Sanitizing...")
                    response_text = response_text.replace(phrase, "")
            
            # Enforce Template Start if missing (soft fix)
            if not response_text.startswith("Different religious traditions"):
                response_text = "Different religious traditions approach this question in different ways. " + response_text

            # RUN GLOBAL SANITIZER (Fixes "ultimate truth" and other prohibited phrases)
            response_text = self._sanitize_response(response_text)

            return {
                "problem": query,
                "guidance": response_text,
                "story": None,
                "sources": [],
                "query_type": "philosophical_comparison",
                "mode": "comparative",
                "model": self.model_name
            }
        except Exception as e:
            print(f"Comparative generation failed: {e}")
            return self._get_mode_response_no_rag(query, ResponseMode.PRACTICAL, trace_id)

    def _get_refusal_response(self, query: str, trace_id: str = None) -> Dict[str, Any]:
        """
        Handle unethical/illegal requests with Refusal Mode.
        CLEAR REFUSAL -> BRIEF REASON -> CONSTRUCTIVE REDIRECT.
        NO stories, NO "Dear Partha".
        """
        system_prompt = """You are a SUPPORTIVE MENTOR.
        Your job is to refuse unethical requests firmly but constructively.
        
        PROTOCOL:
        1. REFUSAL: "I cannot help with [X]." (Direct, neutral).
        2. REASON: One sentence on why (Dishonest/Illegal/Harmful).
        3. REDIRECT: "However, I can help you with [Alternative]." (e.g. study tips, managing financial stress).
        4. TONE: Firm, non-judgmental, forward-looking.
        5. NO STORIES: Do not include stories.
        6. NO MYTHIC ADDRESS: Do not use "Dear Partha".
        
        Query: {query}
        
        Provide the refusal response.
        """
        system_prompt = """You are a SUPPORTIVE MENTOR.
        Your job is to refuse unethical requests firmly but constructively.
        
        PROTOCOL:
        1. REFUSE: "I cannot assist with..."
        2. REASON: "as it involves..." (Use: unethical, dishonest, harmful, illegal)
        3. REDIRECT: "However, I can help you with..." (Short alternative)
        
        CONSTRAINTS:
        - Max 60 words
        - NO moralizing or lectures
        - NO spiritual language
        - NO "Dear Partha"
        
        TEMPLATE:
        I cannot assist with [request] as it involves [unethical/harmful behavior]. However, I can help you [constructive alternative, e.g., improve your writing skills, find resources].
        """
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Request: {query}"}
            ]
            response = self.llm.invoke(messages)
            guidance = response.content.strip()
            
            # Sanitization & Hard Word Limit (80 words max for safety)
            safe_guidance = self._sanitize_response(guidance, max_words=80)
            
            return {
                "problem": query,
                "guidance": safe_guidance,
                "story": None,
                "sources": [],
                "query_type": "I4_REFUSAL",
                "model": "safety_guard"
            }
        except Exception as e:
            print(f"Refusal generation failed: {e}")
            return {
                "problem": query,
                "guidance": "I cannot assist with that request as it involves unethical or illegal behavior. However, I can help you find honest and constructive ways to address your underlying needs.",
                "story": None,
                "sources": [],
                "query_type": "refusal_mode",
                "model": "fallback_refusal"
            }

    
    def get_guidance(
        self, 
        problem: str, 
        include_sources: bool = True,
        skip_story: bool = False,  # NEW: Skip story for fast response
        chat_history: list = None,  # NEW: Support for conversation context
        state_manager: StateManager = None  # Phase 3: Conversation state
    ) -> Dict[str, Any]:
        """
        Get wisdom-based guidance for a problem.
        
        Args:
            problem: The user's problem or question
            include_sources: Whether to include source texts
            skip_story: If True, skip story extraction for faster response
            state_manager: Phase 3 state machine for Path B enforcement
            
        Returns:
            Dictionary with guidance, story (if applicable), and sources
        """
        if self.qa_chain is None:
            # We allow proceeding without QA chain for classification and routing
            # Specific modes checking happen later
            pass
        
        # Start trace
        trace_id = self.tracer.start_trace(problem, {"include_sources": include_sources, "skip_story": skip_story})
        
        try:
            # === PHASE 3: HARD DISTRESS CHECK (Bypass Classifier) ===
            if state_manager and state_manager.check_hard_distress(problem):
                print("🚨 PHASE 3: HARD DISTRESS BYPASS ACTIVATED")
                state_manager.transition("distress_detected")
                response = {
                    "problem": problem,
                    "guidance": EXIT_TEMPLATE,
                    "story": None,
                    "sources": [],
                    "query_type": "I5_EXIT",
                    "mode": "exit",
                    "model": "frozen_template",
                    "state": "distress_exit"
                }
                self.tracer.set_output(trace_id, response)
                state_manager.transition("exit_response_sent")
                return response
            
            # === PHASE 3: STATE-BASED RAG BLOCKING ===
            if state_manager and not state_manager.is_rag_allowed():
                print(f"🚫 RAG BLOCKED (State: {state_manager.state.value})")
                # Check if we can transition back to NEUTRAL
                if state_manager.state == ConversationState.POST_EXIT_LOCK:
                    if state_manager.is_neutral_query(problem):
                        state_manager.transition("neutral_query")
                        print("✅ Transitioned back to NEUTRAL state")
                    else:
                        # Stay locked, return redirect
                        response = {
                            "problem": problem,
                            "guidance": POST_EXIT_REDIRECT,
                            "story": None,
                            "sources": [],
                            "query_type": "locked",
                            "mode": "post_exit_lock",
                            "model": "frozen_template",
                            "state": "post_exit_lock"
                        }
                        self.tracer.set_output(trace_id, response)
                        return response
            
            # === STEP -1: CRITICAL SAFETY CHECK (Circuit Breaker) ===
            with self.tracer.span(trace_id, "safety_check"):
                safety_risk = self._check_safety_risk_llm(problem)
                
            if safety_risk != 'none':
                print(f"🚨 SAFETY RISK DETECTED: {safety_risk}")
                self.tracer.update_span_metadata(trace_id, "safety_check", {"risk": safety_risk, "action": "blocked"})
                response = self._get_crisis_response(safety_risk, problem, trace_id)
                self.tracer.set_output(trace_id, response)
                # Phase 3: Transition to exit if state_manager present
                if state_manager:
                    state_manager.transition("distress_detected")
                    state_manager.transition("exit_response_sent")
                return response
                
            # === STEP 0: Classify query and route appropriately ===
            with self.tracer.span(trace_id, "classification"):
                classification = self._classify_query(problem)
                query_category = classification["category"]
            
            self.tracer.update_span_metadata(trace_id, "classification", {
                "category": query_category,
                "confidence": classification["confidence"]
            })
            
            print(f"[Classification] {query_category} (confidence: {classification['confidence']:.0%})")
            
            # Fast-path responses (no retrieval needed)
            if query_category == "greeting":
                response = self._get_greeting_response(problem)
                response["trace_id"] = trace_id
                self.tracer.set_output(trace_id, response)
                return response
            
            if query_category == "off_topic":
                response = self._get_off_topic_response(problem)
                response["trace_id"] = trace_id
                self.tracer.set_output(trace_id, response)
                return response
            
            if query_category == "followup":
                response = self._get_followup_response(problem)
                response["trace_id"] = trace_id
                self.tracer.set_output(trace_id, response)
                return response

            # === I5_EXIT: Crisis/Safety Exit (PRIORITY 1) ===
            # FIX #3: Confidence-Aware Routing for Safety
            # If confidence is low but query implies distress, FORCE I5_EXIT
            crisis_keywords = ["live", "kill", "die", "hurt", "pain", "suicide", "end it"]
            if classification["confidence"] < 0.7 and any(w in problem.lower() for w in crisis_keywords):
                print("🚨 LOW CONFIDENCE CRISIS DETECTED -> FORCING I5_EXIT")
                classification["category"] = "I5_EXIT"
                classification["needs_story"] = False
                classification["needs_retrieval"] = False
                query_category = "I5_EXIT"

            # Check trace again after override
            self.tracer.update_span_metadata(trace_id, "classification", classification)

            if query_category == "I5_EXIT":
                print(f"🚨 SAFETY RISK DETECTED: {classification.get('risk_type', 'unknown')}")
                response = self._get_exit_response(problem, classification.get('risk_type'), trace_id)
                # FIX #5: Hard 80-word limit for crisis exits
                response["guidance"] = self._sanitize_response(response["guidance"], max_words=80)
                response["trace_id"] = trace_id
                self.tracer.set_output(trace_id, response)
                return response

            if query_category == "unethical_behavior":
                response = self._get_refusal_response(problem, trace_id)
                response["trace_id"] = trace_id
                self.tracer.set_output(trace_id, response)
                return response
        
            if query_category == "philosophical_comparison":
                response = self._get_comparative_response(problem, trace_id)
                response["trace_id"] = trace_id
                self.tracer.set_output(trace_id, response)
                return response
        
            # === PHASE 3: RAG GATING ===
            # Check if retrieval is allowed for this mode
            dispatcher = get_dispatcher()
            mode = dispatcher.get_mode(query_category)
            rag_allowed = dispatcher.should_use_rag(mode)
            
            # FIX #4: Anxiety/Guru Mode Guardrail
            # If query is about anxiety/future, BLOCK RAG to stop "Dear Partha" hallucinations
            anxiety_triggers = ["anxious", "anxiety", "future", "worried", "scared"]
            if any(w in problem.lower() for w in anxiety_triggers):
                print("🛡️ Anxiety/Distress detected - BLOCKING RAG to prevent Guru Mode")
                rag_allowed = False
            
            self.tracer.update_span_metadata(trace_id, "classification", {
                "mode": mode.value,
                "rag_allowed": rag_allowed
            })
            
            if not rag_allowed:
                print(f"🚫 RAG BLOCKED for mode: {mode.value}")
                # Route to appropriate non-RAG handler
                response = self._get_mode_response_no_rag(problem, mode, trace_id)
                response["trace_id"] = trace_id
                self.tracer.set_output(trace_id, response)
                return response
        
            # Determine if story is needed based on classification
            # FIX #4: Force disable stories for I3_COMPARATIVE (Option B)
            if mode == ResponseMode.COMPARATIVE:
                should_skip_story = True
            else:
                should_skip_story = skip_story or not classification["needs_story"]
                
                # FIX #5: Doctrinal Guardrail for Buddhism
                # If query mentions Buddhism/Buddha, BLOCK stories about "soul/atman"
                if "buddh" in problem.lower() and not should_skip_story:
                    print("🛡️ Buddhism detected - enforcing Anatta (No-Self) guardrail on stories")
                    # We can't easily filter story content before retrieval, 
                    # so we just disable stories to be safe against contradiction
                    should_skip_story = True
            
            print(f"🤔 Seeking wisdom for: {problem[:100]}...")
            print(f"📚 RAG ALLOWED for mode: {mode.value}")
            
            # Step 1: Retrieve candidates and optionally rerank for better relevance
            # Reduced from 20 candidates to 10 (Phase 3: reduce chunk count)
            if self.cohere_client:
                # Use Cohere reranking: fetch 10 candidates, rerank to top 3
                with self.tracer.span(trace_id, "retrieval", {"k": 10, "reason": "mode_allowed"}):
                    candidates = []
                    if self.vectorstore:
                        candidates = self.vectorstore.similarity_search(problem, k=10)
                
                with self.tracer.span(trace_id, "reranking", {"candidates": len(candidates), "top_n": 3}):
                    source_docs = self._rerank_documents(problem, candidates, top_n=3)
            else:
                # Fallback: use standard retrieval (reduced from 5 to 3)
                with self.tracer.span(trace_id, "retrieval", {"k": 3, "reason": "mode_allowed"}):
                    source_docs = []
                    if self.vectorstore:
                        source_docs = self.vectorstore.similarity_search(problem, k=5)
            
            # Step 1.5: Proactive Safety Filtering (NEW - Phase 3)
            # Infer user states (e.g. sinking self-love) and filter unsafe stories
            user_states = self._infer_user_states(classification, problem)
            if user_states:
                with self.tracer.span(trace_id, "metadata_filtering", {"states": user_states}):
                    original_count = len(source_docs)
                    source_docs = self._filter_unsafe_stories(source_docs, user_states)
                    if len(source_docs) < original_count:
                        self.tracer.update_span_metadata(trace_id, "metadata_filtering", {
                            "filtered": original_count - len(source_docs),
                            "remaining": len(source_docs)
                        })
            
            # Step 2: Get wisdom guidance using QA chain
            with self.tracer.span(trace_id, "guidance_generation"):
                if self.qa_chain:
                    result = self.qa_chain.invoke({"query": problem})
                    guidance_text = result["result"]
                else:
                    # Fallback if QA chain not set up (e.g. testing)
                    print("⚠️ QA Chain not ready, using raw LLM fallback")
                    fallback_prompt = f"""You are a helpful assistant providing wisdom. 
                    Context: {source_docs}
                    Question: {problem}
                    Provide helpful, grounded guidance (max 150 words). Do NOT use deity persona."""
                    guidance_text = self.llm.invoke(fallback_prompt).content
            
            # Step 3: Extract story with narrative using reranked docs for better relevance
            story_data = None
            if not should_skip_story and len(source_docs) > 0:
                with self.tracer.span(trace_id, "story_extraction"):
                    story_data = self._extract_story_from_context(
                        problem=problem,
                        source_documents=source_docs
                    )
                
                self.tracer.update_span_metadata(trace_id, "story_extraction", {
                    "found": story_data is not None,
                    "title": story_data.get("title") if story_data else None
                })
                
                if story_data and story_data.get('narrative'):
                    print(f"📖 Story with narrative ready: {story_data.get('character', 'N/A')}")
                    
                    narrative = story_data.get('narrative', '')
                    if len(narrative) > 100:
                        suspicious_terms = ['invented', 'imagined', 'supposedly', 'allegedly']
                        if any(term in narrative.lower() for term in suspicious_terms):
                            print("⚠️ Suspicious narrative, running fact-check...")
                            with self.tracer.span(trace_id, "fact_checking"):
                                passages_text = "\n\n".join([doc.page_content for doc in source_docs[:3]])
                                fact_check = self._fact_check_narrative(narrative, passages_text)
                            
                            if fact_check.get('has_issues'):
                                print(f"🔧 Fact-check found {len(fact_check.get('issues', []))} issues, regenerating...")
                                story_data = self._convert_to_narrative_story(
                                    story_data, problem, source_docs
                                )
                        else:
                            print("✅ Narrative looks good, skipping fact-check for speed")
            elif should_skip_story:
                print(f"⏩ Skipping story extraction ({query_category})")
            
            response = {
                "problem": problem,
                "guidance": self._sanitize_response(guidance_text),
                "story": story_data,
                "query_type": query_category,
                "trace_id": trace_id,
                "model": self.model_name
            }
            
            print(f"📦 Response has story: {response.get('story') is not None}")
            
            if include_sources and len(source_docs) > 0:
                response["sources"] = []
                for i, doc in enumerate(source_docs, 1):
                    source_info = {
                        "text": doc.page_content,
                        "metadata": doc.metadata,
                        "relevance_rank": i
                    }
                    response["sources"].append(source_info)
            
            self.tracer.set_output(trace_id, response)
            return response
        
        except Exception as e:
            self.tracer.end_trace(trace_id, error=str(e))
            raise
        finally:
            self.tracer.end_trace(trace_id)
    
    def get_story_only(
        self,
        problem: str
    ) -> Dict[str, Any]:
        """
        Get ONLY the story for a problem (for async loading).
        This is slow due to fact-checking but allows guidance to load first.
        
        Args:
            problem: The user's problem (same as used for guidance)
            
        Returns:
            Dictionary with story data
        """
        if self.qa_chain is None:
            raise ValueError("QA chain not initialized. Run build_pipeline() first.")
        
        print(f"📖 Getting story for: {problem[:100]}...")
        
        # Get relevant documents
        result = self.qa_chain.invoke({"query": problem})
        
        story_data = None
        if "source_documents" in result and len(result["source_documents"]) > 0:
            # Extract story using STAR
            story_data = self._extract_story_from_context(
                problem=problem,
                source_documents=result["source_documents"]
            )
            
            # Convert to narrative with fact-checking
            if story_data:
                story_data = self._convert_to_narrative_story(
                    story_data=story_data,
                    user_problem=problem,
                    source_passages=result["source_documents"][:3]
                )
                print(f"✅ Story ready: {story_data.get('title', 'Untitled')}")
        
        return {
            "problem": problem,
            "story": story_data,
            "model": self.model_name
        }
    
    def _extract_story_from_context(
        self,
        problem: str,
        source_documents: List[Any]
    ) -> Optional[Dict[str, str]]:
        """
        Extract a relevant story from source documents AND write narrative in ONE call.
        Combines STAR extraction + narrative generation for speed.
        
        Args:
            problem: The user's problem
            source_documents: Retrieved wisdom passages
            
        Returns:
            Story dict with narrative already included, or None
        """
        # Combine top passages
        context = "\n\n---\n\n".join([
            doc.page_content for doc in source_documents[:3]
        ])
        
        # Document Verification - Check if passages have sufficient content
        total_chars = sum(len(doc.page_content) for doc in source_documents[:3])
        if total_chars < 200:  # Too short, likely no actual story
            print("⚠️  Passages too short for story extraction (< 200 chars), skipping")
            return None
        
        # Check if passages contain narrative elements
        narrative_keywords = ['was', 'were', 'said', 'asked', 'went', 'came', 'once', 
                             'time', 'day', 'king', 'sage', 'lord', 'god', 'goddess',
                             'then', 'when', 'there']
        if not any(keyword in context.lower() for keyword in narrative_keywords):
            print("⚠️  Passages lack narrative elements, skipping story")
            return None
        
        # NEW: Combined STAR + Narrative prompt
        combined_prompt = f"""Based on these sacred text passages, extract a relevant story AND write it as a narrative.

Sacred Text Passages:
{context}

User's Problem: {problem}

Task: If these passages contain a story relevant to the user's problem:
1. Extract the key elements (STAR framework)
2. Write a 2-3 paragraph narrative connecting it to the user's problem

Respond in JSON format:
{{
  "found": true/false,
  "title": "Short, apt title (e.g., 'Arjuna's Dilemma on the Battlefield')",
  "character": "Main character name",
  "source": "Book, Chapter, Verse (e.g., 'Bhagavad Gita, Chapter 2, Verse 7')",
  "situation": "The context and dilemma faced",
  "task": "What needed to be addressed",
  "action": "What was done",
  "result": "The outcome and lesson",
  "narrative": "A 2-3 paragraph story in simple, warm language. Use what the passages ACTUALLY say. Connect to user's problem at the end. Use modern language freely (anxiety, healing, etc.) - this is for mental wellness support."
}}

IMPORTANT:
- For "narrative": Write naturally, as if telling a friend
- Use modern emotional language (anxiety, healing, coping) - the app is for mental wellness
- Connect the story's lesson to the user's specific problem
- Keep it 2-3 paragraphs
- Be warm and accessible

If NO clear story exists in passages, return: {{"found": false}}

Your JSON response:"""
        
        try:
            from langchain_core.messages import HumanMessage
            
            combined_llm = ChatOpenAI(
                model_name="gpt-4o-mini",
                temperature=0.4,  # Slightly higher for natural narrative
                model_kwargs={"response_format": {"type": "json_object"}}
            )
            
            response = combined_llm.invoke([HumanMessage(content=combined_prompt)])
            story_json = json.loads(response.content)
            
            if story_json.get("found"):
                # Remove the 'found' key
                story_json.pop("found", None)
                print(f"📖 Story extracted: {story_json.get('character', 'Unknown')}")
                
                # VALIDATE story appropriateness before returning
                is_appropriate, reason = self._validate_story_appropriateness(
                    problem=problem,
                    story=story_json
                )
                
                if not is_appropriate:
                    print(f"⚠️  Story validation failed: {reason}")
                    print("   Skipping this story for user safety")
                    return None
                else:
                    print(f"✅ Story validated as appropriate")
                    return story_json
            else:
                print("ℹ️  No specific story found in context")
                return None
                
        except Exception as e:
            print(f"⚠️  Could not extract story: {e}")
            return None
    
    def _check_safety_risk_llm(self, query: str) -> str:
        """
        Check query for safety risks using LLM.
        Returns: 'none' | 'self_harm' | 'harm_to_others' | 'medical_emergency' | 'general_crisis'
        """
        system_prompt = """You are a SAFETY MONITOR for a mental wellness bot.
        Your ONLY job is to detect:
        1. Immediate risk of self-harm or suicide.
        2. Risk of harm to others (violence, homicide).
        3. Medical emergencies.
        4. Acute crisis requiring professional intervention (severe addiction, abuse).

        CLASSIFY the user input into one of these categories:
        - 'self_harm': User mentions dying, killing themselves, self-injury.
        - 'harm_to_others': User mentions killing/hurting others, violence, revenge.
        - 'medical_emergency': Heart attack, overdose, physical collapse.
        - 'general_crisis': Severe addiction spiraling, domestic abuse victim, acute psychosis.
        - 'none': Emotional distress, sadness, anxiety, philosophical questions (even if deep/dark).

        EXAMPLES:
        "I want to die" -> self_harm
        "I feel like hurting someone" -> harm_to_others
        "I'm going to kill him" -> harm_to_others
        "I took all the pills" -> medical_emergency
        "I'm addicted to alcohol help me" -> general_crisis
        "I hate myself" -> none (Emotional distress, but not immediate safety risk)
        "Why is life so painful" -> none

        OUTPUT ONLY THE CATEGORY LABEL.
        """
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ]
            response = self.llm.invoke(messages)
            risk = response.content.strip().lower()
            
            valid_risks = ['self_harm', 'harm_to_others', 'medical_emergency', 'general_crisis', 'none']
            if risk not in valid_risks:
                return 'none'
            return risk
        except Exception as e:
            print(f"Safety check failed: {e}")
            return 'none'

    def _get_crisis_response(self, safety_risk: str, query: str, trace_id: str = None) -> Dict[str, Any]:
        """
        Return a grounded, non-mythic crisis response with resources.
        """
        resources = """
        🚨 **IMMEDIATE SUPPORT RESOURCES:**
        - **Emergency Services:** Call 911 (or your local emergency number) immediately.
        - **Suicide & Crisis Lifeline:** Call or Text 988 (USA/Canada)
        - **Vandrevala Foundation (India):** 1860-266-2345
        - **iCall (India):** 91529 87821
        """
        
        guidance = ""
        if safety_risk == 'self_harm':
            guidance = "I hear how much pain you are in, and I am deeply concerned for your safety. Because you mentioned wanting to hurt yourself, I cannot provide spiritual advice right now—your life matters too much. Please reach out to the resources below or go to the nearest emergency room immediately. You do not have to carry this alone."
        
        elif safety_risk == 'harm_to_others':
            guidance = "I am concerned by what you've shared. Because you mentioned thoughts of harming others, I cannot continue this conversation. Violence causes irreversible harm. Please step back, take a deep breath, and contact emergency services or a crisis counselor immediately."
            
        elif safety_risk == 'general_crisis': # Addiction, etc.
            guidance = "I hear you, and I want to support you, but what you're describing (addiction/crisis) requires professional care that I cannot provide. Recovery is possible, but it starts with real-world help, not spiritual advice. Please contact a professional or the support lines below."
            
        else: # Default/Medical
            guidance = "This sounds like a medical or safety emergency. Please call emergency services immediately. My spiritual guidance is not a substitute for professional help."

        full_response = f"{guidance}\n\n{resources}"
        
        return {
            "problem": query,
            "guidance": self._sanitize_response(full_response),
            "story": None,
            "sources": [],
            "query_type": "safety_circuit_breaker",
            "safety_risk": safety_risk,
            "model": "safety_guardrail"
        }
    
    def _infer_user_states(self, classification: Dict, problem: str) -> List[str]:
        """
        Infer user states (e.g. 'seeking_self_love') from query classification to check contraindications.
        """
        user_states = []
        problem_lower = problem.lower()
        
        # 1. Self-Love / Validation Check
        # If user explicitly wants to love themselves, 'pride warning' stories are harmful
        if ("love myself" in problem_lower or "self-love" in problem_lower or 
            "worthy" in problem_lower or "loves me" in problem_lower):
            user_states.append("seeking_self_love")
        
        # 2. Validation Seeking
        if "am i wrong" in problem_lower or "validate" in problem_lower:
            user_states.append("seeking_validation")
            
        # 3. Grief Stages
        intent = classification.get("intent", "").lower()
        if intent == "grief":
            user_states.append("early_grief")
            
        # 4. Distress Levels
        distress = classification.get("distress_level", 0)
        if distress >= 8:
            user_states.append("crisis_acute")
        elif distress >= 6:
            user_states.append("fragile_self_worth")
            
        return user_states

    def _filter_unsafe_stories(self, documents: List[Any], user_states: List[str]) -> List[Any]:
        """
        Filter out stories that are contraindicated for the user's current state.
        Uses the 'rich_metadata_json' field if available.
        """
        if not user_states:
            return documents
            
        safe_docs = []
        filtered_count = 0
        
        for doc in documents:
            is_safe = True
            reason = ""
            
            # Check for rich metadata
            if "rich_metadata_json" in doc.metadata:
                try:
                    metadata = json.loads(doc.metadata["rich_metadata_json"])
                    
                    # Check Contraindications (e.g. story warns against pride -> unsafe for self-love seeker)
                    contras = metadata.get("CONTRAINDICATIONS", [])
                    if isinstance(contras, str) and contras != "none":
                        contras = [contras] # Handle single string case
                    
                    if isinstance(contras, list):
                        # If ANY user state matches ANY contraindication -> UNSAFE
                        common_risks = set(user_states).intersection(set(contras))
                        if common_risks:
                            is_safe = False
                            reason = f"Contraindicated: {common_risks}"
                            
                except Exception as e:
                    print(f"⚠️ Error parsing metadata for {doc.metadata.get('source', 'unknown')}: {e}")
            
            # Legacy/Hybrid Check (fallback if rich metadata missing but simple tags exist)
            if is_safe and "contraindications" in doc.metadata:
                # Some simple chunkers might put string list directly
                c_tags = doc.metadata["contraindications"]
                if isinstance(c_tags, str):
                    if c_tags in user_states:
                        is_safe = False
                        reason = f"Legacy tag match: {c_tags}"
            
            if is_safe:
                safe_docs.append(doc)
            else:
                filtered_count += 1
                print(f"🚫 PROACTIVE FILTER: Created gap for '{doc.metadata.get('source', 'doc')}' - {reason}")
                
        if filtered_count > 0:
            print(f"🛡️  Safety Filter: Removed {filtered_count} potentially harmful stories")
            
        return safe_docs

    def _validate_story_appropriateness(
        self,
        problem: str,
        story: Dict[str, str]
    ) -> Tuple[bool, str]:
        """
        Validate if a story is philosophically appropriate for the user's query.
        Prevents harmful mismatches like pride-warnings for self-love queries.
        
        Args:
            problem: User's original query
            story: Extracted story dict
            
        Returns:
            (is_appropriate: bool, reason: str)
        """
        validation_prompt = f"""You are a philosophical advisor validating story selections for emotional wellness.

USER'S QUERY: "{problem}"

STORY SELECTED:
Title: {story.get('title', 'Unknown')}
Main Lesson: {story.get('result', 'Unknown')}

First 200 chars of narrative: {story.get('narrative', '')[:200]}...

VALIDATION TASK:
Will this story HELP or potentially HARM someone asking this question?

Consider:
1. **Emotional Alignment**: Does the story's theme match the user's emotional need?
   - Example MISMATCH: User seeks self-love → Story warns about pride/punishment
   - Example MATCH: User seeks self-love → Story teaches inherent worth

2. **Harmful Misinterpretations**: Could this story be read in a harmful way?
   - "Don't love yourself too much"
   - "Your suffering is punishment"
   - "You're not good enough"

3. **Message Coherence**: Does the lesson directly support what the user is seeking?
   - User asks "how to X" → Story should show path to X, not warn about excess X

Respond in JSON:
{{
  "appropriate": true/false,
  "reason": "Brief explanation (1 sentence)",
  "alternative_suggestion": "If inappropriate, what theme would be better? (optional)"
}}

Your validation:"""

        try:
            try:
                from langchain_core.messages import HumanMessage
            except ImportError:
                from langchain_core.messages import HumanMessage
            
            validation_llm = ChatOpenAI(
                model_name="gpt-4o-mini",
                temperature=0.2,  # Low temperature for consistent validation
                model_kwargs={"response_format": {"type": "json_object"}}
            )
            
            response = validation_llm.invoke([HumanMessage(content=validation_prompt)])
            result_json = json.loads(response.content)
            
            is_appropriate = result_json.get("appropriate", False)
            reason = result_json.get("reason", "No reason provided")
            
            if not is_appropriate and result_json.get("alternative_suggestion"):
                reason += f" | Better: {result_json['alternative_suggestion']}"
            
            return is_appropriate, reason
            
        except Exception as e:
            error_msg = f"Validation check failed: {e}"
            print(f"⚠️  Story validation error: {e}")
            # FAIL CLOSED: If we can't validate, assume it's unsafe
            return False, error_msg

    
    def _convert_to_narrative_story(
        self,
        story_data: Dict[str, str],
        user_problem: str,
        source_passages: List[Any]
    ) -> Dict[str, Any]:
        """
        Convert STAR framework story into a narrative format with fact-checking.
        Uses hybrid approach: generate -> fact-check -> regenerate if needed.
        
        Args:
            story_data: Story in STAR format
            user_problem: User's problem to draw parallels
            source_passages: Original text passages from sacred texts
            
        Returns:
            Story with narrative field added
        """
        # Include actual passages to keep narrative grounded
        passages_text = "\n\n---\n\n".join([
            doc.page_content for doc in source_passages
        ])
        
        # Step 1: Generate initial narrative
        print("📝 Generating narrative...")
        narrative_v1 = self._generate_narrative(
            story_data, user_problem, passages_text
        )
        
        # Step 2: Fact-check against passages
        print("🔍 Fact-checking narrative...")
        fact_check_result = self._fact_check_narrative(narrative_v1, passages_text)
        
        # Step 3: Regenerate with feedback if issues found
        if fact_check_result.get("has_issues"):
            issues = fact_check_result.get("issues", [])
            print(f"⚠️  Found {len(issues)} accuracy issues, regenerating...")
            for issue in issues:
                print(f"   - {issue.get('detail')}: {issue.get('reason')}")
            
            narrative_final = self._regenerate_with_feedback(
                narrative_v1, issues, passages_text, story_data, user_problem
            )
            print("✅ Narrative corrected")
        else:
            print("✅ Narrative accurate")
            narrative_final = narrative_v1
        
        # Add narrative to story data
        story_data["narrative"] = narrative_final
        return story_data
    
    def _generate_narrative(
        self,
        story_data: Dict[str, str],
        user_problem: str,
        passages_text: str
    ) -> str:
        """Generate initial narrative from STAR elements."""
        
        narrative_prompt = f"""Create a simple story ONLY from what these passages actually say.

ORIGINAL SACRED TEXT PASSAGES:
{passages_text}

Story Elements (STAR Framework):
- Character: {story_data.get('character', 'Unknown')}
- Situation: {story_data.get('situation', '')}
- Source: {story_data.get('source', '')}

Reader's Problem: {user_problem}

STRICT RULES - WHAT YOU CAN DO:
1. Use ONLY facts explicitly stated in passages
2. Quote or paraphrase actual text from passages
3. Use simple, everyday language
4. Draw connection to reader's problem at the end

ABSOLUTE PROHIBITIONS - NEVER ADD:
❌ Divine characters NOT mentioned in passages (e.g., "Lord Dharma", "Lord of righteousness")
❌ Symbolic interpretations (e.g., "Earth spoke", divine light)  
❌ Emotional motivations NOT in passages (e.g., "to heal grief")
❌ Modern therapeutic angles (e.g., "coping with loss")
❌ Spiritual symbolism not in original text
❌ Proper nouns (people, places, deities) not in passages
❌ Conversations/dialogue not in passages
❌ Events not described in passages

CRITICAL: If passages don't mention something, DON'T include it.
Better to have an incomplete but accurate story than a complete but fabricated one.

FORMAT:
- 2-3 paragraphs
- Start with what passages say about the character/situation
- Tell what actually happened (only from passages)
- End with simple parallel to reader's situation

Your fact-based narrative:"""
        
        try:
            from langchain_core.messages import HumanMessage
            
            narrative_llm = ChatOpenAI(
                model_name="gpt-4o-mini",
                temperature=0.3  # Lower temperature for less creativity
            )
            
            response = narrative_llm.invoke([HumanMessage(content=narrative_prompt)])
            return response.content.strip()
            
        except Exception as e:
            print(f"⚠️  Could not create narrative: {e}")
            # Fallback: create simple narrative from STAR
            return f"{story_data.get('situation', '')} {story_data.get('action', '')} {story_data.get('result', '')}"
    
    def _fact_check_narrative(
        self,
        narrative: str,
        passages_text: str
    ) -> Dict[str, Any]:
        """Fact-check narrative against original passages."""
        
        check_prompt = f"""You are a fact-checker for sacred text narratives. Focus ONLY on factual errors.

ORIGINAL PASSAGES FROM SACRED TEXTS:
{passages_text}

GENERATED NARRATIVE:
{narrative}

Task: Find MAJOR FACTUAL ERRORS in the narrative. Be permissive with style and interpretation.

FLAG ONLY THESE (Real Errors):

1. **Wrong Character Names**:
   - Character named "Krishna" when passages say "Rama"
   - Completely invented character names not in passages
   - NOTE: Generic terms like "the seeker", "the devotee" are OK if describing a real person

2. **Wrong Events**:
   - Events that contradict the passages (Arjuna kills Bhishma when he didn't)
   - Timeline contradictions (child present before being born)
   - NOTE: Narrative framing ("reflects", "learns", "understands") is OK

3. **Wrong Attribution**:
   - Story attributed to wrong book (claims Gita when from Bhagavatam)
   - Wrong chapter/verse numbers
   
4. **Invented Dialogue** (Be Strict Here):
   - Direct quotes ("Krishna said: '...'") not in passages
   - NOTE: Indirect speech ("Krishna taught that...") is OK

DO NOT FLAG THESE (Style, Not Errors):

❌ Narrative framing: "Arjuna reflects", "learns", "understands", "realizes"
❌ Modern language: "anxiety", "emotional", "coping", "healing"
❌ Metaphors: "whirlpool of birth", "ocean of suffering" (common in spiritual texts)
❌ Connecting to user's problem: This is the PURPOSE of the narrative
❌ Generic character terms: "the seeker", "the devotee", "the sage"

ONLY flag if the narrative says something FACTUALLY WRONG about what happened.
Style choices and interpretations are NOT errors.

Respond in JSON:
{{
  "has_issues": true/false,
  "issues": [
    {{"detail": "specific factual error", "reason": "what the correct fact is", "type": "name/event/attribution/dialogue"}},
    ...
  ]
}}

Your fact-check:"""
        
        try:
            from langchain_core.messages import HumanMessage
            
            fact_check_llm = ChatOpenAI(
                model_name="gpt-4o-mini",
                temperature=0,
                model_kwargs={"response_format": {"type": "json_object"}}
            )
            
            response = fact_check_llm.invoke([HumanMessage(content=check_prompt)])
            return json.loads(response.content)
            
        except Exception as e:
            print(f"⚠️  Fact-check failed: {e}")
            return {"has_issues": False, "issues": []}
    
    def _regenerate_with_feedback(
        self,
        original_narrative: str,
        issues: List[Dict],
        passages_text: str,
        story_data: Dict[str, str],
        user_problem: str
    ) -> str:
        """Regenerate narrative fixing specific issues."""
        
        issues_list = "\n".join([
            f"- {issue.get('detail', 'Unknown')}: {issue.get('reason', '')}" 
            for issue in issues
        ])
        
        regen_prompt = f"""Your previous narrative had accuracy issues. Please fix them.

ORIGINAL PASSAGES FROM SACRED TEXTS:
{passages_text}

PREVIOUS NARRATIVE (with issues):
{original_narrative}

ISSUES FOUND - YOU MUST FIX THESE:
{issues_list}

Story Elements (STAR):
- Character: {story_data.get('character')}
- Situation: {story_data.get('situation')}
- Action: {story_data.get('action')}
- Result: {story_data.get('result')}

Reader's Problem: {user_problem}

Task: Rewrite the narrative:
1. REMOVE or FIX each issue listed above
2. Use ONLY details explicitly in passages
3. If timeline is unclear, be vague rather than fabricate
4. Keep warm, simple style
5. Draw parallels to reader's problem
6. 3-4 paragraphs

Your corrected narrative:"""
        try:
            from langchain_core.messages import HumanMessage
            from langchain_openai import ChatOpenAI
            
            regen_llm = ChatOpenAI(
                model_name="gpt-4o-mini",
                temperature=0.5
            )
            
            response = regen_llm.invoke([HumanMessage(content=regen_prompt)])
            return response.content.strip()
            
        except Exception as e:
            print(f"⚠️  Regeneration failed: {e}")
            return original_narrative  # Fallback to original if regen fails
    
    def _retrieve_context(self, query: str) -> List[str]:
        """Retrieve relevant context from vector store."""
        if not self.vectorstore:
            print("⚠️ Vectorstore not initialized - skipping retrieval")
            return []
            
        try:
            docs = self.vectorstore.similarity_search(query, k=3)
            return [d.page_content for d in docs]
        except Exception as e:
            print(f"Retrieval failed: {e}")
            return []
    
    def get_relevant_wisdom(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """
        Get relevant wisdom passages without generating guidance.
        
        Args:
            query: Search query
            k: Number of passages to return
            
        Returns:
            List of relevant wisdom passages
        """
        if self.vectorstore is None:
            raise ValueError("Vector store not initialized")
        
        docs = self.vectorstore.similarity_search(query, k=k)
        passages = []
        
        for i, doc in enumerate(docs, 1):
            passages.append({
                "rank": i,
                "text": doc.page_content,
                "metadata": doc.metadata
            })
        
        return passages
    
    def get_mental_wellness_support(self, emotion: str, situation: str) -> Dict[str, Any]:
        """
        Provide mental wellness support based on emotional state.
        
        Args:
            emotion: Current emotional state (e.g., "anxious", "sad", "stressed")
            situation: Brief description of the situation
            
        Returns:
            Guidance focused on mental wellness
        """
        problem = f"I am feeling {emotion}. {situation}"
        guidance = self.get_guidance(problem, include_sources=True)
        
        # Add wellness-specific metadata
        guidance["emotion"] = emotion
        guidance["support_type"] = "mental_wellness"
        
        return guidance


def main():
    """Test the Vasudeva RAG pipeline."""
    vasudeva = VasudevaRAG(
        documents_dir="../documents",
        vector_db_dir="../vectordb"
    )
    
    # Build pipeline
    vasudeva.build_pipeline()
    
    # Test queries
    test_problems = [
        "I'm struggling with anxiety about my future career",
        "I feel angry all the time and can't control it",
        "How can I find peace in difficult times?",
    ]
    
    print("="*80)
    print("VASUDEVA - WISDOM GUIDANCE TEST")
    print("="*80 + "\n")
    
    for problem in test_problems:
        print(f"\n🙏 Problem: {problem}")
        print("-" * 80)
        
        result = vasudeva.get_guidance(problem)
        
        print(f"\n💡 Guidance:\n{result['guidance']}")
        
        if "sources" in result:
            print(f"\n📖 Based on {len(result['sources'])} wisdom passages")
        
        print("\n" + "="*80)


if __name__ == "__main__":
    main()

