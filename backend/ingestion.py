## enhanced_ingestion.py

import os
import json
import tempfile
import requests
from typing import Dict, List, Optional
from dataclasses import dataclass
import re

# Langchain imports with error handling
try:
    from langchain_community.document_loaders import WebBaseLoader
    from langchain_community.vectorstores import Chroma
    from langchain_community.embeddings import OllamaEmbeddings
    from langchain.schema import Document
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_ollama import OllamaLLM  # For text processing
    LANGCHAIN_IMPORTS_OK = True
except ImportError as e:
    print(f"Warning: Some langchain components not available: {e}")
    LANGCHAIN_IMPORTS_OK = False

@dataclass
class ProcessedRegulation:
    """Structured representation of a processed regulation"""
    citation_id: str
    requirement_summary: str
    full_text_for_embedding: str
    source_url: str
    regulation_category: str
    processing_confidence: float
    raw_text: str

class RegulatoryTextProcessor:
    """Enhanced processor for raw regulatory text using LLM extraction"""
    
    def __init__(self, model_name: str = "llama3"):
        self.llm = None
        if LANGCHAIN_IMPORTS_OK:
            try:
                self.llm = OllamaLLM(model=model_name)
                print(f"✅ Initialized LLM processor with model: {model_name}")
            except Exception as e:
                print(f"⚠️ Could not initialize LLM: {e}")
        
        # Fallback regex patterns for extraction when LLM is not available
        self.citation_patterns = [
            r'(\d+\s+CFR\s+(?:Part\s+)?\d+(?:\.\d+)*)',  # CFR citations
            r'(Sarbanes-Oxley Act(?:,?\s+Sec(?:tion)?\.?\s+\d+(?:\([a-z]\))?)?)',  # SOX
            r'(Dodd-Frank Act(?:,?\s+Sec(?:tion)?\.?\s+\d+)?)',  # Dodd-Frank
            r'(Securities Exchange Act(?:,?\s+Sec(?:tion)?\.?\s+\d+(?:\([a-z]\))?)?)',  # Securities Exchange Act
            r'(Bank Secrecy Act(?:,?\s+Sec(?:tion)?\.?\s+\d+)?)',  # BSA
            r'(\d+\s+U\.S\.C\.?\s+§?\s*\d+(?:\([a-z]\))?)',  # USC citations
        ]
    
    def process_raw_regulation(self, raw_text: str, source_url: str, regulation_category: str) -> Optional[ProcessedRegulation]:
        """Process raw regulatory text to extract structured information"""
        
        if self.llm:
            return self._process_with_llm(raw_text, source_url, regulation_category)
        else:
            return self._process_with_fallback(raw_text, source_url, regulation_category)
    
    def _process_with_llm(self, raw_text: str, source_url: str, regulation_category: str) -> Optional[ProcessedRegulation]:
        """Process using LLM with the enhanced prompt"""
        
        prompt = f"""You are a legal text processing AI. Your task is to analyze a raw block of text from a financial regulation document and extract the primary, specific regulatory citation and its core requirement.

## Instructions:
1. Read the **[Raw Regulation Text]** provided.
2. Identify the most specific official citation (e.g., "Sarbanes-Oxley Act, Sec. 404(a)", "12 CFR Part 326").
3. Summarize the single most important requirement or rule from the text in a concise sentence.
4. Provide the output in a clean, structured JSON format.

## Input:
**[Raw Regulation Text]:**
```
{raw_text[:2000]}
```

## Output Format (Strict JSON):
```json
{{
  "citation_id": "The specific official citation you identified.",
  "requirement_summary": "A concise, one-sentence summary of the core rule.",
  "full_text_for_embedding": "The original, clean text of the regulation itself."
}}
```

Respond ONLY with valid JSON, no other text."""

        try:
            response = self.llm.invoke(prompt)
            # Clean the response to extract JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                parsed_data = json.loads(json_str)
                
                return ProcessedRegulation(
                    citation_id=parsed_data.get("citation_id", "Unknown Citation"),
                    requirement_summary=parsed_data.get("requirement_summary", ""),
                    full_text_for_embedding=parsed_data.get("full_text_for_embedding", raw_text),
                    source_url=source_url,
                    regulation_category=regulation_category,
                    processing_confidence=0.9,  # High confidence for LLM processing
                    raw_text=raw_text
                )
            else:
                print("⚠️ LLM response did not contain valid JSON, falling back to regex")
                return self._process_with_fallback(raw_text, source_url, regulation_category)
                
        except Exception as e:
            print(f"⚠️ LLM processing failed: {e}, falling back to regex")
            return self._process_with_fallback(raw_text, source_url, regulation_category)
    
    def _process_with_fallback(self, raw_text: str, source_url: str, regulation_category: str) -> ProcessedRegulation:
        """Fallback processing using regex patterns"""
        
        # Extract citation using patterns
        citation_id = "General Regulation"
        for pattern in self.citation_patterns:
            match = re.search(pattern, raw_text, re.IGNORECASE)
            if match:
                citation_id = match.group(1)
                break
        
        # Extract first meaningful sentence as requirement
        sentences = re.split(r'[.!?]+', raw_text)
        requirement_summary = ""
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 50 and any(keyword in sentence.lower() for keyword in 
                ['must', 'shall', 'required', 'maintain', 'establish', 'implement', 'ensure']):
                requirement_summary = sentence + "."
                break
        
        if not requirement_summary and sentences:
            requirement_summary = sentences[0].strip() + "."
        
        return ProcessedRegulation(
            citation_id=citation_id,
            requirement_summary=requirement_summary or "Regulatory requirement identified",
            full_text_for_embedding=raw_text,
            source_url=source_url,
            regulation_category=regulation_category,
            processing_confidence=0.6,  # Lower confidence for regex processing
            raw_text=raw_text
        )

