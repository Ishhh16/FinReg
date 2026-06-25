#!/usr/bin/env python3
"""
test_pdf_report.py - Standalone test for Phase 2C Report Integration.
Runs the complete RAG compliance analysis on a sample company document,
generates the professional PDF report, saves it, and verifies that the PDF
exists and contains compliance findings (e.g. "SECTION_134" or "SECTION_139").
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Reconfigure stdout/stderr for Unicode emojis on Windows
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

WORKSPACE_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(WORKSPACE_DIR))
sys.path.insert(0, str(WORKSPACE_DIR / "backend"))

# Load environment variables
load_dotenv(WORKSPACE_DIR / ".env")

try:
    from backend.professional_enhanced_compliance import create_professional_compliance_report
except ImportError:
    from professional_enhanced_compliance import create_professional_compliance_report

def main():
    test_file = WORKSPACE_DIR / "tests" / "fixtures" / "test_compliance.txt"
    if not test_file.exists():
        print(f"❌ Error: Test company document not found at {test_file}")
        sys.exit(1)
        
    print(f"📄 Reading company test document: {test_file.name}")
    with open(test_file, 'r', encoding='utf-8', errors='ignore') as f:
        document_text = f.read()
        
    print(f"📊 Running compliance analysis & generating PDF (Single Call to Gemini)...")
    
    # Save the output PDF path
    output_pdf_path = WORKSPACE_DIR / "reports" / "enhanced_compliance_report_test.pdf"
    
    try:
        # 1. Run compliance analysis and generate PDF
        pdf_bytes = create_professional_compliance_report(
            text_content=document_text,
            company_name="TechCorp India"
        )
        
        # 2. Save PDF to disk
        with open(output_pdf_path, 'wb') as f:
            f.write(pdf_bytes)
            
        print(f"✅ PDF report generated successfully at: {output_pdf_path}")
        
        # 3. Verify the PDF file exists
        if not output_pdf_path.exists():
            print("❌ Failure: PDF report file does not exist on disk!")
            sys.exit(1)
            
        file_size = output_pdf_path.stat().st_size
        print(f"📦 PDF File size: {file_size} bytes")
        if file_size == 0:
            print("❌ Failure: PDF report file is empty!")
            sys.exit(1)
            
        # 4. Verify at least one compliance finding is rendered in the PDF using fitz
        import fitz
        doc = fitz.open(output_pdf_path)
        num_pages = len(doc)
        print(f"📄 Generated PDF has {num_pages} pages.")
        
        # Extract text from all pages
        pdf_text = ""
        for i in range(num_pages):
            page = doc.load_page(i)
            pdf_text += page.get_text()
            
        # Check for presence of compliance requirements or statuses
        requirements = ["SECTION_134", "SECTION_139", "SECTION_92", "SECTION_96", "SECTION_137", "SECTION_203", "SECTION_149", "SECTION_184"]
        statuses = ["Compliant", "Partially Compliant", "Non-Compliant"]
        
        found_reqs = [r for r in requirements if r in pdf_text]
        found_statuses = [s for s in statuses if s in pdf_text]
        
        print("\n🔍 Verification Check:")
        print(f"  - Found requirements in PDF: {found_reqs}")
        print(f"  - Found compliance statuses in PDF: {found_statuses}")
        
        assert len(found_reqs) > 0, "No compliance requirement codes found in the generated PDF!"
        assert len(found_statuses) > 0, "No compliance status strings found in the generated PDF!"
        
        # Verify citations or page numbers are in the PDF text
        assert any(term in pdf_text for term in ["Page", "compliance rules", "p."]), "No regulation citations/page references found in the PDF!"
        
        print("\n🎉 Success: Standalone PDF generation test passed! All verification assertions succeeded.")
        
    except Exception as e:
        print(f"❌ Error during PDF report generation test: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
