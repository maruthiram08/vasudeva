"""
Vasudeva Backend API
FastAPI server for the wisdom guidance system
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import uvicorn
from datetime import datetime

from vasudeva_rag import VasudevaRAG

# Initialize FastAPI
app = FastAPI(
    title="Vasudeva API",
    description="Wisdom-based guidance system powered by ancient texts",
    version="1.0.0"
)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React/Vite dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Vasudeva RAG
vasudeva: Optional[VasudevaRAG] = None


# Request/Response Models
class ProblemRequest(BaseModel):
    """Request model for seeking guidance"""
    problem: str = Field(..., description="The problem or question", min_length=10)
    include_sources: bool = Field(True, description="Include source wisdom texts")


class WellnessRequest(BaseModel):
    """Request model for mental wellness support"""
    emotion: str = Field(..., description="Current emotional state")
    situation: str = Field(..., description="Brief description of the situation")


class GuidanceResponse(BaseModel):
    """Response model for guidance"""
    problem: str
    guidance: str
    sources: Optional[List[Dict[str, Any]]] = None
    timestamp: str
    model: str


class WisdomSearchRequest(BaseModel):
    """Request model for wisdom search"""
    query: str = Field(..., description="Search query")
    k: int = Field(3, description="Number of passages to return", ge=1, le=10)


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    message: str
    wisdom_db_loaded: bool


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize the RAG pipeline on startup"""
    global vasudeva
    try:
        print("🚀 Starting Vasudeva API...")
        vasudeva = VasudevaRAG(
            documents_dir="../documents",
            vector_db_dir="../vectordb"
        )
        vasudeva.build_pipeline()
        print("✅ Vasudeva is ready to serve!")
    except Exception as e:
        print(f"❌ Failed to initialize Vasudeva: {e}")
        raise


# API Endpoints
@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint - health check"""
    return {
        "status": "online",
        "message": "Vasudeva API is running",
        "wisdom_db_loaded": vasudeva is not None and vasudeva.vectorstore is not None
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    if vasudeva is None or vasudeva.vectorstore is None:
        raise HTTPException(status_code=503, detail="Vasudeva is not initialized")
    
    return {
        "status": "healthy",
        "message": "Vasudeva is ready to provide guidance",
        "wisdom_db_loaded": True
    }


@app.post("/api/guidance", response_model=GuidanceResponse)
async def get_guidance(request: ProblemRequest):
    """
    Get wisdom-based guidance for a problem
    
    - **problem**: The problem or question you need help with
    - **include_sources**: Whether to include source wisdom texts in response
    """
    if vasudeva is None:
        raise HTTPException(status_code=503, detail="Vasudeva is not initialized")
    
    try:
        result = vasudeva.get_guidance(
            problem=request.problem,
            include_sources=request.include_sources
        )
        
        result["timestamp"] = datetime.now().isoformat()
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting guidance: {str(e)}")


@app.post("/api/wellness")
async def mental_wellness_support(request: WellnessRequest):
    """
    Get mental wellness support based on emotional state
    
    - **emotion**: Your current emotional state (e.g., "anxious", "sad", "stressed")
    - **situation**: Brief description of what you're going through
    """
    if vasudeva is None:
        raise HTTPException(status_code=503, detail="Vasudeva is not initialized")
    
    try:
        result = vasudeva.get_mental_wellness_support(
            emotion=request.emotion,
            situation=request.situation
        )
        
        result["timestamp"] = datetime.now().isoformat()
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error providing wellness support: {str(e)}")


@app.post("/api/search")
async def search_wisdom(request: WisdomSearchRequest):
    """
    Search for relevant wisdom passages
    
    - **query**: What to search for in the wisdom texts
    - **k**: Number of passages to return (1-10)
    """
    if vasudeva is None:
        raise HTTPException(status_code=503, detail="Vasudeva is not initialized")
    
    try:
        passages = vasudeva.get_relevant_wisdom(
            query=request.query,
            k=request.k
        )
        
        return {
            "query": request.query,
            "passages": passages,
            "count": len(passages),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching wisdom: {str(e)}")


@app.get("/api/stats")
async def get_stats():
    """Get statistics about the wisdom database"""
    if vasudeva is None or vasudeva.vectorstore is None:
        raise HTTPException(status_code=503, detail="Vasudeva is not initialized")
    
    try:
        # Get collection stats (ChromaDB specific)
        collection = vasudeva.vectorstore._collection
        count = collection.count()
        
        return {
            "total_wisdom_chunks": count,
            "model": vasudeva.model_name,
            "chunk_size": vasudeva.chunk_size,
            "status": "ready"
        }
    except Exception as e:
        return {
            "status": "ready",
            "model": vasudeva.model_name,
            "message": "Stats partially available"
        }


if __name__ == "__main__":
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )


