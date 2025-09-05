#!/usr/bin/env python3
"""
Startup script for FinReg application
Handles database initialization and vector store setup
"""

import os
import sys
import time
import subprocess
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

def wait_for_database():
    """Wait for database to be ready"""
    print("🔄 Waiting for database to be ready...")
    max_attempts = 30
    attempt = 0
    
    while attempt < max_attempts:
        try:
            from backend.database import engine
            from sqlalchemy import text
            
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                print("✅ Database is ready!")
                return True
        except Exception as e:
            print(f"⏳ Database not ready (attempt {attempt + 1}/{max_attempts}): {e}")
            time.sleep(2)
            attempt += 1
    
    print("❌ Database failed to become ready")
    return False

def initialize_database():
    """Initialize database tables"""
    try:
        print("🔄 Initializing database tables...")
        from backend import models
        from backend.database import engine
        
        models.Base.metadata.create_all(bind=engine)
        print("✅ Database tables initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize database: {e}")
        return False

def setup_vector_store():
    """Setup vector store with regulatory documents"""
    try:
        print("🔄 Setting up vector store...")
        from backend.ingestion import ingest_documents_to_vector_store
        
        ingest_documents_to_vector_store()
        print("✅ Vector store setup completed")
        return True
    except Exception as e:
        print(f"⚠️ Vector store setup warning: {e}")
        return True  # Don't fail startup for vector store issues

def start_application():
    """Start the FastAPI application"""
    print("🚀 Starting FinReg API...")
    
    cmd = [
        "python", "-m", "uvicorn", 
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
    
    # Step 1: Wait for database
    if not wait_for_database():
        sys.exit(1)
    
    # Step 2: Initialize database
    if not initialize_database():
        sys.exit(1)
    
    # Step 3: Setup vector store (non-critical)
    setup_vector_store()
    
    # Step 4: Start application
    start_application()

if __name__ == "__main__":
    main()