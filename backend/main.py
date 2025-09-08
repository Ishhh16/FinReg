import os
import tempfile
import textwrap
import re
import numpy as np 
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
from collections import Counter

from fastapi import FastAPI, File, Form, UploadFile, Depends
from fastapi.responses import FileResponse, JSONResponse
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from sqlalchemy.orm import Session

import io
from typing import Any
from fastapi import Query
# Optional PDF parsers
try:
    import PyPDF2
    HAS_PYPDF2 = True
except Exception:
    HAS_PYPDF2 = False

try:
    from pdfminer.high_level import extract_text as pdfminer_extract_text
    HAS_PDFMINER = True
except Exception:
    HAS_PDFMINER = False


# Basic document processing
try:
    from unstructured.partition.auto import partition
    HAS_UNSTRUCTURED = True
except ImportError:
    print("Warning: unstructured not available")
    HAS_UNSTRUCTURED = False

# Import models and database functions
try:
    from . import models
    from .database import engine, get_db
    from .ingestion import get_enhanced_vector_store, EnhancedMockVectorStore
except ImportError:
    import models
    from database import engine, get_db
    from ingestion import get_enhanced_vector_store, EnhancedMockVectorStore

# Initialize DB tables
try:
    models.Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")
except Exception as e:
    print(f"⚠️ Database initialization warning: {e}")

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
    citation_id: str = ""  # Added for enhanced specificity
    source_url: str = ""   # Added for traceability

