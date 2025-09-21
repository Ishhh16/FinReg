"""
Simplified Enhanced Compliance Analyzer for Indian Companies Act 2013
Provides detailed compliance reports without vector database dependencies
"""

import os
import re
import json
from datetime import datetime
from typing import List, Dict, Any, Tuple
from io import BytesIO
import tempfile

# PDF generation imports
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, black, red, green, orange, blue
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus.tableofcontents import TableOfContents


class SimpleComplianceItem:
    """Represents a compliance requirement with detailed analysis"""
    def __init__(self, section: str, requirement: str, description: str, penalty: str = ""):
        self.section = section
        self.requirement = requirement
        self.description = description
        self.penalty = penalty
        self.status = "NOT_COMPLIANT"  # NOT_COMPLIANT, PARTIAL, COMPLIANT
        self.confidence_score = 0.0
        self.reasoning = ""
        self.remediation_steps = []
        self.risk_level = "HIGH"  # LOW, MEDIUM, HIGH, CRITICAL
        self.found_evidence = []
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "section": self.section,
            "requirement": self.requirement,
            "description": self.description,
            "penalty": self.penalty,
            "status": self.status,
            "confidence_score": self.confidence_score,
            "reasoning": self.reasoning,
            "remediation_steps": self.remediation_steps,
            "risk_level": self.risk_level,
            "found_evidence": self.found_evidence
        }


