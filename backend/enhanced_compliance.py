import os
import tempfile
import re
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from collections import Counter, defaultdict

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib import colors
from reportlab.lib.units import inch, cm
from reportlab.platypus.flowables import HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY

# Try to import ChromaDB and Ollama
try:
    import chromadb
    from chromadb.config import Settings
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False

try:
    import ollama
    HAS_OLLAMA = True
except ImportError:
    HAS_OLLAMA = False

@dataclass
class ComplianceEvidence:
    """Evidence found for a compliance requirement"""
    text: str
    confidence: float
    context: str
    page_reference: Optional[str] = None
    keywords_matched: List[str] = None

@dataclass
class ComplianceItem:
    """Enhanced compliance item with detailed analysis"""
    code: str
    title: str
    description: str
    legal_basis: str
    deadline: str
    frequency: str
    importance_level: str  # Critical, High, Medium, Low
    business_impact: str
    regulatory_risk: str
    required_documents: List[str]
    responsible_parties: List[str]
    mca_reference: str
    status: str  # Met, Incomplete, Missing
    confidence_score: float
    evidence: List[ComplianceEvidence]
    explanation: str
    remediation_steps: List[str]
    forms_required: List[str]
    deadlines_upcoming: List[str]
    risk_rating: str  # High, Medium, Low
    