class EnhancedComplianceAnalyzer:
    """Enhanced compliance analyzer with improved semantic matching and regulatory specificity"""
    
    def __init__(self):
        try:
            # Use the enhanced vector store from ingestion.py
            self.vector_store = get_enhanced_vector_store()
            # Get enhanced mappings if available
            if hasattr(self.vector_store, 'enhanced_mappings'):
                self.regulatory_mappings = self.vector_store.enhanced_mappings
                print("✅ Loaded enhanced regulatory mappings from vector store")
            else:
                self.regulatory_mappings = self._get_fallback_mappings()
                print("⚠️ Using fallback regulatory mappings")
        except Exception as e:
            print(f"Warning: Could not initialize enhanced vector store: {e}")
            self.vector_store = None
            self.regulatory_mappings = self._get_fallback_mappings()
    
    def _get_fallback_mappings(self):
        """Fallback regulatory mappings with enhanced structure"""
        return {
            "SEC_INTERNAL_CONTROLS": {
                "title": "SEC Regulations - Internal Controls (SOX 404)",
                "sections": {
                    "sox_404a_management_assessment": {
                        "citation": "Sarbanes-Oxley Act, Section 404(a)",
                        "text": "Management must assess and report on internal control effectiveness annually per SOX Section 404.",
                        "full_regulation_text": "Management must document, test, and evaluate the design and operating effectiveness of internal controls over financial reporting annually.",
                        "source_url": "https://www.sec.gov/about/laws/soa2002.pdf",
                        "intent_patterns": [
                            "internal control", "control effectiveness", "SOX", "sarbanes oxley",
                            "management assessment", "control framework", "financial reporting controls"
                        ],
                        "compliance_indicators": [
                            r"internal.*control", r"control.*effectiveness", r"management.*assess",
                            r"sox.*compliance", r"control.*framework", r"financial.*reporting.*control"
                        ]
                    }
                }
            },
            "FDIC_AML_PROGRAM": {
                "title": "FDIC Banking Regulations - Anti-Money Laundering",
                "sections": {
                    "cfr_353_aml_program": {
                        "citation": "12 CFR Part 353.3",
                        "text": "Anti-money laundering programs must include customer identification, monitoring, and suspicious activity reporting.",
                        "full_regulation_text": "Each FDIC-supervised institution shall develop and implement a written anti-money laundering program with system of internal controls, independent testing, designated compliance officer, training, and customer identification procedures.",
                        "source_url": "https://www.ecfr.gov/current/title-12/chapter-III/subchapter-B/part-353",
                        "intent_patterns": [
                            "anti-money laundering", "AML", "suspicious activity", "money laundering",
                            "customer identification", "transaction monitoring", "BSA compliance"
                        ],
                        "compliance_indicators": [
                            r"anti.money.laundering", r"aml.*program", r"suspicious.*activity",
                            r"transaction.*monitor", r"customer.*identification", r"money.*laundering"
                        ]
                    }
                }
            },
            "FDIC_BROKERED_DEPOSITS": {
                "title": "FDIC Banking Regulations - Brokered Deposits",
                "sections": {
                    "cfr_326_brokered_deposits": {
                        "citation": "12 CFR Part 326.8",
                        "text": "Restrictions on brokered deposits based on capital adequacy levels and rate limitations.",
                        "full_regulation_text": "Depository institutions that are not well capitalized may not accept brokered deposits without FDIC waiver. Adequately capitalized institutions may accept brokered deposits only if paying no more than 120 basis points above benchmark rates.",
                        "source_url": "https://www.ecfr.gov/current/title-12/chapter-III/subchapter-B/part-326",
                        "intent_patterns": [
                            "brokered deposit", "deposit broker", "capital adequacy", "well capitalized",
                            "rate restrictions", "basis points", "benchmark rates"
                        ],
                        "compliance_indicators": [
                            r"brokered.*deposit", r"deposit.*broker", r"capital.*adequa",
                            r"well.*capitali", r"rate.*restrict", r"basis.*point"
                        ]
                    }
                }
            },
            "CFPB_CONSUMER_PROTECTION": {
                "title": "CFPB Consumer Protection Requirements",
                "sections": {
                    "cfpa_1036_udaap": {
                        "citation": "Consumer Financial Protection Act, Section 1036(a)",
                        "text": "Prohibition of unfair, deceptive, or abusive acts or practices in consumer financial products and services.",
                        "full_regulation_text": "The Bureau may take action to prevent covered persons from engaging in unfair, deceptive, or abusive acts or practices in connection with consumer financial products or services.",
                        "source_url": "https://www.ecfr.gov/current/title-12/chapter-X/part-1005",
                        "intent_patterns": [
                            "unfair practice", "deceptive practice", "abusive practice", "UDAAP",
                            "consumer protection", "consumer financial", "covered person"
                        ],
                        "compliance_indicators": [
                            r"unfair.*practice", r"deceptive.*practice", r"abusive.*practice",
                            r"consumer.*protect", r"consumer.*financial", r"udaap"
                        ]
                    }
                }
            }
        }
    
    def _calculate_enhanced_confidence(self, policy_content: str, regulation_data: dict, reg_text: str) -> Tuple[float, str]:
        """Enhanced confidence calculation with regulatory citation specificity"""
        policy_lower = policy_content.lower()
        reasoning_parts = []
        
        # 1. Citation-Specific Pattern Matching (35% weight)
        citation = regulation_data.get("citation", "")
        citation_score = self._calculate_citation_relevance(policy_lower, citation)
        reasoning_parts.append(f"Citation relevance: {citation_score:.2f}")
        
        # 2. Intent Pattern Matching (30% weight)
        intent_patterns = regulation_data.get("intent_patterns", [])
        intent_matches = sum(1 for pattern in intent_patterns if pattern.lower() in policy_lower)
        intent_score = min(intent_matches / max(len(intent_patterns), 1), 1.0)
        reasoning_parts.append(f"Intent patterns: {intent_matches}/{len(intent_patterns)} matched")
        
        # 3. Compliance Indicator Regex Matching (25% weight)
        compliance_indicators = regulation_data.get("compliance_indicators", [])
        indicator_matches = 0
        for indicator in compliance_indicators:
            if re.search(indicator, policy_lower):
                indicator_matches += 1
        indicator_score = min(indicator_matches / max(len(compliance_indicators), 1), 1.0)
        reasoning_parts.append(f"Compliance indicators: {indicator_matches}/{len(compliance_indicators)} found")
        
        # 4. Semantic Overlap with Full Regulation Text (10% weight)
        full_text = regulation_data.get("full_regulation_text", reg_text)
        semantic_score = self._calculate_semantic_similarity(policy_content, full_text)
        reasoning_parts.append(f"Semantic similarity: {semantic_score:.2f}")
        
        # Weighted combination with enhanced citation focus
        final_score = (
            citation_score * 0.35 + 
            intent_score * 0.30 + 
            indicator_score * 0.25 + 
            semantic_score * 0.10
        )
        
        reasoning = "; ".join(reasoning_parts)
        return final_score, reasoning
    
    def _calculate_citation_relevance(self, policy_text: str, citation: str) -> float:
        """Calculate relevance based on specific citation elements"""
        if not citation:
            return 0.0
        
        citation_lower = citation.lower()
        policy_lower = policy_text.lower()
        
        # Extract key citation components
        citation_elements = []
        
        # SOX/Sarbanes-Oxley patterns
        if "sarbanes" in citation_lower or "sox" in citation_lower:
            citation_elements.extend(["sarbanes", "oxley", "sox", "404", "internal control"])
        
        # CFR patterns
        cfr_match = re.search(r'(\d+)\s+cfr\s+(?:part\s+)?(\d+)', citation_lower)
        if cfr_match:
            citation_elements.extend([f"{cfr_match.group(1)} cfr", f"part {cfr_match.group(2)}"])
        
        # Act-specific patterns
        if "consumer financial protection" in citation_lower:
            citation_elements.extend(["consumer", "financial", "protection", "cfpb"])
        
        # Calculate match score
        matches = sum(1 for element in citation_elements if element in policy_lower)
        return min(matches / max(len(citation_elements), 1), 1.0) if citation_elements else 0.0
    
    def _calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity using word overlap and context"""
        # Tokenize and clean
        words1 = set(re.findall(r'\b\w{3,}\b', text1.lower()))
        words2 = set(re.findall(r'\b\w{3,}\b', text2.lower()))
        
        # Remove common stopwords
        stopwords = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 
            'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before', 
            'after', 'above', 'below', 'out', 'off', 'over', 'under', 'again', 
            'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why', 
            'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 
            'some', 'such', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 
            'can', 'will', 'just', 'should', 'now', 'must', 'shall'
        }
        
        words1 = words1 - stopwords
        words2 = words2 - stopwords
        
        if not words1 or not words2:
            return 0.0
        
        # Calculate Jaccard similarity
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union) if union else 0.0
    
    def segment_document(self, document_content: str) -> List[PolicySection]:
        """Improved document segmentation with better title extraction"""
        sections = []
        
        # Enhanced section patterns
        section_patterns = [
            r'\n\s*(\d+\.(?:\d+\.)*)\s*([A-Z][^.\n]*)',  # Numbered sections with titles
            r'\n\s*([A-Z][A-Z\s]{5,}?):',  # ALL CAPS headers with colon
            r'\n\s*(#{1,3})\s+([^\n]+)',  # Markdown headers
            r'\n\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*\n',  # Title Case standalone
            r'\n\s*([A-Z][^.\n]{10,100})\s*\n(?=[A-Z])',  # Potential section headers
        ]
        
        # Try to find structured sections
        best_split = None
        max_sections = 0
        
        for pattern in section_patterns:
            matches = list(re.finditer(pattern, document_content))
            if len(matches) > max_sections:
                max_sections = len(matches)
                best_split = matches
        
        if best_split and len(best_split) > 1:
            # Use the best structured split
            for i, match in enumerate(best_split):
                start = match.start()
                end = best_split[i + 1].start() if i + 1 < len(best_split) else len(document_content)
                
                content = document_content[start:end].strip()
                title = match.group(2) if match.lastindex >= 2 else f"Section {i + 1}"
                
                if len(content) > 100:  # Minimum section length
                    sections.append(PolicySection(
                        content=content,
                        section_number=i + 1,
                        title=title.strip()
                    ))
        else:
            # Fallback: split by paragraphs and logical breaks
            paragraphs = [p.strip() for p in re.split(r'\n\s*\n', document_content) if p.strip()]
            
            for i, paragraph in enumerate(paragraphs):
                if len(paragraph) > 100:  # Only substantial paragraphs
                    title = self._extract_improved_title(paragraph)
                    sections.append(PolicySection(
                        content=paragraph,
                        section_number=i + 1,
                        title=title
                    ))
        
        return sections if sections else [PolicySection(document_content, 1, "Full Document")]
    
    def _extract_improved_title(self, content: str) -> str:
        """Improved title extraction with better heuristics"""
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        if not lines:
            return "Untitled Section"
        
        first_line = lines[0]
        
        # Check various title patterns
        title_indicators = [
            (r'^(\d+\.(?:\d+\.)*)\s*(.+)', lambda m: m.group(2)),  # Numbered
            (r'^([A-Z][A-Z\s]{5,}?):', lambda m: m.group(1)),  # ALL CAPS with colon
            (r'^(#{1,3})\s+(.+)', lambda m: m.group(2)),  # Markdown
            (r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*$', lambda m: m.group(1)),  # Title Case
        ]
        
        for pattern, extractor in title_indicators:
            match = re.match(pattern, first_line)
            if match:
                return extractor(match)
        
        # Fallback: use first line if it's reasonable length
        if 10 <= len(first_line) <= 100 and not first_line.endswith('.'):
            return first_line
        
        # Generate descriptive title based on content
        words = content.split()[:10]
        return f"Section ({len(lines)} lines): {' '.join(words)}"
    
    def map_to_regulations(self, sections: List[PolicySection]) -> List[RegulatoryMapping]:
        """Enhanced mapping with improved confidence scoring and citation tracking"""
        mappings = []
        
        for section in sections:
            section_mappings = self._analyze_section_enhanced(section)
            mappings.extend(section_mappings)
        
        # Sort by confidence score and return top mappings
        mappings.sort(key=lambda x: x.confidence_score, reverse=True)
        return mappings
    
    def _analyze_section_enhanced(self, section: PolicySection) -> List[RegulatoryMapping]:
        """Enhanced section analysis with citation-specific scoring"""
        mappings = []
        
        for reg_category, reg_data in self.regulatory_mappings.items():
            for reg_section_key, reg_info in reg_data["sections"].items():
                reg_text = reg_info.get("text", "")
                confidence, reasoning = self._calculate_enhanced_confidence(
                    section.content, reg_info, reg_text
                )
                
                # Only include mappings above a minimum threshold
                if confidence > 0.10:  # Lowered threshold to capture more potential matches
                    evidence = self._find_enhanced_evidence(section.content, reg_info)
                    
                    mapping = RegulatoryMapping(
                        policy_section=section,
                        regulation_category=reg_category,
                        regulation_section=reg_section_key,
                        regulation_text=reg_text,
                        confidence_score=confidence,
                        evidence=evidence,
                        reasoning=reasoning,
                        citation_id=reg_info.get("citation", ""),
                        source_url=reg_info.get("source_url", "")
                    )
                    mappings.append(mapping)
        
        return mappings
    
    def _find_enhanced_evidence(self, policy_content: str, regulation_info: dict) -> List[str]:
        """Find more targeted evidence based on compliance indicators and citations"""
        sentences = re.split(r'[.!?]+', policy_content)
        evidence = []
        
        intent_patterns = regulation_info.get("intent_patterns", [])
        compliance_indicators = regulation_info.get("compliance_indicators", [])
        citation = regulation_info.get("citation", "")
        
        # Score sentences based on multiple criteria
        sentence_scores = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 20:  # Minimum sentence length
                score = 0
                
                # Check for intent patterns
                for pattern in intent_patterns:
                    if pattern.lower() in sentence.lower():
                        score += 2
                
                # Check for compliance indicators
                for indicator in compliance_indicators:
                    if re.search(indicator, sentence.lower()):
                        score += 3
                
                # Check for citation relevance
                if citation:
                    citation_relevance = self._calculate_citation_relevance(sentence, citation)
                    score += citation_relevance * 4
                
                if score > 0:
                    sentence_scores.append((sentence, score))
        
        # Sort by score and return top evidence
        sentence_scores.sort(key=lambda x: x[1], reverse=True)
        return [sentence for sentence, _ in sentence_scores[:3]]
    
    def generate_detailed_report(self, mappings: List[RegulatoryMapping], original_query: str, document_stats: dict) -> str:
        """Generate detailed compliance report with enhanced citation tracking"""
        report_sections = []
        
        # Header
        report_sections.append("DETAILED REGULATORY COMPLIANCE ANALYSIS")
        report_sections.append("=" * 50)
        report_sections.append(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_sections.append(f"Query: {original_query}")
        report_sections.append(f"Document Length: {document_stats.get('length', 'Unknown')} characters")
        report_sections.append("")
        
        # Executive Summary
        report_sections.append("EXECUTIVE SUMMARY")
        report_sections.append("-" * 20)
        
        total_sections = len(set(m.policy_section.section_number for m in mappings))
        total_regulations = len(set(f"{m.regulation_category}_{m.regulation_section}" for m in mappings))
        high_confidence = len([m for m in mappings if m.confidence_score > 0.7])
        medium_confidence = len([m for m in mappings if 0.4 <= m.confidence_score <= 0.7])
        low_confidence = len([m for m in mappings if m.confidence_score < 0.4])
        
        report_sections.append(f"• Document sections analyzed: {total_sections}")
        report_sections.append(f"• Total regulatory mappings identified: {len(mappings)}")
        report_sections.append(f"• Specific regulatory citations found: {len(set(m.citation_id for m in mappings if m.citation_id))}")
        report_sections.append(f"• High-confidence matches (>70%): {high_confidence}")
        report_sections.append(f"• Medium-confidence matches (40-70%): {medium_confidence}")
        report_sections.append(f"• Low-confidence matches (<40%): {low_confidence}")
        report_sections.append("")
        
        # Enhanced Compliance Status Overview
        if high_confidence > 0:
            report_sections.append("✅ STRONG COMPLIANCE INDICATORS:")
            report_sections.append(f"   {high_confidence} policy sections show strong alignment with specific regulatory requirements")
        
        if medium_confidence > 0:
            report_sections.append("⚠️ AREAS NEEDING REVIEW:")
            report_sections.append(f"   {medium_confidence} sections require closer examination for full compliance")
        
        if low_confidence > 0:
            report_sections.append("❌ POTENTIAL COMPLIANCE GAPS:")
            report_sections.append(f"   {low_confidence} areas may need policy updates or additional documentation")
        
        report_sections.append("")
        
        # Section-by-Section Analysis with Citation Details
        report_sections.append("SECTION-BY-SECTION REGULATORY MAPPING")
        report_sections.append("-" * 40)
        
        # Group mappings by policy section
        section_groups = {}
        for mapping in mappings:
            section_num = mapping.policy_section.section_number
            if section_num not in section_groups:
                section_groups[section_num] = []
            section_groups[section_num].append(mapping)
        
        for section_num in sorted(section_groups.keys()):
            section_mappings = section_groups[section_num]
            policy_section = section_mappings[0].policy_section
            
            report_sections.append(f"SECTION {section_num}: {policy_section.title}")
            content_preview = policy_section.content[:200] + "..." if len(policy_section.content) > 200 else policy_section.content
            report_sections.append(f"Content Preview: {content_preview}")
            report_sections.append("")
            
            report_sections.append("Regulatory Matches:")
            for i, mapping in enumerate(sorted(section_mappings, key=lambda x: x.confidence_score, reverse=True)[:5]):
                confidence_indicator = "🟢" if mapping.confidence_score > 0.7 else "🟡" if mapping.confidence_score > 0.4 else "🔴"
                
                report_sections.append(f"  {i+1}. {confidence_indicator} {self.regulatory_mappings[mapping.regulation_category]['title']}")
                
                # Add specific citation information
                if mapping.citation_id:
                    report_sections.append(f"     Specific Citation: {mapping.citation_id}")
                
                report_sections.append(f"     Regulatory Requirement: {mapping.regulation_text}")
                report_sections.append(f"     Confidence Score: {mapping.confidence_score:.2f} ({mapping.confidence_score*100:.0f}%)")
                report_sections.append(f"     Analysis Details: {mapping.reasoning}")
                
                if mapping.evidence:
                    report_sections.append(f"     Supporting Evidence: \"{mapping.evidence[0][:120]}...\"")
                
                # Add source URL if available
                if mapping.source_url:
                    report_sections.append(f"     Regulatory Source: {mapping.source_url}")
                
                # Provide specific recommendations based on confidence
                if mapping.confidence_score < 0.4:
                    report_sections.append("     ⚠️ RECOMMENDATION: Review this section for potential compliance gaps")
                elif mapping.confidence_score < 0.7:
                    report_sections.append("     ℹ️ SUGGESTION: Consider adding more specific language to strengthen compliance")
                else:
                    report_sections.append("     ✅ STATUS: Strong compliance alignment identified")
                
                report_sections.append("")
            
            report_sections.append("-" * 30)
            report_sections.append("")
        
        # Enhanced Citation Coverage Analysis
        report_sections.append("SPECIFIC CITATION COVERAGE ANALYSIS")
        report_sections.append("-" * 40)
        
        citation_coverage = {}
        for mapping in mappings:
            citation = mapping.citation_id
            if citation and citation != "":
                if citation not in citation_coverage:
                    citation_coverage[citation] = {
                        "category": mapping.regulation_category,
                        "confidence_scores": [],
                        "sections": []
                    }
                citation_coverage[citation]["confidence_scores"].append(mapping.confidence_score)
                citation_coverage[citation]["sections"].append(mapping.policy_section.section_number)
        
        for citation, data in citation_coverage.items():
            avg_confidence = sum(data["confidence_scores"]) / len(data["confidence_scores"])
            status = "✅ Well Covered" if avg_confidence > 0.6 else "⚠️ Needs Review" if avg_confidence > 0.3 else "❌ Significant Gap"
            
            report_sections.append(f"Citation: {citation}")
            report_sections.append(f"  • Regulatory Category: {data['category'].replace('_', ' ').title()}")
            report_sections.append(f"  • Policy Sections Referencing: {', '.join(map(str, set(data['sections'])))}")
            report_sections.append(f"  • Average Confidence: {avg_confidence:.2f} ({status})")
            report_sections.append("")
        
        # Continue with existing regulatory coverage analysis and recommendations...
        # [Rest of the report generation remains similar but enhanced with citation details]
        
        return "\n".join(report_sections)

def create_enhanced_pdf_report(report_text: str, mappings: List[RegulatoryMapping], filename: str):
    """Create an enhanced PDF report with better formatting and citation details"""
    doc = SimpleDocTemplate(filename, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    story = []
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.darkblue,
        spaceAfter=20,
        alignment=1  # Center alignment
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.darkgreen,
        spaceBefore=15,
        spaceAfter=10
    )
    
    subheading_style = ParagraphStyle(
        'CustomSubHeading',
        parent=styles['Heading3'],
        fontSize=10,
        textColor=colors.darkblue,
        spaceBefore=10,
        spaceAfter=5
    )
    
    # Process report text
    lines = report_text.split('\n')
    for line in lines:
        if not line.strip():
            story.append(Spacer(1, 6))
            continue
            
        if line.startswith('DETAILED REGULATORY') or line.startswith('='):
            if not line.startswith('='):
                story.append(Paragraph(line, title_style))
        elif line.startswith(('EXECUTIVE SUMMARY', 'SECTION-BY-SECTION', 'SPECIFIC CITATION COVERAGE', 'REGULATORY COVERAGE', 'DETAILED COMPLIANCE RECOMMENDATIONS')):
            story.append(Paragraph(line, heading_style))
        elif line.startswith(('SECTION ', 'Citation:', '🚨 HIGH PRIORITY', '⚠️ MEDIUM PRIORITY', '📋 GENERAL')):
            story.append(Paragraph(line, subheading_style))
        else:
            story.append(Paragraph(line, styles['Normal']))
    
    # Add enhanced compliance summary table with citations
    if mappings:
        story.append(Spacer(1, 20))
        story.append(Paragraph("ENHANCED COMPLIANCE MAPPING SUMMARY", heading_style))
        
        # Create enhanced summary table
        table_data = [['Section', 'Citation', 'Regulation Category', 'Confidence', 'Status']]
        
        for mapping in mappings[:15]:  # Top 15 mappings
            if mapping.confidence_score > 0.7:
                status = "✅ Strong"
            elif mapping.confidence_score > 0.4:
                status = "⚠️ Review"
            else:
                status = "❌ Gap"
            
            citation_short = mapping.citation_id[:30] + "..." if len(mapping.citation_id) > 30 else mapping.citation_id
            reg_short = mapping.regulation_category.replace('_', ' ').replace('CFPB', 'CFPB').replace('SEC', 'SEC').replace('FDIC', 'FDIC')
            
            table_data.append([
                f"Section {mapping.policy_section.section_number}",
                citation_short,
                reg_short,
                f"{mapping.confidence_score:.2f}",
                status
            ])
        
        table = Table(table_data, colWidths=[0.8*inch, 1.8*inch, 1.5*inch, 0.6*inch, 0.8*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
    
    doc.build(story)
# === NEW: PDF paragraph parsing + lightweight vector index =====================

def _normalize_ws(s: str) -> str:
    return re.sub(r'\s+', ' ', s).strip()

def _split_paragraphs(page_text: str) -> List[str]:
    # split on blank lines; also handle long blocks by sentence-ish chunking
    chunks = [p.strip() for p in re.split(r'\n\s*\n', page_text) if p.strip()]
    # If PDF text has no blank lines, fall back to chunking every ~4 sentences
    if len(chunks) <= 1:
        sentences = re.split(r'(?<=[.!?])\s+', _normalize_ws(page_text))
        buf, out = [], []
        for s in sentences:
            buf.append(s)
            if len(buf) >= 4 or sum(len(x) for x in buf) > 700:
                out.append(' '.join(buf))
                buf = []
        if buf:
            out.append(' '.join(buf))
        chunks = out
    # clean and keep substantial paragraphs only
    return [c for c in map(_normalize_ws, chunks) if len(c) >= 120]

def parse_pdf_to_page_paragraphs(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Returns: list of dicts: { 'page': int (1-based), 'text': str }
    """
    results: List[Dict[str, Any]] = []

    # Preferred: PyPDF2 (page-wise access is straightforward)
    if HAS_PYPDF2:
        try:
            with open(pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for i, page in enumerate(reader.pages):
                    try:
                        txt = page.extract_text() or ""
                    except Exception:
                        txt = ""
                    for para in _split_paragraphs(txt):
                        results.append({"page": i + 1, "text": para})
            if results:
                return results
        except Exception:
            pass

    # Fallback: pdfminer (whole-doc; we’ll approximate page splits)
    if HAS_PDFMINER:
        try:
            full = pdfminer_extract_text(pdf_path) or ""
            # very rough page heuristics: look for form feed or large gaps
            rough_pages = re.split(r'\f|\n\s{10,}\n', full)
            if len(rough_pages) <= 1:
                rough_pages = re.split(r'\n{6,}', full)  # desperate fallback
            for i, ptxt in enumerate(rough_pages):
                for para in _split_paragraphs(ptxt):
                    results.append({"page": i + 1, "text": para})
            if results:
                return results
        except Exception:
            pass

    # Last resort: if unstructured is present, get elements and bucket by page if possible
    if HAS_UNSTRUCTURED:
        try:
            elements = partition(filename=pdf_path)
            # some element types may expose .metadata.page_number; guard carefully
            for el in elements:
                txt = str(el).strip()
                if len(txt) < 50:
                    continue
                page_no = getattr(getattr(el, "metadata", None), "page_number", None)
                page_no = int(page_no) if isinstance(page_no, int) else None
                for para in _split_paragraphs(txt):
                    results.append({"page": page_no or 1, "text": para})
            if results:
                return results
        except Exception:
            pass

    # If nothing worked, try reading as text (unlikely for real PDFs, but safe)
    try:
        with open(pdf_path, "r", encoding="utf-8", errors="ignore") as f:
            txt = f.read()
        # pretend it is page 1
        for para in _split_paragraphs(txt):
            results.append({"page": 1, "text": para})
    except Exception:
        pass

    return results


# --------- Tiny hashed bag-of-words encoder + cosine search (no external deps) --

TOKEN_RE = re.compile(r"\b[a-zA-Z0-9]{2,}\b")

def _tokenize(text: str) -> List[str]:
    return [t.lower() for t in TOKEN_RE.findall(text)]

def _hash_token(t: str, dim: int) -> int:
    # stable hash to index
    return (hash(t) & 0x7FFFFFFF) % dim

def embed_hashed_bow(text: str, dim: int = 2048) -> np.ndarray:
    vec = np.zeros(dim, dtype=np.float32)
    toks = _tokenize(text)
    if not toks:
        return vec
    for tok in toks:
        vec[_hash_token(tok, dim)] += 1.0
    # l2 normalize
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec

def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    return float(np.dot(a, b) / denom) if denom > 0 else 0.0

class ParagraphVectorIndex:
    """
    In-memory vector index for paragraph dicts {page:int, text:str}.
    Uses hashed bag-of-words embeddings + cosine similarity.
    """
    def __init__(self, dim: int = 2048):
        self.dim = dim
        self.paragraphs: List[Dict[str, Any]] = []
        self.embeddings: Optional[np.ndarray] = None

    def fit(self, paragraphs: List[Dict[str, Any]]):
        self.paragraphs = paragraphs
        if not paragraphs:
            self.embeddings = np.zeros((0, self.dim), dtype=np.float32)
            return
        embs = [embed_hashed_bow(p["text"], self.dim) for p in paragraphs]
        self.embeddings = np.vstack(embs)

    def query(self, query_text: str, k: int = 5) -> List[Tuple[int, float]]:
        if self.embeddings is None or len(self.paragraphs) == 0:
            return []
        q = embed_hashed_bow(query_text, self.dim)
        # cosine vs all
        sims = (self.embeddings @ q)  # since all are unit-normalized
        # top-k indices
        k = max(1, min(k, sims.shape[0]))
        top_idx = np.argpartition(-sims, k - 1)[:k]
        # sort exact
        top_sorted = top_idx[np.argsort(-sims[top_idx])]
        return [(int(i), float(sims[i])) for i in top_sorted]
# ===============================================================================


# The new report generator class and related functions
class EnhancedComplianceReportGenerator:
    """Enhanced report generator with direct citations, specific remediation, and comprehensive analysis"""
    
    def __init__(self, analyzer):
        self.analyzer = analyzer
        self.regulatory_text_snippets = self._load_regulatory_text_snippets()
    
    def _load_regulatory_text_snippets(self):
        """Load specific regulatory text snippets for direct citation"""
        return {
            "sox_404a_management_assessment": {
                "citation": "Sarbanes-Oxley Act, Section 404(a)",
                "key_text": "The Securities and Exchange Commission shall prescribe rules requiring each annual report...to contain an internal control report, which shall state the responsibility of management for establishing and maintaining adequate internal control structure and procedures for financial reporting",
                "specific_requirements": [
                    "Document internal control structure and procedures",
                    "Annual assessment of control effectiveness", 
                    "Management responsibility statement",
                    "Evidence of testing procedures"
                ]
            },
            "cfr_353_aml_program": {
                "citation": "12 CFR Part 353.3",
                "key_text": "Each FDIC-supervised institution shall develop and implement a written anti-money laundering program that includes, at a minimum: (a) A system of internal controls to ensure ongoing compliance with the Bank Secrecy Act; (b) Independent testing for compliance",
                "specific_requirements": [
                    "Written AML program",
                    "System of internal controls", 
                    "Independent testing procedures",
                    "Designated compliance officer",
                    "Training for appropriate personnel",
                    "Customer identification program"
                ]
            },
            "cfr_326_brokered_deposits": {
                "citation": "12 CFR Part 326.8",
                "key_text": "A depository institution that is not well capitalized may not accept, renew, or roll over any brokered deposit unless it has obtained a waiver from the FDIC",
                "specific_requirements": [
                    "Capital adequacy assessment",
                    "Rate restriction compliance (120 basis points above benchmark)",
                    "Detailed record keeping of brokered deposit arrangements",
                    "Quarterly reporting on brokered deposit activities",
                    "FDIC waiver process documentation"
                ]
            },
            "cfpa_1036_udaap": {
                "citation": "Consumer Financial Protection Act, Section 1036(a)",
                "key_text": "The Bureau may take any action authorized under subtitle E to prevent a covered person or service provider from committing or engaging in an unfair, deceptive, or abusive act or practice",
                "specific_requirements": [
                    "Consumer complaint management system",
                    "Fair lending practice documentation",
                    "Clear and conspicuous disclosures",
                    "Consumer protection training programs",
                    "Regular assessment of practices for UDAAP risks"
                ]
            }
        }
    
    def generate_enhanced_report(self, mappings: List[RegulatoryMapping], original_query: str, document_stats: dict, document_content: str) -> str:
        """Generate comprehensive enhanced report with direct citations and specific remediation"""
        report_sections = []
        
        # Enhanced Header with Analysis Scope
        report_sections.append("COMPREHENSIVE REGULATORY COMPLIANCE ANALYSIS")
        report_sections.append("=" * 60)
        report_sections.append(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_sections.append(f"Document Query: {original_query}")
        report_sections.append(f"Document Statistics:")
        report_sections.append(f"  • Total Length: {document_stats.get('length', 'Unknown'):,} characters")
        report_sections.append(f"  • Sections Analyzed: {document_stats.get('sections', 0)}")
        report_sections.append(f"  • Regulatory Mappings Found: {document_stats.get('mappings', 0)}")
        report_sections.append(f"  • Unique Citations Identified: {document_stats.get('unique_citations', 0)}")
        report_sections.append("")
        
        # Enhanced Executive Summary with Compliance Scoring
        compliance_score = self._calculate_overall_compliance_score(mappings)
        report_sections.extend(self._generate_executive_summary(mappings, compliance_score))
        
        # Comprehensive Section Analysis
        report_sections.extend(self._generate_comprehensive_section_analysis(mappings, document_content))
        
        # Direct Regulatory Citations with Full Text
        report_sections.extend(self._generate_direct_citation_analysis(mappings))
        
        # Specific Remediation Recommendations
        report_sections.extend(self._generate_specific_remediation_recommendations(mappings))
        
        # Gap Analysis and Priority Matrix
        report_sections.extend(self._generate_gap_analysis_and_priority_matrix(mappings))
        
        # Implementation Roadmap
        report_sections.extend(self._generate_implementation_roadmap(mappings))
        
        return "\n".join(report_sections)
    
    def _calculate_overall_compliance_score(self, mappings: List[RegulatoryMapping]) -> dict:
        """Calculate overall compliance scoring metrics"""
        if not mappings:
            return {"overall": 0.0, "by_category": {}, "risk_level": "HIGH"}
        
        # Calculate scores by category
        category_scores = {}
        for mapping in mappings:
            cat = mapping.regulation_category
            if cat not in category_scores:
                category_scores[cat] = []
            category_scores[cat].append(mapping.confidence_score)
        
        # Average scores by category
        for cat in category_scores:
            category_scores[cat] = sum(category_scores[cat]) / len(category_scores[cat])
        
        # Overall weighted score
        overall_score = sum(category_scores.values()) / len(category_scores) if category_scores else 0.0
        
        # Risk level determination
        if overall_score >= 0.8:
            risk_level = "LOW"
        elif overall_score >= 0.6:
            risk_level = "MEDIUM"
        elif overall_score >= 0.4:
            risk_level = "HIGH"
        else:
            risk_level = "CRITICAL"
        
        return {
            "overall": overall_score,
            "by_category": category_scores,
            "risk_level": risk_level
        }
    
    def _generate_executive_summary(self, mappings: List[RegulatoryMapping], compliance_score: dict) -> List[str]:
        """Generate enhanced executive summary with compliance scoring"""
        sections = []
        sections.append("EXECUTIVE SUMMARY & COMPLIANCE DASHBOARD")
        sections.append("-" * 50)
        
        # Compliance Score Dashboard
        sections.append("OVERALL COMPLIANCE ASSESSMENT:")
        sections.append(f"  • Compliance Score: {compliance_score['overall']:.1%}")
        sections.append(f"  • Risk Level: {compliance_score['risk_level']}")
        
        # Category breakdown
        sections.append("  • Regulatory Category Scores:")
        for category, score in compliance_score['by_category'].items():
            status_icon = "✅" if score > 0.7 else "⚠️" if score > 0.4 else "❌"
            category_name = category.replace('_', ' ').title()
            sections.append(f"    {status_icon} {category_name}: {score:.1%}")
        
        sections.append("")
        
        # Key Findings Summary
        high_priority_gaps = [m for m in mappings if m.confidence_score < 0.4]
        medium_priority_gaps = [m for m in mappings if 0.4 <= m.confidence_score < 0.7]
        well_covered = [m for m in mappings if m.confidence_score >= 0.7]
        
        sections.append("KEY FINDINGS:")
        sections.append(f"  • Well-Covered Requirements: {len(well_covered)}")
        sections.append(f"  • Areas Needing Enhancement: {len(medium_priority_gaps)}")
        sections.append(f"  • Critical Compliance Gaps: {len(high_priority_gaps)}")
        sections.append("")
        
        # Risk Assessment
        if compliance_score['risk_level'] in ['HIGH', 'CRITICAL']:
            sections.append("🚨 RISK ALERT:")
            sections.append("   This policy document shows significant compliance gaps that require")
            sections.append("   immediate attention to avoid potential regulatory violations.")
        elif compliance_score['risk_level'] == 'MEDIUM':
            sections.append("⚠️ ATTENTION REQUIRED:")
            sections.append("   Several areas need strengthening to ensure full regulatory compliance.")
        else:
            sections.append("✅ COMPLIANCE STATUS:")
            sections.append("   Policy shows strong alignment with regulatory requirements.")
        
        sections.append("")
        return sections
    
    def _generate_comprehensive_section_analysis(self, mappings: List[RegulatoryMapping], document_content: str) -> List[str]:
        """Generate comprehensive section-by-section analysis with enhanced evidence"""
        sections = []
        sections.append("COMPREHENSIVE SECTION-BY-SECTION ANALYSIS")
        sections.append("-" * 50)
        
        # Group mappings by policy section
        section_groups = {}
        for mapping in mappings:
            section_num = mapping.policy_section.section_number
            if section_num not in section_groups:
                section_groups[section_num] = []
            section_groups[section_num].append(mapping)
        
        for section_num in sorted(section_groups.keys()):
            section_mappings = section_groups[section_num]
            policy_section = section_mappings[0].policy_section
            
            sections.append(f"SECTION {section_num}: {policy_section.title}")
            sections.append("=" * 40)
            
            # Enhanced content preview with context
            content_lines = policy_section.content.split('\n')
            key_sentences = [line.strip() for line in content_lines if line.strip() and len(line.strip()) > 50][:3]
            
            sections.append("POLICY CONTENT ANALYSIS:")
            for i, sentence in enumerate(key_sentences, 1):
                sections.append(f"  {i}. {sentence}")
            sections.append("")
            
            # Regulatory alignment analysis
            sections.append("REGULATORY ALIGNMENT FINDINGS:")
            
            # Sort mappings by confidence score
            sorted_mappings = sorted(section_mappings, key=lambda x: x.confidence_score, reverse=True)
            
            for i, mapping in enumerate(sorted_mappings[:5], 1):
                confidence_level = self._get_confidence_level(mapping.confidence_score)
                sections.append(f"  {i}. {confidence_level['icon']} {confidence_level['label']} MATCH")
                sections.append(f"      Regulation: {mapping.citation_id}")
                sections.append(f"      Requirement: {mapping.regulation_text}")
                sections.append(f"      Confidence: {mapping.confidence_score:.1%}")
                
                # Enhanced evidence with specific quotes
                if mapping.evidence:
                    sections.append(f"      Supporting Evidence from Policy:")
                    for evidence in mapping.evidence[:2]:
                        sections.append(f"        → \"{evidence[:150]}...\"")
                
                # Specific analysis details
                sections.append(f"      Analysis: {mapping.reasoning}")
                sections.append("")
            
            sections.append("-" * 40)
            sections.append("")
        
        return sections
    
    def _generate_direct_citation_analysis(self, mappings: List[RegulatoryMapping]) -> List[str]:
        """Generate direct citation analysis with full regulatory text"""
        sections = []
        sections.append("DIRECT REGULATORY CITATION ANALYSIS")
        sections.append("-" * 50)
        sections.append("This section provides direct quotes from federal regulations")
        sections.append("that correspond to your policy requirements.")
        sections.append("")
        
        # Group by unique citations
        citation_mappings = {}
        for mapping in mappings:
            citation = mapping.citation_id
            if citation and citation not in citation_mappings:
                citation_mappings[citation] = {
                    'mapping': mapping,
                    'policy_sections': []
                }
            if citation:
                citation_mappings[citation]['policy_sections'].append(mapping.policy_section.section_number)
        
        for citation, data in citation_mappings.items():
            mapping = data['mapping']
            sections.append(f"CITATION: {citation}")
            sections.append("=" * len(f"CITATION: {citation}"))
            
            # Find regulatory text snippet
            reg_key = self._find_regulatory_key(citation)
            if reg_key and reg_key in self.regulatory_text_snippets:
                reg_info = self.regulatory_text_snippets[reg_key]
                
                sections.append("OFFICIAL REGULATORY TEXT:")
                sections.append(f'"{reg_info["key_text"]}"')
                sections.append("")
                
                sections.append("SPECIFIC REQUIREMENTS:")
                for req in reg_info["specific_requirements"]:
                    sections.append(f"  • {req}")
                sections.append("")
            
            sections.append(f"POLICY SECTIONS AFFECTED: {', '.join(map(str, set(data['policy_sections'])))}")
            sections.append(f"SOURCE: {mapping.source_url}")
            sections.append("")
            sections.append("-" * 30)
            sections.append("")
        
        return sections
    
    def _generate_specific_remediation_recommendations(self, mappings: List[RegulatoryMapping]) -> List[str]:
        """Generate specific, actionable remediation recommendations"""
        sections = []
        sections.append("SPECIFIC REMEDIATION RECOMMENDATIONS")
        sections.append("-" * 50)
        sections.append("Based on the compliance gap analysis, here are specific actions")
        sections.append("to enhance your policy's regulatory alignment:")
        sections.append("")
        
        # Categorize by priority
        critical_gaps = [m for m in mappings if m.confidence_score < 0.4]
        medium_gaps = [m for m in mappings if 0.4 <= m.confidence_score < 0.7]
        
        if critical_gaps:
            sections.append("🚨 CRITICAL PRIORITY ACTIONS:")
            sections.append("")
            
            for i, mapping in enumerate(critical_gaps, 1):
                sections.append(f"{i}. {mapping.citation_id}")
                
                # Specific recommendations based on regulation type
                recommendations = self._get_specific_recommendations(mapping)
                for rec in recommendations:
                    sections.append(f"    • {rec}")
                
                sections.append(f"    • Current Gap: {mapping.reasoning}")
                sections.append(f"    • Timeline: Immediate (within 30 days)")
                sections.append("")
        
        if medium_gaps:
            sections.append("⚠️ MEDIUM PRIORITY ENHANCEMENTS:")
            sections.append("")
            
            for i, mapping in enumerate(medium_gaps, 1):
                sections.append(f"{i}. {mapping.citation_id}")
                
                recommendations = self._get_specific_recommendations(mapping)
                for rec in recommendations:
                    sections.append(f"    • {rec}")
                
                sections.append(f"    • Enhancement Opportunity: {mapping.reasoning}")
                sections.append(f"    • Timeline: Within 90 days")
                sections.append("")
        
        return sections
    
    def _get_specific_recommendations(self, mapping: RegulatoryMapping) -> List[str]:
        """Generate specific recommendations based on regulation type"""
        citation_lower = mapping.citation_id.lower()
        
        if "sarbanes" in citation_lower or "sox" in citation_lower:
            return [
                "Add explicit language about annual internal control assessments",
                "Include management responsibility statements for control effectiveness",
                "Establish documentation requirements for control testing procedures",
                "Define roles for internal control evaluation and reporting"
            ]
        
        elif "353" in citation_lower and "aml" in citation_lower:
            return [
                "Establish a written anti-money laundering program",
                "Define independent testing procedures for AML compliance",
                "Designate a specific AML compliance officer",
                "Create comprehensive customer identification procedures",
                "Implement transaction monitoring and suspicious activity reporting protocols"
            ]
        
        elif "326" in citation_lower and "brokered" in citation_lower:
            return [
                "Add capital adequacy assessment procedures",
                "Implement rate restriction compliance monitoring (120 basis points rule)",
                "Establish detailed record-keeping for brokered deposit arrangements",
                "Create quarterly reporting procedures for brokered deposit activities",
                "Document FDIC waiver processes for non-well-capitalized institutions"
            ]
        
        elif "consumer financial protection" in citation_lower:
            return [
                "Implement comprehensive consumer complaint management system",
                "Add specific prohibitions on unfair, deceptive, or abusive practices",
                "Create clear disclosure requirements for consumer financial products",
                "Establish regular UDAAP risk assessment procedures",
                "Document consumer protection training programs"
            ]
        
        else:
            return [
                f"Review policy language to better align with {mapping.citation_id}",
                "Add more specific compliance procedures and controls",
                "Include documentation and record-keeping requirements",
                "Establish regular compliance monitoring and reporting"
            ]
    
    def _generate_gap_analysis_and_priority_matrix(self, mappings: List[RegulatoryMapping]) -> List[str]:
        """Generate gap analysis and priority matrix"""
        sections = []
        sections.append("GAP ANALYSIS & PRIORITY MATRIX")
        sections.append("-" * 40)
        
        # Create priority matrix
        sections.append("COMPLIANCE PRIORITY MATRIX:")
        sections.append("")
        sections.append("│ Priority │ Citation                      │ Gap Severity │ Business Impact │")
        sections.append("├──────────┼───────────────────────────────┼──────────────┼─────────────────┤")
        
        # Sort by priority (low confidence = high priority)
        priority_mappings = sorted(mappings, key=lambda x: x.confidence_score)
        
        for i, mapping in enumerate(priority_mappings[:10], 1):
            citation_short = mapping.citation_id[:25] + "..." if len(mapping.citation_id) > 25 else mapping.citation_id
            
            if mapping.confidence_score < 0.4:
                severity = "Critical"
                impact = "High"
                priority = f"P{i}"
            elif mapping.confidence_score < 0.7:
                severity = "Medium"
                impact = "Medium"
                priority = f"P{i}"
            else:
                severity = "Low"
                impact = "Low"
                priority = f"P{i}"
            
            sections.append(f"│ {priority:<8} │ {citation_short:<29} │ {severity:<12} │ {impact:<15} │")
        
        sections.append("└──────────┴───────────────────────────────┴──────────────┴─────────────────┘")
        sections.append("")
        
        return sections
    
    def _generate_implementation_roadmap(self, mappings: List[RegulatoryMapping]) -> List[str]:
        """Generate implementation roadmap"""
        sections = []
        sections.append("IMPLEMENTATION ROADMAP")
        sections.append("-" * 30)
        sections.append("")
        
        critical_gaps = [m for m in mappings if m.confidence_score < 0.4]
        medium_gaps = [m for m in mappings if 0.4 <= m.confidence_score < 0.7]
        
        sections.append("PHASE 1: IMMEDIATE ACTIONS (0-30 days)")
        sections.append("─" * 35)
        if critical_gaps:
            for mapping in critical_gaps:
                sections.append(f"• Address {mapping.citation_id} compliance gap")
        else:
            sections.append("• No critical gaps identified - proceed to Phase 2")
        sections.append("")
        
        sections.append("PHASE 2: MEDIUM-TERM ENHANCEMENTS (30-90 days)")
        sections.append("─" * 45)
        if medium_gaps:
            for mapping in medium_gaps:
                sections.append(f"• Enhance {mapping.citation_id} alignment")
        else:
            sections.append("• Focus on continuous improvement and monitoring")
        sections.append("")
        
        sections.append("PHASE 3: ONGOING COMPLIANCE MANAGEMENT (90+ days)")
        sections.append("─" * 50)
        sections.append("• Establish regular compliance monitoring")
        sections.append("• Implement quarterly policy reviews")
        sections.append("• Create compliance training programs")
        sections.append("• Set up regulatory change monitoring")
        sections.append("")
        
        return sections
    
    def _get_confidence_level(self, score: float) -> dict:
        """Get confidence level indicators"""
        if score >= 0.7:
            return {"icon": "✅", "label": "STRONG"}
        elif score >= 0.4:
            return {"icon": "⚠️", "label": "MODERATE"}
        else:
            return {"icon": "❌", "label": "WEAK"}
    
    def _find_regulatory_key(self, citation: str) -> str:
        """Find regulatory key based on citation"""
        citation_lower = citation.lower()
        
        if "sarbanes" in citation_lower or "sox" in citation_lower:
            return "sox_404a_management_assessment"
        elif "353" in citation_lower:
            return "cfr_353_aml_program"
        elif "326" in citation_lower:
            return "cfr_326_brokered_deposits"
        elif "consumer financial protection" in citation_lower:
            return "cfpa_1036_udaap"
        
        return None


# Enhanced PDF Report Generator
def create_enhanced_pdf_report_v2(report_text: str, mappings: List[RegulatoryMapping], filename: str):
    """Create enhanced PDF with improved formatting and visual elements"""
    doc = SimpleDocTemplate(filename, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    story = []
    
    # Enhanced custom styles
    title_style = ParagraphStyle(
        'EnhancedTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.darkblue,
        spaceAfter=20,
        alignment=1,
        fontName='Helvetica-Bold'
    )
    
    # Add compliance score summary table at the beginning
    if mappings:
        # Calculate compliance metrics
        total_mappings = len(mappings)
        high_conf = len([m for m in mappings if m.confidence_score > 0.7])
        medium_conf = len([m for m in mappings if 0.4 <= m.confidence_score <= 0.7])
        low_conf = len([m for m in mappings if m.confidence_score < 0.4])
        
        # Compliance score table
        score_data = [
            ['Compliance Metric', 'Count', 'Percentage', 'Status'],
            ['Strong Alignment', str(high_conf), f'{high_conf/total_mappings:.1%}', '✅ Good'],
            ['Needs Review', str(medium_conf), f'{medium_conf/total_mappings:.1%}', '⚠️ Caution'],
            ['Critical Gaps', str(low_conf), f'{low_conf/total_mappings:.1%}', '❌ Priority']
        ]
        
        score_table = Table(score_data, colWidths=[2*inch, 0.8*inch, 1*inch, 1*inch])
        score_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(Paragraph("COMPLIANCE ANALYSIS REPORT", title_style))
        story.append(Spacer(1, 20))
        story.append(Paragraph("Executive Dashboard", styles['Heading2']))
        story.append(score_table)
        story.append(Spacer(1, 20))
    
    # Process the rest of the report text with enhanced formatting
    lines = report_text.split('\n')
    for line in lines:
        if not line.strip():
            story.append(Spacer(1, 6))
            continue
        
        # Enhanced formatting rules
        if line.startswith('COMPREHENSIVE REGULATORY') or line.startswith('='):
            if not line.startswith('='):
                story.append(Paragraph(line, title_style))
        elif any(line.startswith(prefix) for prefix in ['EXECUTIVE SUMMARY', 'COMPREHENSIVE SECTION', 'DIRECT REGULATORY', 'SPECIFIC REMEDIATION', 'GAP ANALYSIS', 'IMPLEMENTATION ROADMAP']):
            story.append(Paragraph(line, styles['Heading2']))
        elif line.startswith(('SECTION ', 'CITATION:', '🚨 CRITICAL', '⚠️ MEDIUM', 'PHASE ')):
            story.append(Paragraph(line, styles['Heading3']))
        else:
            story.append(Paragraph(line, styles['Normal']))
    
    doc.build(story)

# Initialize FastAPI app
app = FastAPI(
    title="FinReg API - Enhanced Regulatory Mapping with Citation Tracking",
    description="Phase 2.1: Advanced RAG Pipeline with Detailed Regulatory Compliance Analysis and Specific Citation Mapping",
    version="2.2.0",
)

@app.get("/")
def read_root():
    return {"message": "FinReg Phase 2.2 API - Enhanced Citation-Specific Regulatory Mapping 🏛️", "status": "operational"}

@app.post("/generate-detailed-report/")
async def generate_detailed_report(
    user_document: UploadFile = File(...),
    user_query: str = Form("Generate a detailed compliance report with section-by-section regulatory mapping and specific citation analysis."),
    db: Session = Depends(get_db)
):
    """Generate enhanced compliance report with detailed regulatory mapping and citation tracking"""
    temp_file_path = None
    
    try:
        # File processing
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{user_document.filename}") as temp_file:
            content = await user_document.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        # Extract content based on file type
        user_doc_content = ""
        try:
            if user_document.content_type and user_document.content_type.startswith("text/"):
                with open(temp_file_path, "r", encoding="utf-8") as f:
                    user_doc_content = f.read()
            elif HAS_UNSTRUCTURED:
                elements = partition(filename=temp_file_path)
                user_doc_content = "\n".join([str(el) for el in elements])
            else:
                try:
                    with open(temp_file_path, "r", encoding="utf-8", errors="ignore") as f:
                        user_doc_content = f.read()
                except:
                    return JSONResponse(
                        status_code=400,
                        content={"error": "Could not process document. Please upload a text file."}
                    )
        except Exception as e:
            return JSONResponse(
                status_code=400,
                content={"error": f"Failed to parse document: {str(e)}"}
            )

        if not user_doc_content.strip():
            return JSONResponse(status_code=400, content={"error": "Document appears to be empty"})

        # Enhanced analysis with citation tracking
        analyzer = EnhancedComplianceAnalyzer()
        
        # Segment the document
        sections = analyzer.segment_document(user_doc_content)
        print(f"📄 Document segmented into {len(sections)} sections")
        
        # Map to regulations with enhanced citation analysis
        mappings = analyzer.map_to_regulations(sections)
        print(f"🔗 Generated {len(mappings)} regulatory mappings with citation tracking")
        
        # Enhanced document statistics
        document_stats = {
            "length": len(user_doc_content),
            "sections": len(sections),
            "mappings": len(mappings),
            "unique_citations": len(set(m.citation_id for m in mappings if m.citation_id)),
            "high_confidence_mappings": len([m for m in mappings if m.confidence_score > 0.7])
        }
        
        # Instantiate the new report generator
        enhanced_generator = EnhancedComplianceReportGenerator(analyzer)
        
        # Generate enhanced detailed report
        report_text = enhanced_generator.generate_enhanced_report(mappings, user_query, document_stats, user_doc_content)
        
        # Save to database with enhanced metadata
        try:
            db_report = models.ComplianceReport(
                filename=user_document.filename,
                user_query=user_query,
                report_content=report_text,
                status="completed"
            )
            db.add(db_report)
            db.commit()
            print(f"✅ Enhanced report saved to database with ID: {db_report.id}")
        except Exception as e:
            print(f"⚠️ Could not save to database: {e}")
        
        # Create enhanced PDF with citation details using the new function
        pdf_filename = os.path.join(tempfile.gettempdir(), f"enhanced_compliance_report_{os.getpid()}.pdf")
        create_enhanced_pdf_report_v2(report_text, mappings, pdf_filename)

        return FileResponse(
            pdf_filename, 
            media_type="application/pdf", 
            filename=f"enhanced_compliance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        )

    except Exception as e:
        print(f"❌ Error generating enhanced report: {str(e)}")
        return JSONResponse(status_code=500, content={"error": f"Error generating enhanced report: {str(e)}"})
    
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except:
                pass

# Keep the original simple report endpoint for backward compatibility
@app.post("/generate-report/")
async def generate_basic_report(
    user_document: UploadFile = File(...),
    user_query: str = Form("Generate a compliance report based on the uploaded internal policy."),
):
    """Generate basic compliance report (legacy endpoint)"""
    return await generate_detailed_report(user_document, user_query)



@app.post("/query-paragraphs")
async def query_paragraphs(
    pdf: UploadFile = File(...),
    q: str = Form(...),
    k: int = Form(5),
):
    """
    Single-call endpoint:
    - Parses the uploaded PDF into page-aware paragraphs
    - Builds a lightweight in-memory vector index
    - Returns the top-k matching paragraphs with page & snippet
    """
    temp_file_path = None
    try:
        # save temp
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{pdf.filename}") as tmp:
            content = await pdf.read()
            tmp.write(content)
            temp_file_path = tmp.name

        # parse into paragraphs with page numbers
        page_paras = parse_pdf_to_page_paragraphs(temp_file_path)

        if not page_paras:
            return JSONResponse(
                status_code=400,
                content={"error": "Could not extract any text paragraphs from the PDF"}
            )

        # build index and query
        index = ParagraphVectorIndex(dim=2048)
        index.fit(page_paras)
        hits = index.query(q, k=max(1, min(int(k), 20)))

        # format response
        results = []
        for idx, score in hits:
            para = page_paras[idx]
            text = para["text"]
            # build a small snippet around the first match of a query token if possible
            tokens = _tokenize(q)
            loc = -1
            for t in tokens:
                loc = text.lower().find(t.lower())
                if loc != -1:
                    break
            if loc == -1:
                snippet = text[:350]
            else:
                start = max(0, loc - 140)
                end = min(len(text), loc + 210)
                snippet = text[start:end]
            results.append({
                "page": para.get("page", None),
                "score": round(score, 4),
                "snippet": snippet.strip()
            })

        return {"query": q, "k": len(results), "results": results}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"query failed: {str(e)}"})

    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except:
                pass


@app.get("/health")
def health_check():
    try:
        from database import SessionLocal
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "healthy",
        "database": db_status,
        "document_processing": "available" if HAS_UNSTRUCTURED else "basic",
        "features": ["regulatory_mapping", "section_analysis", "confidence_scoring", "citation_tracking", "enhanced_llm_processing"],
        "version": "2.2.0",
        "llm_processing": "enabled" if hasattr(get_enhanced_vector_store(), 'enhanced_mappings') else "fallback"
    }

@app.get("/analysis-stats")
def get_analysis_stats(db: Session = Depends(get_db)):
    """Get statistics about compliance analyses with enhanced citation tracking"""
    try:
        total_reports = db.query(models.ComplianceReport).count()
        recent_reports = db.query(models.ComplianceReport).filter(
            models.ComplianceReport.created_at >= datetime.now().replace(hour=0, minute=0, second=0)
        ).count()
        
        analyzer = EnhancedComplianceAnalyzer()
        
        return {
            "total_reports": total_reports,
            "reports_today": recent_reports,
            "regulatory_categories": len(analyzer.regulatory_mappings),
            "specific_citations_tracked": sum(
                len(cat_data["sections"]) 
                for cat_data in analyzer.regulatory_mappings.values()
            ),
            "mapping_engine": "enhanced_v2.2_with_citations",
            "llm_processing": "enabled" if hasattr(analyzer.vector_store, 'enhanced_mappings') else "fallback"
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/regulatory-citations")
def get_regulatory_citations():
    """Get list of all tracked regulatory citations"""
    try:
        analyzer = EnhancedComplianceAnalyzer()
        citations = []
        
        for reg_category, reg_data in analyzer.regulatory_mappings.items():
            for section_key, section_info in reg_data["sections"].items():
                citations.append({
                    "citation": section_info.get("citation", ""),
                    "category": reg_category,
                    "title": reg_data.get("title", ""),
                    "requirement": section_info.get("text", ""),
                    "source_url": section_info.get("source_url", ""),
                    "processing_confidence": section_info.get("processing_confidence", 0.0)
                })
        
        return {
            "total_citations": len(citations),
            "citations": citations,
            "categories": list(set(c["category"] for c in citations))
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/test-citation-extraction/")
async def test_citation_extraction(
    raw_regulatory_text: str = Form(...),
    regulation_category: str = Form("TEST_CATEGORY")
):
    """Test the LLM-based regulatory text extraction on custom input"""
    try:
        from ingestion import RegulatoryTextProcessor
        
        processor = RegulatoryTextProcessor()
        result = processor.process_raw_regulation(
            raw_text=raw_regulatory_text,
            source_url="test://manual_input",
            regulation_category=regulation_category
        )
        
        if result:
            return {
                "success": True,
                "extracted_citation": result.citation_id,
                "requirement_summary": result.requirement_summary,
                "processing_confidence": result.processing_confidence,
                "full_text_length": len(result.full_text_for_embedding),
                "processing_method": "LLM" if result.processing_confidence > 0.8 else "Regex_Fallback"
            }
        else:
            return {
                "success": False,
                "error": "Failed to process regulatory text"
            }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Error during citation extraction: {str(e)}"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