class SimpleEnhancedComplianceAnalyzer:
    """Enhanced compliance analyzer with detailed reporting capabilities"""
    
    def __init__(self):
        self.compliance_requirements = self._load_compliance_requirements()
        
    def _load_compliance_requirements(self) -> List[SimpleComplianceItem]:
        """Load comprehensive compliance requirements for Indian Companies Act 2013"""
        requirements = [
            SimpleComplianceItem(
                "Section 134",
                "Annual Financial Statements",
                "Every company shall prepare financial statements including Balance Sheet, Profit & Loss Account, and Cash Flow Statement",
                "Fine up to ₹5,00,000 and imprisonment up to 3 years"
            ),
            SimpleComplianceItem(
                "Section 139",
                "Appointment of Auditors",
                "Every company shall appoint a qualified auditor to audit its financial statements",
                "Fine from ₹25,000 to ₹5,00,000"
            ),
            SimpleComplianceItem(
                "Section 143",
                "Powers and Duties of Auditors",
                "Auditors shall report on company's financial statements and compliance with provisions",
                "Fine up to ₹25,00,000 and imprisonment up to 1 year"
            ),
            SimpleComplianceItem(
                "Section 92",
                "Annual Return Filing",
                "Every company shall file annual return with ROC within 60 days of AGM",
                "Fine from ₹5,000 per day to ₹50,000 per day"
            ),
            SimpleComplianceItem(
                "Section 96",
                "Annual General Meeting",
                "Every company shall hold AGM within 6 months from the end of financial year",
                "Fine from ₹25,000 to ₹5,00,000"
            ),
            SimpleComplianceItem(
                "Section 137",
                "Copy of Financial Statements to be Filed",
                "Financial statements shall be filed with ROC within 30 days of AGM",
                "Fine from ₹5,000 per day to ₹50,000 per day"
            ),
            SimpleComplianceItem(
                "Section 203",
                "Appointment of Key Managerial Personnel",
                "Every company shall have whole-time Key Managerial Personnel",
                "Fine from ₹50,000 to ₹5,00,000"
            ),
            SimpleComplianceItem(
                "Section 179",
                "Powers of Board",
                "Board shall exercise powers in accordance with company's articles and law",
                "Fine up to ₹25,00,000"
            ),
            SimpleComplianceItem(
                "Section 184",
                "Disclosure of Interest by Directors",
                "Directors shall disclose their interests in contracts and arrangements",
                "Fine from ₹50,000 to ₹5,00,000"
            ),
            SimpleComplianceItem(
                "Section 149",
                "Independent Directors",
                "Listed companies shall have at least 1/3rd independent directors",
                "Fine from ₹1,00,000 to ₹5,00,000"
            )
        ]
        
        return requirements
        
    def analyze_document(self, text_content: str) -> Dict[str, Any]:
        """Analyze document content for compliance requirements"""
        
        analysis_results = []
        
        for req in self.compliance_requirements:
            # Simple keyword-based analysis
            compliance_analysis = self._analyze_requirement(req, text_content)
            analysis_results.append(compliance_analysis)
            
        # Calculate overall compliance score
        total_items = len(analysis_results)
        compliant_items = sum(1 for item in analysis_results if item.status == "COMPLIANT")
        partial_items = sum(1 for item in analysis_results if item.status == "PARTIAL")
        
        overall_score = ((compliant_items * 1.0) + (partial_items * 0.5)) / total_items * 100
        
        # Categorize risks
        risk_summary = {
            "CRITICAL": sum(1 for item in analysis_results if item.risk_level == "CRITICAL"),
            "HIGH": sum(1 for item in analysis_results if item.risk_level == "HIGH"),
            "MEDIUM": sum(1 for item in analysis_results if item.risk_level == "MEDIUM"),
            "LOW": sum(1 for item in analysis_results if item.risk_level == "LOW")
        }
        
        return {
            "overall_compliance_score": round(overall_score, 2),
            "total_requirements": total_items,
            "compliant": compliant_items,
            "partial_compliant": partial_items,
            "non_compliant": total_items - compliant_items - partial_items,
            "risk_summary": risk_summary,
            "detailed_analysis": [item.to_dict() for item in analysis_results],
            "analysis_timestamp": datetime.now().isoformat()
        }
    
    def _analyze_requirement(self, requirement: SimpleComplianceItem, text: str) -> SimpleComplianceItem:
        """Analyze a specific compliance requirement against document text"""
        
        # Keywords for different requirements
        keyword_mapping = {
            "Section 134": ["financial statement", "balance sheet", "profit", "loss", "cash flow"],
            "Section 139": ["auditor", "audit", "appointed", "qualified"],
            "Section 143": ["auditor report", "audit report", "compliance", "opinion"],
            "Section 92": ["annual return", "ROC", "filing", "AGM"],
            "Section 96": ["annual general meeting", "AGM", "shareholders"],
            "Section 137": ["financial statements filed", "ROC filing"],
            "Section 203": ["key managerial", "KMP", "managing director", "CEO", "CFO"],
            "Section 179": ["board resolution", "board powers", "board meeting"],
            "Section 184": ["director interest", "related party", "disclosure"],
            "Section 149": ["independent director", "board composition"]
        }
        
        text_lower = text.lower()
        section_keywords = keyword_mapping.get(requirement.section, [])
        
        # Count keyword matches
        matches = sum(1 for keyword in section_keywords if keyword in text_lower)
        total_keywords = len(section_keywords)
        
        if total_keywords > 0:
            match_ratio = matches / total_keywords
        else:
            match_ratio = 0
            
        # Determine compliance status based on matches
        if match_ratio >= 0.7:
            requirement.status = "COMPLIANT"
            requirement.confidence_score = match_ratio
            requirement.risk_level = "LOW"
            requirement.reasoning = f"Strong evidence found for {requirement.section} compliance with {matches}/{total_keywords} key indicators present."
        elif match_ratio >= 0.4:
            requirement.status = "PARTIAL"
            requirement.confidence_score = match_ratio
            requirement.risk_level = "MEDIUM"
            requirement.reasoning = f"Partial compliance detected for {requirement.section} with {matches}/{total_keywords} indicators present."
        else:
            requirement.status = "NOT_COMPLIANT"
            requirement.confidence_score = match_ratio
            requirement.risk_level = "HIGH" if match_ratio < 0.2 else "MEDIUM"
            requirement.reasoning = f"Limited evidence found for {requirement.section} compliance. Only {matches}/{total_keywords} indicators detected."
            
        # Generate remediation steps
        requirement.remediation_steps = self._generate_remediation_steps(requirement)
        
        # Extract evidence snippets
        requirement.found_evidence = self._extract_evidence(text, section_keywords)
        
        return requirement
    
    def _generate_remediation_steps(self, requirement: SimpleComplianceItem) -> List[str]:
        """Generate remediation steps based on compliance requirement"""
        
        remediation_map = {
            "Section 134": [
                "Prepare comprehensive financial statements including Balance Sheet, Profit & Loss, and Cash Flow",
                "Ensure compliance with Indian Accounting Standards (Ind AS)",
                "Have financial statements reviewed by qualified accountant",
                "Include notes to financial statements with required disclosures"
            ],
            "Section 139": [
                "Identify and appoint qualified chartered accountant as auditor",
                "Ensure auditor independence and no disqualifications",
                "File auditor appointment form with ROC",
                "Obtain written consent from auditor before appointment"
            ],
            "Section 143": [
                "Provide auditor with complete access to books and records",
                "Ensure auditor reports on financial statements and compliance",
                "Address any audit qualifications or concerns",
                "File auditor's report with annual return"
            ],
            "Section 92": [
                "Prepare annual return in prescribed format (MGT-7)",
                "File annual return within 60 days of AGM",
                "Ensure all required information is accurately included",
                "Pay applicable fees and charges"
            ],
            "Section 96": [
                "Schedule AGM within 6 months of financial year end",
                "Send proper notice to all shareholders",
                "Prepare agenda and required documents",
                "Conduct AGM with required quorum"
            ],
            "Section 137": [
                "File financial statements with ROC within 30 days of AGM",
                "Include auditor's report and board report",
                "Ensure proper digital signatures and certifications",
                "Pay applicable filing fees"
            ],
            "Section 203": [
                "Appoint required Key Managerial Personnel (MD/CEO, CFO, CS)",
                "File appointment forms with ROC",
                "Ensure KMPs meet qualification requirements",
                "Maintain proper records of appointments"
            ],
            "Section 179": [
                "Conduct regular board meetings with proper notice",
                "Ensure board exercises powers as per articles of association",
                "Maintain minutes of board meetings",
                "Delegate powers appropriately to committees"
            ],
            "Section 184": [
                "Implement system for directors to disclose interests",
                "Maintain register of interests disclosed by directors",
                "Ensure related party transactions are properly approved",
                "File required forms for material related party transactions"
            ],
            "Section 149": [
                "Identify and appoint required independent directors",
                "Ensure independent directors meet independence criteria",
                "File appointment forms and declarations",
                "Conduct proper evaluation of independent directors"
            ]
        }
        
        return remediation_map.get(requirement.section, [
            "Review compliance requirement in detail",
            "Consult with legal/compliance expert",
            "Develop implementation plan",
            "Monitor ongoing compliance"
        ])
    
    def _extract_evidence(self, text: str, keywords: List[str]) -> List[str]:
        """Extract relevant text snippets as evidence"""
        evidence = []
        text_lower = text.lower()
        sentences = text.split('.')
        
        for sentence in sentences[:10]:  # Limit to first 10 sentences
            sentence_lower = sentence.lower().strip()
            if any(keyword in sentence_lower for keyword in keywords):
                if len(sentence.strip()) > 20:  # Only meaningful sentences
                    evidence.append(sentence.strip()[:200] + "..." if len(sentence.strip()) > 200 else sentence.strip())
                    
        return evidence[:3]  # Return top 3 evidence snippets