class EnhancedRegulatoryIngestion:
    """Enhanced ingestion pipeline with LLM processing"""
    
    def __init__(self):
        self.processor = RegulatoryTextProcessor()
        
        # Enhanced raw regulatory content with real citations
        self.raw_regulatory_sources = [
            {
                "raw_text": """
                12 CFR Part 326.8 - Brokered deposits
                
                (a) Restrictions on brokered deposits. A depository institution that is not well capitalized may not accept, renew, or roll over any brokered deposit unless it has obtained a waiver from the FDIC. A depository institution that is adequately capitalized may accept, renew, or roll over brokered deposits only if it pays no more than 120 basis points above certain benchmark rates for deposits of similar maturity.
                
                (b) Definitions. For purposes of this section:
                (1) Brokered deposit has the meaning set forth in section 29 of the FDI Act (12 U.S.C. 1831f).
                (2) Well capitalized, adequately capitalized, and undercapitalized have the meanings set forth in the prompt corrective action regulations applicable to the institution.
                
                Banks must maintain detailed records of all brokered deposit arrangements and report quarterly on their brokered deposit activities to demonstrate compliance with rate restrictions and capital adequacy requirements.
                """,
                "source_url": "https://www.ecfr.gov/current/title-12/chapter-III/subchapter-B/part-326",
                "category": "FDIC_BROKERED_DEPOSITS"
            },
            {
                "raw_text": """
                Sarbanes-Oxley Act, Section 404(a) - Management Assessment of Internal Controls
                
                The Securities and Exchange Commission shall prescribe rules requiring each annual report required by section 13(a) or 15(d) of the Securities Exchange Act of 1934 to contain an internal control report, which shall—
                
                (1) state the responsibility of management for establishing and maintaining adequate internal control structure and procedures for financial reporting; and
                
                (2) contain an assessment, as of the end of the most recent fiscal year of the issuer, of the effectiveness of the internal control structure and procedures of the issuer for financial reporting.
                
                Management must document, test, and evaluate the design and operating effectiveness of internal controls over financial reporting annually. This includes maintaining evidence of testing procedures, identifying material weaknesses, and providing detailed remediation plans for any control deficiencies identified during the assessment process.
                """,
                "source_url": "https://www.sec.gov/about/laws/soa2002.pdf",
                "category": "SEC_INTERNAL_CONTROLS"
            },
            {
                "raw_text": """
                12 CFR Part 353 - Anti-Money Laundering Program Requirements
                
                Section 353.3 - Minimum standards for anti-money laundering programs
                
                Each FDIC-supervised institution shall develop and implement a written anti-money laundering program that includes, at a minimum:
                
                (a) A system of internal controls to ensure ongoing compliance with the Bank Secrecy Act;
                (b) Independent testing for compliance to be conducted by bank personnel or by an outside party;
                (c) Designation of an individual or individuals responsible for coordinating and monitoring day-to-day compliance;
                (d) Training for appropriate personnel; and
                (e) Customer identification program requirements under 31 CFR 1020.220.
                
                The program must include risk-based procedures for conducting ongoing customer due diligence, including procedures for identifying and reporting suspicious transactions consistent with safe and sound banking practices. Banks must maintain comprehensive records of customer identification verification, transaction monitoring systems, and suspicious activity reporting procedures.
                """,
                "source_url": "https://www.ecfr.gov/current/title-12/chapter-III/subchapter-B/part-353",
                "category": "FDIC_AML_PROGRAM"
            },
            {
                "raw_text": """
                Consumer Financial Protection Act, Section 1036(a) - Unfair, Deceptive, or Abusive Acts or Practices
                
                The Bureau may take any action authorized under subtitle E to prevent a covered person or service provider from committing or engaging in an unfair, deceptive, or abusive act or practice under Federal law in connection with any transaction with a consumer for a consumer financial product or service, or the offering of a consumer financial product or service.
                
                12 CFR Part 1005.18 - Requirements for financial institutions offering prepaid accounts
                
                (b) Pre-acquisition disclosure requirements. Before a consumer acquires a prepaid account, a financial institution must provide clear and conspicuous disclosures about account terms, fees, and conditions. These disclosures must include all periodic fees, per-transaction fees, and third-party fees that may be imposed in connection with the prepaid account.
                
                Financial institutions must implement comprehensive consumer complaint management systems, maintain detailed records of consumer interactions, and provide regular training to staff on fair lending practices and consumer protection requirements.
                """,
                "source_url": "https://www.ecfr.gov/current/title-12/chapter-X/part-1005",
                "category": "CFPB_CONSUMER_PROTECTION"
            }
        ]
    
    def process_all_regulations(self) -> List[ProcessedRegulation]:
        """Process all raw regulatory sources through LLM extraction"""
        processed_regulations = []
        
        print("🔄 Processing raw regulatory text through LLM extraction...")
        
        for source in self.raw_regulatory_sources:
            print(f"📄 Processing: {source['category']}")
            
            processed = self.processor.process_raw_regulation(
                raw_text=source["raw_text"],
                source_url=source["source_url"],
                regulation_category=source["category"]
            )
            
            if processed:
                processed_regulations.append(processed)
                print(f"   ✅ Citation: {processed.citation_id}")
                print(f"   📝 Requirement: {processed.requirement_summary[:100]}...")
                print(f"   🎯 Confidence: {processed.processing_confidence:.2f}")
            else:
                print(f"   ⚠️ Failed to process")
            
            print()
        
        return processed_regulations
    
    def create_enhanced_mappings(self, processed_regulations: List[ProcessedRegulation]) -> Dict:
        """Create enhanced regulatory mappings from processed regulations"""
        enhanced_mappings = {}
        
        for reg in processed_regulations:
            category_key = reg.regulation_category
            
            # Create detailed intent patterns from the requirement summary
            intent_patterns = self._extract_intent_patterns(reg.requirement_summary)
            compliance_indicators = self._extract_compliance_indicators(reg.full_text_for_embedding)
            
            # Create section key from citation
            section_key = self._create_section_key(reg.citation_id)
            
            if category_key not in enhanced_mappings:
                enhanced_mappings[category_key] = {
                    "title": self._format_category_title(category_key),
                    "sections": {}
                }
            
            enhanced_mappings[category_key]["sections"][section_key] = {
                "citation": reg.citation_id,
                "text": reg.requirement_summary,
                "full_regulation_text": reg.full_text_for_embedding,
                "source_url": reg.source_url,
                "intent_patterns": intent_patterns,
                "compliance_indicators": compliance_indicators,
                "processing_confidence": reg.processing_confidence
            }
        
        return enhanced_mappings
    
    def _extract_intent_patterns(self, requirement_summary: str) -> List[str]:
        """Extract key intent patterns from requirement summary"""
        # Extract key regulatory concepts
        patterns = []
        
        # Common regulatory terms
        regulatory_terms = {
            'internal control': ['internal control', 'control structure', 'control procedures'],
            'reporting': ['reporting', 'report', 'disclose', 'disclosure'],
            'assessment': ['assessment', 'evaluate', 'review', 'test'],
            'anti-money laundering': ['anti-money laundering', 'AML', 'suspicious activity'],
            'customer identification': ['customer identification', 'know your customer', 'KYC'],
            'brokered deposits': ['brokered deposit', 'deposit broker', 'deposit arrangement'],
            'consumer protection': ['consumer protection', 'unfair practice', 'deceptive practice']
        }
        
        text_lower = requirement_summary.lower()
        for concept, terms in regulatory_terms.items():
            if any(term in text_lower for term in terms):
                patterns.extend(terms)
        
        # Extract specific nouns and regulatory actions
        regulatory_actions = re.findall(r'\b(?:maintain|establish|implement|document|test|evaluate|monitor|report|disclose)\w*\b', text_lower)
        patterns.extend(regulatory_actions)
        
        return list(set(patterns))  # Remove duplicates
    
    def _extract_compliance_indicators(self, full_text: str) -> List[str]:
        """Extract regex patterns for compliance detection"""
        indicators = []
        
        # Extract key phrases and convert to regex patterns
        key_phrases = re.findall(r'\b(?:must|shall|required?|establish|maintain|implement|ensure)\s+[^.]{10,50}', full_text, re.IGNORECASE)
        
        for phrase in key_phrases:
            # Convert to regex pattern
            pattern = re.sub(r'\s+', r'\\s+', phrase.lower().strip())
            indicators.append(pattern)
        
        # Add common compliance patterns
        indicators.extend([
            r'internal.*control',
            r'risk.*management',
            r'anti.*money.*laundering',
            r'customer.*identification',
            r'suspicious.*activity',
            r'consumer.*protection',
            r'brokered.*deposit'
        ])
        
        return indicators
    
    def _create_section_key(self, citation_id: str) -> str:
        """Create a clean section key from citation"""
        # Convert citation to a clean key
        key = re.sub(r'[^\w\s]', '', citation_id.lower())
        key = re.sub(r'\s+', '_', key.strip())
        return key[:50]  # Limit length
    
    def _format_category_title(self, category_key: str) -> str:
        """Format category key into readable title"""
        parts = category_key.split('_')
        formatted = []
        
        for part in parts:
            if part.upper() in ['SEC', 'FDIC', 'CFPB', 'AML']:
                formatted.append(part.upper())
            else:
                formatted.append(part.title())
        
        return ' '.join(formatted)

