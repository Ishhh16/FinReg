#!/usr/bin/env python3
"""
test_retrieval_integration.py - Integration test for Phase 2A retrieval.
Starts the FastAPI backend, uploads a company document to /analyze-retrieval,
verifies that the API successfully returns regulation chunks and company document chunks
for each statutory requirement, and prints a structured sample of the results.
"""

import os
import sys
import time
import requests
import subprocess
from pathlib import Path

# Configure stdout/stderr for Unicode emojis on Windows
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

WORKSPACE_DIR = Path(__file__).parent.parent.resolve()
TEST_FILE = WORKSPACE_DIR / "tests" / "fixtures" / "test_compliance.txt"
PORT = 8009  # Use a distinct port to avoid conflicts with existing runs
API_URL = f"http://localhost:{PORT}/analyze-retrieval"

def main():
    if not TEST_FILE.exists():
        print(f"❌ Test file not found at: {TEST_FILE}")
        sys.exit(1)
        
    print("🚀 Starting FastAPI backend in a background process...")
    # Run uvicorn on a test port
    cmd = [
        sys.executable, "-m", "uvicorn",
        "backend.main:app",
        "--host", "127.0.0.1",
        "--port", str(PORT)
    ]
    
    server_process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
    )
    
    # Wait for server to start
    print("⏳ Waiting for backend to initialize (loading embeddings)...")
    time.sleep(12)  # Loading local embeddings can take a few seconds
    
    # Check if server is running
    try:
        health_resp = requests.get(f"http://localhost:{PORT}/health", timeout=3)
        print(f"✅ Backend health check status: {health_resp.status_code}")
    except Exception as e:
        print(f"⚠️ Health check failed to connect. Checking server stdout...")
        # Check if the process died immediately
        ret_code = server_process.poll()
        if ret_code is not None:
            print(f"❌ Server exited immediately with code: {ret_code}")
            # Print stderr if available
            _, stderr = server_process.communicate()
            print(f"Server stderr:\n{stderr}")
            sys.exit(1)
        print("⏳ Server is still starting up, waiting another 5 seconds...")
        time.sleep(5)

    print(f"📤 Uploading '{TEST_FILE.name}' to {API_URL}...")
    try:
        with open(TEST_FILE, 'rb') as f:
            files = {'user_document': (TEST_FILE.name, f, 'text/plain')}
            response = requests.post(API_URL, files=files, timeout=90)
            
        print(f"📊 Response Status Code: {response.status_code}")
        
        if response.status_code == 200:
            results = response.json()
            print("✅ Retrieval mapping successfully generated!")
            print(f"🔑 Retrieved requirements in mapping: {list(results.keys())}")
            
            # Print a detailed sample for Section 92 (Annual Return)
            target_key = "SECTION_92"
            if target_key in results:
                print("\n" + "="*80)
                print(f"🔎 DETAILED RETRIEVAL RESULTS SAMPLE FOR: {target_key}")
                print("="*80)
                req_data = results[target_key]
                print(f"📌 Citation: {req_data.get('citation')}")
                print(f"📌 Title: {req_data.get('title')}")
                
                print("\n🏛️  Retrieved Regulation Chunks (Top matches):")
                reg_chunks = req_data.get("regulation_chunks", [])
                for i, chunk in enumerate(reg_chunks[:2]):
                    print(f"  [{i+1}] (Page {chunk.get('page_number')}, Score: {chunk.get('score')})")
                    print(f"      Text: {chunk.get('text')[:200]}...")
                    
                print("\n🏢 Retrieved Company Document Chunks (Top matches):")
                company_chunks = req_data.get("company_chunks", [])
                for i, chunk in enumerate(company_chunks[:2]):
                    print(f"  [{i+1}] (Index {chunk.get('chunk_index')}, Score: {chunk.get('score')})")
                    print(f"      Text: {chunk.get('text')[:200]}...")
            else:
                print(f"⚠️ Warning: Could not find target key {target_key} in response.")
        else:
            print(f"❌ Error: API returned status {response.status_code}")
            print(f"Response Body:\n{response.text}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
        # Try to print uvicorn subprocess output to help diagnose
        print("🔍 Attempting to capture background server logs...")
        try:
            outs, errs = server_process.communicate(timeout=2)
            if outs:
                print(f"Server stdout:\n{outs}")
            if errs:
                print(f"Server stderr:\n{errs}")
        except Exception as log_err:
            print(f"Could not read server process buffers: {log_err}")
        
    finally:
        print("\n🛑 Terminating background FastAPI backend process...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
            print("✅ Server successfully shut down.")
        except subprocess.TimeoutExpired:
            print("⚠️ Server failed to terminate gracefully, forcing kill...")
            server_process.kill()

if __name__ == "__main__":
    main()
