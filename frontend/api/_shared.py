"""
Shared Vasudeva RAG instance for Vercel serverless functions.
Uses Pinecone for vector storage (Vercel-compatible).
"""

import os
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()

# Lazy import to reduce cold start
_vasudeva_instance = None


def get_vasudeva():
    """Get or create Vasudeva RAG instance (singleton)."""
    global _vasudeva_instance
    
    if _vasudeva_instance is None:
        from vasudeva_rag_pinecone import VasudevaRAGPinecone
        _vasudeva_instance = VasudevaRAGPinecone()
        _vasudeva_instance.build_pipeline()
    
    return _vasudeva_instance


def get_state_manager():
    """Get a fresh StateManager for each request."""
    from conversation_state import StateManager
    return StateManager()
