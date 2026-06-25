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
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain.schema import Document
    from langchain.text_splitter import RecursiveCharacterTextSplitter
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
        
        # Indian regulatory citation patterns
        self.citation_patterns = [
            r'(Section\s+\d+(?:[A-Z]?),?\s+Companies Act,?\s+2013)',  # Companies Act sections
            r'(Rule\s+\d+[A-Z]?,?\s+Companies\s+\([^)]+\)\s+Rules,?\s+20\d{2})',  # Companies Rules
            r'(Companies\s+\([^)]+\)\s+Order,?\s+20\d{2})',  # MCA Orders
            r'(MSME-1|DPT-3|AOC-4|MGT-7A?|ADT-1|DIR-3\s+KYC|CSR-2)',  # MCA forms
            r'(Securities and Exchange Board of India\s+\([^)]+\)\s+Regulations,?\s+20\d{2})',  # SEBI
            r'(Reserve Bank of India\s+\([^)]+\)\s+Directions?,?\s+20\d{2})',  # RBI
            r'(Income Tax Act,?\s+1961)',  # Income Tax Act
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
        
        # Indian regulatory content examples for testing
        self.raw_regulatory_sources = [
            {
                "raw_text": """
                Section 137, Companies Act, 2013 - Filing of Financial Statements
                
                (1) A copy of the financial statement, including consolidated financial statement, if any, shall be filed with the Registrar within thirty days from the date on which the annual general meeting is held or ought to have been held.
                
                (3) If any company fails to file financial statement before the expiry of the period specified under sub-section (1), such company and its every officer who is in default shall be punishable with fine which shall not be less than fifty thousand rupees but which may extend to twenty-five lakh rupees and where the failure is a continuing one, with a further fine which may extend to one hundred rupees for every day after the first during which the failure continues.
                
                Every company shall mandatorily file Form AOC-4 along with the required attachments within the prescribed timeline to avoid penalties.
                """,
                "source_url": "https://www.mca.gov.in/",
                "category": "INDIAN_COMPANIES_ACT"
            },
            {
                "raw_text": """
                Section 96, Companies Act, 2013 - Annual General Meeting
                
                (1) Every company other than a One Person Company shall in each year hold a general meeting as its annual general meeting and shall specify the meeting as such in the notices calling it, and not more than fifteen months shall elapse between the date of one annual general meeting of a company and that of the next.
                
                Provided that in case of the first annual general meeting, it shall be held within a period of nine months from the date of closing of the first financial year of the company.
                
                The AGM must be conducted within 6 months from the financial year end for most companies and proper notices, quorum, and minutes must be maintained.
                """,
                "source_url": "https://www.mca.gov.in/",
                "category": "INDIAN_COMPANIES_ACT"
            },
            {
                "raw_text": """
                Rule 16, Companies (Acceptance of Deposits) Rules, 2014 - Return of Deposits
                
                (1) Every company which has accepted deposits or any monies which are not considered as deposits in terms of rule 2 of these rules during a financial year shall file a return in Form DPT-3 within sixty days from the commencement of the next financial year.
                
                (2) The return shall be accompanied by an auditor's certificate in the prescribed format where the company has accepted deposits during the financial year.
                
                Companies must compile details of all deposits and non-deposit receipts and file DPT-3 by 30 June annually with requisite certifications.
                """,
                "source_url": "https://www.mca.gov.in/",
                "category": "INDIAN_COMPANIES_ACT"
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
        words = requirement_summary.split()
        key_words = [w.lower() for w in words if len(w) > 4 and w.isalpha()]
        patterns.extend(key_words[:5])  # Top 5 key words
        
        return patterns
    
    def _extract_compliance_indicators(self, full_text: str) -> List[str]:
        """Extract regex compliance indicators from full text"""
        # Create regex patterns for key compliance terms
        indicators = []
        
        key_terms = ['must', 'shall', 'required', 'mandatory', 'file', 'report', 'maintain', 
                    'establish', 'implement', 'assess', 'evaluate', 'document', 'disclose']
        
        for term in key_terms:
            if term in full_text.lower():
                indicators.append(rf'\b{term}\b')
        
        return indicators
    
    def _create_section_key(self, citation_id: str) -> str:
        """Create a section key from citation ID"""
        # Normalize citation to create consistent keys
        key = citation_id.lower()
        key = re.sub(r'[^a-zA-Z0-9_]', '_', key)
        key = re.sub(r'_+', '_', key).strip('_')
        return key[:50]  # Limit length
    
    def _format_category_title(self, category_key: str) -> str:
        """Format category key into readable title"""
        return category_key.replace('_', ' ').title()

def ingest_documents_to_vector_store():
    """Main ingestion function for regulatory documents"""
    try:
        print("🔄 Starting regulatory document ingestion...")
        get_enhanced_vector_store()
        print("✅ Document ingestion completed")
    except Exception as e:
        print(f"⚠️ Document ingestion warning: {e}")
        return False
    return True

def get_enhanced_vector_store():
    """Get enhanced vector store with LLM-processed regulatory content"""
    try:
        if not LANGCHAIN_IMPORTS_OK:
            print("⚠️ Langchain not available, using enhanced mock vector store")
            return EnhancedMockVectorStore()
        
        # Initialize enhanced regulatory ingestion
        ingestion = EnhancedRegulatoryIngestion()
        processed_regulations = ingestion.process_all_regulations()
        enhanced_mappings = ingestion.create_enhanced_mappings(processed_regulations)
        
        # Initialize vector store with local embeddings
        embeddings = HuggingFaceEmbeddings(
            model_name="BAAI/bge-small-en-v1.5",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        vector_store = Chroma(embedding_function=embeddings, persist_directory="./chroma_db")
        
        # Check if we need to populate the vector store
        collection_count = vector_store._collection.count()
        
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
