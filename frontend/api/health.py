"""
Vercel Serverless Function: /api/health
GET - Health check endpoint
"""

from http.server import BaseHTTPRequestHandler
import json
import os


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # Check configuration
            pinecone_key = os.environ.get('PINECONE_API_KEY')
            openai_key = os.environ.get('OPENAI_API_KEY')
            
            status = {
                'status': 'healthy' if (pinecone_key and openai_key) else 'degraded',
                'message': 'Vasudeva API is running on Vercel',
                'platform': 'vercel',
                'pinecone_configured': bool(pinecone_key),
                'openai_configured': bool(openai_key),
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(status).encode())
            
        except Exception as e:
            self.send_response(503)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'status': 'unhealthy',
                'message': str(e),
                'platform': 'vercel'
            }).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
