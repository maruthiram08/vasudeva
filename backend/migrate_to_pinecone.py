"""
Migrate ChromaDB vectors to Pinecone
Run this script to transfer all embeddings from local ChromaDB to Pinecone cloud.

Usage:
    1. Set environment variables:
       - OPENAI_API_KEY
       - PINECONE_API_KEY
       - PINECONE_INDEX_NAME (default: vasudeva-wisdom)
    
    2. Run:
       python migrate_to_pinecone.py
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Verify environment
required_vars = ["OPENAI_API_KEY", "PINECONE_API_KEY"]
missing = [v for v in required_vars if not os.getenv(v)]
if missing:
    print(f"❌ Missing environment variables: {', '.join(missing)}")
    print("Please set them in .env or environment")
    sys.exit(1)

print("🚀 Starting ChromaDB → Pinecone migration...")

# Import dependencies
try:
    from langchain_community.vectorstores import Chroma
    from langchain_openai import OpenAIEmbeddings
    from pinecone import Pinecone, ServerlessSpec
    print("✅ Dependencies loaded")
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("Run: pip install pinecone-client langchain-pinecone")
    sys.exit(1)

# Configuration
CHROMA_DIR = "./vectordb"
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "vasudeva-wisdom")
BATCH_SIZE = 100

# Initialize OpenAI embeddings
embeddings = OpenAIEmbeddings()
print("✅ OpenAI embeddings initialized")

# Load ChromaDB
print(f"📂 Loading ChromaDB from {CHROMA_DIR}...")
try:
    chroma = Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=embeddings
    )
    collection = chroma._collection
    total_count = collection.count()
    print(f"✅ Found {total_count} vectors in ChromaDB")
except Exception as e:
    print(f"❌ Failed to load ChromaDB: {e}")
    sys.exit(1)

# Get all data from ChromaDB
print("📦 Extracting all vectors (this may take a moment)...")
results = collection.get(include=["documents", "metadatas", "embeddings"])
print(f"✅ Extracted {len(results['ids'])} vectors")

# Initialize Pinecone
print("🌲 Connecting to Pinecone...")
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

# Create index if not exists
existing_indexes = [idx.name for idx in pc.list_indexes()]
if INDEX_NAME not in existing_indexes:
    print(f"📌 Creating index '{INDEX_NAME}'...")
    pc.create_index(
        name=INDEX_NAME,
        dimension=1536,  # OpenAI ada-002
        metric="cosine",
        spec=ServerlessSpec(
            cloud="aws",
            region="us-east-1"
        )
    )
    print(f"✅ Index '{INDEX_NAME}' created")
else:
    print(f"✅ Index '{INDEX_NAME}' already exists")

# Connect to index
index = pc.Index(INDEX_NAME)
print(f"✅ Connected to Pinecone index")

# Migrate in batches
print(f"\n📤 Migrating {len(results['ids'])} vectors in batches of {BATCH_SIZE}...")
migrated = 0
errors = 0

for i in range(0, len(results['ids']), BATCH_SIZE):
    batch_end = min(i + BATCH_SIZE, len(results['ids']))
    batch_ids = results['ids'][i:batch_end]
    batch_embeddings = results['embeddings'][i:batch_end]
    batch_metadatas = results['metadatas'][i:batch_end]
    batch_docs = results['documents'][i:batch_end]
    
    vectors = []
    for j in range(len(batch_ids)):
        # Prepare metadata (Pinecone has metadata size limits)
        metadata = batch_metadatas[j] if batch_metadatas[j] else {}
        
        # Store text in metadata (truncate to avoid limits)
        text = batch_docs[j] if batch_docs[j] else ""
        metadata['text'] = text[:3000]  # Pinecone metadata limit ~40KB
        
        # Clean metadata keys (Pinecone doesn't allow certain characters)
        clean_metadata = {}
        for k, v in metadata.items():
            clean_key = k.replace(".", "_").replace("$", "_")
            if isinstance(v, (str, int, float, bool)):
                clean_metadata[clean_key] = v
            elif isinstance(v, list):
                clean_metadata[clean_key] = str(v)
        
        vectors.append({
            'id': batch_ids[j],
            'values': batch_embeddings[j],
            'metadata': clean_metadata
        })
    
    try:
        index.upsert(vectors=vectors)
        migrated += len(vectors)
        print(f"  ✅ Migrated {migrated}/{len(results['ids'])} vectors")
    except Exception as e:
        errors += len(vectors)
        print(f"  ❌ Error in batch: {e}")

# Summary
print("\n" + "=" * 50)
print("📊 MIGRATION SUMMARY")
print("=" * 50)
print(f"Total vectors in ChromaDB: {len(results['ids'])}")
print(f"Successfully migrated: {migrated}")
print(f"Errors: {errors}")

# Verify
stats = index.describe_index_stats()
print(f"\n🌲 Pinecone index stats:")
print(f"   Total vectors: {stats.total_vector_count}")
print(f"   Dimension: {stats.dimension}")

if migrated == len(results['ids']):
    print("\n🎉 Migration complete! All vectors transferred to Pinecone.")
else:
    print(f"\n⚠️  Migration incomplete. {errors} vectors failed.")
    print("Please check errors above and retry if needed.")
