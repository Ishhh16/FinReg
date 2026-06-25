import os
import sys
import tempfile
import re
import numpy as np
import uuid
import logging
from contextlib import asynccontextmanager

# Configure stdout and stderr to handle UTF-8 encoding (especially emojis) on Windows
sys.stdout.reconfigure(encoding='utf-8')

# Initialize logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("finreg_backend")

from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from collections import Counter
from pydantic import BaseModel

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.units import inch

def validate_uploaded_pdf(user_document: UploadFile) -> Tuple[Optional[bytes], Optional[JSONResponse]]:
    """Helper to validate file type, file size (10MB limit), and sanitize filename."""
    if not user_document or not user_document.filename:
        return None, JSONResponse(status_code=400, content={"error": "No file uploaded."})
        
    # Sanitize filename
    raw_basename = os.path.basename(user_document.filename)
    clean_filename = re.sub(r'[^a-zA-Z0-9._-]', '_', raw_basename)
    
    # Check extension
    if not clean_filename.lower().endswith('.pdf'):
        return None, JSONResponse(
            status_code=400, 
            content={"error": f"Invalid file type for {clean_filename}. Only PDF files are supported."}
        )
        
    # Check MIME content type if available
    if user_document.content_type and user_document.content_type != "application/pdf":
        return None, JSONResponse(
            status_code=400, 
            content={"error": "Invalid content type. Only application/pdf is supported."}
        )
        
    # Check file size (10MB maximum limit)
    try:
        content = user_document.file.read(10 * 1024 * 1024 + 1)
        if len(content) > 10 * 1024 * 1024:
            return None, JSONResponse(
                status_code=400, 
                content={"error": "File size exceeds the maximum allowed limit of 10MB."}
            )
        user_document.file.seek(0)
        return content, None
    except Exception as e:
        logger.error(f"Error reading file uploads: {e}", exc_info=True)
        return None, JSONResponse(
            status_code=500, 
            content={"error": "Internal error occurred while reading the uploaded file."}
        )

try:
    from .utils import extract_text
    from .professional_enhanced_compliance import create_professional_compliance_report, ProfessionalEnhancedComplianceAnalyzer, generate_pdf_report_from_data
except ImportError:
    from utils import extract_text
    from professional_enhanced_compliance import create_professional_compliance_report, ProfessionalEnhancedComplianceAnalyzer, generate_pdf_report_from_data

@dataclass
class PolicySection:
    """Represents a section of the policy document"""
    content: str
    section_number: int
    title: str = ""
    regulatory_matches: List[str] = None
    
    def __post_init__(self):
        if self.regulatory_matches is None:
            self.regulatory_matches = []

@dataclass
class RegulatoryMapping:
    """Represents a mapping between policy content and regulations"""
    policy_section: PolicySection
    regulation_category: str
    regulation_section: str
    regulation_text: str
    confidence_score: float
    evidence: List[str]
    reasoning: str = ""
    citation_id: str = ""
    source_url: str = ""

