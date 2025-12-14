"""
Vercel Serverless Function: /api/guidance
POST - Get wisdom-based guidance using Pinecone vectorstore

Self-contained implementation for Vercel (no external imports)
"""

from http.server import BaseHTTPRequestHandler
import json
import os


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            # Parse request body
            content_length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(content_length)) if content_length else {}
            
            problem = body.get('problem', '')
            
            if not problem or len(problem) < 10:
                self._send_json(400, {'error': 'Problem must be at least 10 characters'})
                return
            
            # Get guidance using Pinecone + OpenAI
            result = self._get_guidance(problem)
            
            from datetime import datetime
            result['timestamp'] = datetime.now().isoformat()
            
            self._send_json(200, result)
            
        except Exception as e:
            import traceback
            self._send_json(500, {
                'error': f'Error: {str(e)}',
                'traceback': traceback.format_exc()
            })

    def _get_guidance(self, problem: str) -> dict:
        """Get guidance using Pinecone for retrieval and OpenAI for generation."""
        from pinecone import Pinecone
        from openai import OpenAI
        
        # Initialize clients
        openai_client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
        pc = Pinecone(api_key=os.environ.get('PINECONE_API_KEY'))
        
        index_name = os.environ.get('PINECONE_INDEX_NAME', 'vasudeva-wisdom')
        index = pc.Index(index_name)
        
        # Create embedding for the query
        embedding_response = openai_client.embeddings.create(
            model="text-embedding-ada-002",
            input=problem
        )
        query_embedding = embedding_response.data[0].embedding
        
        # Query Pinecone for relevant wisdom
        results = index.query(
            vector=query_embedding,
            top_k=5,
            include_metadata=True
        )
        
        # Build context from retrieved documents
        context_parts = []
        for match in results.matches:
            text = match.metadata.get('text', '')
            if text:
                context_parts.append(text[:500])  # Limit each chunk
        
        context = "\n\n".join(context_parts)
        
        # Generate guidance using OpenAI
        system_prompt = """You are a wise, compassionate guide who provides support based on timeless wisdom.

Guidelines:
1. Be empathetic and understanding
2. Draw insights from the wisdom texts provided
3. Offer practical advice they can apply
4. Maintain a supportive, non-judgmental tone
5. Keep responses meaningful but concise (3-6 sentences)
6. DO NOT use flowery archaic language
7. DO NOT roleplay as a deity or spiritual authority
8. DO NOT provide emotional support or therapy
9. If they seem distressed, suggest professional help"""

        user_prompt = f"""Sacred Wisdom from the Texts:
{context}

Seeker's Question:
{problem}

Provide wise, practical guidance:"""

        chat_response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=300
        )
        
        guidance_text = chat_response.choices[0].message.content.strip()
        
        return {
            'problem': problem,
            'guidance': guidance_text,
            'model': 'gpt-4o-mini',
            'sources_count': len(results.matches),
            'platform': 'vercel'
        }

    def _send_json(self, status: int, data: dict):
        """Send JSON response with CORS headers."""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