def get_enhanced_vector_store():
    """Initialize vector store with enhanced regulatory content"""
    if not LANGCHAIN_IMPORTS_OK or not all([Chroma, OllamaEmbeddings]):
        print("Warning: Vector store components not available. Using enhanced mock store.")
        return EnhancedMockVectorStore()

    try:
        # Initialize the enhanced ingestion pipeline
        ingestion = EnhancedRegulatoryIngestion()
        processed_regulations = ingestion.process_all_regulations()
        
        # Create enhanced mappings
        enhanced_mappings = ingestion.create_enhanced_mappings(processed_regulations)
        
        # Ensure the database directory exists
        persist_dir = "./chroma_db"
        os.makedirs(persist_dir, exist_ok=True)

        embeddings = OllamaEmbeddings(model="llama3")
        vector_store = Chroma(
            embedding_function=embeddings, 
            persist_directory=persist_dir
        )

        # Check if vector store needs population
        try:
            collection_count = len(vector_store.get()["ids"]) if hasattr(vector_store, "get") else 0
        except:
            collection_count = 0

        if collection_count == 0:
            print("🔄 Populating vector store with enhanced regulatory documents...")
            ingest_enhanced_documents_to_store(vector_store, processed_regulations)
        else:
            print(f"✅ Vector store already contains {collection_count} documents")

        # Store enhanced mappings for later use
        vector_store.enhanced_mappings = enhanced_mappings
        return vector_store
        
    except Exception as e:
        print(f"❌ Error initializing enhanced vector store: {e}")
        return EnhancedMockVectorStore()