class EnhancedComplianceAnalyzer:
    """Enhanced compliance analyzer with semantic vector search for Indian Companies Act requirements"""
    
    def __init__(self):
        self.regulatory_mappings = self._get_indian_mappings()
        self.vector_store = None
        logger.info("✅ Loaded Indian Companies Act compliance framework")
    
    def _get_indian_mappings(self):
        """Indian Companies Act/Rules compliance framework"""
        return {
            "INDIAN_COMPANIES_ACT": {
                "title": "Indian Companies Act Compliance Framework",
                "sections": {
                    "MSME_1": {
                        "citation": "Companies (Furnishing of information about payment to micro and small enterprise suppliers) Order, 2019",
                        "rule": "Half-yearly return for outstanding dues to MSME suppliers",
                        "deadline_rule": "For Oct–Mar: due by 30 April; For Apr–Sep: due by 31 October",
                        "frequency": "Half-yearly",
                        "docs_required": ["Details of outstanding payments to MSME suppliers", "Board confirmation"],
                        "detection_patterns": ["MSME-1", "MSME 1", "micro and small enterprise", "outstanding to MSME"],
                        "remediation": "Prepare MSME-1 with supplier-wise outstanding details and file within applicable due date.",
                        "source_url": "https://www.mca.gov.in/"
                    },
                    "AOC_4": {
                        "citation": "Section 137, Companies Act, 2013; Rule 12 of Companies (Accounts) Rules, 2014",
                        "rule": "Filing of financial statements",
                        "deadline_rule": "Within 30 days of AGM (for OPC: within 180 days from FY end)",
                        "frequency": "Annual",
                        "docs_required": ["Signed financial statements", "Board's report", "Auditor's report"],
                        "detection_patterns": ["AOC-4", "AOC 4", "financial statements filing", "Section 137"],
                        "remediation": "Finalize audited financials and e-file AOC-4 within 30 days of AGM with all mandatory attachments.",
                        "source_url": "https://www.mca.gov.in/"
                    },
                    "MGT_7": {
                        "citation": "Section 92, Companies Act, 2013; Rule 11 of Companies (Management and Administration) Rules, 2014",
                        "rule": "Filing of Annual Return",
                        "deadline_rule": "Within 60 days of AGM",
                        "frequency": "Annual",
                        "docs_required": ["Annual Return Form MGT-7", "Financial statements", "Board resolution"],
                        "detection_patterns": ["MGT-7", "MGT 7", "annual return", "Section 92"],
                        "remediation": "Prepare and e-file Form MGT-7 within 60 days of AGM with required attachments.",
                        "source_url": "https://www.mca.gov.in/"
                    },
                    "AGM": {
                        "citation": "Section 96, Companies Act, 2013",
                        "rule": "Holding of Annual General Meeting",
                        "deadline_rule": "Within 6 months from FY end (by 30 September for most)",
                        "frequency": "Annual",
                        "docs_required": ["Notice of AGM", "Proof of dispatch", "Minutes of AGM", "Attendance register"],
                        "detection_patterns": ["AGM", "Annual General Meeting", "Section 96"],
                        "remediation": "Convene AGM within prescribed timelines; maintain notices, quorum proof, minutes and resolutions.",
                        "source_url": "https://www.mca.gov.in/"
                    },
                    "DIR3_KYC": {
                        "citation": "Rule 12A of Companies (Appointment and Qualification of Directors) Rules, 2014",
                        "rule": "Directors KYC verification",
                        "deadline_rule": "Between 1 April to 30 September every year",
                        "frequency": "Annual",
                        "docs_required": ["DIR-3 KYC form", "Identity proof", "Address proof"],
                        "detection_patterns": ["DIR-3", "DIR 3", "directors KYC", "KYC verification"],
                        "remediation": "All directors must file DIR-3 KYC form annually between 1 April to 30 September.",
                        "source_url": "https://www.mca.gov.in/"
                    }
                }
            }
        }
    
    def segment_document(self, content: str) -> List[PolicySection]:
        """Segment document into sections"""
        paragraphs = re.split(r'\n\s*\n', content.strip())
        sections = []
        
        for i, para in enumerate(paragraphs):
            if len(para.strip()) > 50:
                title = para.split('\n')[0][:50] + "..." if '\n' in para else para[:50] + "..."
                sections.append(PolicySection(
                    content=para.strip(),
                    section_number=i + 1,
                    title=title
                ))
        
        return sections
    
    def map_to_regulations(self, sections: List[PolicySection]) -> List[RegulatoryMapping]:
        """Map document sections to regulatory requirements"""
        mappings = []
        
        for section in sections:
            content_lower = section.content.lower()
            
            for category, cat_data in self.regulatory_mappings.items():
                for req_key, req_info in cat_data["sections"].items():
                    confidence = 0.0
                    evidence = []
                    
                    # Check detection patterns
                    for pattern in req_info["detection_patterns"]:
                        if pattern.lower() in content_lower:
                            confidence = max(confidence, 0.7)
                            evidence.append(f"Found pattern: {pattern}")
                    
                    # Check for specific terms
                    citation_terms = req_info["citation"].lower().split()
                    rule_terms = req_info["rule"].lower().split()
                    
                    matches = 0
                    for term in citation_terms + rule_terms:
                        if len(term) > 3 and term in content_lower:
                            matches += 1
                    
                    if matches > 0:
                        confidence = max(confidence, min(0.6, matches * 0.1))
                        evidence.append(f"Content similarity: {matches} matching terms")
                    
                    if confidence > 0.3:
                        reasoning = f"Pattern matching analysis with {confidence:.1%} confidence"
                        mappings.append(RegulatoryMapping(
                            policy_section=section,
                            regulation_category=category,
                            regulation_section=req_key,
                            regulation_text=req_info["rule"],
                            confidence_score=confidence,
                            evidence=evidence,
                            reasoning=reasoning,
                            citation_id=req_info["citation"],
                            source_url=req_info.get("source_url", "")
                        ))
                        
                        logger.info(f"🇮🇳 Section '{section.title}' -> {req_key}: {confidence:.3f} (Evidence: {len(evidence)})")
        
        return mappings

