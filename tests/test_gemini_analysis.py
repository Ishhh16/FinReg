#!/usr/bin/env python3
"""
test_gemini_analysis.py - Standalone test for Phase 2B Gemini evaluation.
Retrieves context chunks for each compliance requirement, prompts gemini-2.5-flash
with a single structured prompt using JSON mode, and prints the verified compliance findings.
Also tests the automatic single-try repair/retry logic if the output is invalid.
"""

import os
import sys
import json
from typing import List, Dict, Any
from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Reconfigure stdout/stderr for Unicode emojis on Windows
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

WORKSPACE_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(WORKSPACE_DIR))
sys.path.insert(0, str(WORKSPACE_DIR / "backend"))

# Load environment variables
load_dotenv(WORKSPACE_DIR / ".env")
load_dotenv(WORKSPACE_DIR / "backend" / ".env")  # Fallback

# Import custom modules
try:
    from backend.professional_enhanced_compliance import ProfessionalEnhancedComplianceAnalyzer
    from backend.utils import extract_text
except ImportError:
    from professional_enhanced_compliance import ProfessionalEnhancedComplianceAnalyzer
    from utils import extract_text

# Define strict Pydantic schemas for Gemini Structured Output
class ComplianceFinding(BaseModel):
    requirement_code: str = Field(description="The unique code of the compliance requirement (e.g. SECTION_92, SECTION_134)")
    regulation_name: str = Field(description="The name of the regulation / legal citation (e.g. Section 92, Companies Act, 2013)")
    status: str = Field(description="The compliance status: Compliant, Partially Compliant, or Non-Compliant")
    reasoning: str = Field(description="Detailed explanation comparing the company text against the official regulation rules")
    evidence_company: str = Field(description="Verbatim exact quote(s) from the company document showing compliance or gaps")
    evidence_regulation: str = Field(description="Verbatim exact quote(s) from the retrieved official regulation chunks")
    remediation: str = Field(description="Clear, actionable remediation steps if not fully compliant. Empty list/text if fully compliant.")
    confidence_score: float = Field(description="A confidence score for this compliance assessment between 0.0 and 1.0")

class ComplianceReportSchema(BaseModel):
    findings: List[ComplianceFinding]

def generate_rag_prompt(retrieval_results: Dict[str, Any]) -> str:
    """Builds a single prompt containing context chunks for all requirements."""
    context_str = ""
    for req_code, req_data in retrieval_results.items():
        context_str += f"=== REQUIREMENT: {req_code} ===\n"
        context_str += f"Title: {req_data['title']}\n"
        context_str += f"Legal Citation: {req_data['citation']}\n"
        
        context_str += "\n--- RETRIEVED REGULATIONS (OFFICIAL RULES) ---\n"
        reg_chunks = req_data.get("regulation_chunks", [])
        if reg_chunks:
            for idx, r in enumerate(reg_chunks):
                context_str += f"[{idx+1}] (Page {r['page_number']}, Source: {r['source_filename']}): {r['text']}\n"
        else:
            context_str += "[No official regulation chunks retrieved]\n"
            
        context_str += "\n--- RETRIEVED COMPANY DOCUMENT EXCERPTS ---\n"
        company_chunks = req_data.get("company_chunks", [])
        if company_chunks:
            for idx, c in enumerate(company_chunks):
                context_str += f"[{idx+1}] (Relevance Score: {c['score']}): {c['text']}\n"
        else:
            context_str += "[No matching company document excerpts found in the uploaded text]\n"
        context_str += "\n=========================================\n\n"

    prompt = f"""You are a professional financial compliance auditor specializing in the Indian Companies Act, 2013.
Your task is to analyze the compliance of the uploaded company document excerpts against the retrieved official regulations.

For each compliance requirement:
1. Compare the company excerpts (evidence of compliance) against the retrieved regulation rules.
2. Determine the status:
   - "Compliant": If the company document contains clear evidence meeting all the regulation requirements.
   - "Partially Compliant": If some evidence is found but it fails to show complete implementation or misses key legal details.
   - "Non-Compliant": If the company document fails to address the requirement, or indicates a direct breach.
3. Extract exact verbatim quotes from both the company excerpts and the regulation chunks as supporting evidence.
4. If the status is not "Compliant", provide actionable remediation instructions.

Evaluate all of the following requirements at once. Rely ONLY on the provided contexts. Do not hallucinate or assume compliance if no evidence is found in the excerpts.

Here is the context data:
{context_str}

Please generate the report list of findings in the exact JSON schema requested.
"""
    return prompt

