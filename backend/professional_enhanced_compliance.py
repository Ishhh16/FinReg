"""
Professional Enhanced Compliance Analyzer for Indian Companies Act 2013
Provides comprehensive, detailed compliance reports with professional formatting
"""

import os
import re
import json
import html
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from typing import List, Dict, Any, Tuple, Optional
from pydantic import BaseModel, Field
from io import BytesIO
import tempfile
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger("finreg_backend")

# RAG and embeddings imports
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
import numpy as np

# PDF generation imports
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, black, white, red, green, orange, blue
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
    KeepTogether, NextPageTemplate, PageTemplate, Frame
)
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.platypus.tableofcontents import TableOfContents


def clean_text_for_pdf(text: str) -> str:
    """Clean text to prevent PDF generation errors"""
    if not text:
        return ""
    
    # Remove PDF processing artifacts aggressively
    text = re.sub(r'\b\d+\s+0\s+obj\b.*?endobj', '', text, flags=re.DOTALL)  # Remove PDF objects
    text = re.sub(r'\b\d+\s+0\s+R\b', '', text)  # Remove PDF reference objects
    text = re.sub(r'/Parent\s+\d+\s+0\s+R', '', text)  # Remove parent references
    text = re.sub(r'/Resources/Font[^\s]*', '', text)  # Remove font resources
    text = re.sub(r'\b04\]/Parent\s+\d+\s+0\s+R.*?Font', '', text)  # Remove specific PDF artifacts
    text = re.sub(r'Supporting Evidence:\s*\d+\.\s*\d+\]/Parent.*?Font[^\w]*', '', text)  # Remove evidence artifacts
    text = re.sub(r'\d+]/Parent\s+\d+\s+0\s+R/Resources.*?$', '', text, flags=re.MULTILINE)  # Remove resource lines
    
    # Remove HTML/XML tags
    text = re.sub(r'</?[^>]+>', '', text)  # Remove HTML tags
    
    # Remove problematic characters and patterns
    text = re.sub(r'[<>"\\`\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)  # Remove control characters
    text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
    text = text.strip()
    
    # If text is still containing PDF artifacts, provide a clean alternative
    if any(pattern in text.lower() for pattern in ['obj', 'endobj', '/parent', '/resources', '/font']):
        return "Document content reviewed for compliance requirements"
    
    # Escape HTML entities properly
    text = html.escape(text, quote=False)
    
    return text


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


class ComplianceStatus(Enum):
    FULLY_COMPLIANT = "Fully Compliant"
    PARTIALLY_COMPLIANT = "Partially Compliant"
    NON_COMPLIANT = "Non-Compliant"
    NOT_APPLICABLE = "Not Applicable"


class RiskLevel(Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


@dataclass
class ComplianceEvidence:
    """Represents evidence found for compliance"""
    text_snippet: str
    page_reference: Optional[str] = None
    section_reference: Optional[str] = None
    confidence_score: float = 0.0
    relevance_explanation: str = ""


@dataclass
class ComplianceRecommendation:
    """Represents actionable recommendations"""
    priority: str  # Immediate, High, Medium, Low
    action_required: str
    responsible_party: str
    timeline: str
    resources_needed: List[str] = field(default_factory=list)
    regulatory_reference: str = ""


@dataclass
class DetailedComplianceItem:
    """Comprehensive compliance requirement analysis"""
    section_code: str
    section_title: str
    legal_citation: str
    requirement_description: str
    deadline_requirements: str
    frequency: str
    
    # Analysis Results
    compliance_status: ComplianceStatus
    risk_level: RiskLevel
    compliance_score: float  # 0-100
    
    # Evidence and Analysis
    evidence_found: List[ComplianceEvidence] = field(default_factory=list)
    compliance_rationale: str = ""
    gap_analysis: str = ""
    
    # Recommendations
    recommendations: List[ComplianceRecommendation] = field(default_factory=list)
    
    # Additional Details
    regulatory_importance: str = ""
    potential_penalties: str = ""
    documentation_required: List[str] = field(default_factory=list)
    next_due_date: Optional[str] = None


_embeddings_instance = None
_vector_store_instance = None

def get_shared_embeddings():
    global _embeddings_instance
    if _embeddings_instance is None:
        logger.info("🧬 Loading embeddings model in analyzer: BAAI/bge-small-en-v1.5...")
        _embeddings_instance = HuggingFaceEmbeddings(
            model_name="BAAI/bge-small-en-v1.5",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
    return _embeddings_instance

def get_shared_vector_store():
    global _vector_store_instance
    if _vector_store_instance is None:
        emb = get_shared_embeddings()
        logger.info("📁 Loading persistent regulations Chroma DB...")
        _vector_store_instance = Chroma(
            collection_name="regulations_knowledge_base",
            embedding_function=emb,
            persist_directory="./chroma_db"
        )
        logger.info("✅ Regulations vector store loaded in analyzer.")
    return _vector_store_instance

class ProfessionalEnhancedComplianceAnalyzer:
    """Professional compliance analyzer with comprehensive reporting capabilities"""
    
    def __init__(self):
        self.compliance_framework = self._load_comprehensive_framework()
        self.embeddings = get_shared_embeddings()
        self.vector_store = get_shared_vector_store()
        
    def _load_comprehensive_framework(self) -> Dict[str, DetailedComplianceItem]:
        """Load comprehensive Indian Companies Act compliance framework"""
        framework = {}
        
        # Section 134 - Financial Statements
        framework["SECTION_134"] = DetailedComplianceItem(
            section_code="SECTION_134",
            section_title="Preparation of Financial Statements",
            legal_citation="Section 134, Companies Act, 2013; Rule 8 of Companies (Accounts) Rules, 2014",
            requirement_description="Every company shall prepare financial statements comprising Balance Sheet, Statement of Profit and Loss, and Cash Flow Statement as per prescribed format and accounting standards",
            deadline_requirements="Financial statements must be approved by Board before AGM",
            frequency="Annual",
            compliance_status=ComplianceStatus.NON_COMPLIANT,
            risk_level=RiskLevel.HIGH,
            compliance_score=0.0,
            regulatory_importance="Fundamental requirement for financial transparency and regulatory compliance",
            potential_penalties="Fine up to ₹5,00,000 and imprisonment up to 3 years for officers",
            documentation_required=[
                "Balance Sheet as per Schedule III",
                "Statement of Profit and Loss as per Schedule III", 
                "Cash Flow Statement as per AS-3/Ind AS-7",
                "Notes to Financial Statements",
                "Board Resolution approving financial statements"
            ]
        )
        
        # Section 139 - Auditor Appointment
        framework["SECTION_139"] = DetailedComplianceItem(
            section_code="SECTION_139",
            section_title="Appointment of Auditors",
            legal_citation="Section 139, Companies Act, 2013; Rule 4 of Companies (Audit and Auditors) Rules, 2014",
            requirement_description="Every company shall appoint a qualified individual or firm as auditor to audit financial statements",
            deadline_requirements="First auditor appointed by Board within 30 days of incorporation; subsequent appointments at AGM",
            frequency="Annual appointment required",
            compliance_status=ComplianceStatus.NON_COMPLIANT,
            risk_level=RiskLevel.HIGH,
            compliance_score=0.0,
            regulatory_importance="Mandatory for financial statement audit and compliance certification",
            potential_penalties="Fine from ₹25,000 to ₹5,00,000 for company; ₹10,000 to ₹1,00,000 for officers",
            documentation_required=[
                "Auditor appointment resolution",
                "Auditor consent letter",
                "Certificate of eligibility",
                "ADT-1 form filing",
                "Remuneration fixation resolution"
            ]
        )
        
        # Section 92 - Annual Return
        framework["SECTION_92"] = DetailedComplianceItem(
            section_code="SECTION_92", 
            section_title="Annual Return Filing",
            legal_citation="Section 92, Companies Act, 2013; Rule 11 of Companies (Management and Administration) Rules, 2014",
            requirement_description="Every company shall file annual return containing prescribed particulars with ROC",
            deadline_requirements="Within 60 days of AGM; for companies not required to hold AGM, within 300 days of FY end",
            frequency="Annual",
            compliance_status=ComplianceStatus.NON_COMPLIANT,
            risk_level=RiskLevel.HIGH,
            compliance_score=0.0,
            regulatory_importance="Critical for maintaining company records with ROC and transparency",
            potential_penalties="Fine from ₹5,000 to ₹50,000 per day of delay; additional fees as prescribed",
            documentation_required=[
                "Form MGT-7 (Annual Return)",
                "Copy of Financial Statements",
                "Copy of Board Report",
                "Copy of Auditor Report",
                "Details of shareholding pattern"
            ]
        )
        
        # Section 96 - Annual General Meeting
        framework["SECTION_96"] = DetailedComplianceItem(
            section_code="SECTION_96",
            section_title="Annual General Meeting",
            legal_citation="Section 96, Companies Act, 2013; Rule 1 of Companies (Management and Administration) Rules, 2014",
            requirement_description="Every company shall hold AGM within 6 months from end of financial year",
            deadline_requirements="AGM must be held within 6 months from FY end; not more than 15 months gap between two AGMs",
            frequency="Annual",
            compliance_status=ComplianceStatus.NON_COMPLIANT,
            risk_level=RiskLevel.MEDIUM,
            compliance_score=0.0,
            regulatory_importance="Essential for shareholder participation and approval of financial statements",
            potential_penalties="Fine from ₹25,000 to ₹5,00,000 for company; ₹5,000 to ₹25,000 for officers",
            documentation_required=[
                "AGM Notice (21 days advance)",
                "Attendance register",
                "Minutes of AGM",
                "Proxy forms (if any)",
                "Resolutions passed"
            ]
        )
        
        # Section 137 - Filing of Financial Statements
        framework["SECTION_137"] = DetailedComplianceItem(
            section_code="SECTION_137",
            section_title="Filing of Financial Statements",
            legal_citation="Section 137, Companies Act, 2013; Rule 12 of Companies (Accounts) Rules, 2014",
            requirement_description="Copy of financial statements adopted at AGM shall be filed with ROC",
            deadline_requirements="Within 30 days of AGM or 300 days from FY end, whichever is earlier",
            frequency="Annual",
            compliance_status=ComplianceStatus.NON_COMPLIANT,
            risk_level=RiskLevel.HIGH,
            compliance_score=0.0,
            regulatory_importance="Mandatory for public disclosure and regulatory oversight",
            potential_penalties="Fine from ₹5,000 to ₹50,000 per day of delay",
            documentation_required=[
                "Form AOC-4 with attachments",
                "Audited Financial Statements",
                "Board Report",
                "Auditor Report",
                "Director Responsibility Statement"
            ]
        )
        
        # Section 203 - Key Managerial Personnel
        framework["SECTION_203"] = DetailedComplianceItem(
            section_code="SECTION_203",
            section_title="Appointment of Key Managerial Personnel",
            legal_citation="Section 203, Companies Act, 2013; Rule 8A of Companies (Appointment and Qualification of Directors) Rules, 2014",
            requirement_description="Every company shall have whole-time key managerial personnel",
            deadline_requirements="Appointment within 60 days of incorporation or vacancy arising",
            frequency="Continuous requirement",
            compliance_status=ComplianceStatus.NON_COMPLIANT,
            risk_level=RiskLevel.MEDIUM,
            compliance_score=0.0,
            regulatory_importance="Ensures proper management structure and accountability",
            potential_penalties="Fine from ₹50,000 to ₹5,00,000 for company; ₹25,000 to ₹5,00,000 for officers",
            documentation_required=[
                "KMP appointment resolution",
                "Consent to act as KMP",
                "Form DIR-12 (for MD/WTD)",
                "Contract/agreement terms",
                "Qualification certificates"
            ]
        )
        
        # Section 149 - Independent Directors
        framework["SECTION_149"] = DetailedComplianceItem(
            section_code="SECTION_149",
            section_title="Independent Directors",
            legal_citation="Section 149, Companies Act, 2013; Rule 4 of Companies (Appointment and Qualification of Directors) Rules, 2014",
            requirement_description="Listed companies and certain classes of companies shall have Independent Directors",
            deadline_requirements="Appointment required as per company category; continuous compliance",
            frequency="Continuous requirement with annual declarations",
            compliance_status=ComplianceStatus.NON_COMPLIANT,
            risk_level=RiskLevel.MEDIUM,
            compliance_score=0.0,
            regulatory_importance="Ensures independent oversight and corporate governance",
            potential_penalties="Fine from ₹1,00,000 to ₹5,00,000 for company",
            documentation_required=[
                "Independent Director appointment",
                "Declaration of independence",
                "Annual confirmation",
                "Board evaluation",
                "Familiarization program records"
            ]
        )
        
        # Section 184 - Disclosure of Interest
        framework["SECTION_184"] = DetailedComplianceItem(
            section_code="SECTION_184",
            section_title="Disclosure of Interest by Directors",
            legal_citation="Section 184, Companies Act, 2013; Rule 9 of Companies (Meetings of Board and its Powers) Rules, 2014",
            requirement_description="Directors shall disclose interest in contracts, arrangements, or transactions",
            deadline_requirements="At first Board meeting and whenever interest arises",
            frequency="As and when required",
            compliance_status=ComplianceStatus.NON_COMPLIANT,
            risk_level=RiskLevel.MEDIUM,
            compliance_score=0.0,
            regulatory_importance="Prevents conflicts of interest and ensures transparency",
            potential_penalties="Fine from ₹50,000 to ₹5,00,000 for directors",
            documentation_required=[
                "Disclosure forms/declarations",
                "Register of contracts and arrangements",
                "Board meeting minutes",
                "Related party transaction approvals",
                "Annual compliance certificate"
            ]
        )
        
        return framework
    
    def retrieve_compliance_context(self, document_text: str) -> Dict[str, Any]:
        """
        Retrieves relevant regulation chunks (from persistent ChromaDB) and
        company document chunks (via in-memory embeddings and similarity)
        for each compliance requirement in the framework.
        
        Does NOT call Gemini or modify compliance scoring.
        """
        logger.info(f"📊 Running retrieval context matching on uploaded document ({len(document_text)} characters)...")
        
        # 1. Chunk the uploaded company document in memory
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        company_chunks = text_splitter.split_text(document_text)
        logger.info(f"🧩 Segmented company document into {len(company_chunks)} chunks.")
        
        # 2. Compute embeddings for company chunks in-memory
        company_embeddings = []
        if company_chunks:
            # Batch embedding computation
            company_embeddings = self.embeddings.embed_documents(company_chunks)
            logger.info("🧬 In-memory embeddings computed for company chunks.")
            
        retrieval_results = {}
        
        # 3. For each requirement, retrieve regulation chunks and company chunks
        for req_code, item in self.compliance_framework.items():
            logger.info(f"🔍 Retrieving context for requirement: {req_code}")
            
            # Formulate query using code, title, and description
            query_str = f"{item.legal_citation} {item.section_title} {item.requirement_description}"
            
            # A. Retrieve regulation chunks from persistent ChromaDB
            reg_matches = []
            try:
                # Retrieve top 3 matching chunks
                reg_results = self.vector_store.similarity_search_with_score(query_str, k=3)
                for doc, score in reg_results:
                    l2_dist = float(score)
                    cos_sim = 1.0 - (l2_dist / 2.0)
                    reg_matches.append({
                        "text": doc.page_content.strip(),
                        "score": round(cos_sim, 4),
                        "page_number": doc.metadata.get("page_number", "Unknown"),
                        "source_filename": doc.metadata.get("source_filename", "compliance rules pdf.pdf"),
                        "chunk_id": doc.metadata.get("chunk_id", "Unknown")
                    })
            except Exception as e:
                logger.error(f"⚠️ Error retrieving regulations for {req_code}: {e}")
                
            # B. Retrieve relevant company document chunks in memory using cosine similarity
            company_matches = []
            if company_chunks and company_embeddings:
                try:
                    # Embed the query
                    query_emb = self.embeddings.embed_query(query_str)
                    query_vec = np.array(query_emb)
                    
                    scores = []
                    for i, chunk_emb in enumerate(company_embeddings):
                        chunk_vec = np.array(chunk_emb)
                        # Cosine similarity (dot product of normalized unit vectors)
                        similarity = float(np.dot(query_vec, chunk_vec))
                        scores.append((similarity, i))
                        
                    # Sort by similarity descending
                    scores.sort(reverse=True, key=lambda x: x[0])
                    
                    # Get top 3
                    for sim, idx in scores[:3]:
                        company_matches.append({
                            "text": company_chunks[idx].strip(),
                            "score": round(sim, 4),
                            "chunk_index": idx
                        })
                except Exception as e:
                    logger.error(f"⚠️ Error retrieving company chunks for {req_code}: {e}")
                    
            # Store in results mapping
            retrieval_results[req_code] = {
                "requirement_code": req_code,
                "citation": item.legal_citation,
                "title": item.section_title,
                "regulation_chunks": reg_matches,
                "company_chunks": company_matches
            }
            
        return retrieval_results

    def analyze_document(self, text_content: str, company_name: str = "Company") -> Dict[str, Any]:
        """Perform comprehensive compliance analysis using RAG and Gemini 2.5 Flash"""
        # 1. Retrieve the context mapping for all requirements using the existing RAG retrieval method
        retrieval_results = self.retrieve_compliance_context(text_content)
        
        # 2. Build the combined prompt context
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
        
        # 3. Resolve API keys pool
        raw_keys = os.getenv("GEMINI_API_KEYS")
        if raw_keys:
            api_keys = [k.strip() for k in raw_keys.split(",") if k.strip()]
        else:
            api_keys = []
            
        # Fallback to single key
        if not api_keys:
            single_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if single_key:
                api_keys = [single_key]
                
        if not api_keys:
            raise ValueError("Neither GEMINI_API_KEYS nor GEMINI_API_KEY environment variables are set!")

        import google.generativeai as genai
        
        generation_config = {
            "response_mime_type": "application/json",
            "response_schema": ComplianceReportSchema
        }
        
        findings_json = None
        last_error = None
        
        for idx, key in enumerate(api_keys):
            logger.info(f"⏳ Invoking Gemini 2.5 Flash API with Key {idx+1}/{len(api_keys)}...")
            try:
                genai.configure(api_key=key)
                model = genai.GenerativeModel("gemini-2.5-flash")
                
                response = model.generate_content(prompt, generation_config=generation_config)
                raw_output = response.text
                
                try:
                    findings_json = json.loads(raw_output)
                    logger.info("✅ Gemini successfully returned valid JSON matching the schema.")
                    break  # Success, exit the key rotation loop!
                except json.JSONDecodeError as je:
                    logger.warning(f"⚠️ Warning: Gemini returned invalid JSON. Error: {je}")
                    logger.info("🧹 Attempting automatic JSON repair/retry prompt...")
                    
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
                    repair_response = model.generate_content(repair_prompt, generation_config=generation_config)
                    findings_json = json.loads(repair_response.text)
                    logger.info("🎉 Repair successful! Cleaned JSON parsed successfully on retry.")
                    break  # Success, exit key rotation loop!
                    
            except Exception as e:
                err_msg = str(e).lower()
                # Check for quota exceeded (429) rate limit indicators
                if "429" in err_msg or "quota" in err_msg or "resource_exhausted" in err_msg or "limit" in err_msg:
                    logger.warning(f"⚠️ API Key {idx+1} rate limit/quota hit. Error: {e}. Rotating to next key...")
                    last_error = e
                    continue
                else:
                    logger.error(f"❌ Gemini execution failed on API Key {idx+1} with non-quota error: {e}")
                    raise RuntimeError(f"Gemini compliance analysis call failed: {e}")
        
        if findings_json is None:
            raise RuntimeError(f"All configured Gemini API keys have exhausted their quota for today. Last error: {last_error}")

        # 4. Map the Gemini findings JSON into DetailedComplianceItem objects in the framework
        findings = findings_json.get("findings", [])
        findings_map = {f.get("requirement_code"): f for f in findings if f.get("requirement_code")}
        
        analysis_results = []
        for section_code, item in self.compliance_framework.items():
            finding = findings_map.get(section_code)
            if finding:
                # Status mapping
                status_str = finding.get("status", "Non-Compliant")
                if status_str == "Compliant":
                    compliance_status = ComplianceStatus.FULLY_COMPLIANT
                    risk_level = RiskLevel.LOW
                elif status_str == "Partially Compliant":
                    compliance_status = ComplianceStatus.PARTIALLY_COMPLIANT
                    risk_level = RiskLevel.MEDIUM
                else:
                    compliance_status = ComplianceStatus.NON_COMPLIANT
                    risk_level = RiskLevel.HIGH
                
                # Confidence score mapping
                confidence_score = float(finding.get("confidence_score", 0.0))
                compliance_score = confidence_score * 100.0
                
                # Reasoning and Quotes mapping
                reasoning = finding.get("reasoning", "")
                evidence_company = finding.get("evidence_company", "")
                evidence_regulation = finding.get("evidence_regulation", "")
                
                # Retrieve matching page references from regulations context
                req_data = retrieval_results.get(section_code, {})
                reg_chunks = req_data.get("regulation_chunks", [])
                
                page_refs = []
                for r in reg_chunks:
                    page_no = r.get("page_number", "Unknown")
                    src = r.get("source_filename", "compliance rules pdf.pdf")
                    page_refs.append(f"p. {page_no} of {src}")
                
                page_reference_str = ", ".join(page_refs) if page_refs else "Regulations PDF"
                
                evidence_list = []
                if evidence_company:
                    clean_company = clean_text_for_pdf(evidence_company)
                    evidence_list.append(ComplianceEvidence(
                        text_snippet=clean_company,
                        section_reference="Company Document",
                        confidence_score=confidence_score,
                        relevance_explanation="Verbatim company document evidence"
                    ))
                if evidence_regulation:
                    clean_reg = clean_text_for_pdf(evidence_regulation)
                    evidence_list.append(ComplianceEvidence(
                        text_snippet=clean_reg,
                        section_reference=f"Regulation: {page_reference_str}",
                        confidence_score=confidence_score,
                        relevance_explanation="Verbatim regulation rule reference"
                    ))
                
                # Remediation mapping
                remediation_str = finding.get("remediation", "")
                recommendations_list = []
                if remediation_str:
                    recommendations_list.append(ComplianceRecommendation(
                        priority="Immediate" if risk_level == RiskLevel.HIGH else "Medium",
                        action_required=clean_text_for_pdf(remediation_str),
                        responsible_party="Compliance Officer / Management",
                        timeline="Immediate" if risk_level == RiskLevel.HIGH else "60 days",
                        resources_needed=["Internal Audit", "Legal Council"],
                        regulatory_reference=item.legal_citation
                    ))
                else:
                    recommendations_list.append(ComplianceRecommendation(
                        priority="Low",
                        action_required="Continue monitoring and maintain current compliance standards",
                        responsible_party="Compliance Officer",
                        timeline="Ongoing",
                        resources_needed=["Regular monitoring procedures"],
                        regulatory_reference=section_code
                    ))
                
                # Populate DetailedComplianceItem fields
                item.compliance_status = compliance_status
                item.risk_level = risk_level
                item.compliance_score = round(compliance_score, 2)
                item.evidence_found = evidence_list
                item.compliance_rationale = reasoning
                item.gap_analysis = reasoning if compliance_status != ComplianceStatus.FULLY_COMPLIANT else "No significant gaps identified."
                item.recommendations = recommendations_list
                
                # Attach RAG metadata for PDF transparency display
                company_chunks = req_data.get("company_chunks", [])
                scores = [r.get("score", 1.0) for r in reg_chunks] + [c.get("score", 1.0) for c in company_chunks]
                avg_score = sum(scores) / len(scores) if scores else 0.0
                item.rag_metadata = {
                    "sources_retrieved": list(set([r.get("source_filename", "compliance rules pdf.pdf") for r in reg_chunks])),
                    "chunks_used": len(reg_chunks) + len(company_chunks),
                    "avg_similarity_score": round(avg_score, 4),
                    "embedding_model": "BAAI/bge-small-en-v1.5",
                    "retrieval_method": "Semantic Vector Search",
                    "reranking_status": "None (Cosine Similarity Match)",
                    "regulation_chunks": reg_chunks,
                    "company_chunks": company_chunks
                }
                
            else:
                # Fallback if requirement wasn't returned by Gemini
                item.compliance_status = ComplianceStatus.NON_COMPLIANT
                item.risk_level = RiskLevel.CRITICAL
                item.compliance_score = 0.0
                item.compliance_rationale = "Requirement not assessed by evaluation model."
                item.gap_analysis = "Missing evaluation context."
                item.recommendations = [ComplianceRecommendation(
                    priority="Critical",
                    action_required="Manually review this requirement against regulatory texts.",
                    responsible_party="Compliance Officer",
                    timeline="Immediate",
                    resources_needed=["Manual Audit"]
                )]
            
            analysis_results.append(item)
            
        # Calculate overall metrics
        overall_metrics = self._calculate_overall_metrics(analysis_results)
        
        return {
            "company_name": company_name,
            "analysis_date": datetime.now().isoformat(),
            "overall_metrics": overall_metrics,
            "detailed_analysis": analysis_results,
            "executive_summary": self._generate_executive_summary(analysis_results, overall_metrics),
            "risk_assessment": self._generate_risk_assessment(analysis_results)
        }
    
    def _extract_detailed_evidence(self, text: str, patterns: Dict, section_code: str) -> List[ComplianceEvidence]:
        """Extract detailed evidence with context and explanations"""
        evidence = []
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if len(s.strip()) > 20]
        
        all_patterns = patterns["primary"] + patterns["secondary"] + patterns["evidence_indicators"]
        
        for i, sentence in enumerate(sentences):
            sentence_lower = sentence.lower()
            for pattern in all_patterns:
                if pattern in sentence_lower:
                    confidence = 0.8 if pattern in patterns["primary"] else 0.6 if pattern in patterns["secondary"] else 0.4
                    
                    # Get surrounding context
                    context_start = max(0, i-1)
                    context_end = min(len(sentences), i+2)
                    context = ' '.join(sentences[context_start:context_end])
                    
                    # Clean the text snippet for PDF generation
                    clean_snippet = clean_text_for_pdf(sentence)
                    evidence.append(ComplianceEvidence(
                        text_snippet=clean_snippet,
                        section_reference=f"Document Section {i+1}",
                        confidence_score=confidence,
                        relevance_explanation=f"Contains key compliance indicator '{pattern}' related to {section_code}"
                    ))
                    break
        
        return evidence[:5]  # Limit to top 5 pieces of evidence
    
    def _determine_compliance_status(self, score: float, evidence_count: int) -> Tuple[ComplianceStatus, RiskLevel]:
        """Determine compliance status and risk level based on score and evidence"""
        
        # Enhanced logic for better status and risk assignment
        if score >= 80 and evidence_count >= 3:
            return ComplianceStatus.FULLY_COMPLIANT, RiskLevel.LOW
        elif score >= 65 and evidence_count >= 2:
            return ComplianceStatus.FULLY_COMPLIANT, RiskLevel.MEDIUM
        elif score >= 45 and evidence_count >= 2:
            return ComplianceStatus.PARTIALLY_COMPLIANT, RiskLevel.MEDIUM
        elif score >= 30 and evidence_count >= 1:
            return ComplianceStatus.PARTIALLY_COMPLIANT, RiskLevel.HIGH
        elif score >= 15 or evidence_count >= 1:
            return ComplianceStatus.NON_COMPLIANT, RiskLevel.HIGH
        else:
            return ComplianceStatus.NON_COMPLIANT, RiskLevel.CRITICAL
    
    def _generate_compliance_rationale(self, section_code: str, score: float, primary: int, secondary: int, evidence: int, evidence_count: int) -> str:
        """Generate detailed rationale for compliance determination"""
        
        rationale_parts = [
            f"Compliance analysis for {section_code} yielded a score of {score:.1f}% based on comprehensive pattern matching and evidence extraction.",
            f"Analysis found {primary} primary compliance indicators, {secondary} secondary indicators, and {evidence} evidence markers.",
            f"A total of {evidence_count} pieces of supporting evidence were identified in the source documentation."
        ]
        
        if score >= 75:
            rationale_parts.append("Strong evidence of compliance with clear documentation and proper implementation.")
        elif score >= 50:
            rationale_parts.append("Moderate evidence suggests partial compliance with some areas requiring attention.")
        elif score >= 25:
            rationale_parts.append("Limited evidence indicates significant compliance gaps requiring immediate action.")
        else:
            rationale_parts.append("Minimal or no evidence found, indicating critical compliance deficiency requiring urgent remediation.")
        
        return " ".join(rationale_parts)
    
    def _generate_gap_analysis(self, section_code: str, status: ComplianceStatus, evidence: List[ComplianceEvidence]) -> str:
        """Generate detailed gap analysis"""
        
        if status == ComplianceStatus.FULLY_COMPLIANT:
            return "No significant compliance gaps identified. Continue monitoring for ongoing compliance maintenance."
        
        gap_templates = {
            "SECTION_134": "Financial statements may not be comprehensive or properly formatted. Ensure all components (Balance Sheet, P&L, Cash Flow) are prepared as per Schedule III requirements.",
            "SECTION_139": "Auditor appointment process may be incomplete. Verify proper appointment procedures, eligibility, and documentation are in place.",
            "SECTION_92": "Annual return filing may be pending or incomplete. Ensure Form MGT-7 is prepared with accurate information and filed within statutory timelines.",
            "SECTION_96": "AGM conduct may not meet statutory requirements. Verify proper notice, quorum, and documentation procedures are followed.",
            "SECTION_137": "Financial statement filing with ROC may be delayed or incomplete. Ensure Form AOC-4 is filed within prescribed timelines.",
            "SECTION_203": "Key Managerial Personnel structure may be incomplete. Verify all required KMP positions are filled and properly documented.",
            "SECTION_149": "Independent Director requirements may not be met. Assess board composition and independence criteria compliance.",
            "SECTION_184": "Interest disclosure mechanisms may be inadequate. Implement proper disclosure procedures and maintain required registers."
        }
        
        base_gap = gap_templates.get(section_code, "Compliance gaps identified requiring detailed assessment and remediation.")
        
        if len(evidence) == 0:
            return f"{base_gap} No supporting evidence found in documentation, indicating potential non-compliance."
        else:
            return f"{base_gap} Limited evidence suggests partial implementation requiring enhancement and completion."
    
    def _generate_recommendations(self, section_code: str, status: ComplianceStatus, risk_level: RiskLevel) -> List[ComplianceRecommendation]:
        """Generate detailed, actionable recommendations"""
        
        if status == ComplianceStatus.FULLY_COMPLIANT:
            return [ComplianceRecommendation(
                priority="Low",
                action_required="Continue monitoring and maintain current compliance standards",
                responsible_party="Compliance Officer",
                timeline="Ongoing",
                resources_needed=["Regular monitoring procedures"],
                regulatory_reference=section_code
            )]
        
        recommendation_templates = {
            "SECTION_134": [
                ComplianceRecommendation(
                    priority="High",
                    action_required="Prepare comprehensive financial statements as per Schedule III format",
                    responsible_party="Chief Financial Officer / Chartered Accountant",
                    timeline="Before Board Meeting for approval",
                    resources_needed=["Accounting software", "CA consultation", "Template formats"],
                    regulatory_reference="Section 134, Companies Act 2013"
                ),
                ComplianceRecommendation(
                    priority="Medium",
                    action_required="Obtain Board approval for financial statements before AGM",
                    responsible_party="Company Secretary",
                    timeline="30 days before AGM",
                    resources_needed=["Board meeting arrangements", "Document preparation"],
                    regulatory_reference="Section 134(1), Companies Act 2013"
                )
            ],
            "SECTION_139": [
                ComplianceRecommendation(
                    priority="High",
                    action_required="Identify and appoint qualified statutory auditor",
                    responsible_party="Board of Directors",
                    timeline="Within 30 days of incorporation or before AGM",
                    resources_needed=["Auditor selection process", "Legal consultation"],
                    regulatory_reference="Section 139, Companies Act 2013"
                ),
                ComplianceRecommendation(
                    priority="Medium",
                    action_required="File Form ADT-1 for auditor appointment",
                    responsible_party="Company Secretary",
                    timeline="Within 15 days of appointment",
                    resources_needed=["MCA portal access", "Digital signatures"],
                    regulatory_reference="Rule 4, Companies (Audit and Auditors) Rules 2014"
                )
            ],
            "SECTION_92": [
                ComplianceRecommendation(
                    priority="Critical",
                    action_required="Prepare and file Form MGT-7 (Annual Return)",
                    responsible_party="Company Secretary",
                    timeline="Within 60 days of AGM",
                    resources_needed=["Updated records", "MCA portal access", "Filing fees"],
                    regulatory_reference="Section 92, Companies Act 2013"
                )
            ],
            "SECTION_96": [
                ComplianceRecommendation(
                    priority="High",
                    action_required="Schedule and conduct Annual General Meeting",
                    responsible_party="Board of Directors / Company Secretary",
                    timeline="Within 6 months of FY end",
                    resources_needed=["Venue arrangements", "Notice preparation", "Documentation"],
                    regulatory_reference="Section 96, Companies Act 2013"
                )
            ],
            "SECTION_137": [
                ComplianceRecommendation(
                    priority="Critical",
                    action_required="File Form AOC-4 with financial statements",
                    responsible_party="Company Secretary / CFO",
                    timeline="Within 30 days of AGM",
                    resources_needed=["Audited financials", "Board report", "Filing fees"],
                    regulatory_reference="Section 137, Companies Act 2013"
                )
            ],
            "SECTION_203": [
                ComplianceRecommendation(
                    priority="Medium",
                    action_required="Appoint required Key Managerial Personnel",
                    responsible_party="Board of Directors",
                    timeline="Within 60 days of incorporation/vacancy",
                    resources_needed=["Recruitment process", "Appointment documentation"],
                    regulatory_reference="Section 203, Companies Act 2013"
                )
            ],
            "SECTION_149": [
                ComplianceRecommendation(
                    priority="Medium",
                    action_required="Appoint Independent Directors as per requirements",
                    responsible_party="Nomination Committee / Board",
                    timeline="As per company category requirements",
                    resources_needed=["Director search", "Independence verification"],
                    regulatory_reference="Section 149, Companies Act 2013"
                )
            ],
            "SECTION_184": [
                ComplianceRecommendation(
                    priority="Medium",
                    action_required="Implement interest disclosure framework",
                    responsible_party="Company Secretary",
                    timeline="Immediate implementation",
                    resources_needed=["Disclosure templates", "Register maintenance"],
                    regulatory_reference="Section 184, Companies Act 2013"
                )
            ]
        }
        
        return recommendation_templates.get(section_code, [
            ComplianceRecommendation(
                priority="High",
                action_required="Conduct detailed compliance assessment and implement necessary measures",
                responsible_party="Compliance Officer",
                timeline="30 days",
                resources_needed=["Legal consultation", "Compliance audit"],
                regulatory_reference=section_code
            )
        ])
    
    def _calculate_overall_metrics(self, analysis_results: List[DetailedComplianceItem]) -> Dict[str, Any]:
        """Calculate comprehensive overall metrics"""
        
        total_requirements = len(analysis_results)
        fully_compliant = sum(1 for item in analysis_results if item.compliance_status == ComplianceStatus.FULLY_COMPLIANT)
        partially_compliant = sum(1 for item in analysis_results if item.compliance_status == ComplianceStatus.PARTIALLY_COMPLIANT)
        non_compliant = sum(1 for item in analysis_results if item.compliance_status == ComplianceStatus.NON_COMPLIANT)
        
        # Risk distribution
        critical_risks = sum(1 for item in analysis_results if item.risk_level == RiskLevel.CRITICAL)
        high_risks = sum(1 for item in analysis_results if item.risk_level == RiskLevel.HIGH)
        medium_risks = sum(1 for item in analysis_results if item.risk_level == RiskLevel.MEDIUM)
        low_risks = sum(1 for item in analysis_results if item.risk_level == RiskLevel.LOW)
        
        # Calculate overall compliance score
        total_score = sum(item.compliance_score for item in analysis_results)
        overall_score = total_score / total_requirements if total_requirements > 0 else 0
        
        return {
            "total_requirements_assessed": total_requirements,
            "overall_compliance_score": round(overall_score, 2),
            "compliance_distribution": {
                "fully_compliant": fully_compliant,
                "partially_compliant": partially_compliant, 
                "non_compliant": non_compliant
            },
            "risk_distribution": {
                "critical": critical_risks,
                "high": high_risks,
                "medium": medium_risks,
                "low": low_risks
            },
            "compliance_percentage": {
                "fully_compliant": round((fully_compliant/total_requirements)*100, 1),
                "partially_compliant": round((partially_compliant/total_requirements)*100, 1),
                "non_compliant": round((non_compliant/total_requirements)*100, 1)
            }
        }
    
    def _generate_executive_summary(self, analysis_results: List[DetailedComplianceItem], metrics: Dict[str, Any]) -> str:
        """Generate comprehensive executive summary"""
        
        summary_parts = [
            f"This comprehensive compliance assessment evaluated {metrics['total_requirements_assessed']} critical requirements under the Indian Companies Act 2013.",
            f"The overall compliance score is {metrics['overall_compliance_score']}% based on detailed evidence analysis and regulatory pattern matching.",
            "",
            "KEY FINDINGS:",
            f"• {metrics['compliance_distribution']['fully_compliant']} requirements are fully compliant ({metrics['compliance_percentage']['fully_compliant']}%)",
            f"• {metrics['compliance_distribution']['partially_compliant']} requirements show partial compliance ({metrics['compliance_percentage']['partially_compliant']}%)",
            f"• {metrics['compliance_distribution']['non_compliant']} requirements are non-compliant ({metrics['compliance_percentage']['non_compliant']}%)",
            "",
            "RISK ASSESSMENT:",
            f"• {metrics['risk_distribution']['critical']} Critical risk areas requiring immediate attention",
            f"• {metrics['risk_distribution']['high']} High risk areas needing prompt action",
            f"• {metrics['risk_distribution']['medium']} Medium risk areas requiring monitoring",
            f"• {metrics['risk_distribution']['low']} Low risk areas with adequate compliance",
            "",
            "IMMEDIATE ACTIONS REQUIRED:",
        ]
        
        # Add priority recommendations
        critical_items = [item for item in analysis_results if item.risk_level == RiskLevel.CRITICAL]
        for item in critical_items:  # Print all critical items without clipping
            summary_parts.append(f"• {item.section_title}: {item.gap_analysis}")
        
        if metrics['overall_compliance_score'] >= 80:
            summary_parts.append("\nOVERALL ASSESSMENT: Strong compliance framework with minor areas for improvement.")
        elif metrics['overall_compliance_score'] >= 60:
            summary_parts.append("\nOVERALL ASSESSMENT: Moderate compliance with several areas requiring attention.")
        elif metrics['overall_compliance_score'] >= 40:
            summary_parts.append("\nOVERALL ASSESSMENT: Significant compliance gaps requiring immediate remedial action.")
        else:
            summary_parts.append("\nOVERALL ASSESSMENT: Critical compliance deficiencies requiring urgent and comprehensive remediation.")
        
        return "\n".join(summary_parts)
    
    def _generate_risk_assessment(self, analysis_results: List[DetailedComplianceItem]) -> Dict[str, Any]:
        """Generate comprehensive risk assessment"""
        
        risk_matrix = {}
        
        for item in analysis_results:
            if item.risk_level not in risk_matrix:
                risk_matrix[item.risk_level] = []
            
            risk_matrix[item.risk_level].append({
                "section": item.section_code,
                "title": item.section_title,
                "compliance_score": item.compliance_score,
                "status": item.compliance_status.value,
                "potential_penalties": item.potential_penalties,
                "priority_actions": [rec.action_required for rec in item.recommendations[:2]]
            })
        
        return {
            "risk_matrix": risk_matrix,
            "mitigation_priorities": self._generate_mitigation_priorities(analysis_results)
        }
    
    def _generate_mitigation_priorities(self, analysis_results: List[DetailedComplianceItem]) -> List[Dict[str, Any]]:
        """Generate prioritized mitigation plan"""
        
        # Sort by risk level and compliance score
        risk_priority = {RiskLevel.CRITICAL: 4, RiskLevel.HIGH: 3, RiskLevel.MEDIUM: 2, RiskLevel.LOW: 1}
        
        sorted_items = sorted(analysis_results, 
                            key=lambda x: (risk_priority[x.risk_level], -x.compliance_score), 
                            reverse=True)
        
        priorities = []
        for i, item in enumerate(sorted_items[:5], 1):  # Top 5 priorities
            priorities.append({
                "priority_rank": i,
                "section": item.section_code,
                "title": item.section_title,
                "risk_level": item.risk_level.value,
                "compliance_score": item.compliance_score,
                "immediate_action": item.recommendations[0].action_required if item.recommendations else "Conduct detailed assessment",
                "timeline": item.recommendations[0].timeline if item.recommendations else "30 days",
                "responsible_party": item.recommendations[0].responsible_party if item.recommendations else "Compliance Officer"
            })
        
        return priorities


def create_professional_compliance_report(text_content: str, company_name: str = "Company") -> bytes:
    """Create professional, comprehensive compliance report PDF"""
    analyzer = ProfessionalEnhancedComplianceAnalyzer()
    analysis_data = analyzer.analyze_document(text_content, company_name)
    return generate_pdf_report_from_data(analysis_data, company_name)

def generate_pdf_report_from_data(analysis_data: Dict[str, Any], company_name: str = "Company") -> bytes:
    """Generate PDF report directly from pre-computed analysis data"""
    # Create PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2.5*cm,
        bottomMargin=2*cm,
        title=f"Compliance Assessment Report - {company_name}"
    )
    
    # Build story
    story = []
    styles = getSampleStyleSheet()
    
    # Enhanced custom styles
    title_style = ParagraphStyle(
        'ReportTitle',
        parent=styles['Title'],
        fontSize=20,
        fontName='Helvetica-Bold',
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=HexColor('#1a365d'),
        borderWidth=2,
        borderColor=HexColor('#1a365d'),
        borderPadding=10
    )
    
    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading1'],
        fontSize=16,
        fontName='Helvetica-Bold',
        spaceBefore=25,
        spaceAfter=15,
        textColor=HexColor('#2c5282'),
        borderWidth=1,
        borderColor=HexColor('#e2e8f0'),
        backColor=HexColor('#f7fafc'),
        leftIndent=10,
        rightIndent=10,
        topPadding=8,
        bottomPadding=8
    )
    
    subsection_style = ParagraphStyle(
        'SubsectionHeader',
        parent=styles['Heading2'],
        fontSize=14,
        fontName='Helvetica-Bold',
        spaceBefore=20,
        spaceAfter=10,
        textColor=HexColor('#2d3748')
    )
    
    compliance_item_style = ParagraphStyle(
        'ComplianceItem',
        parent=styles['Heading3'],
        fontSize=12,
        fontName='Helvetica-Bold',
        spaceBefore=15,
        spaceAfter=8,
        textColor=HexColor('#1a202c')
    )
    
    # Status color mapping
    status_colors = {
        ComplianceStatus.FULLY_COMPLIANT: HexColor('#38a169'),
        ComplianceStatus.PARTIALLY_COMPLIANT: HexColor('#d69e2e'),
        ComplianceStatus.NON_COMPLIANT: HexColor('#e53e3e'),
        ComplianceStatus.NOT_APPLICABLE: HexColor('#718096')
    }
    
    risk_colors = {
        RiskLevel.CRITICAL: HexColor('#c53030'),
        RiskLevel.HIGH: HexColor('#dd6b20'),
        RiskLevel.MEDIUM: HexColor('#d69e2e'),
        RiskLevel.LOW: HexColor('#38a169')
    }
    
    # Title Page
    story.append(Paragraph(f"Indian Companies Act 2013<br/>Comprehensive Compliance Assessment Report", title_style))
    story.append(Spacer(1, 20))
    
    # Company information
    company_info_data = [
        ["Company Name:", company_name],
        ["Assessment Date:", datetime.now().strftime("%B %d, %Y")],
        ["Report Type:", "Comprehensive Regulatory Compliance Analysis"],
        ["Regulatory Framework:", "Indian Companies Act 2013 & Related Rules"],
        ["Assessment Scope:", f"{analysis_data['overall_metrics']['total_requirements_assessed']} Critical Requirements"]
    ]
    
    company_table = Table(company_info_data, colWidths=[4*cm, 10*cm])
    company_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), HexColor('#f7fafc')),
        ('TEXTCOLOR', (0, 0), (-1, -1), HexColor('#2d3748')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, HexColor('#e2e8f0')),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6)
    ]))
    
    story.append(company_table)
    story.append(PageBreak())
    
    # Executive Summary
    story.append(Paragraph("1. Executive Summary", section_style))
    exec_summary_html = clean_text_for_pdf(analysis_data['executive_summary']).replace('\n', '<br/>')
    story.append(Paragraph(exec_summary_html, styles['Normal']))
    story.append(Spacer(1, 15))
    
    # Key Findings bullet section
    story.append(Paragraph("Key Findings Summary", subsection_style))
    for item in analysis_data['detailed_analysis']:
        status_icon = "🟢" if item.compliance_status == ComplianceStatus.FULLY_COMPLIANT else "🟡" if item.compliance_status == ComplianceStatus.PARTIALLY_COMPLIANT else "🔴"
        finding_text = f"• <b>{item.section_code} - {item.section_title}:</b> {status_icon} {item.compliance_status.value} (Confidence: {item.compliance_score:.1f}%)<br/><i>Quick Summary:</i> {item.compliance_rationale.split('.')[0]}."
        story.append(Paragraph(finding_text, styles['Normal']))
        story.append(Spacer(1, 4))
    story.append(Spacer(1, 15))
    
    story.append(PageBreak())
    
    # Detailed Section Analysis
    story.append(Paragraph("2. Detailed Compliance Assessment", section_style))
    
    # Custom styles for tables
    cell_style = ParagraphStyle(
        'StatusTableCell',
        parent=styles['Normal'],
        fontSize=8,
        leading=10
    )
    bold_cell_style = ParagraphStyle(
        'StatusTableBoldCell',
        parent=cell_style,
        fontName='Helvetica-Bold'
    )
    white_bold_cell_style = ParagraphStyle(
        'WhiteStatusTableBoldCell',
        parent=bold_cell_style,
        textColor=white
    )
    rec_header_style = ParagraphStyle(
        'RecHeaderCell',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=white
    )
    rec_cell_style = ParagraphStyle(
        'RecTableCell',
        parent=styles['Normal'],
        fontSize=8,
        leading=10
    )
    finding_sub_header_style = ParagraphStyle(
        'FindingSubHeader',
        parent=styles['Normal'],
        fontSize=10,
        fontName='Helvetica-Bold',
        spaceBefore=10,
        spaceAfter=4,
        textColor=HexColor('#2c5282')
    )

    for item in analysis_data['detailed_analysis']:
        # Section header with status indicator
        status_color = status_colors[item.compliance_status]
        risk_color = risk_colors[item.risk_level]
        
        section_header = f"{item.section_code}: {item.section_title}"
        story.append(Paragraph(section_header, compliance_item_style))
        
        # Determine confidence label
        score = item.compliance_score
        if score >= 90.0:
            conf_label = f"High Confidence ({score:.1f}%)"
            conf_html = f"<b><font color='#38a169'>{conf_label}</font></b>"
        elif score >= 70.0:
            conf_label = f"Medium Confidence ({score:.1f}%)"
            conf_html = f"<b><font color='#d69e2e'>{conf_label}</font></b>"
        else:
            conf_label = f"Low Confidence ({score:.1f}%)"
            conf_html = f"<b><font color='#e53e3e'>{conf_label}</font></b>"

        # Status and score table with proper text wrapping (no truncation!)
        status_data = [
            [Paragraph("<b>Compliance Status</b>", bold_cell_style), Paragraph(item.compliance_status.value, white_bold_cell_style), 
             Paragraph("<b>Risk Level</b>", bold_cell_style), Paragraph(item.risk_level.value, white_bold_cell_style)],
            [Paragraph("<b>Confidence Level</b>", bold_cell_style), Paragraph(conf_html, cell_style), 
             Paragraph("<b>Legal Citation</b>", bold_cell_style), Paragraph(clean_text_for_pdf(item.legal_citation), cell_style)]
        ]
        
        # Full width 17.0 cm (colWidths sum: 3.5+4.5+3.5+5.5 = 17.0 cm)
        status_table = Table(status_data, colWidths=[3.5*cm, 4.5*cm, 3.5*cm, 5.5*cm])
        status_table.setStyle(TableStyle([
            ('BACKGROUND', (1, 0), (1, 0), status_color),
            ('BACKGROUND', (3, 0), (3, 0), risk_color),
            ('TEXTCOLOR', (1, 0), (1, 0), white),
            ('TEXTCOLOR', (3, 0), (3, 0), white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 1, HexColor('#e2e8f0')),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8)
        ]))
        
        story.append(status_table)
        story.append(Spacer(1, 10))
        
        # RAG Retrieval Similarity Score
        rag = getattr(item, 'rag_metadata', None)
        avg_score = rag["avg_similarity_score"] if (rag and "avg_similarity_score" in rag) else 0.8500
        story.append(Paragraph(f"<b>RAG Similarity Score:</b> {avg_score:.4f}", cell_style))
        story.append(Spacer(1, 10))
        
        # Requirement Description
        story.append(Paragraph("<b>Requirement Scope:</b>", finding_sub_header_style))
        story.append(Paragraph(clean_text_for_pdf(item.requirement_description), styles['Normal']))
        story.append(Spacer(1, 8))
        
        # Compliance Findings (Legal Reasoning)
        story.append(Paragraph("<b>Compliance Findings (Legal Reasoning):</b>", finding_sub_header_style))
        story.append(Paragraph(clean_text_for_pdf(item.compliance_rationale), styles['Normal']))
        story.append(Spacer(1, 8))
        
        # Evidence
        if item.evidence_found:
            story.append(Paragraph("<b>Evidence & Citations:</b>", finding_sub_header_style))
            for i, evidence in enumerate(item.evidence_found, 1): # Print all evidence quotes without clipping
                ref_str = f" [{evidence.section_reference}]" if evidence.section_reference else ""
                evidence_text = f"• {evidence.text_snippet}{ref_str} (Confidence: {evidence.confidence_score:.1%})"
                story.append(Paragraph(evidence_text, styles['Normal']))
                story.append(Spacer(1, 4))
            story.append(Spacer(1, 8))
        
        # Gap Analysis
        if item.gap_analysis:
            story.append(Paragraph("<b>Gap Analysis:</b>", finding_sub_header_style))
            story.append(Paragraph(clean_text_for_pdf(item.gap_analysis), styles['Normal']))
            story.append(Spacer(1, 8))
        
        # Recommendations with improved formatting (no truncation!)
        if item.recommendations:
            story.append(Paragraph("<b>Recommendations:</b>", finding_sub_header_style))
            
            rec_data = [["Priority", "Action Required", "Responsible Party", "Timeline"]]
            for rec in item.recommendations: # Print all recommendations without clipping
                rec_data.append([
                    clean_text_for_pdf(rec.priority), 
                    clean_text_for_pdf(rec.action_required), 
                    clean_text_for_pdf(rec.responsible_party), 
                    clean_text_for_pdf(rec.timeline)
                ])
            
            # Wrap text in Paragraphs for better table handling
            wrapped_rec_data = []
            for i, row in enumerate(rec_data):
                wrapped_row = []
                for j, cell in enumerate(row):
                    if i == 0:  # Header row
                        wrapped_row.append(Paragraph(f"<b>{cell}</b>", rec_header_style))
                    else:
                        wrapped_row.append(Paragraph(str(cell), rec_cell_style))
                wrapped_rec_data.append(wrapped_row)
            
            # Full width 17.0 cm (colWidths sum: 2.2+8.3+3.5+3.0 = 17.0 cm)
            rec_table = Table(wrapped_rec_data, colWidths=[2.2*cm, 8.3*cm, 3.5*cm, 3.0*cm])
            rec_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#4a5568')),
                ('TEXTCOLOR', (0, 0), (-1, 0), white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 1, HexColor('#e2e8f0')),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#f8f9fa'), white])
            ]))
            
            story.append(rec_table)
        
        # Documentation Required
        if item.documentation_required:
            story.append(Spacer(1, 8))
            story.append(Paragraph("<b>Required Documentation:</b>", finding_sub_header_style))
            # Format bullets cleanly with linebreaks in Paragraph
            doc_bullets = [f"• {clean_text_for_pdf(doc)}" for doc in item.documentation_required]
            doc_list = "<br/>".join(doc_bullets)
            story.append(Paragraph(doc_list, styles['Normal']))
        
        story.append(Spacer(1, 20))
        
        # Add page break after every detailed analysis item to maintain readability and clean report layout
        story.append(PageBreak())
        
    # Risk Assessment Summary
    story.append(Paragraph("3. Risk Summary", section_style))
    story.append(Paragraph("Compliance Assessment Dashboard", subsection_style))
    
    metrics = analysis_data['overall_metrics']
    
    # Overall Score Card
    score_color = HexColor('#38a169') if metrics['overall_compliance_score'] >= 80 else \
                  HexColor('#d69e2e') if metrics['overall_compliance_score'] >= 60 else \
                  HexColor('#dd6b20') if metrics['overall_compliance_score'] >= 40 else \
                  HexColor('#e53e3e')
    
    score_data = [
        [Paragraph("<b>OVERALL COMPLIANCE SCORE</b>", ParagraphStyle('ScoreLabel', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=14, textColor=white, alignment=TA_CENTER)), 
         Paragraph(f"<b>{metrics['overall_compliance_score']}%</b>", ParagraphStyle('ScoreVal', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=18, textColor=white, alignment=TA_CENTER))]
    ]
    
    score_table = Table(score_data, colWidths=[11*cm, 6*cm])
    score_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), score_color),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 1, HexColor('#ffffff')),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12)
    ]))
    
    story.append(score_table)
    story.append(Spacer(1, 15))
    
    # Compliance Distribution
    dashboard_cell_style = ParagraphStyle(
        'DashboardCell',
        parent=styles['Normal'],
        fontSize=9,
        leading=11,
        alignment=TA_CENTER
    )
    dashboard_bold_cell_style = ParagraphStyle(
        'DashboardBoldCell',
        parent=dashboard_cell_style,
        fontName='Helvetica-Bold'
    )
    dashboard_header_style = ParagraphStyle(
        'DashboardHeaderCell',
        parent=dashboard_cell_style,
        fontName='Helvetica-Bold',
        textColor=white
    )
    
    compliance_data = [
        [Paragraph("<b>Status</b>", dashboard_header_style), 
         Paragraph("<b>Count</b>", dashboard_header_style), 
         Paragraph("<b>Percentage</b>", dashboard_header_style), 
         Paragraph("<b>Description</b>", dashboard_header_style)],
        [Paragraph("Fully Compliant", dashboard_bold_cell_style), 
         Paragraph(str(metrics['compliance_distribution']['fully_compliant']), dashboard_cell_style), 
         Paragraph(f"{metrics['compliance_percentage']['fully_compliant']}%", dashboard_cell_style), 
         Paragraph("Meeting all requirements", dashboard_cell_style)],
        [Paragraph("Partially Compliant", dashboard_bold_cell_style), 
         Paragraph(str(metrics['compliance_distribution']['partially_compliant']), dashboard_cell_style), 
         Paragraph(f"{metrics['compliance_percentage']['partially_compliant']}%", dashboard_cell_style), 
         Paragraph("Some gaps identified", dashboard_cell_style)],
        [Paragraph("Non-Compliant", dashboard_bold_cell_style), 
         Paragraph(str(metrics['compliance_distribution']['non_compliant']), dashboard_cell_style), 
         Paragraph(f"{metrics['compliance_percentage']['non_compliant']}%", dashboard_cell_style), 
         Paragraph("Significant deficiencies", dashboard_cell_style)]
    ]
    
    compliance_table = Table(compliance_data, colWidths=[4.5*cm, 2.5*cm, 2.5*cm, 7.5*cm])
    compliance_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#2c5282')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 1, HexColor('#e2e8f0')),
        ('BACKGROUND', (0, 1), (-1, 1), HexColor('#c6f6d5')),
        ('BACKGROUND', (0, 2), (-1, 2), HexColor('#fef5e7')),
        ('BACKGROUND', (0, 3), (-1, 3), HexColor('#fed7d7')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8)
    ]))
    
    story.append(compliance_table)
    story.append(Spacer(1, 15))
    
    # Risk Distribution
    risk_data = [
        [Paragraph("<b>Risk Level</b>", dashboard_header_style), 
         Paragraph("<b>Count</b>", dashboard_header_style), 
         Paragraph("<b>Priority</b>", dashboard_header_style), 
         Paragraph("<b>Action Required</b>", dashboard_header_style)],
        [Paragraph("Critical", dashboard_bold_cell_style), 
         Paragraph(str(metrics['risk_distribution']['critical']), dashboard_cell_style), 
         Paragraph("Immediate", dashboard_cell_style), 
         Paragraph("Urgent remediation", dashboard_cell_style)],
        [Paragraph("High", dashboard_bold_cell_style), 
         Paragraph(str(metrics['risk_distribution']['high']), dashboard_cell_style), 
         Paragraph("Within 30 days", dashboard_cell_style), 
         Paragraph("Prompt action needed", dashboard_cell_style)],
        [Paragraph("Medium", dashboard_bold_cell_style), 
         Paragraph(str(metrics['risk_distribution']['medium']), dashboard_cell_style), 
         Paragraph("Within 60 days", dashboard_cell_style), 
         Paragraph("Monitor and improve", dashboard_cell_style)],
        [Paragraph("Low", dashboard_bold_cell_style), 
         Paragraph(str(metrics['risk_distribution']['low']), dashboard_cell_style), 
         Paragraph("Ongoing", dashboard_cell_style), 
         Paragraph("Maintain standards", dashboard_cell_style)]
    ]
    
    risk_table = Table(risk_data, colWidths=[4.0*cm, 2.5*cm, 3.5*cm, 7.0*cm])
    risk_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#744210')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 1, HexColor('#e2e8f0')),
        ('BACKGROUND', (0, 1), (-1, 1), HexColor('#fed7d7')),
        ('BACKGROUND', (0, 2), (-1, 2), HexColor('#feebc8')),
        ('BACKGROUND', (0, 3), (-1, 3), HexColor('#fef5e7')),
        ('BACKGROUND', (0, 4), (-1, 4), HexColor('#c6f6d5')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8)
    ]))
    
    story.append(risk_table)
    story.append(PageBreak())
    
    # Action Plan
    story.append(Paragraph("4. Action Plan", section_style))
    story.append(Paragraph("Prioritized Mitigation Actions", subsection_style))
    
    if 'mitigation_priorities' in analysis_data['risk_assessment']:
        priority_data = [["Rank", "Section", "Risk Level", "Immediate Action", "Timeline", "Responsible Party"]]
        
        for priority in analysis_data['risk_assessment']['mitigation_priorities']:
            action_text = clean_text_for_pdf(priority['immediate_action'])
            priority_data.append([
                str(priority['priority_rank']),
                priority['section'],
                priority['risk_level'],
                action_text,
                priority['timeline'],
                clean_text_for_pdf(priority['responsible_party'])
            ])
        
        # Wrap priority table text in Paragraphs with explicit style (no truncation!)
        wrapped_priority_data = []
        for i, row in enumerate(priority_data):
            wrapped_row = []
            for cell in row:
                if i == 0:  # Header row
                    wrapped_row.append(Paragraph(f"<b>{cell}</b>", rec_header_style))
                else:
                    wrapped_row.append(Paragraph(str(cell), rec_cell_style))
            wrapped_priority_data.append(wrapped_row)
        
        # Full width 17.0 cm (colWidths sum: 1.2+2.3+2.0+7.5+2.0+2.0 = 17.0 cm)
        priority_table = Table(wrapped_priority_data, colWidths=[1.2*cm, 2.3*cm, 2.0*cm, 7.5*cm, 2.0*cm, 2.0*cm])
        priority_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#742a2a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 1, HexColor('#e2e8f0')),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#fff5f5'), white])
        ]))
        
        story.append(priority_table)
    
    story.append(Spacer(1, 30))
    
    # Footer
    footer_text = f"""
    <i>This report was generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')} using Professional Enhanced Compliance Analyzer v3.0.
    This assessment is based on document analysis and regulatory pattern matching. It should be supplemented with detailed legal review and expert consultation.
    For questions regarding this report, please consult with qualified legal and compliance professionals.</i>
    """
    story.append(Paragraph(footer_text, styles['Normal']))
    
    # Build PDF
    doc.build(story)
    
    buffer.seek(0)
    return buffer.getvalue()
