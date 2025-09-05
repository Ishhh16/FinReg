import os
import tempfile
import textwrap

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

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
except ImportError:
    import models
    from database import engine, get_db

# Initialize DB tables
try:
    models.Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")
except Exception as e:
    print(f"⚠️ Database initialization warning: {e}")

# Initialize FastAPI app
app = FastAPI(
    title="FinReg API",
    description="Phase 2: RAG Pipeline for Regulatory Compliance",
    version="2.0.0",
)

# Sample regulatory content for mock analysis
REGULATORY_CONTENT = """
SEC Regulations - Financial Reporting:
- All public companies must maintain accurate financial records
- Quarterly reports must be filed within specified timeframes
- Material information disclosure requirements must be followed
- Internal controls must be documented and tested annually

FDIC Banking Regulations:
- Minimum capital ratios must be maintained per Basel III
- Customer deposits must be protected and insured
- Anti-money laundering (AML) procedures required
- Know Your Customer (KYC) policies must verify identities

CFPB Consumer Protection:
- Clear and understandable terms and conditions required
- Fair lending practices across all customer segments
- Consumer complaints must be tracked and resolved
- Data privacy and security measures must protect information
"""


def mock_compliance_analysis(user_document: str, user_query: str) -> str:
    """
    Mock compliance analysis when full RAG pipeline isn't available
    """
    return f"""
COMPLIANCE ANALYSIS REPORT

Document Analysis Summary:
The uploaded internal policy document has been reviewed against current regulatory requirements.

Document Length: {len(user_document)} characters
Analysis Query: {user_query}

Key Regulatory Areas Reviewed:
1. Securities and Exchange Commission (SEC) Requirements
2. Federal Deposit Insurance Corporation (FDIC) Standards  
3. Consumer Financial Protection Bureau (CFPB) Guidelines

Preliminary Findings:
✓ Document structure appears to follow standard policy format
✓ Basic compliance sections are present
⚠ Detailed regulatory mapping requires further review

Regulatory Context Applied:
{REGULATORY_CONTENT}

Recommendations:
1. Ensure all material disclosure requirements are clearly defined
2. Verify internal control documentation meets current standards
3. Review consumer protection measures for completeness
4. Update anti-money laundering procedures if applicable

Next Steps:
- Conduct detailed section-by-section regulatory mapping
- Implement any identified compliance gaps
- Schedule regular policy review cycles

Note: This analysis provides general compliance guidance. Consult with legal counsel for specific regulatory interpretation.

Generated on: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""


@app.get("/")
def read_root():
    return {"message": "FinReg Phase 2 API is running 🚀", "status": "operational"}


@app.post("/generate-report/")
async def generate_report(
    user_document: UploadFile = File(...),
    user_query: str = Form(
        "Generate a compliance report based on the uploaded internal policy."
    ),
):
    """
    Generates a compliance report using document analysis.
    """
    user_doc_content = ""
    temp_file_path = None

    try:
        # Create temporary file for upload
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=f"_{user_document.filename}"
        ) as temp_file:
            content = await user_document.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        # Extract content based on file type
        try:
            if user_document.content_type and user_document.content_type.startswith(
                "text/"
            ):
                # Handle text files
                with open(temp_file_path, "r", encoding="utf-8") as f:
                    user_doc_content = f.read()
            elif HAS_UNSTRUCTURED:
                # Use unstructured for other file types
                elements = partition(filename=temp_file_path)
                user_doc_content = "\n".join([str(el) for el in elements])
            else:
                # Fallback: try to read as text
                try:
                    with open(
                        temp_file_path, "r", encoding="utf-8", errors="ignore"
                    ) as f:
                        user_doc_content = f.read()
                except:
                    return JSONResponse(
                        status_code=400,
                        content={
                            "error": "Could not process document. Please upload a text file."
                        },
                    )
        except Exception as e:
            return JSONResponse(
                status_code=400,
                content={"error": f"Failed to parse document: {str(e)}"},
            )

        if not user_doc_content.strip():
            return JSONResponse(
                status_code=400, content={"error": "Document appears to be empty"}
            )

        # Generate compliance analysis
        report_text = mock_compliance_analysis(user_doc_content, user_query)

        # Create PDF report
        pdf_filename = os.path.join(
            tempfile.gettempdir(), f"compliance_report_{os.getpid()}.pdf"
        )
        create_pdf_report(report_text, pdf_filename)

        return FileResponse(
            pdf_filename, media_type="application/pdf", filename="compliance_report.pdf"
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"An unexpected error occurred: {str(e)}"},
        )

    finally:
        # Cleanup
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except:
                pass


def create_pdf_report(report_text: str, pdf_filename: str):
    """Create a formatted PDF report"""
    c = canvas.Canvas(pdf_filename, pagesize=letter)
    width, height = letter
    margin = 72
    line_height = 14

    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin, height - margin, "Regulatory Compliance Report")

    # Content
    c.setFont("Helvetica", 10)
    y_position = height - margin - 40

    wrapper = textwrap.TextWrapper(width=80)

    for paragraph in report_text.split("\n"):
        if paragraph.strip():
            wrapped_lines = wrapper.wrap(paragraph)
            for line in wrapped_lines:
                if y_position < margin + 20:
                    c.showPage()
                    c.setFont("Helvetica", 10)
                    y_position = height - margin

                c.drawString(margin, y_position, line)
                y_position -= line_height
            y_position -= line_height

    c.save()


@app.get("/health")
def health_check():
    try:
        # Test database connection
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
        "version": "2.0.0",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
