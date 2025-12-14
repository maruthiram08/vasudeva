"""
Vercel Serverless Function: /api/health
GET - Health check endpoint
"""

import os
import sys
import json

# Add backend to Python path
backend_path = os.path.join(os.path.dirname(__file__), '../../backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)


def handler(request):
    """Vercel serverless function handler."""
    
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type',
            },
            'body': ''
        }
    
    # Handle GET request
    if request.method == 'GET':
        try:
            # Check if we can connect to Pinecone
            from vasudeva_rag import VasudevaRAG, PINECONE_AVAILABLE
            
            pinecone_key = os.getenv('PINECONE_API_KEY')
            openai_key = os.getenv('OPENAI_API_KEY')
            
            status = {
                'status': 'healthy' if (pinecone_key and openai_key) else 'degraded',
                'message': 'Vasudeva API is running on Vercel',
                'platform': 'vercel',
                'pinecone_available': PINECONE_AVAILABLE,
                'pinecone_configured': bool(pinecone_key),
                'openai_configured': bool(openai_key),
            }
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                },
                'body': json.dumps(status)
            }
            
        except Exception as e:
            return {
                'statusCode': 503,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'status': 'unhealthy',
                    'message': f'Health check failed: {str(e)}',
                    'platform': 'vercel'
                })
            }
    
    # Method not allowed
    return {
        'statusCode': 405,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'error': 'Method not allowed'})
    }
