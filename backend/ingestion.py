## ingestion.py

import os
import tempfile
from typing import Dict, List

import requests
from bs4 import BeautifulSoup

# Langchain imports with updated imports and error handling
try:
    from langchain_community.document_loaders import WebBaseLoader
    from langchain_community.vectorstores import Chroma

    # Updated import for Ollama embeddings
    try:
        from langchain_community.embeddings import OllamaEmbeddings
    except ImportError:
        # Fallback for older versions
        from langchain.embeddings import OllamaEmbeddings

    from langchain.schema import Document
    from langchain.text_splitter import RecursiveCharacterTextSplitter

    LANGCHAIN_IMPORTS_OK = True
except ImportError as e:
    print(f"Warning: Some langchain components not available: {e}")
    # Fallback to basic functionality
    WebBaseLoader = None
    Chroma = None
    OllamaEmbeddings = None
    RecursiveCharacterTextSplitter = None
    Document = None
    LANGCHAIN_IMPORTS_OK = False

# Define a list of sample regulatory content
# In production, you would scrape from actual regulatory websites
SAMPLE_REGULATORY_CONTENT = [
    {
        "content": """
        Securities and Exchange Commission Regulation:
        All public companies must maintain accurate financial records and provide quarterly reports.
        Companies must disclose material information that could affect stock prices.
        Internal controls must be documented and tested annually.
        Risk management policies must be clearly defined and implemented.
        """,
        "source": "SEC Regulations - Financial Reporting",
        "url": "https://www.sec.gov/regulations",
    },
    {
        "content": """
        FDIC Banking Regulations:
        Banks must maintain minimum capital ratios as defined by Basel III standards.
        Customer deposits must be protected and insured up to regulatory limits.
        Anti-money laundering (AML) procedures must be implemented and regularly updated.
        Know Your Customer (KYC) policies must verify customer identities.
        Credit risk assessments must be conducted for all lending activities.
        """,
        "source": "FDIC Banking Rules",
        "url": "https://www.fdic.gov/regulations/laws/rules",
    },
    {
        "content": """
        Consumer Financial Protection Bureau (CFPB) Requirements:
        Financial institutions must provide clear and understandable terms and conditions.
        Fair lending practices must be maintained across all customer segments.
        Consumer complaints must be tracked and resolved in a timely manner.
        Data privacy and security measures must protect consumer information.
        Regular audits must ensure compliance with consumer protection laws.
        """,
        "source": "CFPB Consumer Protection",
        "url": "https://www.consumerfinance.gov/policy-compliance/",
    },
]


def scrape_documents(urls: List[str] = None) -> List[Dict]:
    """
    Scrapes or loads regulatory documents.
    For demo purposes, returns sample content.
    In production, implement actual web scraping.
    """
    print("Loading regulatory documents...")

    # For now, return sample content instead of scraping
    # This avoids network dependencies and potential scraping issues
    documents = []

    for sample in SAMPLE_REGULATORY_CONTENT:
        documents.append(
            {
                "content": sample["content"].strip(),
                "source": sample["source"],
                "metadata": {"url": sample["url"]},
            }
        )

    print(f"Loaded {len(documents)} regulatory documents")
    return documents


def get_vector_store():
    """
    Initializes and returns a ChromaDB vector store.
    If components are not available, returns a mock store.
    """
    if not LANGCHAIN_IMPORTS_OK or not all([Chroma, OllamaEmbeddings]):
        print("Warning: Vector store components not available. Using mock store.")
        return MockVectorStore()

    try:
        # Ensure the database directory exists
        persist_dir = "./chroma_db"
        os.makedirs(persist_dir, exist_ok=True)

        embeddings = OllamaEmbeddings(model="llama3")
        vector_store = Chroma(
            embedding_function=embeddings, persist_directory=persist_dir
        )

        # Check if vector store is empty and populate it
        try:
            collection_count = (
                len(vector_store.get()["ids"]) if hasattr(vector_store, "get") else 0
            )
        except:
            collection_count = 0

        if collection_count == 0:
            print("Vector store is empty. Populating with regulatory documents...")
            ingest_documents_to_existing_store(vector_store)
        else:
            print(f"Vector store already contains {collection_count} documents")

        return vector_store
    except Exception as e:
        print(f"Error initializing vector store: {e}")
        return MockVectorStore()


def ingest_documents_to_existing_store(vector_store):
    """Add documents to an existing vector store"""
    if not LANGCHAIN_IMPORTS_OK or not RecursiveCharacterTextSplitter:
        print("⚠️ Text splitter not available, skipping ingestion")
        return

    raw_documents = scrape_documents()

    if not raw_documents:
        print("⚠️ No documents to ingest")
        return

    # Initialize text splitter
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        is_separator_regex=False,
    )

    documents_to_ingest = []
    metadatas = []

    for doc in raw_documents:
        chunks = text_splitter.split_text(doc["content"])
        for i, chunk in enumerate(chunks):
            documents_to_ingest.append(chunk)
            metadatas.append(
                {"source": doc["source"], "chunk_id": i, **doc.get("metadata", {})}
            )

    # Add documents to the vector store
    print(
        f"📥 Adding {len(documents_to_ingest)} document chunks to the vector store..."
    )
    try:
        vector_store.add_texts(documents_to_ingest, metadatas=metadatas)
        print("✅ Documents successfully added to vector store")
    except Exception as e:
        print(f"❌ Error adding documents to vector store: {e}")


def ingest_documents_to_vector_store():
    """
    Main function to run the ingestion pipeline.
    """
    vector_store = get_vector_store()
    if hasattr(vector_store, "add_texts"):
        ingest_documents_to_existing_store(vector_store)
    else:
        print("🔍 Using mock vector store - no ingestion needed")


class MockVectorStore:
    """Mock vector store for when Chroma is not available"""

    def __init__(self):
        self.documents = SAMPLE_REGULATORY_CONTENT
        print("🔍 Mock vector store initialized with sample regulatory content")

    def as_retriever(self):
        return MockRetriever(self.documents)

    def add_texts(self, texts, metadatas=None):
        print(f"🔍 Mock: Would add {len(texts)} texts to vector store")


class MockRetriever:
    """Mock retriever for testing purposes"""

    def __init__(self, documents):
        self.documents = documents

    def invoke(self, query):
        # Return all documents as mock retrieval
        if Document:  # If langchain Document is available
            return [
                Document(
                    page_content=doc["content"], metadata={"source": doc["source"]}
                )
                for doc in self.documents
            ]
        else:
            # Return simple dict format if Document class not available
            return [
                {"page_content": doc["content"], "metadata": {"source": doc["source"]}}
                for doc in self.documents
            ]

    def __or__(self, other):
        # Support for chain operations
        return lambda x: other(self.invoke(x))


if __name__ == "__main__":
    ingest_documents_to_vector_store()
