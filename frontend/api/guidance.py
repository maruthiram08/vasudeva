"""
Vercel Serverless Function: /api/guidance
POST - Get wisdom-based guidance using Pinecone vectorstore
"""

import os
import sys
import json
from datetime import datetime

# Add backend to Python path
backend_path = os.path.join(os.path.dirname(__file__), '../../backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Global RAG instance (reused across invocations for warm starts)
_rag_instance = None

def get_rag():
    """Get or create VasudevaRAG instance with Pinecone."""
    global _rag_instance
    if _rag_instance is None:
        from vasudeva_rag import VasudevaRAG
        _rag_instance = VasudevaRAG(use_pinecone=True)
        _rag_instance.build_pipeline()
    return _rag_instance


def handler(request):
    """Vercel serverless function handler."""
    from http.server import BaseHTTPRequestHandler
    
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type',
            },
            'body': ''
        }
    
    # Handle POST request
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            problem = body.get('problem', '')
            
            if not problem or len(problem) < 10:
                return {
                    'statusCode': 400,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({'error': 'Problem must be at least 10 characters'})
                }
            
            # Get guidance from RAG
            rag = get_rag()
            result = rag.get_guidance(problem=problem, skip_story=True)
            result['timestamp'] = datetime.now().isoformat()
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                },
                'body': json.dumps(result)
            }
            
        except Exception as e:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': f'Error getting guidance: {str(e)}'})
            }
    
    # Method not allowed
    return {
        'statusCode': 405,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'error': 'Method not allowed'})
    }
