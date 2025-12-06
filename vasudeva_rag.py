"""
Vasudeva - Wisdom-Based RAG Pipeline
A RAG system that provides solutions and guidance based on ancient wisdom from great books.
"""

import os
from typing import List, Dict, Any, Optional
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class VasudevaRAG:
    """
    Vasudeva - A wisdom-based RAG system for providing guidance and solutions.
    """
    
    def __init__(
        self,
        documents_dir: str = "documents",
        vector_db_dir: str = "vasudeva_db",
        chunk_size: int = 800,
        chunk_overlap: int = 150,
        model_name: str = "gpt-3.5-turbo",
        temperature: float = 0.7
    ):
        """
        Initialize Vasudeva RAG pipeline.
        
        Args:
            documents_dir: Directory containing wisdom texts (PDFs)
            vector_db_dir: Directory to store vector database
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
            model_name: OpenAI model name
            temperature: Higher for more creative/empathetic responses
        """
        self.documents_dir = Path(documents_dir)
        self.vector_db_dir = Path(vector_db_dir)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.model_name = model_name
        self.temperature = temperature
        
        # Initialize components
        self.embeddings = OpenAIEmbeddings()
        self.llm = ChatOpenAI(model_name=model_name, temperature=temperature)
        self.vectorstore = None
        self.qa_chain = None
        
        # Create vector DB directory if it doesn't exist
        self.vector_db_dir.mkdir(exist_ok=True)
    
    def load_documents(self) -> List[Any]:
        """
        Load all wisdom texts (PDFs) from the documents directory.
        
        Returns:
            List of loaded documents
        """
        documents = []
        pdf_files = list(self.documents_dir.glob("*.pdf"))
        
        if not pdf_files:
            raise ValueError(f"No PDF files found in {self.documents_dir}")
        
        print(f"📚 Loading {len(pdf_files)} sacred texts...")
        for pdf_file in pdf_files:
            print(f"  ✨ {pdf_file.name}")
            loader = PyPDFLoader(str(pdf_file))
            documents.extend(loader.load())
        
        print(f"✅ Loaded {len(documents)} pages of wisdom")
        return documents
    
    def split_documents(self, documents: List[Any]) -> List[Any]:
        """
        Split documents into meaningful chunks.
        
        Args:
            documents: List of documents to split
            
        Returns:
            List of document chunks
        """
        print(f"✂️  Organizing wisdom into meaningful segments...")
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        chunks = text_splitter.split_documents(documents)
        print(f"✅ Created {len(chunks)} wisdom segments")
        return chunks
    
    def create_vectorstore(self, chunks: List[Any]) -> None:
        """
        Create and persist vector store from document chunks.
        
        Args:
            chunks: List of document chunks
        """
        print("🔮 Creating wisdom embeddings...")
        self.vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            persist_directory=str(self.vector_db_dir)
        )
        print(f"✅ Vasudeva's knowledge base ready with {len(chunks)} segments")
    
    def load_vectorstore(self) -> None:
        """
        Load existing vector store from disk.
        """
        if not self.vector_db_dir.exists():
            raise ValueError(f"Knowledge base not found at {self.vector_db_dir}")
        
        print("📖 Loading Vasudeva's knowledge base...")
        self.vectorstore = Chroma(
            persist_directory=str(self.vector_db_dir),
            embedding_function=self.embeddings
        )
        print("✅ Knowledge base loaded successfully")
    
    def setup_qa_chain(self, retrieval_k: int = 4) -> None:
        """
        Set up the wisdom guidance chain.
        
        Args:
            retrieval_k: Number of relevant wisdom segments to retrieve
        """
        if self.vectorstore is None:
            raise ValueError("Knowledge base not initialized. Run build_pipeline() first.")
        
        # Wisdom-focused prompt template
        wisdom_prompt = """You are Vasudeva, a wise and compassionate guide who draws wisdom from ancient sacred texts to help people with their problems.

You have access to wisdom from great books. Use this wisdom to provide thoughtful, empathetic guidance.

Sacred Wisdom:
{context}

Person's Question/Problem:
{question}

Instructions for your response:
1. If the sacred texts contain relevant wisdom, share it in a warm, accessible way
2. Relate the ancient wisdom to their modern situation
3. Be empathetic and understanding
4. If no directly relevant wisdom is found, still provide supportive guidance to improve their mental state
5. Keep your response concise but meaningful (3-5 sentences)
6. End with encouragement or a gentle reflection

Vasudeva's Guidance:"""
        
        WISDOM_PROMPT = PromptTemplate(
            template=wisdom_prompt,
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
        print("🙏 Vasudeva is ready to guide")
    
    def build_pipeline(self, force_rebuild: bool = False) -> None:
        """
        Build the complete Vasudeva wisdom pipeline.
        
        Args:
            force_rebuild: If True, rebuild knowledge base even if it exists
        """
        print("\n" + "="*60)
        print("🕉️  Initializing Vasudeva - Wisdom Guide")
        print("="*60 + "\n")
        
        # Check if vector store already exists
        if self.vector_db_dir.exists() and not force_rebuild:
            self.load_vectorstore()
        else:
            # Load and process documents
            documents = self.load_documents()
            chunks = self.split_documents(documents)
            self.create_vectorstore(chunks)
        
        # Set up QA chain
        self.setup_qa_chain()
        print("\n✅ Vasudeva is ready to offer guidance\n")
    
    def get_guidance(
        self, 
        question: str, 
        return_sources: bool = False,
        min_relevance_score: float = 0.5
    ) -> Dict[str, Any]:
        """
        Get wisdom-based guidance for a question or problem.
        
        Args:
            question: User's question or problem
            return_sources: Whether to return source wisdom texts
            min_relevance_score: Minimum relevance threshold
            
        Returns:
            Dictionary containing guidance and optionally sources
        """
        if self.qa_chain is None:
            raise ValueError("Vasudeva not initialized. Run build_pipeline() first.")
        
        # Get response from the chain
        result = self.qa_chain.invoke({"query": question})
        
        response = {
            "question": question,
            "guidance": result["result"],
            "has_relevant_wisdom": True
        }
        
        # Check if we found relevant wisdom
        if "source_documents" in result and result["source_documents"]:
            # Calculate basic relevance (you can enhance this)
            sources = result["source_documents"]
            
            if return_sources:
                response["wisdom_sources"] = []
                for i, doc in enumerate(sources, 1):
                    source_info = {
                        "rank": i,
                        "text": doc.page_content,
                        "source": doc.metadata.get("source", "Unknown"),
                        "page": doc.metadata.get("page", "Unknown")
                    }
                    response["wisdom_sources"].append(source_info)
        
        return response
    
    def find_relevant_wisdom(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """
        Find relevant wisdom passages without generating a response.
        
        Args:
            query: Search query
            k: Number of results to return
            
        Returns:
            List of relevant wisdom passages
        """
        if self.vectorstore is None:
            raise ValueError("Knowledge base not initialized. Run build_pipeline() first.")
        
        docs = self.vectorstore.similarity_search(query, k=k)
        results = []
        
        for i, doc in enumerate(docs, 1):
            results.append({
                "rank": i,
                "text": doc.page_content,
                "source": doc.metadata.get("source", "Unknown"),
                "page": doc.metadata.get("page", "Unknown")
            })
        
        return results
    
    def get_supportive_response(self, question: str) -> str:
        """
        Generate a supportive response when no specific wisdom is found.
        This uses the LLM to provide general mental wellness support.
        
        Args:
            question: User's question or problem
            
        Returns:
            Supportive response
        """
        support_prompt = f"""You are Vasudeva, a compassionate guide. Someone has come to you with this concern:

"{question}"

While you don't have specific ancient wisdom for this exact situation, provide warm, supportive guidance to help improve their mental state. Be empathetic, encouraging, and offer practical wisdom for mental wellness.

Keep your response concise (3-4 sentences) and end with encouragement.

Your response:"""
        
        response = self.llm.invoke(support_prompt)
        return response.content


def main():
    """
    Example usage of Vasudeva wisdom guide.
    """
    # Initialize Vasudeva
    vasudeva = VasudevaRAG(
        documents_dir="documents",
        vector_db_dir="vasudeva_db",
        temperature=0.7
    )
    
    # Build pipeline
    vasudeva.build_pipeline(force_rebuild=False)
    
    # Example questions
    example_problems = [
        "I am struggling with anxiety and fear about the future",
        "I feel lost and don't know my purpose in life",
        "How can I deal with difficult people at work?",
    ]
    
    print("\n" + "="*60)
    print("🙏 VASUDEVA - WISDOM GUIDANCE EXAMPLES")
    print("="*60)
    
    for problem in example_problems:
        print(f"\n💭 Problem: {problem}")
        
        result = vasudeva.get_guidance(problem, return_sources=True)
        
        print(f"\n🕉️  Vasudeva's Guidance:")
        print(f"   {result['guidance']}")
        
        if "wisdom_sources" in result:
            print(f"\n📚 Based on wisdom from:")
            for source in result["wisdom_sources"][:2]:  # Show top 2
                print(f"   • {source['source']} (Page {source['page']})")
        
        print("\n" + "-"*60)


if __name__ == "__main__":
    main()