class IndianComplianceReportGenerator:
    """Generates an Indian compliance checklist with deadlines, docs, and remediation"""
    def __init__(self, analyzer: EnhancedComplianceAnalyzer):
        self.analyzer = analyzer

    def build_checklist(self, mappings: List[RegulatoryMapping]) -> List[Dict[str, any]]:
        """Build enhanced compliance checklist with semantic analysis results"""
        checklist: Dict[str, Dict[str, any]] = {}
        
        # Build a lookup for requirement metadata
        req_meta = {}
        for cat, cat_data in self.analyzer.regulatory_mappings.items():
            for key, info in cat_data["sections"].items():
                req_meta[key] = info

        # Process mappings from analysis
        for m in mappings:
            key = m.regulation_section
            meta = req_meta.get(key, {})
            
            if key not in checklist:
                checklist[key] = {
                    "code": key,
                    "name": key.replace('_', '-'),
                    "citation": meta.get("citation", ""),
                    "rule": meta.get("rule", ""),
                    "deadline_rule": meta.get("deadline_rule", ""),
                    "frequency": meta.get("frequency", ""),
                    "docs_required": meta.get("docs_required", []),
                    "source_url": meta.get("source_url", ""),
                    "confidence_scores": [],
                    "evidence": [],
                }
            
            entry = checklist[key]
            entry["confidence_scores"].append(m.confidence_score)
            if m.evidence:
                entry["evidence"].extend(m.evidence[:2])

        # Enhanced status determination
        for key, entry in checklist.items():
            if entry["confidence_scores"]:
                max_conf = max(entry["confidence_scores"])
                evidence_count = len(entry["evidence"])
                
                if max_conf >= 0.6 and evidence_count >= 1:
                    entry["status"] = "Met"
                    entry["status_explanation"] = f"Compliance evidence found ({max_conf:.1%} confidence)"
                elif max_conf >= 0.35:
                    entry["status"] = "Incomplete"
                    entry["status_explanation"] = f"Partial compliance detected ({max_conf:.1%} confidence)"
                else:
                    entry["status"] = "Missing"
                    entry["status_explanation"] = f"Minimal evidence found ({max_conf:.1%} confidence)"
            else:
                entry["status"] = "Missing"
                entry["status_explanation"] = "No compliance evidence detected"
        
        # Add all requirements that weren't found
        for key, meta in req_meta.items():
            if key not in checklist:
                checklist[key] = {
                    "code": key,
                    "name": key.replace('_', '-'),
                    "citation": meta.get("citation", ""),
                    "rule": meta.get("rule", ""),
                    "deadline_rule": meta.get("deadline_rule", ""),
                    "frequency": meta.get("frequency", ""),
                    "docs_required": meta.get("docs_required", []),
                    "source_url": meta.get("source_url", ""),
                    "status": "Missing",
                    "status_explanation": "Not found in analyzed document",
                    "evidence": [],
                }
        
        return [checklist[k] for k in sorted(checklist.keys())]

    def render_report(self, checklist: List[Dict[str, any]], original_query: str, doc_stats: dict) -> str:
        lines = []
        lines.append("INDIAN COMPANIES ACT COMPLIANCE CHECKLIST REPORT")
        lines.append("=" * 60)
        lines.append(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Query: {original_query}")
        lines.append(f"Document Length: {doc_stats.get('length', 'Unknown')} characters")
        lines.append("")
        
        # Summary
        met = sum(1 for i in checklist if i["status"] == "Met")
        incomplete = sum(1 for i in checklist if i["status"] == "Incomplete")
        missing = sum(1 for i in checklist if i["status"] == "Missing")
        total = len(checklist)
        
        lines.append("SUMMARY")
        lines.append("-" * 20)
        lines.append(f"✅ Met: {met}/{total} ({(met/max(total,1)):.1%})")
        lines.append(f"🟡 Incomplete: {incomplete}/{total} ({(incomplete/max(total,1)):.1%})")
        lines.append(f"❌ Missing: {missing}/{total} ({(missing/max(total,1)):.1%})")
        lines.append("")
        
        # Detailed checklist
        lines.append("SECTION-BY-SECTION CHECKLIST")
        lines.append("-" * 35)
        
        for item in checklist:
            status_icon = "✅" if item["status"] == "Met" else "🟡" if item["status"] == "Incomplete" else "❌"
            lines.append(f"\n{status_icon} {item['code']} - {item['rule']}")
            lines.append(f"Legal Basis: {item['citation']}")
            if item.get('deadline_rule'):
                lines.append(f"Deadline: {item['deadline_rule']}")
            if item.get('frequency'):
                lines.append(f"Frequency: {item['frequency']}")
            lines.append(f"Status: {item.get('status_explanation', 'No analysis')}")
            
            if item.get('evidence'):
                lines.append("Evidence:")
                for evidence in item['evidence'][:2]:
                    lines.append(f"  - {evidence}")
            
            if item.get('docs_required'):
                lines.append("Required Documentation:")
                for doc in item['docs_required']:
                    lines.append(f"  - {doc}")
            
            if item.get('source_url'):
                lines.append(f"MCA Reference: {item['source_url']}")
        
        return "\n".join(lines)

def create_indian_compliance_pdf(report_text: str, checklist: List[Dict[str, any]], mappings: List[RegulatoryMapping], filename: str, company_name: str = "Company"):
    """Create Indian Companies Act compliance PDF"""
    
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        topMargin=0.9*inch,
        bottomMargin=0.7*inch,
        leftMargin=0.6*inch,
        rightMargin=0.6*inch,
    )
    
    styles = getSampleStyleSheet()
    story = []
    
    # Custom styles
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16, textColor=colors.darkblue, spaceAfter=16, alignment=1)
    h2_style = ParagraphStyle('H2', parent=styles['Heading2'], fontSize=14, spaceBefore=12, spaceAfter=8, textColor=colors.black)
    normal_style = styles['Normal']
    
    # Title page
    story.append(Paragraph(f"Indian Companies Act Compliance Report", title_style))
    story.append(Spacer(1, 8))
    story.append(Paragraph(f"<b>Company:</b> {company_name}", normal_style))
    story.append(Paragraph(f"<b>Analysis Date:</b> {datetime.now().strftime('%d %B %Y at %H:%M')}", normal_style))
    story.append(Paragraph(f"<b>Compliance Framework:</b> Companies Act, 2013 & MCA Rules", normal_style))
    story.append(Spacer(1, 20))
    
    # Executive summary
    if checklist:
        met = sum(1 for i in checklist if i["status"] == "Met")
        inc = sum(1 for i in checklist if i["status"] == "Incomplete")
        miss = sum(1 for i in checklist if i["status"] == "Missing")
        total = len(checklist)
        
        story.append(Paragraph("Executive Summary", h2_style))
        summary_data = [
            ['Status', 'Count', 'Percentage'],
            [f'✅ Requirements Met', str(met), f'{(met/max(total,1)):.1%}'],
            [f'🟡 Incomplete Items', str(inc), f'{(inc/max(total,1)):.1%}'],
            [f'❌ Missing/Gap Items', str(miss), f'{(miss/max(total,1)):.1%}']
        ]
        
        summary_table = Table(summary_data, colWidths=[2.5*inch, 1.0*inch, 1.5*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0b3d91')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 20))
    
    # Report content
    story.append(Paragraph("Detailed Analysis", h2_style))
    lines = report_text.split('\n')
    for line in lines:
        if line.strip():
            story.append(Paragraph(line, normal_style))
            story.append(Spacer(1, 4))
    
    # Build the PDF
    doc.build(story)

# Pydantic models
class CompanyDetails(BaseModel):
    incorporation_date: Optional[str] = None
    company_type: Optional[str] = None
    cin: Optional[str] = None
    registered_office: Optional[str] = None

class IndianComplianceRequest(BaseModel):
    company_name: str
    company_details: Optional[CompanyDetails] = None
    compliance_data: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting up FinReg API - Preloading shared AI models and Vector DB...")
    try:
        from backend.professional_enhanced_compliance import get_shared_embeddings, get_shared_vector_store
    except ImportError:
        from professional_enhanced_compliance import get_shared_embeddings, get_shared_vector_store
    get_shared_embeddings()
    get_shared_vector_store()
    logger.info("✅ Preloaded embeddings and ChromaDB client.")
    yield
    logger.info("🛑 Shutting down FinReg API...")

# Initialize FastAPI app
app = FastAPI(
    title="FinReg API - Indian Companies Act Compliance Checker",
    description="Compliance analysis focused exclusively on Indian Companies Act, Rules, and MCA forms with deadlines and documentation.",
    version="3.0.0",
    lifespan=lifespan,
)

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception occurred: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "An unexpected server error occurred. No internal details have been leaked."}
    )

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "FinReg API - Indian Companies Act Compliance Checker 🇮🇳", "status": "operational"}

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "version": "3.0.0",
        "features": ["regulatory_mapping", "section_analysis", "confidence_scoring", "citation_tracking"]
    }



