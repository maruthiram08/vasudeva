"""
Vercel Serverless Function: /api/guidance
POST - Get wisdom-based guidance using Pinecone vectorstore
"""

from http.server import BaseHTTPRequestHandler
import json
import os
import sys

# Add backend to path
backend_path = os.path.join(os.path.dirname(__file__), '..', '..', 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Global RAG instance
_rag_instance = None


def get_rag():
    """Get or create VasudevaRAG instance with Pinecone."""
    global _rag_instance
    if _rag_instance is None:
        from vasudeva_rag import VasudevaRAG
        _rag_instance = VasudevaRAG(use_pinecone=True)
        _rag_instance.build_pipeline()
    return _rag_instance


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            # Parse request body
            content_length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(content_length)) if content_length else {}
            
            problem = body.get('problem', '')
            
            if not problem or len(problem) < 10:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Problem must be at least 10 characters'}).encode())
                return
            
            # Get guidance
            rag = get_rag()
            result = rag.get_guidance(problem=problem, skip_story=True)
            
            from datetime import datetime
            result['timestamp'] = datetime.now().isoformat()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': f'Error: {str(e)}'}).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