def ingest_enhanced_documents_to_store(vector_store, processed_regulations: List[ProcessedRegulation]):
    """Add enhanced processed documents to vector store"""
    if not LANGCHAIN_IMPORTS_OK or not RecursiveCharacterTextSplitter:
        print("⚠️ Text splitter not available, skipping ingestion")
        return

    # Initialize text splitter
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,  # Smaller chunks for more precise matching
        chunk_overlap=150,
        length_function=len,
        is_separator_regex=False,
    )

    documents_to_ingest = []
    metadatas = []

    for reg in processed_regulations:
        # Create chunks from full regulation text
        chunks = text_splitter.split_text(reg.full_text_for_embedding)
        
        for i, chunk in enumerate(chunks):
            documents_to_ingest.append(chunk)
            metadatas.append({
                "citation": reg.citation_id,
                "requirement_summary": reg.requirement_summary,
                "source_url": reg.source_url,
                "category": reg.regulation_category,
                "chunk_id": i,
                "processing_confidence": reg.processing_confidence
            })

    # Add documents to the vector store
    print(f"📥 Adding {len(documents_to_ingest)} enhanced document chunks to vector store...")
    try:
        vector_store.add_texts(documents_to_ingest, metadatas=metadatas)
        print("✅ Enhanced documents successfully added to vector store")
    except Exception as e:
        print(f"❌ Error adding enhanced documents to vector store: {e}")