class EnhancedComplianceAnalyzer:
    """Advanced compliance analyzer with ChromaDB, semantic search, and RAG"""
    
    def __init__(self):
        self.regulatory_framework = self._initialize_regulatory_framework()
        self.vector_db = self._initialize_chroma_db()
        self.compliance_groups = self._define_compliance_groups()
        print("✅ Enhanced Compliance Analyzer initialized with semantic search capabilities")
    
    def _initialize_chroma_db(self):
        """Initialize ChromaDB with Ollama embeddings"""
        if not HAS_CHROMADB:
            print("⚠️ ChromaDB not available, using fallback analysis")
            return None
            
        try:
            # Initialize ChromaDB client
            client = chromadb.PersistentClient(path="./chroma_db")
            
            # Get or create collection for Indian compliance
            collection = client.get_or_create_collection(
                name="indian_compliance_requirements",
                metadata={"description": "Indian Companies Act compliance requirements"}
            )
            
            # Populate with regulatory requirements if empty
            if collection.count() == 0:
                self._populate_regulatory_knowledge(collection)
            
            print(f"✅ ChromaDB initialized with {collection.count()} regulatory requirements")
            return collection
            
        except Exception as e:
            print(f"⚠️ ChromaDB initialization failed: {e}")
            return None
    
    def _populate_regulatory_knowledge(self, collection):
        """Populate ChromaDB with comprehensive regulatory knowledge"""
        documents = []
        metadatas = []
        ids = []
        
        for req_code, req_data in self.regulatory_framework.items():
            # Create comprehensive document text for embedding
            doc_text = f"""
            {req_data['title']} - {req_code}
            Legal Basis: {req_data['legal_basis']}
            Description: {req_data['description']}
            Requirements: {' '.join(req_data['required_documents'])}
            Keywords: {' '.join(req_data['detection_keywords'])}
            Business Impact: {req_data['business_impact']}
            Compliance Indicators: {' '.join(req_data['compliance_indicators'])}
            """
            
            documents.append(doc_text.strip())
            metadatas.append({
                "requirement_code": req_code,
                "title": req_data['title'],
                "legal_basis": req_data['legal_basis'],
                "importance": req_data['importance_level'],
                "group": req_data['group']
            })
            ids.append(f"req_{req_code}")
        
        # Add documents to collection
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        print(f"✅ Populated ChromaDB with {len(documents)} regulatory requirements")
    
    def _initialize_regulatory_framework(self):
        """Comprehensive Indian Companies Act regulatory framework"""
        return {
            "AGM": {
                "title": "Annual General Meeting",
                "description": "Mandatory annual meeting of shareholders to approve accounts, appoint directors, and conduct other business",
                "legal_basis": "Section 96, Companies Act, 2013",
                "deadline": "Within 6 months from close of financial year",
                "frequency": "Annual",
                "importance_level": "Critical",
                "group": "Board Matters",
                "business_impact": "Non-compliance can result in penalties up to ₹1 lakh per default and potential legal action by shareholders",
                "regulatory_risk": "High - MCA prosecution possible, director disqualification risk",
                "required_documents": [
                    "Notice of AGM (21 days advance)",
                    "Annual Report including Audited Financial Statements",
                    "Board's Report with attachments",
                    "Auditor's Report",
                    "Minutes of AGM",
                    "Attendance register"
                ],
                "responsible_parties": ["Board of Directors", "Company Secretary", "CFO"],
                "mca_reference": "https://www.mca.gov.in/content/mca/global/en/acts-rules/ebooks/acts.html",
                "detection_keywords": ["annual general meeting", "AGM", "shareholders meeting", "annual report"],
                "compliance_indicators": ["AGM notice", "AGM held", "annual report", "shareholder meeting"],
                "forms_required": ["MGT-14 (AGM Resolution)", "MGT-15 (Notice to ROC)"],
                "remediation_template": "Schedule AGM immediately, prepare required documents, file necessary forms with MCA"
            },
            "AOC_4": {
                "title": "Filing of Financial Statements",
                "description": "Annual filing of audited financial statements, board report, and auditor's report with MCA",
                "legal_basis": "Section 137, Companies Act, 2013; Rule 12, Companies (Accounts) Rules, 2014",
                "deadline": "Within 30 days of AGM (180 days for OPC from FY end)",
                "frequency": "Annual",
                "importance_level": "Critical",
                "group": "Annual Filings",
                "business_impact": "Late filing attracts penalties, impacts credit rating, and can affect business operations",
                "regulatory_risk": "High - Additional fees, prosecution possible for extended delays",
                "required_documents": [
                    "Audited Financial Statements",
                    "Board's Report",
                    "Auditor's Report",
                    "Cash Flow Statement",
                    "Notes to Accounts",
                    "CSR Report (if applicable)"
                ],
                "responsible_parties": ["CFO", "Auditor", "Company Secretary", "Board of Directors"],
                "mca_reference": "https://www.mca.gov.in/content/mca/global/en/data-and-reports/forms/form-aoc-4.html",
                "detection_keywords": ["financial statements", "AOC-4", "audited accounts", "balance sheet", "profit loss"],
                "compliance_indicators": ["AOC-4 filed", "financial statements", "auditor report", "board report"],
                "forms_required": ["Form AOC-4"],
                "remediation_template": "Finalize audited accounts, obtain board approval, file AOC-4 within deadline"
            },
            "MGT_7": {
                "title": "Annual Return Filing",
                "description": "Comprehensive annual return containing company particulars, shareholding, and other statutory information",
                "legal_basis": "Section 92, Companies Act, 2013; Rule 11, Companies (Management & Administration) Rules, 2014",
                "deadline": "Within 60 days of AGM",
                "frequency": "Annual", 
                "importance_level": "Critical",
                "group": "Annual Filings",
                "business_impact": "Essential for maintaining good standing, impacts statutory compliance record",
                "regulatory_risk": "Medium to High - Penalties increase with delay, affects company's legal status",
                "required_documents": [
                    "Updated Register of Members",
                    "Details of shareholding changes",
                    "Board and Committee composition",
                    "Registered office details",
                    "Details of charges/borrowings"
                ],
                "responsible_parties": ["Company Secretary", "CFO", "Board of Directors"],
                "mca_reference": "https://www.mca.gov.in/content/mca/global/en/data-and-reports/forms/form-mgt-7.html",
                "detection_keywords": ["annual return", "MGT-7", "shareholding pattern", "register of members"],
                "compliance_indicators": ["MGT-7 filed", "annual return", "shareholding details", "member register"],
                "forms_required": ["Form MGT-7"],
                "remediation_template": "Update registers, compile shareholding data, file MGT-7 within 60 days of AGM"
            },
            "DIR3_KYC": {
                "title": "Directors KYC Verification",
                "description": "Annual KYC compliance for all directors to maintain active DIN status",
                "legal_basis": "Rule 12A, Companies (Appointment & Qualification of Directors) Rules, 2014",
                "deadline": "Between April 1 - September 30 annually",
                "frequency": "Annual",
                "importance_level": "High",
                "group": "Director Compliance",
                "business_impact": "Non-compliance leads to DIN deactivation, affecting director's ability to serve",
                "regulatory_risk": "Medium - DIN becomes inactive, director cannot act until reactivation",
                "required_documents": [
                    "DIR-3 KYC form",
                    "Identity proof (PAN, Aadhaar)",
                    "Address proof",
                    "Photograph",
                    "Mobile number and email verification"
                ],
                "responsible_parties": ["Individual Directors", "Company Secretary"],
                "mca_reference": "https://www.mca.gov.in/content/mca/global/en/data-and-reports/forms/form-dir-3-kyc.html",
                "detection_keywords": ["director KYC", "DIR-3", "DIN verification", "director identification"],
                "compliance_indicators": ["DIR-3 KYC", "director verification", "DIN active", "KYC compliance"],
                "forms_required": ["Form DIR-3 KYC"],
                "remediation_template": "Each director must file DIR-3 KYC individually before September 30"
            },
            "BOARD_MEETINGS": {
                "title": "Board Meetings Compliance",
                "description": "Regular board meetings with proper notice, quorum, minutes, and resolutions",
                "legal_basis": "Section 173, Companies Act, 2013; Companies (Meetings of Board) Rules, 2014",
                "deadline": "At least 4 meetings per year with max 120 days gap",
                "frequency": "Quarterly minimum",
                "importance_level": "High",
                "group": "Board Matters",
                "business_impact": "Essential for corporate governance, decision-making, and regulatory compliance",
                "regulatory_risk": "Medium - Penalties for non-compliance, governance issues",
                "required_documents": [
                    "Board meeting notices (7 days advance)",
                    "Board meeting minutes",
                    "Board resolutions",
                    "Attendance register",
                    "Declaration of interests"
                ],
                "responsible_parties": ["Board of Directors", "Company Secretary"],
                "mca_reference": "https://www.mca.gov.in/content/mca/global/en/acts-rules/rules/companies-meetings-of-board-and-its-powers-rules-2014.html",
                "detection_keywords": ["board meeting", "board resolution", "minutes", "quorum", "directors meeting"],
                "compliance_indicators": ["board meetings held", "minutes recorded", "resolutions passed", "quorum maintained"],
                "forms_required": ["MGT-14 (Special Resolutions)", "Internal documentation"],
                "remediation_template": "Schedule regular board meetings, ensure proper documentation and minute-keeping"
            }
        }
    
    def _define_compliance_groups(self):
        """Define logical groupings for compliance requirements"""
        return {
            "Board Matters": {
                "description": "Board meetings, director appointments, and corporate governance",
                "priority": 1,
                "color": colors.HexColor('#1f4e79')
            },
            "Annual Filings": {
                "description": "Mandatory annual filings with MCA including financial statements and returns",
                "priority": 2,
                "color": colors.HexColor('#2e8b57')
            },
            "Director Compliance": {
                "description": "Director-specific compliance requirements and verifications",
                "priority": 3,
                "color": colors.HexColor('#8b4513')
            },
            "Periodic Returns": {
                "description": "Regular filings and returns as per regulatory schedule",
                "priority": 4,
                "color": colors.HexColor('#4b0082')
            }
        }
    
    def analyze_document_with_rag(self, document_text: str) -> List[ComplianceItem]:
        """Perform comprehensive RAG-based compliance analysis"""
        print("🔍 Starting semantic compliance analysis...")
        
        compliance_items = []
        
        for req_code, req_data in self.regulatory_framework.items():
            print(f"📋 Analyzing requirement: {req_code}")
            
            # Perform semantic search if ChromaDB is available
            evidence = self._find_semantic_evidence(document_text, req_code, req_data)
            
            # Determine compliance status and confidence
            status, confidence, explanation = self._determine_compliance_status(evidence, req_data)
            
            # Generate remediation steps
            remediation_steps = self._generate_remediation_steps(status, req_data)
            
            # Create compliance item
            compliance_item = ComplianceItem(
                code=req_code,
                title=req_data['title'],
                description=req_data['description'],
                legal_basis=req_data['legal_basis'],
                deadline=req_data['deadline'],
                frequency=req_data['frequency'],
                importance_level=req_data['importance_level'],
                business_impact=req_data['business_impact'],
                regulatory_risk=req_data['regulatory_risk'],
                required_documents=req_data['required_documents'],
                responsible_parties=req_data['responsible_parties'],
                mca_reference=req_data['mca_reference'],
                status=status,
                confidence_score=confidence,
                evidence=evidence,
                explanation=explanation,
                remediation_steps=remediation_steps,
                forms_required=req_data['forms_required'],
                deadlines_upcoming=self._calculate_upcoming_deadlines(req_data),
                risk_rating=self._assess_risk_rating(status, req_data['importance_level'])
            )
            
            compliance_items.append(compliance_item)
        
        print(f"✅ Analysis complete: {len(compliance_items)} requirements analyzed")
        return compliance_items
    
    def _find_semantic_evidence(self, document_text: str, req_code: str, req_data: dict) -> List[ComplianceEvidence]:
        """Use semantic search to find evidence of compliance"""
        evidence = []
        
        # Use ChromaDB semantic search if available
        if self.vector_db:
            try:
                # Query for relevant content
                results = self.vector_db.query(
                    query_texts=[document_text[:1000]],  # Limit query length
                    n_results=3,
                    where={"requirement_code": req_code}
                )
                
                if results['documents'] and results['documents'][0]:
                    for doc, distance in zip(results['documents'][0], results['distances'][0]):
                        confidence = max(0, 1 - distance)  # Convert distance to confidence
                        if confidence > 0.3:
                            evidence.append(ComplianceEvidence(
                                text=doc[:200] + "..." if len(doc) > 200 else doc,
                                confidence=confidence,
                                context="Semantic search match",
                                keywords_matched=[]
                            ))
            except Exception as e:
                print(f"⚠️ Semantic search failed for {req_code}: {e}")
        
        # Fallback to keyword-based search
        doc_lower = document_text.lower()
        for keyword in req_data['detection_keywords']:
            if keyword.lower() in doc_lower:
                # Find context around the keyword
                keyword_pos = doc_lower.find(keyword.lower())
                context_start = max(0, keyword_pos - 100)
                context_end = min(len(document_text), keyword_pos + 100)
                context = document_text[context_start:context_end]
                
                evidence.append(ComplianceEvidence(
                    text=context,
                    confidence=0.7,
                    context=f"Keyword match: '{keyword}'",
                    keywords_matched=[keyword]
                ))
        
        # Look for compliance indicators
        for indicator in req_data['compliance_indicators']:
            if indicator.lower() in doc_lower:
                indicator_pos = doc_lower.find(indicator.lower())
                context_start = max(0, indicator_pos - 150)
                context_end = min(len(document_text), indicator_pos + 150)
                context = document_text[context_start:context_end]
                
                evidence.append(ComplianceEvidence(
                    text=context,
                    confidence=0.8,
                    context=f"Compliance indicator: '{indicator}'",
                    keywords_matched=[indicator]
                ))
        
        return evidence[:5]  # Return top 5 pieces of evidence
    
    def _determine_compliance_status(self, evidence: List[ComplianceEvidence], req_data: dict) -> Tuple[str, float, str]:
        """Determine compliance status with detailed explanation"""
        if not evidence:
            return "Missing", 0.0, f"""
            **Status: Missing** - No evidence found for {req_data['title']}.
            
            **Why this matters:** {req_data['business_impact']}
            
            **Regulatory Risk:** {req_data['regulatory_risk']}
            
            **Action Required:** Immediate attention needed to implement this requirement.
            """
        
        avg_confidence = sum(e.confidence for e in evidence) / len(evidence)
        max_confidence = max(e.confidence for e in evidence)
        
        if max_confidence >= 0.75 and len(evidence) >= 2:
            return "Met", max_confidence, f"""
            **Status: Met** - Strong evidence found for {req_data['title']}.
            
            **Evidence Quality:** High confidence ({max_confidence:.1%}) with {len(evidence)} supporting indicators.
            
            **Business Benefit:** This requirement is properly addressed, reducing regulatory risk.
            
            **Next Steps:** Continue monitoring for ongoing compliance and periodic reviews.
            """
        
        elif max_confidence >= 0.5 or len(evidence) >= 1:
            return "Incomplete", avg_confidence, f"""
            **Status: Incomplete** - Partial evidence found for {req_data['title']}.
            
            **Evidence Quality:** Moderate confidence ({avg_confidence:.1%}) but may lack completeness.
            
            **Why this matters:** {req_data['business_impact']}
            
            **Gaps Identified:** Documentation or implementation may be insufficient for full compliance.
            
            **Action Required:** Strengthen existing processes and documentation.
            """
        
        else:
            return "Missing", avg_confidence, f"""
            **Status: Missing** - Insufficient evidence for {req_data['title']}.
            
            **Evidence Quality:** Low confidence ({avg_confidence:.1%}) indicates significant gaps.
            
            **Business Impact:** {req_data['business_impact']}
            
            **Regulatory Risk:** {req_data['regulatory_risk']}
            
            **Immediate Action Required:** Implement this requirement to avoid penalties and ensure compliance.
            """
    
    def _generate_remediation_steps(self, status: str, req_data: dict) -> List[str]:
        """Generate detailed step-by-step remediation instructions"""
        base_steps = []
        
        if status == "Met":
            base_steps = [
                "✅ Continue current compliance practices",
                "📅 Schedule periodic review to ensure ongoing compliance",
                "📋 Document current processes for consistency",
                "🔍 Monitor for any regulatory changes or updates"
            ]
        
        elif status == "Incomplete":
            base_steps = [
                f"📋 Review current {req_data['title']} documentation for gaps",
                f"👥 Assign responsibility to: {', '.join(req_data['responsible_parties'])}",
                "📝 Strengthen existing documentation and processes",
                "🔍 Conduct internal audit to identify specific deficiencies",
                "📅 Set timeline for completion based on deadline requirements",
                "✅ Implement quality checks and approval processes"
            ]
        
        else:  # Missing
            base_steps = [
                f"🚨 **IMMEDIATE ACTION:** Implement {req_data['title']} compliance",
                f"👥 **Responsible Parties:** {', '.join(req_data['responsible_parties'])}",
                f"📅 **Deadline:** {req_data['deadline']}",
                "📋 **Required Documents:**"
            ]
            
            # Add specific document requirements
            for doc in req_data['required_documents']:
                base_steps.append(f"   • {doc}")
            
            base_steps.extend([
                f"📄 **Forms to File:** {', '.join(req_data['forms_required'])}",
                f"🔗 **MCA Reference:** {req_data['mca_reference']}",
                "⚖️ **Legal Consultation:** Consider consulting with company secretary or legal advisor",
                "📅 **Timeline:** Create detailed implementation timeline with milestones",
                "✅ **Validation:** Set up monitoring and validation processes"
            ])
        
        return base_steps
    
    def _calculate_upcoming_deadlines(self, req_data: dict) -> List[str]:
        """Calculate upcoming deadlines based on requirement frequency"""
        deadlines = []
        current_date = datetime.now()
        
        # This is a simplified version - in practice, you'd calculate based on actual company dates
        if req_data['frequency'] == 'Annual':
            if 'AGM' in req_data['deadline']:
                deadlines.append("AGM due by September 30, 2024")
            if 'financial year' in req_data['deadline']:
                deadlines.append("Within 6 months of FY end (March 31)")
        
        return deadlines
    
    def _assess_risk_rating(self, status: str, importance_level: str) -> str:
        """Assess overall risk rating based on status and importance"""
        risk_matrix = {
            ("Missing", "Critical"): "High",
            ("Missing", "High"): "High", 
            ("Missing", "Medium"): "Medium",
            ("Incomplete", "Critical"): "High",
            ("Incomplete", "High"): "Medium",
            ("Incomplete", "Medium"): "Medium",
            ("Met", "Critical"): "Low",
            ("Met", "High"): "Low",
            ("Met", "Medium"): "Low"
        }
        
        return risk_matrix.get((status, importance_level), "Medium")