@app.get("/regulatory-citations")
def get_regulatory_citations():
    """Get list of tracked Indian compliance items"""
    try:
        analyzer = EnhancedComplianceAnalyzer()
        citations = []
        for reg_category, reg_data in analyzer.regulatory_mappings.items():
            for section_key, section_info in reg_data["sections"].items():
                citations.append({
                    "code": section_key,
                    "citation": section_info.get("citation", ""),
                    "category": reg_category,
                    "title": reg_data.get("title", ""),
                    "requirement": section_info.get("rule", ""),
                    "deadline": section_info.get("deadline_rule", ""),
                    "frequency": section_info.get("frequency", ""),
                    "source_url": section_info.get("source_url", "")
                })
        return {
            "total_items": len(citations),
            "items": citations,
            "categories": list(set(c["category"] for c in citations))
        }
    except Exception as e:
        logger.error(f"Error in get_regulatory_citations: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": "An internal error occurred while fetching regulatory citations."})

@app.post("/query-paragraphs")
async def query_paragraphs(
    pdf: UploadFile = File(...),
    q: str = Form(...),
    k: int = Form(5),
):
    """Query the persistent regulations ChromaDB using BAAI/bge-small-en-v1.5 embeddings"""
    try:
        # Validate uploaded file
        content, error_response = validate_uploaded_pdf(pdf)
        if error_response:
            return error_response
            
        clean_filename = os.path.basename(pdf.filename)
        logger.info(f"📄 Processing query regulations search for: '{q}' (k={k}) in {clean_filename}")
        
        # Load analyzer to reuse its persistent vector store connection
        analyzer = ProfessionalEnhancedComplianceAnalyzer()
        
        # Query regulations database
        results = analyzer.vector_store.similarity_search_with_score(q, k=k)
        
        output_results = []
        for doc, score in results:
            l2_dist = float(score)
            cos_sim = 1.0 - (l2_dist / 2.0)
            
            output_results.append({
                "page": doc.metadata.get("page_number", 1),
                "score": round(cos_sim, 4),
                "snippet": doc.page_content.strip(),
                "source": doc.metadata.get("source_filename", "compliance rules pdf.pdf")
            })
            
        return JSONResponse(content={
            "query": q,
            "k": k,
            "results": output_results
        })
        
    except Exception as e:
        logger.error(f"Error in query_paragraphs: {str(e)}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": "An unexpected error occurred while querying compliance paragraphs."})

