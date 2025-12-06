"""
Pydantic v2 models and constants used by the API layer.

Covers:
- Leaky bucket rate limiting defaults.
-.pdf upload constraints (size/type) for streamed uploads.
- File metadata structures for filesystem persistence and PostgreSQL writes.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator

# ---- Paths and limits -----------------------------------------------------

# Fixed locations provided in the requirements (Windows paths are kept explicit)
METADATA_DIR = Path(r"C:\Users\Admin\Desktop\rag-hootone\data\uploads\Metadata")
PDF_STORAGE_DIR = Path(r"C:\Users\Admin\Desktop\rag-hootone\data\uploads\PDF")

MAX_PDF_SIZE_MB = 100
MAX_PDF_SIZE_BYTES = MAX_PDF_SIZE_MB * 1024 * 1024

# ---- Rate limiting --------------------------------------------------------


class LeakyBucketConfig(BaseModel):
    """Leaky bucket settings (requests/sec)."""

    capacity: int = Field(default=2, ge=1, description="Maximum queued requests")
    leak_rate: float = Field(
        default=0.016, gt=0, description="Tokens leaked per second (req/sec)"
    )


class RateLimitStatus(BaseModel):
    """Response-friendly rate-limit status."""

    allowed: bool = Field(default=True)
    reason: Optional[str] = Field(default=None)
    status_code: int = Field(default=200)
    bucket_capacity: int
    bucket_leak_rate: float


class BusyError(BaseModel):
    """Represents a busy server response."""

    status_code: int = Field(default=503)
    message: str = Field(default="Server is Busy")


# ---- Upload constraints and metadata --------------------------------------


class UploadConstraints(BaseModel):
    """Static constraints for PDF uploads."""

    max_size_bytes: int = Field(default=MAX_PDF_SIZE_BYTES, gt=0)
    allowed_mime_types: list[str] = Field(
        default_factory=lambda: ["application/pdf"], description="Accepted MIME types"
    )
    allowed_extensions: list[str] = Field(
        default_factory=lambda: [".pdf"], description="Accepted file extensions"
    )


class StreamUploadRequest(BaseModel):
    """
    Represents a streamed upload request (no UploadFile, uses request.stream()).
    """

    file_name: str
    content_length: Optional[int] = Field(
        default=None, description="Content-Length header, if provided"
    )
    content_type: Optional[str] = Field(
        default=None, description="Content-Type header, if provided"
    )

    @field_validator("file_name")
    @classmethod
    def validate_extension(cls, value: str) -> str:
        if not value.lower().endswith(".pdf"):
            raise ValueError("Only PDF files are allowed")
        return value

    @field_validator("content_length")
    @classmethod
    def validate_size(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value > MAX_PDF_SIZE_BYTES:
            raise ValueError("Cannot be Upload! Max File size is 100 MB")
        return value


class DuplicateCheck(BaseModel):
    """Represents a duplicate file-name check (case-sensitive)."""

    file_name: str
    exists: bool


class FileMetadata(BaseModel):
    """Metadata stored alongside each upload."""

    unique_id: UUID = Field(default_factory=uuid4)
    file_name: str
    storage_path: Path
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("file_name")
    @classmethod
    def ensure_case_sensitive_name(cls, value: str) -> str:
        # Case-sensitive duplicate checking is handled elsewhere; here we keep the name unchanged.
        if not value:
            raise ValueError("File name cannot be empty")
        return value

    @field_validator("storage_path")
    @classmethod
    def ensure_storage_path(cls, value: Path) -> Path:
        # Keep validation light; callers ensure directories exist.
        return value


class MetadataRecord(BaseModel):
    """
    Shape aligned to the PostgreSQL `Metadata` table for insert/read operations.
    """

    unique_id: UUID
    uploaded_at: datetime
    file_name: str
    storage_path: str

    @classmethod
    def from_file_metadata(cls, meta: FileMetadata) -> "MetadataRecord":
        return cls(
            unique_id=meta.unique_id,
            uploaded_at=meta.uploaded_at,
            file_name=meta.file_name,
            storage_path=str(meta.storage_path),
        )


# ---- Error/response helpers -----------------------------------------------


class UploadError(BaseModel):
    status_code: int
    message: str
    detail: Optional[str] = None


class UploadSuccess(BaseModel):
    status_code: int = Field(default=201)
    message: str = Field(default="Upload successful")
    file_name: str
    unique_id: UUID
    stored_at: str

