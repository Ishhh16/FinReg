#!/usr/bin/env python3
"""
Startup script for FinReg application
Handles database initialization and vector store setup
"""

import os
import sys
import subprocess
from pathlib import Path

# Configure stdout to handle UTF-8 encoding (especially emojis) on Windows
sys.stdout.reconfigure(encoding='utf-8')

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

def setup_vector_store():
    """Setup vector store with actual regulatory PDF chunks from ingest.py"""
    try:
        import chromadb
        from pathlib import Path
        
        chroma_dir = Path(__file__).parent / "chroma_db"
        collection_name = "regulations_knowledge_base"
        
        # Check if database already exists and contains documents
        db_exists = False
        if chroma_dir.exists():
            try:
                client = chromadb.PersistentClient(path=str(chroma_dir))
                if collection_name in [c.name for c in client.list_collections()]:
                    if client.get_collection(collection_name).count() > 0:
                        db_exists = True
            except Exception:
                pass
                
        if db_exists:
            print("✅ Vector store already exists with PDF chunks. Skipping build.")
            return True
            
        print("🔄 Regulations database not found. Ingesting PDF regulations...")
        import subprocess
        import sys
        subprocess.run([sys.executable, "ingest.py"], check=True)
        print("✅ Vector store setup completed with PDF chunks!")
        return True
    except Exception as e:
        print(f"⚠️ Vector store setup warning: {e}")
        return True  # Don't fail startup for vector store issues

def start_application():
    """Start the FastAPI application"""
    print("🚀 Starting FinReg API...")
    
    cmd = [
        sys.executable, "-m", "uvicorn", 
        "backend.main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--reload"
    ]
    
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down FinReg API")
    except Exception as e:
        print(f"❌ Failed to start application: {e}")
        sys.exit(1)

def main():
    print("🏁 Starting FinReg application initialization...")
    
    # Step 1: Setup vector store (non-critical)
    setup_vector_store()
    
    # Step 2: Start application
    start_application()

if __name__ == "__main__":
    main()