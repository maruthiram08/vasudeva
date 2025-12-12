"""
Vasudeva RAG Pipeline - Wisdom-based guidance system
Provides solutions and mental wellness support based on ancient wisdom texts
"""

import os
import json
import tempfile
from typing import List, Dict, Any, Optional
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv

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
        gcs_project_id: Optional[str] = None
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
        
        # Initialize components
        self.embeddings = OpenAIEmbeddings()
        self.llm = ChatOpenAI(model_name=model_name, temperature=0.7)
        self.vectorstore = None
        self.qa_chain = None
        
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
        """Split documents into chunks optimized for wisdom retrieval."""
        print(f"✂️  Splitting into wisdom chunks...")
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        chunks = text_splitter.split_documents(documents)
        print(f"✅ Created {len(chunks)} wisdom chunks")
        return chunks
    
    def create_vectorstore(self, chunks: List[Any]) -> None:
        """Create vector store from wisdom chunks."""
        print("🔮 Creating vector embeddings...")
        self.vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            persist_directory=str(self.vector_db_dir)
        )
        print(f"✅ Vector store ready with {len(chunks)} chunks")
    
    def load_vectorstore(self) -> None:
        """Load existing vector store from disk."""
        if not self.vector_db_dir.exists():
            raise ValueError(f"Vector store not found at {self.vector_db_dir}")
        
        print("📖 Loading wisdom database...")
        self.vectorstore = Chroma(
            persist_directory=str(self.vector_db_dir),
            embedding_function=self.embeddings
        )
        print("✅ Wisdom database loaded")
    
    def setup_qa_chain(self, retrieval_k: int = 5) -> None:
        """Set up the wisdom guidance QA chain."""
        if self.vectorstore is None:
            raise ValueError("Vector store not initialized")
        
        # Simplified wisdom prompt - story extraction happens separately
        wisdom_prompt_template = """You are Vasudeva (Krishna), a compassionate divine guide who provides wisdom to seekers.

A person (your dear friend) has come to you seeking guidance. Like Krishna teaching Arjuna, you address them as "Partha" and share profound wisdom with compassion.

Guidelines:
1. ALWAYS begin your response with "Dear Partha," or "Partha,"
2. Be empathetic and understanding of their situation
3. Draw insights from the wisdom texts provided
4. Offer practical advice they can apply to their life
5. Maintain a supportive, non-judgmental, wise tone like Krishna
6. Keep responses meaningful but not too long (3-6 sentences)

Sacred Wisdom from the Texts:
{context}

Partha's Problem:
{question}

Your Guidance (as Vasudeva/Krishna):"""
        
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
        # Check if vector store already exists
        if self.vector_db_dir.exists() and not force_rebuild:
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
    
    def get_guidance(
        self, 
        problem: str, 
        include_sources: bool = True,
        skip_story: bool = False  # NEW: Skip story for fast response
    ) -> Dict[str, Any]:
        """
        Get wisdom-based guidance for a problem.
        
        Args:
            problem: The user's problem or question
            include_sources: Whether to include source texts
            skip_story: If True, skip story extraction for faster response
            
        Returns:
            Dictionary with guidance, story (if applicable), and sources
        """
        if self.qa_chain is None:
            raise ValueError("QA chain not initialized. Run build_pipeline() first.")
        
        print(f"🤔 Seeking wisdom for: {problem[:100]}...")
        
        # Step 1: Get wisdom guidance
        result = self.qa_chain.invoke({"query": problem})
        guidance_text = result["result"]
        
        # Step 2: Try to extract a relevant story from the retrieved context
        story_data = None
        if not skip_story and "source_documents" in result and len(result["source_documents"]) > 0:
            story_data = self._extract_story_from_context(
                problem=problem,
                source_documents=result["source_documents"]
            )
            print(f"📚 Story data returned: {story_data is not None}")
            
            # Step 3: Convert STAR to narrative story with parallels
            if story_data:
                story_data = self._convert_to_narrative_story(
                    story_data=story_data,
                    user_problem=problem,
                    source_passages=result["source_documents"][:3]  # Pass actual passages
                )
                print(f"📖 Story converted to narrative: {story_data.get('character', 'N/A')}")
        elif skip_story:
            print("⏩ Skipping story extraction for fast response")
        
        response = {
            "problem": problem,
            "guidance": guidance_text,
            "story": story_data,
            "model": self.model_name
        }
        
        print(f"📦 Response has story: {response.get('story') is not None}")
        
        if include_sources and "source_documents" in result:
            response["sources"] = []
            for i, doc in enumerate(result["source_documents"], 1):
                source_info = {
                    "text": doc.page_content,
                    "metadata": doc.metadata,
                    "relevance_rank": i
                }
                response["sources"].append(source_info)
        
        return response
    
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
        Extract a relevant story from source documents using STAR framework.
        
        Args:
            problem: The user's problem
            source_documents: Retrieved wisdom passages
            
        Returns:
            Story in STAR format or None
        """
        # Combine top passages
        context = "\n\n---\n\n".join([
            doc.page_content for doc in source_documents[:3]
        ])
        
        # OPTION 4: Document Verification - Check if passages have sufficient content
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
        
        story_prompt = f"""Based on these sacred text passages, extract a relevant story if one exists.

