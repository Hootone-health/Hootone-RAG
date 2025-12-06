# RAG Hootone API

A FastAPI-based REST API service for secure PDF file uploads with rate limiting, metadata management, and PostgreSQL integration. The API supports streamed file uploads without buffering, ensuring efficient memory usage for large files.

## Table of Contents

- [Features](#features)
- [Technology Stack](#technology-stack)
- [Prerequisites](#prerequisites)
- [Installation & Setup](#installation--setup)
- [Configuration](#configuration)
- [Database Setup](#database-setup)
- [API Documentation](#api-documentation)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Usage Examples](#usage-examples)
- [What We Built](#what-we-built)

## Features

- **Streamed PDF Uploads**: Efficient file handling using request streaming (no buffering)
- **Rate Limiting**: Leaky bucket algorithm to prevent server overload (capacity: 2 requests, leak rate: 0.016 req/sec)
- **File Validation**: 
  - PDF files only
  - Maximum file size: 100 MB
  - Case-sensitive duplicate filename detection
- **Metadata Management**: 
  - Filesystem-based metadata storage
  - PostgreSQL database synchronization
  - Automatic unique ID generation (UUID)
- **Error Handling**: Comprehensive error responses with appropriate HTTP status codes
- **Health Monitoring**: Health check endpoint for service status

## Technology Stack

- **Framework**: FastAPI 0.115.0+
- **Language**: Python 3.13+
- **Database**: PostgreSQL 14 (via Docker)
- **Database Driver**: psycopg3 (psycopg[binary,pool])
- **HTTP Client**: httpx 0.28.1+
- **Validation**: Pydantic 2.7.0+
- **Testing**: pytest 8.3.0+
- **Package Manager**: uv
- **Server**: Uvicorn with standard extensions

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.13+** - [Download Python](https://www.python.org/downloads/)
- **Docker & Docker Compose** - [Install Docker](https://docs.docker.com/get-docker/)
- **uv** (Python package manager) - [Install uv](https://github.com/astral-sh/uv)
- **Git** - For cloning the repository

## Installation & Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd rag-hootone
```

### 2. Install Dependencies

Using `uv` (recommended):

```bash
uv sync
```

Or using traditional pip:

```bash
pip install -r requirements.txt
```

### 3. Set Up Environment Variables

Create a `.env` file in the project root directory:

```env
# PostgreSQL Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=app_db
DB_USER=admin
DB_PASSWORD=admin

# Docker Compose Environment Variables
POSTGRES_DB=app_db
POSTGRES_USER=admin
POSTGRES_PASSWORD=admin
POSTGRES_PORT=5432

# PgAdmin Configuration (optional)
PGADMIN_DEFAULT_EMAIL=admin@example.com
PGADMIN_DEFAULT_PASSWORD=admin
PGADMIN_PORT=5050
```

### 4. Start PostgreSQL Database

Using Docker Compose:

```bash
docker-compose up -d
```

This will start:
- PostgreSQL database on port 5432
- PgAdmin (database management UI) on port 5050 (if configured)

### 5. Create Database Schema

Connect to PostgreSQL and create the metadata table:

```sql
CREATE TABLE IF NOT EXISTS metadata (
    unique_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    file_name VARCHAR(255) NOT NULL,
    storage_path TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_metadata_unique_id ON metadata(unique_id);
```

### 6. Start the API Server

```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API Base URL**: `http://localhost:8000`
- **Interactive API Docs**: `http://localhost:8000/docs`
- **Alternative Docs**: `http://localhost:8000/redoc`

## Configuration

### Environment Variables

The application uses the following environment variables (with defaults):

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_HOST` | `localhost` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_NAME` | `app_db` | Database name |
| `DB_USER` | `admin` | Database user |
| `DB_PASSWORD` | `admin` | Database password |

### File Storage Paths

By default, files are stored at:
- **PDF Storage**: `data/uploads/PDF/`
- **Metadata Storage**: `data/uploads/Metadata/`

These directories are automatically created on first upload.

### Rate Limiting Configuration

The leaky bucket rate limiter is configured with:
- **Capacity**: 2 requests
- **Leak Rate**: 0.016 requests per second (~1 request per minute)

These values can be adjusted in `src/models/api_models.py` in the `LeakyBucketConfig` class.

## Database Setup

### Manual Setup

If you're not using Docker Compose, you can set up PostgreSQL manually:

1. Install PostgreSQL 14+
2. Create a database:
   ```sql
   CREATE DATABASE app_db;
   ```
3. Create the metadata table (see step 5 in Installation & Setup)

### Using PgAdmin

1. Access PgAdmin at `http://localhost:5050`
2. Login with credentials from your `.env` file
3. Connect to the PostgreSQL server
4. Navigate to `app_db` database
5. Execute the table creation SQL

## API Documentation

### Base URL

```
http://localhost:8000
```

### Endpoints

#### 1. Health Check

Check if the API is running.

**Endpoint**: `GET /health`

**Response**:
```json
{
  "status": "ok"
}
```

**Status Code**: `200 OK`

---

#### 2. Rate Limit Status

Get current rate limit status. This endpoint also consumes a rate limit token.

**Endpoint**: `GET /rate-limit`

**Response**:
```json
{
  "allowed": true,
  "reason": null,
  "status_code": 200,
  "bucket_capacity": 2,
  "bucket_leak_rate": 0.016
}
```

**Status Codes**:
- `200 OK`: Request allowed
- `503 Service Unavailable`: Rate limit exceeded

---

#### 3. Upload PDF

Upload a PDF file with streaming support.

**Endpoint**: `POST /upload/pdf`

**Headers**:
- `x-file-name`: The name of the PDF file (required)
- `Content-Type`: `application/pdf` (optional but recommended)
- `Content-Length`: File size in bytes (optional)

**Request Body**: Raw PDF file bytes

**Success Response** (`201 Created`):
```json
{
  "message": "Upload successful",
  "file_name": "example.pdf",
  "unique_id": "550e8400-e29b-41d4-a716-446655440000",
  "stored_at": "C:\\Users\\Admin\\Desktop\\rag-hootone\\data\\uploads\\PDF\\example.pdf",
  "db_rows_inserted": 1
}
```

**Error Responses**:

| Status Code | Description | Response |
|-------------|-------------|----------|
| `400 Bad Request` | Missing `x-file-name` header | `{"message": "Missing file name header: x-file-name", "status_code": 400}` |
| `409 Conflict` | Duplicate filename (case-sensitive) | `{"message": "File already Exist!", "status_code": 409}` |
| `413 Request Entity Too Large` | File exceeds 100 MB limit | `{"message": "Cannot be Upload! Max File size is 100 MB", "status_code": 413}` |
| `415 Unsupported Media Type` | Non-PDF file type | `{"message": "Only PDF files are allowed", "status_code": 415}` |
| `503 Service Unavailable` | Rate limit exceeded | `{"message": "Server is Busy", "status_code": 503}` |
| `500 Internal Server Error` | Unexpected server error | `{"message": "Internal Server Error", "status_code": 500}` |

## Project Structure

```
rag-hootone/
├── src/
│   ├── api/
│   │   └── main.py              # FastAPI application and endpoints
│   ├── models/
│   │   └── api_models.py        # Pydantic models and constants
│   └── services/
│       ├── file_handler.py      # PDF upload handling and validation
│       └── db_manager.py        # PostgreSQL metadata operations
├── data/
│   └── uploads/
│       ├── PDF/                 # Stored PDF files
│       └── Metadata/            # Metadata text files
├── tests/
│   ├── test_api_upload.py       # API endpoint tests
│   └── test_files/              # Test PDF files
├── config/
│   └── logging_config.yaml      # Logging configuration
├── db/
│   └── postgres_data/           # PostgreSQL data (Docker volume)
├── docker-compose.yaml          # Docker services configuration
├── pyproject.toml               # Project dependencies and metadata
├── uv.lock                      # Locked dependency versions
├── requirements.txt             # Alternative dependency list
└── README.md                    # This file
```

## Testing

Run the test suite using pytest:

```bash
pytest
```

Run with verbose output:

```bash
pytest -v
```

Run specific test file:

```bash
pytest tests/test_api_upload.py
```

### Test Coverage

The test suite includes:
- Successful PDF uploads
- Duplicate filename rejection
- Non-PDF file rejection
- File storage verification
- Metadata file creation

## Usage Examples

### Using cURL

#### Upload a PDF file:

```bash
curl -X POST "http://localhost:8000/upload/pdf" \
  -H "x-file-name: document.pdf" \
  -H "Content-Type: application/pdf" \
  --data-binary "@path/to/your/file.pdf"
```

#### Check health:

```bash
curl http://localhost:8000/health
```

#### Check rate limit:

```bash
curl http://localhost:8000/rate-limit
```

### Using Python (httpx)

```python
import httpx

# Upload a PDF
with open("document.pdf", "rb") as f:
    response = httpx.post(
        "http://localhost:8000/upload/pdf",
        headers={
            "x-file-name": "document.pdf",
            "Content-Type": "application/pdf"
        },
        content=f.read()
    )
    print(response.json())
```

### Using JavaScript (fetch)

```javascript
// Upload a PDF
const formData = new FormData();
formData.append('file', fileInput.files[0]);

fetch('http://localhost:8000/upload/pdf', {
  method: 'POST',
  headers: {
    'x-file-name': 'document.pdf',
    'Content-Type': 'application/pdf'
  },
  body: fileInput.files[0]
})
.then(response => response.json())
.then(data => console.log(data));
```

## What We Built

This project implements a production-ready PDF upload API with the following key accomplishments:

### Core Functionality

1. **Streamed File Upload System**
   - Implemented efficient file streaming using FastAPI's `request.stream()` to avoid memory buffering
   - Supports large files up to 100 MB without loading entire file into memory
   - Chunked processing (1 MB chunks) for optimal performance

2. **Rate Limiting Implementation**
   - Leaky bucket algorithm for request throttling
   - In-memory rate limiting with thread-safe async locks
   - Configurable capacity and leak rate
   - Prevents server overload and ensures fair resource usage

3. **File Validation & Security**
   - Strict PDF-only file type validation (both extension and MIME type)
   - Maximum file size enforcement (100 MB)
   - Case-sensitive duplicate filename detection
   - Comprehensive error handling with appropriate HTTP status codes

4. **Metadata Management System**
   - Dual storage approach: filesystem + database
   - Automatic UUID generation for each upload
   - Metadata files stored alongside PDFs for redundancy
   - PostgreSQL synchronization after each successful upload
   - Conflict resolution (ON CONFLICT DO NOTHING) for idempotency

5. **Database Integration**
   - PostgreSQL connection pooling using psycopg3
   - Environment-based configuration
   - Automatic metadata synchronization from filesystem to database
   - Batch insert operations for efficiency

6. **API Design**
   - RESTful endpoint structure
   - Health check endpoint for monitoring
   - Rate limit status endpoint for client awareness
   - Comprehensive error responses
   - Interactive API documentation (Swagger/ReDoc)

### Technical Achievements

- **Memory Efficiency**: Streaming uploads prevent memory issues with large files
- **Scalability**: Rate limiting ensures system stability under load
- **Reliability**: Dual metadata storage (filesystem + database) provides redundancy
- **Developer Experience**: Clear error messages, comprehensive documentation, and test coverage
- **Production Ready**: Docker Compose setup, environment configuration, logging support

### Architecture Decisions

- **No UploadFile Dependency**: Uses raw request streaming for better control and efficiency
- **Case-Sensitive Filenames**: Prevents accidental overwrites and maintains file integrity
- **Metadata First Approach**: Metadata written to filesystem immediately, then synced to DB
- **Leaky Bucket Algorithm**: Smooth rate limiting that allows bursts while preventing overload

This API serves as a foundation for document management systems, RAG (Retrieval-Augmented Generation) applications, or any system requiring secure, efficient PDF file handling with metadata tracking.

