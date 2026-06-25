import fitz  # PyMuPDF

def extract_text(file_bytes: bytes, filename: str = "") -> str:
    """Extract text from PDF bytes or decode text file bytes."""
    # Check if filename suggests a plain text file or if we can decode it directly
    if filename.lower().endswith('.txt'):
        try:
            return file_bytes.decode('utf-8')
        except UnicodeDecodeError:
            pass
            
    # Try parsing as PDF
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    except Exception as pdf_error:
        # Fallback to UTF-8 decoding for text-based formats
        try:
            return file_bytes.decode('utf-8', errors='ignore')
        except Exception:
            raise ValueError(f"Failed to extract text from file. PDF error: {pdf_error}")

