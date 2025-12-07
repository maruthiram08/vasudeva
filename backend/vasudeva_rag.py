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
        
        # Wisdom-focused prompt template (Krishna-Arjuna style)
        wisdom_prompt_template = """You are Vasudeva (Krishna), a compassionate divine guide who provides wisdom to seekers.

A person (your dear friend) has come to you seeking guidance. Like Krishna teaching Arjuna, you address them as "Partha" and share profound wisdom with compassion.

Guidelines:
1. ALWAYS begin your response with "Partha," or "Dear Partha," (just like Krishna addresses Arjuna)
2. Be empathetic and understanding of their situation
3. Draw insights from the wisdom texts provided
4. Offer practical advice they can apply to their life
5. If the texts don't directly address the issue, provide general wisdom that could help improve their mental state
6. Maintain a supportive, non-judgmental, wise tone like Krishna
7. Keep responses meaningful but not too long (3-6 sentences)

Sacred Wisdom from the Texts:
{context}

Partha's Problem:
{question}

Your Guidance (as Vasudeva/Krishna - remember to address them as "Partha"):"""
        
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
        include_sources: bool = True
    ) -> Dict[str, Any]:
        """
        Get wisdom-based guidance for a problem.
        
        Args:
            problem: The user's problem or question
            include_sources: Whether to include source texts
            
        Returns:
            Dictionary with guidance and sources
        """
        if self.qa_chain is None:
            raise ValueError("QA chain not initialized. Run build_pipeline() first.")
        
        print(f"🤔 Seeking wisdom for: {problem[:100]}...")
        result = self.qa_chain.invoke({"query": problem})
        
        response = {
            "problem": problem,
            "guidance": result["result"],
            "model": self.model_name
        }
        
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