@app.post("/analyze-retrieval")
async def analyze_retrieval(
    user_document: UploadFile = File(...),
):
    """Parse uploaded company document and return retrieved regulation and company chunks for each requirement"""
    try:
        # Validate uploaded file
        content, error_response = validate_uploaded_pdf(user_document)
        if error_response:
            return error_response
            
        clean_filename = os.path.basename(user_document.filename)
        logger.info(f"📄 Running retrieval analysis for uploaded document: {clean_filename}")
        
        # Extract text using our robust utility
        try:
            from .utils import extract_text
        except ImportError:
            from utils import extract_text
            
        document_text = extract_text(content, filename=clean_filename)
        
        if not document_text.strip():
            return JSONResponse(status_code=400, content={"error": "Uploaded document contains no readable text."})
            
        # Instantiate analyzer and get retrieval mapping
        analyzer = ProfessionalEnhancedComplianceAnalyzer()
        retrieval_mapping = analyzer.retrieve_compliance_context(document_text)
        
        return JSONResponse(content=retrieval_mapping)
        
    except Exception as e:
        logger.error(f"Error in analyze-retrieval: {str(e)}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": "An unexpected error occurred during document retrieval analysis."})


@app.post("/generate-detailed-report/")
async def generate_detailed_report(
    user_document: UploadFile = File(...),
    user_query: str = Form("Generate a detailed Indian Companies Act 2013 compliance report"),
):
    """Generate comprehensive enhanced compliance report from uploaded document"""
    try:
        # Validate uploaded file
        content, error_response = validate_uploaded_pdf(user_document)
        if error_response:
            return error_response
            
        clean_filename = os.path.basename(user_document.filename)
        logger.info(f"📄 Generating enhanced detailed report for: {clean_filename}")
        logger.info(f"📝 Query: {user_query}")
        
        # Extract text using our robust utility
        document_text = extract_text(content, filename=clean_filename)
        
        if not document_text.strip():
            return JSONResponse(status_code=400, content={"error": "Uploaded document contains no readable text."})
            
        # Generate professional enhanced compliance report
        company_name = clean_filename.split('.')[0].replace('_', ' ').title()
        pdf_bytes = create_professional_compliance_report(
            text_content=document_text,
            company_name=company_name
        )
        
        # Save to temporary file for response
        report_uuid = str(uuid.uuid4())
        pdf_filename = os.path.join(tempfile.gettempdir(), f"report_{report_uuid}.pdf")
        with open(pdf_filename, 'wb') as f:
            f.write(pdf_bytes)
        
        return FileResponse(
            pdf_filename,
            media_type="application/pdf",
            filename=f"enhanced_compliance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        )
        
    except Exception as e:
        logger.error(f"Error generating enhanced detailed report: {str(e)}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": "An unexpected error occurred while compiling the detailed PDF report."})