class EnhancedPDFGenerator:
    """Advanced PDF generator with professional formatting and comprehensive content"""
    
    def __init__(self):
        self.colors = {
            'met': colors.HexColor('#28a745'),
            'incomplete': colors.HexColor('#ffc107'), 
            'missing': colors.HexColor('#dc3545'),
            'primary': colors.HexColor('#0b3d91'),
            'secondary': colors.HexColor('#6c757d'),
            'light_gray': colors.HexColor('#f8f9fa'),
            'dark_gray': colors.HexColor('#495057')
        }
        
        self.status_icons = {
            'Met': '✅',
            'Incomplete': '🟡', 
            'Missing': '❌'
        }
    
    def generate_comprehensive_report(
        self, 
        compliance_items: List[ComplianceItem], 
        company_name: str, 
        document_stats: dict,
        output_path: str
    ):
        """Generate comprehensive compliance report with all enhancements"""
        
        # Create PDF document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            topMargin=1*inch,
            bottomMargin=0.8*inch,
            leftMargin=0.7*inch,
            rightMargin=0.7*inch
        )
        
        # Initialize styles
        styles = self._create_custom_styles()
        
        # Build story elements
        story = []
        
        # Add header and title page
        story.extend(self._create_title_page(company_name, document_stats, styles))
        
        # Add executive summary
        story.extend(self._create_executive_summary(compliance_items, styles))
        
        # Add compliance overview
        story.extend(self._create_compliance_overview(compliance_items, styles))
        
        # Add grouped detailed analysis
        story.extend(self._create_grouped_analysis(compliance_items, styles))
        
        # Add risk matrix
        story.extend(self._create_risk_matrix(compliance_items, styles))
        
        # Add action plan
        story.extend(self._create_action_plan(compliance_items, styles))
        
        # Add glossary and references
        story.extend(self._create_glossary_and_references(styles))
        
        # Build PDF with custom page templates
        doc.build(story, onFirstPage=self._create_header_footer, onLaterPages=self._create_header_footer)
        
        print(f"✅ Comprehensive compliance report generated: {output_path}")
    
    def _create_custom_styles(self) -> dict:
        """Create comprehensive custom styles for the PDF"""
        base_styles = getSampleStyleSheet()
        
        styles = {
            'title': ParagraphStyle(
                'CustomTitle',
                parent=base_styles['Title'],
                fontSize=24,
                textColor=self.colors['primary'],
                spaceAfter=20,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            ),
            'h1': ParagraphStyle(
                'CustomH1',
                parent=base_styles['Heading1'],
                fontSize=18,
                textColor=self.colors['primary'],
                spaceBefore=20,
                spaceAfter=12,
                fontName='Helvetica-Bold'
            ),
            'h2': ParagraphStyle(
                'CustomH2', 
                parent=base_styles['Heading2'],
                fontSize=14,
                textColor=self.colors['dark_gray'],
                spaceBefore=16,
                spaceAfter=8,
                fontName='Helvetica-Bold'
            ),
            'h3': ParagraphStyle(
                'CustomH3',
                parent=base_styles['Heading3'], 
                fontSize=12,
                textColor=self.colors['secondary'],
                spaceBefore=12,
                spaceAfter=6,
                fontName='Helvetica-Bold'
            ),
            'normal': ParagraphStyle(
                'CustomNormal',
                parent=base_styles['Normal'],
                fontSize=10,
                leading=14,
                textColor=colors.black,
                alignment=TA_JUSTIFY
            ),
            'small': ParagraphStyle(
                'CustomSmall',
                parent=base_styles['Normal'],
                fontSize=8,
                leading=11,
                textColor=self.colors['secondary']
            ),
            'center': ParagraphStyle(
                'CustomCenter',
                parent=base_styles['Normal'],
                fontSize=10,
                alignment=TA_CENTER
            )
        }
        
        return styles
    
    def _create_header_footer(self, canvas, doc):
        """Create professional header and footer"""
        canvas.saveState()
        width, height = A4
        
        # Header
        canvas.setFont('Helvetica-Bold', 10)
        canvas.setFillColor(self.colors['primary'])
        canvas.drawString(0.7*inch, height - 0.6*inch, "Indian Companies Act Compliance Report")
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.black)
        canvas.drawRightString(width - 0.7*inch, height - 0.6*inch, datetime.now().strftime('%B %d, %Y'))
        
        # Footer
        canvas.setFont('Helvetica-Oblique', 8)
        canvas.setFillColor(self.colors['secondary'])
        canvas.drawString(0.7*inch, 0.5*inch, "Confidential - For Internal Use Only")
        canvas.drawCentredString(width/2, 0.5*inch, "Ministry of Corporate Affairs - Companies Act, 2013")
        canvas.drawRightString(width - 0.7*inch, 0.5*inch, f"Page {canvas.getPageNumber()}")
        
        canvas.restoreState()
    
    def _create_title_page(self, company_name: str, document_stats: dict, styles: dict) -> List:
        """Create professional title page"""
        elements = []
        
        # Main title
        elements.append(Paragraph("Indian Companies Act 2013", styles['title']))
        elements.append(Paragraph("Compliance Assessment Report", styles['title']))
        elements.append(Spacer(1, 30))
        
        # Company information
        elements.append(Paragraph(f"<b>Company:</b> {company_name}", styles['h2']))
        elements.append(Paragraph(f"<b>Report Date:</b> {datetime.now().strftime('%B %d, %Y')}", styles['normal']))
        elements.append(Paragraph(f"<b>Analysis Scope:</b> Comprehensive regulatory compliance review", styles['normal']))
        elements.append(Spacer(1, 40))
        
        # Document statistics
        stats_data = [
            ['Analysis Metrics', 'Value'],
            ['Document Length Analyzed', f"{document_stats.get('length', 0):,} characters"],
            ['Regulatory Requirements Checked', str(document_stats.get('total_requirements', 0))],
            ['Evidence Items Identified', str(document_stats.get('evidence_count', 0))],
            ['Compliance Framework', 'Indian Companies Act, 2013 & Rules']
        ]
        
        stats_table = Table(stats_data, colWidths=[3*inch, 2*inch])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.colors['primary']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.colors['light_gray']])
        ]))
        
        elements.append(stats_table)
        elements.append(PageBreak())
        
        return elements
    
    def _create_executive_summary(self, compliance_items: List[ComplianceItem], styles: dict) -> List:
        """Create executive summary with key insights"""
        elements = []
        
        elements.append(Paragraph("Executive Summary", styles['h1']))
        elements.append(Spacer(1, 12))
        
        # Calculate summary statistics
        total_items = len(compliance_items)
        met_items = len([item for item in compliance_items if item.status == 'Met'])
        incomplete_items = len([item for item in compliance_items if item.status == 'Incomplete']) 
        missing_items = len([item for item in compliance_items if item.status == 'Missing'])
        
        high_risk_items = len([item for item in compliance_items if item.risk_rating == 'High'])
        critical_items = len([item for item in compliance_items if item.importance_level == 'Critical'])
        
        # Summary statistics table
        summary_data = [
            ['Compliance Metric', 'Count', 'Percentage', 'Status'],
            ['✅ Requirements Met', str(met_items), f'{(met_items/total_items*100):.1f}%', 'Good'],
            ['🟡 Incomplete Items', str(incomplete_items), f'{(incomplete_items/total_items*100):.1f}%', 'Attention Needed'],
            ['❌ Missing Requirements', str(missing_items), f'{(missing_items/total_items*100):.1f}%', 'Immediate Action'],
            ['🔴 High Risk Items', str(high_risk_items), f'{(high_risk_items/total_items*100):.1f}%', 'Critical Priority']
        ]
        
        summary_table = Table(summary_data, colWidths=[2.5*inch, 0.8*inch, 1*inch, 1.5*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.colors['primary']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            # Color code rows by status
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#d4f4dd')),  # Met - light green
            ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#fff3cd')),  # Incomplete - light yellow  
            ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#f8d7da')),  # Missing - light red
            ('BACKGROUND', (0, 4), (-1, 4), colors.HexColor('#f5c6cb')),  # High risk - red
        ]))
        
        elements.append(summary_table)
        elements.append(Spacer(1, 16))
        
        # Key findings
        elements.append(Paragraph("Key Findings & Recommendations", styles['h2']))
        
        findings = []
        
        if met_items >= total_items * 0.8:
            findings.append("✅ <b>Strong Compliance Posture:</b> Company demonstrates good overall compliance with Indian Companies Act requirements.")
        elif met_items >= total_items * 0.6:
            findings.append("🟡 <b>Moderate Compliance:</b> Company has reasonable compliance but attention needed for several requirements.")
        else:
            findings.append("❌ <b>Compliance Gaps:</b> Significant compliance gaps identified requiring immediate management attention.")
        
        if high_risk_items > 0:
            findings.append(f"🔴 <b>High Risk Alert:</b> {high_risk_items} high-risk compliance issues require immediate remediation.")
        
        if critical_items > met_items:
            findings.append("⚠️ <b>Critical Requirements:</b> Several critical regulatory requirements need immediate implementation.")
        
        # Top priority actions
        missing_critical = [item for item in compliance_items if item.status == 'Missing' and item.importance_level == 'Critical']
        if missing_critical:
            findings.append(f"🚨 <b>Immediate Action Required:</b> {len(missing_critical)} critical requirements are completely missing.")
        
        for finding in findings:
            elements.append(Paragraph(finding, styles['normal']))
            elements.append(Spacer(1, 6))
        
        elements.append(PageBreak())
        return elements
    
    def _create_compliance_overview(self, compliance_items: List[ComplianceItem], styles: dict) -> List:
        """Create visual compliance overview with status legend"""
        elements = []
        
        elements.append(Paragraph("Compliance Overview", styles['h1']))
        elements.append(Spacer(1, 12))
        
        # Status legend
        elements.append(Paragraph("Status Legend", styles['h2']))
        legend_data = [
            ['Status', 'Icon', 'Description', 'Action Required'],
            ['Met', '✅', 'Requirement fully satisfied with evidence', 'Monitor and maintain'],
            ['Incomplete', '🟡', 'Partial compliance or insufficient evidence', 'Strengthen and complete'],
            ['Missing', '❌', 'No evidence of compliance found', 'Immediate implementation needed']
        ]
        
        legend_table = Table(legend_data, colWidths=[1*inch, 0.6*inch, 2.5*inch, 1.7*inch])
        legend_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.colors['primary']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.colors['light_gray']])
        ]))
        
        elements.append(legend_table)
        elements.append(Spacer(1, 20))
        
        return elements
    
    def _create_grouped_analysis(self, compliance_items: List[ComplianceItem], styles: dict) -> List:
        """Create detailed analysis grouped by compliance categories"""
        elements = []
        
        elements.append(Paragraph("Detailed Compliance Analysis", styles['h1']))
        elements.append(Spacer(1, 12))
        
        # Group items by compliance group
        analyzer = EnhancedComplianceAnalyzer()
        groups = analyzer._define_compliance_groups()
        grouped_items = defaultdict(list)
        
        for item in compliance_items:
            # Find the group for this item based on regulatory framework
            item_group = "Other"
            for req_code, req_data in analyzer.regulatory_framework.items():
                if req_code == item.code:
                    item_group = req_data['group']
                    break
            grouped_items[item_group].append(item)
        
        # Process each group
        for group_name, group_info in groups.items():
            if group_name in grouped_items:
                items = grouped_items[group_name]
                
                # Group header
                elements.append(Paragraph(f"{group_name}", styles['h2']))
                elements.append(Paragraph(group_info['description'], styles['normal']))
                elements.append(Spacer(1, 10))
                
                # Create detailed table for this group
                table_data = [['Requirement', 'Status', 'Confidence', 'Risk Level', 'Key Finding']]
                
                for item in items:
                    status_icon = self.status_icons.get(item.status, '❓')
                    
                    # Truncate explanation for table
                    key_finding = item.explanation.split('\n\n')[0].replace('**Status: ' + item.status + '**', '').strip()
                    if len(key_finding) > 100:
                        key_finding = key_finding[:97] + "..."
                    
                    # Create paragraphs for proper text wrapping
                    req_para = Paragraph(f"<b>{item.code}</b><br/>{item.title}", styles['small'])
                    status_para = Paragraph(f"{status_icon}<br/>{item.status}", styles['small'])
                    conf_para = Paragraph(f"{item.confidence_score:.1%}", styles['small'])
                    risk_para = Paragraph(item.risk_rating, styles['small'])
                    finding_para = Paragraph(key_finding, styles['small'])
                    
                    table_data.append([req_para, status_para, conf_para, risk_para, finding_para])
                
                group_table = Table(table_data, colWidths=[1.8*inch, 0.8*inch, 0.7*inch, 0.7*inch, 2.5*inch])
                group_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), group_info['color']),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.colors['light_gray']]),
                    ('LEFTPADDING', (0, 0), (-1, -1), 6),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8)
                ]))
                
                # Apply status-specific row coloring
                for i, item in enumerate(items, 1):
                    if item.status == 'Met':
                        bg_color = colors.HexColor('#d4f4dd')
                    elif item.status == 'Incomplete':
                        bg_color = colors.HexColor('#fff3cd')
                    else:
                        bg_color = colors.HexColor('#f8d7da')
                    
                    group_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, i), (-1, i), bg_color)
                    ]))
                
                elements.append(group_table)
                elements.append(Spacer(1, 20))
                
                # Detailed explanations for each item in the group
                for item in items:
                    elements.append(self._create_detailed_item_analysis(item, styles))
        
        return elements
    
    def _create_detailed_item_analysis(self, item: ComplianceItem, styles: dict) -> KeepTogether:
        """Create detailed analysis for individual compliance item"""
        item_elements = []
        
        # Item header with status
        status_icon = self.status_icons.get(item.status, '❓')
        status_color = self.colors.get(item.status.lower(), colors.black)
        
        item_title_style = ParagraphStyle(
            'ItemTitle',
            parent=styles['h3'],
            textColor=status_color,
            fontSize=11,
            spaceAfter=8
        )
        
        item_elements.append(Paragraph(f"{status_icon} {item.code} - {item.title}", item_title_style))
        
        # Legal basis and deadlines
        item_elements.append(Paragraph(f"<b>Legal Basis:</b> {item.legal_basis}", styles['normal']))
        item_elements.append(Paragraph(f"<b>Deadline:</b> {item.deadline} ({item.frequency})", styles['normal']))
        item_elements.append(Paragraph(f"<b>Importance:</b> {item.importance_level} | <b>Risk Level:</b> {item.risk_rating}", styles['normal']))
        item_elements.append(Spacer(1, 6))
        
        # Status explanation
        item_elements.append(Paragraph("<b>Detailed Analysis:</b>", styles['normal']))
        # Split explanation into paragraphs for better formatting
        explanation_parts = item.explanation.split('\n\n')
        for part in explanation_parts:
            if part.strip():
                item_elements.append(Paragraph(part.strip(), styles['normal']))
        
        item_elements.append(Spacer(1, 6))
        
        # Evidence section
        if item.evidence:
            item_elements.append(Paragraph("<b>Evidence Found:</b>", styles['normal']))
            for evidence in item.evidence[:3]:  # Show top 3 pieces of evidence
                evidence_text = f"• <i>{evidence.context}</i> (Confidence: {evidence.confidence:.1%})"
                if evidence.text:
                    evidence_text += f"<br/>  \"{evidence.text[:150]}{'...' if len(evidence.text) > 150 else ''}\""
                item_elements.append(Paragraph(evidence_text, styles['small']))
            item_elements.append(Spacer(1, 6))
        
        # Required documents
        if item.required_documents:
            item_elements.append(Paragraph("<b>Required Documents:</b>", styles['normal']))
            for doc in item.required_documents:
                item_elements.append(Paragraph(f"• {doc}", styles['small']))
            item_elements.append(Spacer(1, 6))
        
        # Remediation steps
        item_elements.append(Paragraph("<b>Recommended Actions:</b>", styles['normal']))
        for step in item.remediation_steps[:5]:  # Show top 5 steps
            item_elements.append(Paragraph(f"{step}", styles['small']))
        
        # Business impact
        item_elements.append(Spacer(1, 6))
        item_elements.append(Paragraph(f"<b>Business Impact:</b> {item.business_impact}", styles['small']))
        
        # MCA reference
        if item.mca_reference:
            item_elements.append(Paragraph(f"<b>Reference:</b> <link href=\"{item.mca_reference}\">{item.mca_reference}</link>", styles['small']))
        
        item_elements.append(Spacer(1, 16))
        item_elements.append(HRFlowable(width="100%", thickness=1, lineCap='round', color=colors.lightgrey))
        item_elements.append(Spacer(1, 8))
        
        return KeepTogether(item_elements)
    
    def _create_risk_matrix(self, compliance_items: List[ComplianceItem], styles: dict) -> List:
        """Create risk assessment matrix"""
        elements = []
        
        elements.append(PageBreak())
        elements.append(Paragraph("Risk Assessment Matrix", styles['h1']))
        elements.append(Spacer(1, 12))
        
        # Group items by risk level and importance
        risk_groups = {
            'High': [item for item in compliance_items if item.risk_rating == 'High'],
            'Medium': [item for item in compliance_items if item.risk_rating == 'Medium'],
            'Low': [item for item in compliance_items if item.risk_rating == 'Low']
        }
        
        # Create risk summary table
        risk_data = [['Risk Level', 'Count', 'Requirements', 'Action Priority']]
        
        for risk_level, items in risk_groups.items():
            if items:
                req_codes = ', '.join([item.code for item in items[:5]])  # Show first 5
                if len(items) > 5:
                    req_codes += f" (+{len(items)-5} more)"
                
                priority = "Immediate" if risk_level == "High" else "Planned" if risk_level == "Medium" else "Monitor"
                
                risk_data.append([
                    risk_level,
                    str(len(items)),
                    req_codes,
                    priority
                ])
        
        risk_table = Table(risk_data, colWidths=[1*inch, 0.8*inch, 3*inch, 1*inch])
        risk_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.colors['primary']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.colors['light_gray']])
        ]))
        
        elements.append(risk_table)
        elements.append(Spacer(1, 20))
        
        return elements
    
    def _create_action_plan(self, compliance_items: List[ComplianceItem], styles: dict) -> List:
        """Create prioritized action plan"""
        elements = []
        
        elements.append(Paragraph("Prioritized Action Plan", styles['h1']))
        elements.append(Spacer(1, 12))
        
        # Sort items by priority (Missing Critical first, then Incomplete Critical, etc.)
        priority_order = {
            ('Missing', 'Critical'): 1,
            ('Missing', 'High'): 2,
            ('Incomplete', 'Critical'): 3,
            ('Missing', 'Medium'): 4,
            ('Incomplete', 'High'): 5,
            ('Incomplete', 'Medium'): 6,
            ('Met', 'Critical'): 7,
            ('Met', 'High'): 8,
            ('Met', 'Medium'): 9
        }
        
        sorted_items = sorted(
            compliance_items,
            key=lambda x: priority_order.get((x.status, x.importance_level), 10)
        )
        
        # Create action plan table
        action_data = [['Priority', 'Requirement', 'Status', 'Timeline', 'Responsible Party', 'Key Actions']]
        
        priority = 1
        for item in sorted_items:
            if item.status in ['Missing', 'Incomplete']:  # Only show items needing action
                timeline = "Immediate" if item.importance_level == "Critical" else "30 days" if item.importance_level == "High" else "90 days"
                responsible = item.responsible_parties[0] if item.responsible_parties else "Management"
                
                key_actions = "; ".join(item.remediation_steps[:2])  # Show first 2 actions
                if len(key_actions) > 80:
                    key_actions = key_actions[:77] + "..."
                
                action_data.append([
                    str(priority),
                    f"{item.code}\n{item.title}",
                    item.status,
                    timeline,
                    responsible,
                    key_actions
                ])
                priority += 1
        
        action_table = Table(action_data, colWidths=[0.5*inch, 1.5*inch, 0.8*inch, 0.8*inch, 1*inch, 2.2*inch])
        action_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.colors['primary']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.colors['light_gray']]),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6)
        ]))
        
        elements.append(action_table)
        elements.append(Spacer(1, 20))
        
        return elements
    
    def _create_glossary_and_references(self, styles: dict) -> List:
        """Create glossary and references section"""
        elements = []
        
        elements.append(PageBreak())
        elements.append(Paragraph("Glossary & References", styles['h1']))
        elements.append(Spacer(1, 12))
        
        # Glossary
        elements.append(Paragraph("Regulatory Terms Glossary", styles['h2']))
        
        glossary_terms = {
            "AGM": "Annual General Meeting - Mandatory yearly meeting of shareholders",
            "AOC-4": "Annual Return of Financial Statements filing form",
            "MGT-7": "Annual Return form containing company details and shareholding",
            "DIR-3 KYC": "Director Know Your Customer verification form", 
            "MCA": "Ministry of Corporate Affairs - Government regulatory body",
            "DIN": "Director Identification Number - Unique ID for company directors",
            "ROC": "Registrar of Companies - Regional MCA office",
            "OPC": "One Person Company - Special category of private company"
        }
        
        for term, definition in glossary_terms.items():
            elements.append(Paragraph(f"<b>{term}:</b> {definition}", styles['normal']))
            elements.append(Spacer(1, 4))
        
        elements.append(Spacer(1, 16))
        
        # References
        elements.append(Paragraph("Key References & Resources", styles['h2']))
        
        references = [
            "Companies Act, 2013 - https://www.mca.gov.in/content/mca/global/en/acts-rules/acts.html",
            "MCA Forms and Filing - https://www.mca.gov.in/content/mca/global/en/data-and-reports/forms.html", 
            "Compliance Calendar - https://www.mca.gov.in/content/mca/global/en/home.html",
            "Director Database - https://www.mca.gov.in/content/mca/global/en/data-and-reports/director-data.html",
            "Company Search - https://www.mca.gov.in/content/mca/global/en/data-and-reports/company-data.html"
        ]
        
        for ref in references:
            elements.append(Paragraph(f"• {ref}", styles['small']))
            elements.append(Spacer(1, 3))
        
        elements.append(Spacer(1, 16))
        
        # FAQ Section
        elements.append(Paragraph("Frequently Asked Questions", styles['h2']))
        
        faqs = [
            ("What happens if we miss a filing deadline?", 
             "Late filing attracts additional fees and penalties. Continuous non-compliance can lead to prosecution and director disqualification."),
            ("How often should we review compliance status?", 
             "Quarterly reviews are recommended, with monthly monitoring for critical requirements like board meetings."),
            ("Who is responsible for ensuring compliance?", 
             "Board of Directors has ultimate responsibility, typically delegated to Company Secretary and management team."),
            ("What are the penalties for non-compliance?", 
             "Penalties vary by requirement - from ₹1,000 to ₹25 lakh depending on the violation and delay period.")
        ]
        
        for question, answer in faqs:
            elements.append(Paragraph(f"<b>Q: {question}</b>", styles['normal']))
            elements.append(Paragraph(f"A: {answer}", styles['normal']))
            elements.append(Spacer(1, 8))
        
        return elements


def create_enhanced_compliance_report(
    document_text: str,
    company_name: str,
    output_path: str,
    document_stats: dict = None
) -> bool:
    """Main function to create enhanced compliance report"""
    try:
        print("🚀 Starting enhanced compliance report generation...")
        
        # Initialize analyzer
        analyzer = EnhancedComplianceAnalyzer()
        
        # Perform RAG analysis
        compliance_items = analyzer.analyze_document_with_rag(document_text)
        
        # Calculate document stats if not provided
        if not document_stats:
            document_stats = {
                'length': len(document_text),
                'total_requirements': len(compliance_items),
                'evidence_count': sum(len(item.evidence) for item in compliance_items)
            }
        
        # Generate PDF
        pdf_generator = EnhancedPDFGenerator()
        pdf_generator.generate_comprehensive_report(
            compliance_items=compliance_items,
            company_name=company_name,
            document_stats=document_stats,
            output_path=output_path
        )
        
        print(f"✅ Enhanced compliance report generated successfully: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error generating enhanced compliance report: {e}")
        return False
