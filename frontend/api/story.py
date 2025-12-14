"""
Vercel Serverless Function: /api/story
POST - Get a story from the sacred texts for a given problem

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
            
            # Get story using Pinecone + OpenAI
            result = self._get_story(problem)
            
            from datetime import datetime
            result['timestamp'] = datetime.now().isoformat()
            
            self._send_json(200, result)
            
        except Exception as e:
            import traceback
            self._send_json(500, {
                'error': f'Error: {str(e)}',
                'traceback': traceback.format_exc()
            })

    def _get_story(self, problem: str) -> dict:
        """Get a relevant story from the wisdom texts using Pinecone and OpenAI."""
        from pinecone import Pinecone
        from openai import OpenAI
        
        # Initialize clients
        openai_client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
        pc = Pinecone(api_key=os.environ.get('PINECONE_API_KEY'))
        
        index_name = os.environ.get('PINECONE_INDEX_NAME', 'vasudeva-wisdom')
        index = pc.Index(index_name)
        
        # Create embedding for the query with story focus
        story_query = f"story narrative about {problem}"
        embedding_response = openai_client.embeddings.create(
            model="text-embedding-ada-002",
            input=story_query
        )
        query_embedding = embedding_response.data[0].embedding
        
        # Query Pinecone for story chunks
        results = index.query(
            vector=query_embedding,
            top_k=8,
            include_metadata=True,
            filter={"chunk_type": {"$eq": "story"}} if False else None  # Disabled filter for now
        )
        
        # Build context from retrieved documents
        context_parts = []
        for match in results.matches:
            text = match.metadata.get('text', '')
            if text:
                context_parts.append(text[:800])
        
        context = "\n\n".join(context_parts[:5])  # Use top 5 chunks
        
        if not context:
            return {
                'problem': problem,
                'story': None,
                'message': 'No relevant story found'
            }
        
        # Generate story narrative using OpenAI
        system_prompt = """You are a storyteller who shares wisdom through ancient tales.

Based on the provided text excerpts, create a coherent, narrative story that:
1. Has a clear beginning, middle, and end
2. Features a character facing a similar challenge
3. Shows how wisdom helped them overcome it
4. Is 150-250 words
5. Feels authentic to the source material
6. Does NOT add fictional elements not present in the source

If the excerpts don't contain a clear story, politely indicate that."""

        user_prompt = f"""Seeker's Challenge:
{problem}

Source Excerpts:
{context}

Create a narrative story based on these excerpts:"""

        chat_response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.8,
            max_tokens=400
        )
        
        narrative = chat_response.choices[0].message.content.strip()
        
        # Extract title from the first match metadata
        title = "A Tale from the Sacred Texts"
        source = "Ancient Wisdom Texts"
        if results.matches:
            first_meta = results.matches[0].metadata
            title = first_meta.get('title', title)
            source = first_meta.get('source', source)
        
        return {
            'problem': problem,
            'story': {
                'title': title,
                'narrative': narrative,
                'source': source,
                'character': 'Seeker of Wisdom'
            },
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
