#!/usr/bin/env python3
"""
test_retrieval.py - Simple retrieval test script for FinReg.
Loads the persistent ChromaDB vector store and queries it with specific compliance concepts
to verify embedding retrieval quality and metadata capture.
"""

import sys
import os
from pathlib import Path

# Configure stdout and stderr to handle UTF-8 encoding on Windows
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

WORKSPACE_DIR = Path(__file__).parent.parent.resolve()
CHROMA_DIR = WORKSPACE_DIR / "chroma_db"
COLLECTION_NAME = "regulations_knowledge_base"
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"

# Define target queries
queries = [
    "MGT-7 annual return filing requirements",
    "Section 92 annual return",
    "AOC-4 financial statements",
    "DIR-3 KYC director requirements"
]

def main():
    print("🧬 Initializing local embeddings model...")
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings
        embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        print("✅ Embeddings model initialized.")
    except Exception as e:
        print(f"❌ Failed to initialize HuggingFace embeddings: {e}")
        sys.exit(1)
        
    print(f"📁 Loading Chroma DB from: {CHROMA_DIR}...")
    if not CHROMA_DIR.exists():
        print("❌ Chroma database directory does not exist! Please run 'python ingest.py' first.")
        sys.exit(1)
        
    try:
        from langchain_community.vectorstores import Chroma
        vector_store = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=str(CHROMA_DIR)
        )
        total_docs = vector_store._collection.count()
        print(f"✅ Chroma DB loaded successfully. Collection count: {total_docs} document chunks.")
    except Exception as e:
        print(f"❌ Failed to load Chroma DB: {e}")
        sys.exit(1)
    
    # Process queries
    for q in queries:
        print("\n" + "="*80)
        print(f"🔍 QUERY: \"{q}\"")
        print("="*80)
        
        try:
            # Query the vector store
            # similarity_search_with_score returns (Document, float_distance)
            results = vector_store.similarity_search_with_score(q, k=5)
            
            if not results:
                print("⚠️ No matching chunks found.")
                continue
                
            for idx, (doc, score) in enumerate(results):
                # Chroma uses L2 distance by default (lower is closer/better).
                # For normalized embeddings:
                # distance = 2 - 2 * cos_sim => cos_sim = 1 - (distance / 2)
                l2_distance = float(score)
                cosine_sim = 1.0 - (l2_distance / 2.0)
                
                meta = doc.metadata
                page_num = meta.get("page_number", "Unknown")
                filename = meta.get("source_filename", "Unknown")
                chunk_id = meta.get("chunk_id", "Unknown")
                
                print(f"\n[{idx + 1}] MATCH - Score (L2 Distance: {l2_distance:.4f}, Cosine Similarity: {cosine_sim:.4f})")
                print(f"📄 Page Number: {page_num} | Source: {filename} | Chunk ID: {chunk_id}")
                print(f"📝 Excerpt:")
                print("-" * 60)
                # Clean up multiple newlines for cleaner print
                clean_text = "\n".join([line.strip() for line in doc.page_content.splitlines() if line.strip()])
                print(clean_text)
                print("-" * 60)
                
        except Exception as e:
            print(f"❌ Error performing query search for '{q}': {e}")

if __name__ == "__main__":
    main()
