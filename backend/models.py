from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

# Handle both relative and direct imports
try:
    from .database import Base
except ImportError:
    from database import Base


class ComplianceReport(Base):
    __tablename__ = "compliance_reports"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    user_query = Column(Text)
    report_content = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String, default="completed")


class RegulatoryDocument(Base):
    __tablename__ = "regulatory_documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    source_url = Column(String)
    content = Column(Text)
    document_type = Column(String)  # e.g., "SEC", "FDIC", "CFPB"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)


class UserDocument(Base):
    __tablename__ = "user_documents"

    id = Column(Integer, primary_key=True, index=True)
    original_filename = Column(String, nullable=False)
    content = Column(Text)
    file_type = Column(String)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    processed = Column(Boolean, default=False)