@app.post("/indian-compliance-report")
async def generate_indian_compliance_report(request: IndianComplianceRequest):
    """Generate Indian Companies Act compliance report from JSON input"""
    try:
        logger.info(f"🇮🇳 Generating Indian compliance report for {request.company_name}")
        logger.info(f"📄 Processing {len(request.compliance_data)} characters of compliance data")
        
        # Initialize analyzer
        analyzer = EnhancedComplianceAnalyzer()
        
        # Process the compliance data
        sections = analyzer.segment_document(request.compliance_data)
        logger.info(f"📄 Document segmented into {len(sections)} sections")
        
        # Map to Indian regulations
        mappings = analyzer.map_to_regulations(sections)
        logger.info(f"🇮🇳 Generated {len(mappings)} Indian compliance mappings")
        
        document_stats = {
            "length": len(request.compliance_data),
            "sections": len(sections),
            "mappings": len(mappings),
        }
        
        # Build checklist and report
        indian_reporter = IndianComplianceReportGenerator(analyzer)
        checklist = indian_reporter.build_checklist(mappings)
        report_text = indian_reporter.render_report(checklist, "Indian Companies Act Compliance Analysis", document_stats)
        
        # Create PDF
        report_uuid = str(uuid.uuid4())
        pdf_filename = os.path.join(tempfile.gettempdir(), f"report_{report_uuid}.pdf")
        create_indian_compliance_pdf(report_text, checklist, mappings, pdf_filename, request.company_name)
        
        return FileResponse(
            pdf_filename, 
            media_type="application/pdf", 
            filename=f"indian_compliance_report_{request.company_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        )
        
    except Exception as e:
        logger.error(f"Error generating Indian compliance report: {str(e)}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": "An unexpected error occurred while compiling the compliance checklist report."})

