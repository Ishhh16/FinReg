#!/usr/bin/env python3
"""
ingest.py - Ingestion script for FinReg regulations.
Parses PDF documents in the regulations directory, chunks them,
embeds them using BAAI/bge-small-en-v1.5, and stores them in a
persistent ChromaDB vector database.
"""

import os
import sys
import argparse
import fitz  # PyMuPDF
from pathlib import Path

# Configure stdout and stderr to handle UTF-8 encoding (especially emojis) on Windows
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Set up paths
WORKSPACE_DIR = Path(__file__).parent.resolve()
REGULATIONS_DIR = WORKSPACE_DIR / "regulations"
CHROMA_DIR = WORKSPACE_DIR / "chroma_db"
COLLECTION_NAME = "regulations_knowledge_base"
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"

# Add backend to path for imports consistency
sys.path.insert(0, str(WORKSPACE_DIR / "backend"))

def parse_args():
    parser = argparse.ArgumentParser(description="Ingest regulatory PDFs into ChromaDB.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force rebuild of the vector database even if it already exists.",
    )
    return parser.parse_args()

def check_db_exists():
    """Check if the regulations collection already exists and has records."""
    if not CHROMA_DIR.exists():
        return False
        
    try:
        # Import dynamically to avoid loading heavy models/libs if not needed
        import chromadb
        
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        # Check if collection exists
        collections = [c.name for c in client.list_collections()]
        if COLLECTION_NAME in collections:
            collection = client.get_collection(COLLECTION_NAME)
            count = collection.count()
            if count > 0:
                print(f"📊 Found existing ChromaDB collection '{COLLECTION_NAME}' with {count} documents.")
                return True
    except Exception as e:
        print(f"⚠️ Error checking ChromaDB status: {e}")
    return False

def extract_pdf_chunks(pdf_path: Path):
    """
    Extracts text page-by-page from PDF and splits into chunks.
    Preserves page number, filename, and chunk ID in metadata.
    """
    print(f"📄 Loading PDF: {pdf_path.name}...")
    try:
        doc = fitz.open(str(pdf_path))
    except Exception as e:
        print(f"❌ Failed to open PDF {pdf_path}: {e}")
        return [], []

    from langchain_text_splitters import RecursiveCharacterTextSplitter

    # Initialize text splitter
    # Chunk size 1000 with 200 overlap targets detailed paragraphs while maintaining context
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )

    chunk_texts = []
    chunk_metadatas = []
    
    total_pages = len(doc)
    print(f"📖 PDF has {total_pages} pages. Extracting text page-by-page...")

    global_chunk_idx = 0
    for page_idx in range(total_pages):
        page = doc[page_idx]
        page_num = page_idx + 1
        page_text = page.get_text()

        if not page_text.strip():
            continue

        # Split text for the current page
        page_chunks = text_splitter.split_text(page_text)
        
        for chunk_idx, chunk in enumerate(page_chunks):
            chunk_texts.append(chunk)
            chunk_metadatas.append({
                "source_filename": pdf_path.name,
                "page_number": page_num,
                "chunk_id": f"{pdf_path.stem}_p{page_num}_c{chunk_idx}"
            })
            global_chunk_idx += 1

    print(f"✅ Extracted {global_chunk_idx} chunks from {pdf_path.name}")
    return chunk_texts, chunk_metadatas

def main():
    args = parse_args()
    
    # 1. Check if we need to rebuild
    if check_db_exists() and not args.force:
        print("⏭️ Database already exists and contains documents. Skipping ingestion.")
        print("💡 Use '--force' flag if you want to rebuild the database.")
        sys.exit(0)

    # 2. Check for PDF documents
    if not REGULATIONS_DIR.exists():
        print(f"❌ Regulations directory not found at: {REGULATIONS_DIR}")
        sys.exit(1)

    pdf_files = list(REGULATIONS_DIR.glob("*.pdf"))
    if not pdf_files:
        print(f"❌ No PDF files found in {REGULATIONS_DIR}")
        sys.exit(1)

    print(f"🔍 Found {len(pdf_files)} PDF file(s) for ingestion.")

    # 3. Extract chunks from all PDFs
    all_texts = []
    all_metadatas = []
    for pdf_file in pdf_files:
        texts, metadatas = extract_pdf_chunks(pdf_file)
        all_texts.extend(texts)
        all_metadatas.extend(metadatas)

    if not all_texts:
        print("⚠️ No text content could be extracted from the PDF files. Exiting.")
        sys.exit(1)

    # 4. Initialize local BAAI embeddings
    print(f"🧬 Initializing local embeddings model: {EMBEDDING_MODEL} (this may take a moment on first run)...")
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings
        embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={'device': 'cpu'},  # Default to CPU for maximum portability
            encode_kwargs={'normalize_embeddings': True}
        )
        print("✅ Embeddings model initialized.")
    except Exception as e:
        print(f"❌ Failed to initialize HuggingFace embeddings: {e}")
        sys.exit(1)

    # 5. Store in Persistent ChromaDB
    print(f"📥 Storing {len(all_texts)} chunks into persistent ChromaDB collection '{COLLECTION_NAME}'...")
    try:
        from langchain_community.vectorstores import Chroma
        
        # If force flag, recreate the collection by deleting first
        if args.force and CHROMA_DIR.exists():
            import shutil
            print(f"🧹 Clearing existing ChromaDB directory at {CHROMA_DIR}...")
            shutil.rmtree(str(CHROMA_DIR), ignore_errors=True)

        vector_store = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=str(CHROMA_DIR)
        )
        
        # Batch addition to prevent memory/payload limits
        batch_size = 100
        for i in range(0, len(all_texts), batch_size):
            end_idx = min(i + batch_size, len(all_texts))
            vector_store.add_texts(
                texts=all_texts[i:end_idx],
                metadatas=all_metadatas[i:end_idx]
            )
            print(f"   • Ingested chunks {i+1} to {end_idx}...")
            
        print("🎉 Ingestion complete! Database successfully populated and persisted.")
    except Exception as e:
        print(f"❌ Failed to ingest into ChromaDB: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
