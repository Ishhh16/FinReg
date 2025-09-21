"""
Professional Enhanced Compliance Analyzer for Indian Companies Act 2013
Provides comprehensive, detailed compliance reports with professional formatting
"""

import os
import re
import json
import html
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from io import BytesIO
import tempfile
from dataclasses import dataclass, field
from enum import Enum

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
    
    # Limit length to prevent extremely long text
    if len(text) > 500:
        text = text[:497] + "..."
    
    return text


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


class ProfessionalEnhancedComplianceAnalyzer:
    """Professional compliance analyzer with comprehensive reporting capabilities"""
    
    def __init__(self):
        self.compliance_framework = self._load_comprehensive_framework()
        
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
    
    def analyze_document(self, text_content: str, company_name: str = "Company") -> Dict[str, Any]:
        """Perform comprehensive compliance analysis"""
        
        analysis_results = []
        text_lower = text_content.lower()
        
        # Define enhanced keyword patterns for each section
        enhanced_patterns = {
            "SECTION_134": {
                "primary": ["financial statement", "balance sheet", "profit and loss", "cash flow", "income statement", "statement of financial position"],
                "secondary": ["audited", "financial report", "accounts", "accounting standard", "schedule iii", "board approval"],
                "evidence_indicators": ["prepared", "adopted", "approved", "certified", "auditor", "notes to accounts"]
            },
            "SECTION_139": {
                "primary": ["auditor", "audit", "chartered accountant", "statutory audit"],
                "secondary": ["appointment", "rotation", "remuneration", "independence", "adt-1"],
                "evidence_indicators": ["appointed", "consent", "eligible", "qualified", "certified"]
            },
            "SECTION_92": {
                "primary": ["annual return", "mgt-7", "form mgt", "return filing"],
                "secondary": ["roc", "registrar", "shareholding", "particulars", "filing"],
                "evidence_indicators": ["filed", "submitted", "uploaded", "registered", "acknowledged"]
            },
            "SECTION_96": {
                "primary": ["annual general meeting", "agm", "shareholders meeting"],
                "secondary": ["notice", "quorum", "resolution", "minutes", "attendance"],
                "evidence_indicators": ["held", "conducted", "convened", "attended", "resolved"]
            },
            "SECTION_137": {
                "primary": ["aoc-4", "filing financial statements", "roc filing"],
                "secondary": ["financial statements filed", "board report", "auditor report", "adoption"],
                "evidence_indicators": ["filed", "submitted", "adopted", "attached", "uploaded"]
            },
            "SECTION_203": {
                "primary": ["key managerial personnel", "kmp", "managing director", "ceo", "cfo", "company secretary"],
                "secondary": ["whole-time", "appointment", "designation", "management"],
                "evidence_indicators": ["appointed", "designated", "acting", "resigned", "contract"]
            },
            "SECTION_149": {
                "primary": ["independent director", "board composition", "non-executive"],
                "secondary": ["independence", "declaration", "nomination", "board diversity"],
                "evidence_indicators": ["appointed", "independent", "declared", "confirmed", "evaluated"]
            },
            "SECTION_184": {
                "primary": ["disclosure of interest", "conflict of interest", "related party"],
                "secondary": ["director interest", "contracts", "arrangements", "transactions"],
                "evidence_indicators": ["disclosed", "declared", "register", "recorded", "abstained"]
            }
        }
        
        # Analyze each compliance requirement
        for section_code, item in self.compliance_framework.items():
            patterns = enhanced_patterns.get(section_code, {"primary": [], "secondary": [], "evidence_indicators": []})
            
            # Calculate compliance score and find evidence
            primary_matches = sum(1 for pattern in patterns["primary"] if pattern in text_lower)
            secondary_matches = sum(1 for pattern in patterns["secondary"] if pattern in text_lower)
            evidence_matches = sum(1 for pattern in patterns["evidence_indicators"] if pattern in text_lower)
            
            total_primary = len(patterns["primary"])
            total_secondary = len(patterns["secondary"]) 
            total_evidence = len(patterns["evidence_indicators"])
            
            # Calculate weighted score
            primary_score = (primary_matches / max(total_primary, 1)) * 0.5
            secondary_score = (secondary_matches / max(total_secondary, 1)) * 0.3  
            evidence_score = (evidence_matches / max(total_evidence, 1)) * 0.2
            
            final_score = (primary_score + secondary_score + evidence_score) * 100
            
            # Extract evidence
            evidence_found = self._extract_detailed_evidence(text_content, patterns, section_code)
            
            # Determine compliance status and risk level
            compliance_status, risk_level = self._determine_compliance_status(final_score, len(evidence_found))
            
            # Generate detailed rationale
            rationale = self._generate_compliance_rationale(
                section_code, final_score, primary_matches, secondary_matches, 
                evidence_matches, len(evidence_found)
            )
            
            # Generate gap analysis
            gap_analysis = self._generate_gap_analysis(section_code, compliance_status, evidence_found)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(section_code, compliance_status, risk_level)
            
            # Update the item with analysis results
            item.compliance_score = round(final_score, 2)
            item.compliance_status = compliance_status
            item.risk_level = risk_level
            item.evidence_found = evidence_found
            item.compliance_rationale = rationale
            item.gap_analysis = gap_analysis
            item.recommendations = recommendations
            
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
        for item in critical_items[:3]:  # Top 3 critical items
            summary_parts.append(f"• {item.section_title}: {item.gap_analysis[:100]}...")
        
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
    
    # Perform analysis
    analyzer = ProfessionalEnhancedComplianceAnalyzer()
    analysis_data = analyzer.analyze_document(text_content, company_name)
    
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
    story.append(Paragraph("Executive Summary", section_style))
    story.append(Paragraph(clean_text_for_pdf(analysis_data['executive_summary']), styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Overall Metrics Dashboard
    story.append(Paragraph("Compliance Dashboard", subsection_style))
    
    metrics = analysis_data['overall_metrics']
    
    # Overall Score Card
    score_color = HexColor('#38a169') if metrics['overall_compliance_score'] >= 80 else \
                  HexColor('#d69e2e') if metrics['overall_compliance_score'] >= 60 else \
                  HexColor('#dd6b20') if metrics['overall_compliance_score'] >= 40 else \
                  HexColor('#e53e3e')
    
    score_data = [
        ["OVERALL COMPLIANCE SCORE", f"{metrics['overall_compliance_score']}%"]
    ]
    
    score_table = Table(score_data, colWidths=[8*cm, 4*cm])
    score_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), score_color),
        ('TEXTCOLOR', (0, 0), (-1, -1), white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 16),
        ('TOPPADDING', (0, 0), (-1, -1), 15),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 15)
    ]))
    
    story.append(score_table)
    story.append(Spacer(1, 15))
    
    # Compliance Distribution
    compliance_data = [
        ["Status", "Count", "Percentage", "Description"],
        ["Fully Compliant", str(metrics['compliance_distribution']['fully_compliant']), 
         f"{metrics['compliance_percentage']['fully_compliant']}%", "Meeting all requirements"],
        ["Partially Compliant", str(metrics['compliance_distribution']['partially_compliant']), 
         f"{metrics['compliance_percentage']['partially_compliant']}%", "Some gaps identified"],
        ["Non-Compliant", str(metrics['compliance_distribution']['non_compliant']), 
         f"{metrics['compliance_percentage']['non_compliant']}%", "Significant deficiencies"]
    ]
    
    compliance_table = Table(compliance_data, colWidths=[4*cm, 2*cm, 2*cm, 6*cm])
    compliance_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#2c5282')),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
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
        ["Risk Level", "Count", "Priority", "Action Required"],
        ["Critical", str(metrics['risk_distribution']['critical']), "Immediate", "Urgent remediation"],
        ["High", str(metrics['risk_distribution']['high']), "Within 30 days", "Prompt action needed"],
        ["Medium", str(metrics['risk_distribution']['medium']), "Within 60 days", "Monitor and improve"],
        ["Low", str(metrics['risk_distribution']['low']), "Ongoing", "Maintain standards"]
    ]
    
    risk_table = Table(risk_data, colWidths=[3*cm, 2*cm, 3*cm, 6*cm])
    risk_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#744210')),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
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
    
    # Detailed Section Analysis
    story.append(Paragraph("Detailed Compliance Analysis", section_style))
    
    for item in analysis_data['detailed_analysis']:
        # Section header with status indicator
        status_color = status_colors[item.compliance_status]
        risk_color = risk_colors[item.risk_level]
        
        section_header = f"{item.section_code}: {item.section_title}"
        story.append(Paragraph(section_header, compliance_item_style))
        
        # Status and score table with proper text wrapping
        status_data = [
            ["Compliance Status", item.compliance_status.value, "Risk Level", item.risk_level.value],
            ["Compliance Score", f"{item.compliance_score}%", "Legal Citation", clean_text_for_pdf(item.legal_citation[:60] + "...")]
        ]
        
        # Wrap text in Paragraphs for proper handling
        wrapped_data = []
        for row in status_data:
            wrapped_row = []
            for cell in row:
                wrapped_row.append(Paragraph(str(cell), styles['Normal']))
            wrapped_data.append(wrapped_row)
        
        status_table = Table(wrapped_data, colWidths=[3*cm, 4*cm, 3*cm, 4*cm])
        status_table.setStyle(TableStyle([
            ('BACKGROUND', (1, 0), (1, 0), status_color),
            ('BACKGROUND', (3, 0), (3, 0), risk_color),
            ('TEXTCOLOR', (1, 0), (1, 0), white),
            ('TEXTCOLOR', (3, 0), (3, 0), white),
            ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (3, 0), (3, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 1, HexColor('#e2e8f0')),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10)
        ]))
        
        story.append(status_table)
        story.append(Spacer(1, 10))
        
        # Requirement Description
        story.append(Paragraph("<b>Requirement:</b>", styles['Normal']))
        story.append(Paragraph(clean_text_for_pdf(item.requirement_description), styles['Normal']))
        story.append(Spacer(1, 8))
        
        # Compliance Rationale
        story.append(Paragraph("<b>Analysis Rationale:</b>", styles['Normal']))
        story.append(Paragraph(clean_text_for_pdf(item.compliance_rationale), styles['Normal']))
        story.append(Spacer(1, 8))
        
        # Evidence Found
        if item.evidence_found:
            story.append(Paragraph("<b>Supporting Evidence:</b>", styles['Normal']))
            for i, evidence in enumerate(item.evidence_found[:3], 1):
                # Use pre-cleaned text snippet
                evidence_text = f"{i}. {evidence.text_snippet} (Confidence: {evidence.confidence_score:.1%})"
                story.append(Paragraph(evidence_text, styles['Normal']))
            story.append(Spacer(1, 8))
        
        # Gap Analysis
        if item.gap_analysis:
            story.append(Paragraph("<b>Gap Analysis:</b>", styles['Normal']))
            story.append(Paragraph(clean_text_for_pdf(item.gap_analysis), styles['Normal']))
            story.append(Spacer(1, 8))
        
        # Recommendations with improved formatting
        if item.recommendations:
            story.append(Paragraph("<b>Recommendations:</b>", styles['Normal']))
            
            rec_data = [["Priority", "Action Required", "Responsible Party", "Timeline"]]
            for rec in item.recommendations[:3]:
                action_text = clean_text_for_pdf(rec.action_required)
                if len(action_text) > 120:
                    action_text = action_text[:117] + "..."
                rec_data.append([
                    clean_text_for_pdf(rec.priority), 
                    action_text, 
                    clean_text_for_pdf(rec.responsible_party), 
                    clean_text_for_pdf(rec.timeline)
                ])
            
            # Wrap text in Paragraphs for better table handling
            wrapped_rec_data = []
            for i, row in enumerate(rec_data):
                wrapped_row = []
                for j, cell in enumerate(row):
                    if i == 0:  # Header row
                        wrapped_row.append(Paragraph(f"<b>{cell}</b>", styles['Normal']))
                    else:
                        # Create a smaller paragraph style for table cells
                        cell_style = ParagraphStyle('TableCell', parent=styles['Normal'], fontSize=8, leading=10)
                        wrapped_row.append(Paragraph(str(cell), cell_style))
                wrapped_rec_data.append(wrapped_row)
            
            rec_table = Table(wrapped_rec_data, colWidths=[2.5*cm, 7*cm, 3.5*cm, 3*cm])
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
            story.append(Paragraph("<b>Required Documentation:</b>", styles['Normal']))
            doc_list = "• " + "\n• ".join(item.documentation_required[:5])
            story.append(Paragraph(doc_list, styles['Normal']))
        
        story.append(Spacer(1, 20))
        
        # Add page break after every 2 sections to maintain readability
        if analysis_data['detailed_analysis'].index(item) % 2 == 1:
            story.append(PageBreak())
    
    # Risk Assessment Summary
    story.append(Paragraph("Risk Assessment & Mitigation Plan", section_style))
    
    if 'mitigation_priorities' in analysis_data['risk_assessment']:
        priority_data = [["Rank", "Section", "Risk Level", "Immediate Action", "Timeline", "Responsible Party"]]
        
        for priority in analysis_data['risk_assessment']['mitigation_priorities']:
            action_text = clean_text_for_pdf(priority['immediate_action'])
            if len(action_text) > 80:
                action_text = action_text[:77] + "..."
            priority_data.append([
                str(priority['priority_rank']),
                priority['section'],
                priority['risk_level'],
                action_text,
                priority['timeline'],
                clean_text_for_pdf(priority['responsible_party'])
            ])
        
        # Wrap priority table text in Paragraphs
        wrapped_priority_data = []
        for i, row in enumerate(priority_data):
            wrapped_row = []
            for cell in row:
                if i == 0:  # Header row
                    wrapped_row.append(Paragraph(f"<b>{cell}</b>", styles['Normal']))
                else:
                    cell_style = ParagraphStyle('PriorityCell', parent=styles['Normal'], fontSize=8, leading=9)
                    wrapped_row.append(Paragraph(str(cell), cell_style))
            wrapped_priority_data.append(wrapped_row)
        
        priority_table = Table(wrapped_priority_data, colWidths=[1.5*cm, 2.5*cm, 2*cm, 6*cm, 2.5*cm, 3.5*cm])
        priority_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#742a2a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
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