import uuid

@app.post("/analyze-compliance")
async def analyze_compliance(
    user_document: UploadFile = File(...),
):
    """Parse uploaded company document, perform Gemini compliance analysis, generate cached report, and return detailed JSON results"""
    try:
        # Validate uploaded file
        content, error_response = validate_uploaded_pdf(user_document)
        if error_response:
            return error_response
            
        clean_filename = os.path.basename(user_document.filename)
        logger.info(f"📄 Consolidated analyze-compliance request received for: {clean_filename}")
        
        # 2. Extract text using robust utility
        document_text = extract_text(content, filename=clean_filename)
        if not document_text.strip():
            return JSONResponse(status_code=400, content={"error": "Uploaded document contains no readable text."})
            
        # 3. Instantiate professional analyzer and run RAG + Gemini analysis
        analyzer = ProfessionalEnhancedComplianceAnalyzer()
        company_name = clean_filename.split('.')[0].replace('_', ' ').title()
        analysis_data = analyzer.analyze_document(document_text, company_name)
        
        # 4. Generate the PDF report immediately and save to cache
        pdf_bytes = generate_pdf_report_from_data(analysis_data, company_name)
        report_id = str(uuid.uuid4())
        pdf_filename = os.path.join(tempfile.gettempdir(), f"report_{report_id}.pdf")
        with open(pdf_filename, 'wb') as f:
            f.write(pdf_bytes)
        logger.info(f"💾 Saved report PDF to cache: {pdf_filename}")
        
        # 5. Format detailed analysis findings
        findings_list = []
        for item in analysis_data["detailed_analysis"]:
            # Extract company evidence & regulation evidence quotes
            ev_company = ""
            ev_reg = ""
            for ev in item.evidence_found:
                if ev.section_reference == "Company Document":
                    ev_company += ev.text_snippet + "\n"
                else:
                    ev_reg += ev.text_snippet + "\n"
            ev_company = ev_company.strip()
            ev_reg = ev_reg.strip()
            
            # Extract citation & page numbers from rag_metadata
            citation_str = item.legal_citation
            page_numbers_list = []
            
            rag = getattr(item, 'rag_metadata', None)
            if rag:
                reg_chunks = rag.get("regulation_chunks", [])
                for r in reg_chunks:
                    p_num = r.get("page_number", "Unknown")
                    if p_num not in page_numbers_list:
                        page_numbers_list.append(str(p_num))
            
            # Format recommendations
            rec_text = ""
            if item.recommendations:
                rec_text = "\n".join([f"{r.priority} Priority: {r.action_required} (Timeline: {r.timeline})" for r in item.recommendations])
            
            findings_list.append({
                "requirement_code": item.section_code,
                "regulation_name": item.section_title,
                "status": item.compliance_status.value,
                "risk_level": item.risk_level.value,
                "confidence_score": item.compliance_score, # out of 100
                "gap_summary": item.gap_analysis,
                "reasoning": item.compliance_rationale,
                "evidence_company": ev_company,
                "evidence_regulation": ev_reg,
                "source_citations": citation_str,
                "page_numbers": ", ".join(page_numbers_list) if page_numbers_list else "Unknown",
                "recommendations": rec_text,
                "rag_metadata": rag
            })
            
        # 6. Format metrics and distribution summary
        metrics = analysis_data["overall_metrics"]
        
        # Determine overall risk text description based on risk distribution
        if metrics["risk_distribution"]["critical"] > 0:
            overall_risk = "Critical"
        elif metrics["risk_distribution"]["high"] > 0:
            overall_risk = "High"
        elif metrics["risk_distribution"]["medium"] > 0:
            overall_risk = "Medium"
        else:
            overall_risk = "Low"
            
        # Overall confidence score average
        conf_scores = [item.compliance_score for item in analysis_data["detailed_analysis"]]
        avg_confidence = sum(conf_scores) / len(conf_scores) if conf_scores else 0.0
        
        summary_info = {
            "compliant_count": metrics["compliance_distribution"]["fully_compliant"],
            "partially_compliant_count": metrics["compliance_distribution"]["partially_compliant"],
            "non_compliant_count": metrics["compliance_distribution"]["non_compliant"],
            "total_count": metrics["total_requirements_assessed"],
            "average_confidence": round(avg_confidence, 2),
            "executive_summary": analysis_data["executive_summary"]
        }
        
        response_json = {
            "report_id": report_id,
            "overall_score": metrics["overall_compliance_score"],
            "overall_risk": overall_risk,
            "findings": findings_list,
            "summary": summary_info
        }
        
        return JSONResponse(content=response_json)
        
    except Exception as e:
        logger.error(f"Error in POST /analyze-compliance: {str(e)}", exc_info=True)
        # Specific user friendly check for rate limit quota limits
        err_msg = str(e)
        if "quota" in err_msg.lower() or "429" in err_msg.lower():
            friendly_msg = "Gemini API daily compliance analysis quota exceeded. Please configure an upgraded key or try again tomorrow."
        else:
            friendly_msg = "An unexpected error occurred during compliance document analysis. No details have been leaked."
        return JSONResponse(status_code=500, content={"error": friendly_msg})

@app.get("/download-report/{report_id}")
def download_report(report_id: str):
    """Download the pre-generated PDF report for the given report_id without invoking Gemini again"""
    try:
        # Sanitize report_id to avoid path traversal
        sanitized_id = re.sub(r'[^a-zA-Z0-9\-]', '', report_id)
        pdf_filename = os.path.join(tempfile.gettempdir(), f"report_{sanitized_id}.pdf")
        if not os.path.exists(pdf_filename):
            return JSONResponse(status_code=404, content={"error": "Report not found or has expired."})
            
        logger.info(f"📥 Streaming pre-generated report PDF: {pdf_filename}")
        return FileResponse(
            pdf_filename,
            media_type="application/pdf",
            filename=f"compliance_report_{sanitized_id[:8]}.pdf"
        )
    except Exception as e:
        logger.error(f"Error in GET /download-report: {str(e)}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": "Failed to stream the cached compliance report PDF."})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