def run_gemini_analysis(prompt: str) -> Dict[str, Any]:
    """Executes the single Gemini API call with schema constraints and auto-repair logic."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ Error: GEMINI_API_KEY environment variable is not set!")
        sys.exit(1)

    import google.generativeai as genai
    genai.configure(api_key=api_key)
    
    print("🤖 Instantiating gemini-2.5-flash model...")
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    # Configure JSON mode and supply the Pydantic schema
    generation_config = {
        "response_mime_type": "application/json",
        "response_schema": ComplianceReportSchema
    }
    
    print("⏳ Invoking Gemini 2.5 Flash API for compliance analysis (Single Call)...")
    try:
        response = model.generate_content(prompt, generation_config=generation_config)
        raw_output = response.text
        
        # Try to parse response text
        try:
            parsed_data = json.loads(raw_output)
            print("✅ Gemini successfully returned valid JSON matching the schema.")
            return parsed_data
        except json.JSONDecodeError as je:
            print(f"⚠️ Warning: Gemini returned invalid JSON. Error: {je}")
            print("🧹 Attempting automatic JSON repair/retry prompt...")
            
            repair_prompt = f"""The previous response returned invalid JSON which failed parsing:
Error: {je}
Response received:
```json
{raw_output}
```

Please fix the formatting, ensuring it is 100% valid JSON and conforms strictly to the schema description:
- The top-level key must be "findings" (a list of objects).
- Each finding object must contain: requirement_code, regulation_name, status, reasoning, evidence_company, evidence_regulation, remediation, confidence_score.
"""
            # Rerun with the repair prompt
            repair_response = model.generate_content(repair_prompt, generation_config=generation_config)
            parsed_data = json.loads(repair_response.text)
            print("🎉 Repair successful! Cleaned JSON parsed successfully on retry.")
            return parsed_data
            
    except Exception as e:
        print(f"❌ Gemini API Call or Parsing failed: {e}")
        sys.exit(1)

def main():
    test_file = WORKSPACE_DIR / "tests" / "fixtures" / "test_compliance.txt"
    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        sys.exit(1)
        
    print(f"📄 Reading company test document: {test_file.name}")
    with open(test_file, 'rb') as f:
        file_bytes = f.read()
        
    # 1. Extract text
    text_content = extract_text(file_bytes, filename=test_file.name)
    print(f"✅ Text extracted: {len(text_content)} characters.")
    
    # 2. Run retrieval engine
    analyzer = ProfessionalEnhancedComplianceAnalyzer()
    retrieval_results = analyzer.retrieve_compliance_context(text_content)
    print("✅ Context retrieval complete.")
    
    # 3. Generate RAG Prompt
    prompt = generate_rag_prompt(retrieval_results)
    
    # 4. Invoke Gemini LLM
    findings_json = run_gemini_analysis(prompt)
    
    # 5. Print results
    print("\n" + "="*80)
    print("🏆 GEMINI COMPLIANCE REPORT JSON OUTPUT")
    print("="*80)
    print(json.dumps(findings_json, indent=2))
    print("="*80)
    
    # Verify that we got results for the requirements
    findings = findings_json.get("findings", [])
    print(f"\n📊 Summary: Evaluated {len(findings)} requirements.")
    for f in findings:
        status_icon = "🟢" if f['status'] == "Compliant" else "🟡" if f['status'] == "Partially Compliant" else "🔴"
        print(f"  {status_icon} {f['requirement_code']} ({f['regulation_name']}): {f['status']} - Conf: {f.get('confidence_score', 0.0):.2f}")

if __name__ == "__main__":
    main()