def create_simple_enhanced_compliance_report(text_content: str, company_name: str = "Company") -> bytes:
    """Create enhanced compliance report PDF"""
    
    analyzer = SimpleEnhancedComplianceAnalyzer()
    analysis_results = analyzer.analyze_document(text_content)
    
    # Create PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18
    )
    
    # Build story
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=HexColor('#1f4e79')
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12,
        textColor=HexColor('#2f5f8f')
    )
    
    # Title
    story.append(Paragraph(f"Enhanced Compliance Report - {company_name}", title_style))
    story.append(Spacer(1, 20))
    
    # Executive Summary
    story.append(Paragraph("Executive Summary", heading_style))
    
    summary_data = [
        ["Overall Compliance Score", f"{analysis_results['overall_compliance_score']}%"],
        ["Total Requirements Analyzed", analysis_results['total_requirements']],
        ["Fully Compliant", analysis_results['compliant']],
        ["Partially Compliant", analysis_results['partial_compliant']],
        ["Non-Compliant", analysis_results['non_compliant']],
    ]
    
    summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#4f81bd')),
        ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), HexColor('#f2f2f2')),
        ('GRID', (0, 0), (-1, -1), 1, HexColor('#000000'))
    ]))
    
    story.append(summary_table)
    story.append(Spacer(1, 30))
    
    # Risk Analysis
    story.append(Paragraph("Risk Analysis", heading_style))
    
    risk_data = [["Risk Level", "Count"]]
    for level, count in analysis_results['risk_summary'].items():
        risk_data.append([level, str(count)])
    
    risk_table = Table(risk_data, colWidths=[2*inch, 1*inch])
    risk_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#d94441')),
        ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), HexColor('#f9f9f9')),
        ('GRID', (0, 0), (-1, -1), 1, HexColor('#000000'))
    ]))
    
    story.append(risk_table)
    story.append(PageBreak())
    
    # Detailed Analysis
    story.append(Paragraph("Detailed Compliance Analysis", heading_style))
    story.append(Spacer(1, 20))
    
    for item in analysis_results['detailed_analysis']:
        # Compliance item header
        status_color = {
            "COMPLIANT": HexColor('#4f7942'),
            "PARTIAL": HexColor('#bf8f00'),
            "NOT_COMPLIANT": HexColor('#c5504b')
        }.get(item['status'], black)
        
        item_style = ParagraphStyle(
            'ItemHeader',
            parent=styles['Heading3'],
            fontSize=12,
            textColor=status_color,
            spaceAfter=6
        )
        
        story.append(Paragraph(f"{item['section']}: {item['requirement']}", item_style))
        story.append(Paragraph(f"<b>Status:</b> {item['status']} (Confidence: {item['confidence_score']:.2f})", styles['Normal']))
        story.append(Paragraph(f"<b>Risk Level:</b> {item['risk_level']}", styles['Normal']))
        story.append(Paragraph(f"<b>Analysis:</b> {item['reasoning']}", styles['Normal']))
        
        if item['remediation_steps']:
            story.append(Paragraph("<b>Recommended Actions:</b>", styles['Normal']))
            for step in item['remediation_steps'][:3]:  # Limit to 3 steps
                story.append(Paragraph(f"• {step}", styles['Normal']))
        
        story.append(Spacer(1, 15))
    
    # Footer
    story.append(Spacer(1, 30))
    story.append(Paragraph(
        f"<i>Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} by Enhanced Compliance Analyzer</i>",
        styles['Normal']
    ))
    
    # Build PDF
    doc.build(story)
    
    buffer.seek(0)
    return buffer.getvalue()