class EnhancedMockVectorStore:
    """Enhanced mock vector store with processed regulatory content"""

    def __init__(self):
        ingestion = EnhancedRegulatoryIngestion()
        self.processed_regulations = ingestion.process_all_regulations()
        self.enhanced_mappings = ingestion.create_enhanced_mappings(self.processed_regulations)
        print("📝 Enhanced mock vector store initialized with LLM-processed regulatory content")

    def as_retriever(self):
        return EnhancedMockRetriever(self.processed_regulations)

    def add_texts(self, texts, metadatas=None):
        print(f"📝 Mock: Would add {len(texts)} enhanced texts to vector store")

class EnhancedMockRetriever:
    """Enhanced mock retriever with processed content"""

    def __init__(self, processed_regulations: List[ProcessedRegulation]):
        self.processed_regulations = processed_regulations

    def invoke(self, query):
        # Return processed regulations as mock retrieval
        if Document:  # If langchain Document is available
            return [
                Document(
                    page_content=reg.full_text_for_embedding,
                    metadata={
                        "citation": reg.citation_id,
                        "source": reg.regulation_category,
                        "url": reg.source_url,
                        "requirement": reg.requirement_summary
                    }
                )
                for reg in self.processed_regulations
            ]
        else:
            # Return simple dict format if Document class not available
            return [
                {
                    "page_content": reg.full_text_for_embedding,
                    "metadata": {
                        "citation": reg.citation_id,
                        "source": reg.regulation_category,
                        "url": reg.source_url,
                        "requirement": reg.requirement_summary
                    }
                }
                for reg in self.processed_regulations
            ]

if __name__ == "__main__":
    # Test the enhanced ingestion pipeline
    ingestion = EnhancedRegulatoryIngestion()
    processed_regulations = ingestion.process_all_regulations()
    enhanced_mappings = ingestion.create_enhanced_mappings(processed_regulations)
    
    print("\n" + "="*80)
    print("ENHANCED REGULATORY MAPPINGS CREATED")
    print("="*80)
    
    for category, data in enhanced_mappings.items():
        print(f"\n📋 Category: {data['title']}")
        for section_key, section_data in data['sections'].items():
            print(f"  🏛️  Citation: {section_data['citation']}")
            print(f"  📝 Requirement: {section_data['text'][:100]}...")
            print(f"  🎯 Confidence: {section_data['processing_confidence']:.2f}")
            print(f"  🔍 Intent Patterns: {len(section_data['intent_patterns'])}")
            print(f"  ⚡ Compliance Indicators: {len(section_data['compliance_indicators'])}")
            print()
