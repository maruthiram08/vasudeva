"""
Vasudeva FastAPI Backend
Production-ready REST API for the Vasudeva wisdom guide.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from vasudeva_rag import VasudevaRAG
import uvicorn

# Initialize FastAPI app
app = FastAPI(
    title="Vasudeva API",
    description="REST API for Vasudeva - Wisdom-based guidance system",
    version="1.0.0"
)

# CORS middleware for web frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Vasudeva instance
vasudeva: Optional[VasudevaRAG] = None


# Pydantic models
class QuestionRequest(BaseModel):
    question: str
    return_sources: bool = False


class GuidanceResponse(BaseModel):
    question: str
    guidance: str
    has_relevant_wisdom: bool
    wisdom_sources: Optional[List[dict]] = None


class WisdomSearchRequest(BaseModel):
    query: str
    k: int = 3


class HealthResponse(BaseModel):
    status: str
    message: str


@app.on_event("startup")
async def startup_event():
    """Initialize Vasudeva on startup."""
    global vasudeva
    try:
        vasudeva = VasudevaRAG(
            documents_dir="documents",
            vector_db_dir="vasudeva_db",
            temperature=0.7
        )
        vasudeva.build_pipeline(force_rebuild=False)
        print("✅ Vasudeva initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize Vasudeva: {e}")
        raise


@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint."""
    return {
        "status": "healthy",
        "message": "Vasudeva API is running. Visit /docs for API documentation."
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    if vasudeva is None:
        raise HTTPException(status_code=503, detail="Vasudeva not initialized")
    
    return {
        "status": "healthy",
        "message": "Vasudeva is ready to provide guidance"
    }


@app.post("/guidance", response_model=GuidanceResponse)
async def get_guidance(request: QuestionRequest):
    """
    Get wisdom-based guidance for a question or problem.
    
    Args:
        request: Question request with optional source return flag
        
    Returns:
        Guidance response with answer and optional sources
    """
    if vasudeva is None:
        raise HTTPException(status_code=503, detail="Vasudeva not initialized")
    
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    
    try:
        result = vasudeva.get_guidance(
            request.question,
            return_sources=request.return_sources
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting guidance: {str(e)}")


@app.post("/wisdom/search")
async def search_wisdom(request: WisdomSearchRequest):
    """
    Search for relevant wisdom passages.
    
    Args:
        request: Search request with query and number of results
        
    Returns:
        List of relevant wisdom passages
    """
    if vasudeva is None:
        raise HTTPException(status_code=503, detail="Vasudeva not initialized")
    
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    try:
        results = vasudeva.find_relevant_wisdom(request.query, k=request.k)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching wisdom: {str(e)}")


@app.get("/stats")
async def get_stats():
    """Get statistics about the knowledge base."""
    if vasudeva is None:
        raise HTTPException(status_code=503, detail="Vasudeva not initialized")
    
    # Get collection stats
    try:
        collection = vasudeva.vectorstore._collection
        count = collection.count()
        
        return {
            "total_wisdom_segments": count,
            "model": vasudeva.model_name,
            "status": "operational"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting stats: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