Sacred Text Passages:
{context}

User's Problem: {problem}

Task: If these passages describe a story, character, or specific instance relevant to the problem, extract it using STAR framework.

Respond in JSON format:
{{
  "found": true/false,
  "title": "Short, apt title for the story (e.g., 'Arjuna's Dilemma on the Battlefield')",
  "situation": "The context and dilemma faced",
  "task": "What needed to be addressed",
  "action": "What was done",
  "result": "The outcome and lesson",
  "source": "Detailed source with book, canto/chapter, verse (e.g., 'Srimad Bhagavatam, Canto 3, Chapter 15, Verse 33')",
  "character": "Main character name"
}}

IMPORTANT FOR SOURCE:
- Include book name (Bhagavad Gita, Srimad Bhagavatam, etc.)
- Include canto/chapter numbers if mentioned in passages
- Include verse numbers if available
- Example: "Bhagavad Gita, Chapter 2, Verse 7"
- Example: "Srimad Bhagavatam, Canto 10, Chapter 3"

If NO clear story exists in the passages, return: {{"found": false}}

Your JSON response:"""
        
        try:
            # Use a simpler LLM call for story extraction
            from langchain.schema import HumanMessage
            
            story_llm = ChatOpenAI(
                model_name="gpt-4o-mini",
                temperature=0.3,
                model_kwargs={"response_format": {"type": "json_object"}}
            )
            
            response = story_llm.invoke([HumanMessage(content=story_prompt)])
            story_json = json.loads(response.content)
            
            if story_json.get("found"):
                # Remove the 'found' key and return the story
                story_json.pop("found", None)
                print(f"📖 Story extracted: {story_json.get('character', 'Unknown')}")
                return story_json
            else:
                print("ℹ️  No specific story found in context")
                return None
                
        except Exception as e:
            print(f"⚠️  Could not extract story: {e}")
            return None
    
    def _convert_to_narrative_story(
        self,
        story_data: Dict[str, str],
        user_problem: str,
        source_passages: List[Any]
    ) -> Dict[str, Any]:
        """
        Convert STAR framework story into a narrative format with fact-checking.
        Uses hybrid approach: generate → fact-check → regenerate if needed.
        
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
            from langchain.schema import HumanMessage
            
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
        
        check_prompt = f"""You are a strict fact-checker for sacred text stories.

ORIGINAL PASSAGES FROM SACRED TEXTS:
{passages_text}

GENERATED NARRATIVE:
{narrative}

Task: Find ANY details in the narrative that are NOT explicitly in the original passages.

CRITICAL CHECKS - Flag if narrative contains:

1. **Invented Characters/Deities**:
   - Divine figures not named in passages (e.g., "Lord Dharma", "Lord of righteousness")
   - Entities like "Earth spoke", "gods appeared" if not in text
   
2. **Fabricated Events**:
   - Events not described in passages
   - Actions characters didn't take
   - Timeline issues (e.g., child present when not born yet)
   
3. **Added Dialogue**:
   - Quotes/conversations not in passages
   - "Said", "spoke", "told" if dialogue not in text
   
4. **Conceptual Inventions**:
   - Symbolic interpretations not in passages (e.g., divine light, spiritual symbolism)
   - Emotional motivations not stated (e.g., "to heal grief" when text says "to fulfill duty")
   - Modern therapeutic angles (e.g., "coping mechanism", "emotional recovery")
   
5. **Thematic Reinterpretations**:
   - Changing the purpose/meaning of events
   - Adding spiritual lessons not in text
   - Modernizing the message beyond text

IMPORTANT: 
- Be STRICT - flag anything not explicitly in passages
- Conceptual additions are as bad as factual errors
- Proper nouns (names, places) must be in passages

Respond in JSON:
{{
  "has_issues": true/false,
  "issues": [
    {{"detail": "specific fabrication", "reason": "why it's not in passages", "type": "character/event/dialogue/conceptual"}},
    ...
  ]
}}

Your fact-check:"""
        
        try:
            from langchain.schema import HumanMessage
            
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
            from langchain.schema import HumanMessage
            
            regen_llm = ChatOpenAI(
                model_name="gpt-4o-mini",
                temperature=0.5
            )
            
            response = regen_llm.invoke([HumanMessage(content=regen_prompt)])
            return response.content.strip()
            
        except Exception as e:
            print(f"⚠️  Regeneration failed: {e}")
            return original_narrative  # Fallback to original if regen fails
    
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

