# FinReg - Financial Regulatory Compliance API

A FastAPI-based system for regulatory compliance analysis and document processing.

## 🏗️ Architecture

- **FastAPI** - Modern web framework for APIs
- **PostgreSQL** - Database for storing reports and documents  
- **ChromaDB** - Vector database for regulatory document search
- **Unstructured** - Document processing and text extraction
- **ReportLab** - PDF report generation

## 📁 Project Structure

```
FinReg/
├── backend/
│   ├── main.py          # FastAPI application
│   ├── models.py        # SQLAlchemy database models
│   ├── database.py      # Database configuration
│   └── ingestion.py     # Document ingestion pipeline
├── requirements.txt     # Python dependencies
├── docker-compose.yml   # Docker services configuration
├── Dockerfile          # Container build instructions
├── startup.py          # Application initialization script
└── .env                # Environment configuration
```

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)

### Running with Docker

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd FinReg
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start the services**
   ```bash
   docker-compose up -d
   ```

4. **Check service health**
   ```bash
   curl http://localhost:8000/health
   ```

### Running Locally

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start PostgreSQL** (using Docker)
   ```bash
   docker-compose up db -d
   ```

3. **Run the application**
   ```bash
   python startup.py
   ```

## 🔧 API Endpoints

### Core Endpoints

- **GET /** - API status and information
- **GET /health** - Health check with database status
- **POST /generate-report/** - Generate compliance report from uploaded document

### Generate Report

Upload a document and receive a compliance analysis report:

```bash
curl -X POST "http://localhost:8000/generate-report/" \
     -H "accept: application/pdf" \
     -H "Content-Type: multipart/form-data" \
     -F "user_document=@your-policy-document.txt" \
     -F "user_query=Analyze compliance gaps" \
     --output compliance_report.pdf
```

## 📊 Database Schema

### ComplianceReport
- `id` - Primary key
- `filename` - Original document filename
- `user_query` - Analysis query provided
- `report_content` - Generated report text
- `created_at` - Timestamp
- `status` - Processing status

### RegulatoryDocument
- `id` - Primary key
- `title` - Document title
- `source_url` - Original source URL
- `content` - Document text content
- `document_type` - Regulatory agency (SEC, FDIC, CFPB)
- `created_at` - Timestamp
- `is_active` - Active status

### UserDocument
- `id` - Primary key
- `original_filename` - Uploaded filename
- `content` - Extracted text content
- `file_type` - Document type
- `uploaded_at` - Timestamp
- `processed` - Processing status

## 🔍 Features

### Document Processing
- Supports multiple file formats (text, PDF, Word, etc.)
- Automatic text extraction using Unstructured library
- Fallback processing for unsupported formats

### Compliance Analysis
- Mock regulatory analysis against SEC, FDIC, and CFPB requirements
- Structured compliance reporting
- PDF report generation with professional formatting

### Vector Search (Planned)
- ChromaDB integration for semantic document search
- Ollama embeddings for local processing
- RAG pipeline for regulatory document retrieval

## 🛠️ Development

### Local Development Setup

1. **Set up virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate     # Windows
   ```

2. **Install development dependencies**
   ```bash
   pip install -r requirements.txt
   pip install pytest black isort mypy
   ```

3. **Run tests**
   ```bash
   pytest
   ```

4. **Format code**
   ```bash
   black backend/
   isort backend/
   ```

### Docker Development

**Rebuild and restart:**
```bash
docker-compose up --build -d
```

**View logs:**
```bash
docker-compose logs -f api
```

**Access database:**
```bash
docker-compose exec db psql -U finreg -d finreg_db
```

## 🔧 Configuration

### Environment Variables (.env)

```env
# Database
DATABASE_URL=postgresql://finreg:finreg123@db:5432/finreg_db

# API
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=False

# Application
APP_NAME=FinReg API
VERSION=2.0.0
```

### Docker Compose Profiles

**Standard services:**
```bash
docker-compose up -d
```

**Include pgAdmin:**
```bash
docker-compose --profile admin up -d
```

## 📝 API Documentation

Once running, visit:
- **Interactive API Docs:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## 🔍 Monitoring

### Health Checks
- Application: http://localhost:8000/health
- Database connectivity check included
- Docker health check configured

### Database Administration
- pgAdmin: http://localhost:5050 (with admin profile)
  - Email: admin@finreg.local  
  - Password: admin123

## 🚨 Troubleshooting

### Common Issues

**Database connection failed:**
```bash
docker-compose logs db
# Check if PostgreSQL is running and accepting connections
```

**Document processing errors:**
```bash
# Ensure unstructured library is properly installed
pip install "unstructured[local-inference]"
```

**Port already in use:**
```bash
# Change ports in docker-compose.yml or stop conflicting services
docker-compose down
lsof -ti:8000 | xargs kill -9
```

### Reset Everything

```bash
docker-compose down -v
docker system prune -f
docker-compose up --build -d
```

## 📄 License

This project is licensed under the MIT License.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📞 Support

For questions or issues:
- Check the [troubleshooting section](#-troubleshooting)
- Open an issue on GitHub
- Review API documentation at `/docs`