#!/usr/bin/env python3

import sys
import requests
import time

# Reconfigure stdout/stderr for Unicode emojis on Windows
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

def test_enhanced_report():
    """Test the enhanced compliance report generation"""
    
    # Read test file
    import os
    test_file_path = os.path.join(os.path.dirname(__file__), 'fixtures', 'test_compliance.txt')
    with open(test_file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Prepare the file for upload
    files = {
        'user_document': ('test_compliance.txt', content, 'text/plain')
    }
    
    data = {
        'user_query': 'Generate detailed Indian Companies Act compliance report'
    }
    
    print("🔍 Testing enhanced compliance report generation...")
    print("📄 Uploading test compliance document...")
    
    try:
        # Make the API request
        response = requests.post(
            'http://localhost:8000/generate-detailed-report/',
            files=files,
            data=data,
            timeout=30
        )
        
        print(f"📊 API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            # Save the PDF
            pdf_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'reports', 'enhanced_compliance_report_test.pdf')
            with open(pdf_path, 'wb') as f:
                f.write(response.content)
            print("✅ Enhanced compliance report generated successfully!")
            print(f"📄 PDF saved as: {pdf_path}")
            print(f"📋 PDF size: {len(response.content)} bytes")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")

def test_health():
    """Test API health"""
    try:
        response = requests.get('http://localhost:8000/health')
        print(f"🔍 Health check: {response.status_code}")
        print(f"📊 Response: {response.json()}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")

if __name__ == "__main__":
    print("🚀 Starting API tests...")
    
    # Test health first
    test_health()
    print()
    
    # Test enhanced report
    test_enhanced_report()
    
    print("\n🏁 Testing completed!")