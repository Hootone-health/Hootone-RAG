"""
File handling utilities for streamed PDF uploads (no UploadFile).

Responsibilities:
- Enforce PDF-only uploads and max size (100 MB).
- Reject duplicate file names (case-sensitive).
- Stream body via request.stream() to avoid buffering.
- Persist PDF to disk and write metadata alongside it.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import AsyncIterator, Optional
from uuid import uuid4

from fastapi import HTTPException, status
from starlette.requests import Request

from src.models.api_models import (
    MAX_PDF_SIZE_BYTES,
    METADATA_DIR,
    PDF_STORAGE_DIR,
    FileMetadata,
    UploadSuccess,
)

LOGGER = logging.getLogger(__name__)
CHUNK_SIZE = 1024 * 1024  # 1 MB


def _ensure_directories() -> None:
    PDF_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_DIR.mkdir(parents=True, exist_ok=True)


def _metadata_path(file_name: str) -> Path:
    # Metadata file shares the base name but is stored as .txt
    return METADATA_DIR / f"{file_name}.txt"


def _storage_path(file_name: str) -> Path:
    return PDF_STORAGE_DIR / file_name


def _check_duplicate(file_name: str) -> None:
    if _storage_path(file_name).exists():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="File already Exist!"
        )


def _check_type(file_name: str, content_type: Optional[str]) -> None:
    if not file_name.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF files are allowed",
        )
    if content_type and content_type.lower() not in ("application/pdf", "application/x-pdf"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF files are allowed",
        )


def _write_metadata(meta: FileMetadata) -> None:
    meta_file = _metadata_path(meta.file_name)
    lines = [
        f"unique_id={meta.unique_id}",
        f"file_name={meta.file_name}",
        f"storage_path={meta.storage_path}",
        f"uploaded_at={meta.uploaded_at.isoformat()}",
    ]
    meta_file.write_text("\n".join(lines), encoding="utf-8")


async def _stream_to_disk(stream: AsyncIterator[bytes], dest: Path, max_bytes: int) -> int:
    written = 0
    with dest.open("wb") as f:
        async for chunk in stream:
            if not chunk:
                continue
            written += len(chunk)
            if written > max_bytes:
                dest.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Cannot be Upload! Max File size is 100 MB",
                )
            f.write(chunk)
    return written


async def handle_pdf_upload(request: Request) -> UploadSuccess:
    """
    Process a streamed PDF upload using request.stream().

    Raises HTTPException on validation failures.
    """
    _ensure_directories()

    content_length = request.headers.get("content-length")
    content_type = request.headers.get("content-type")
    file_name = request.headers.get("x-file-name")

    if not file_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing file name header: x-file-name",
        )

    _check_type(file_name, content_type)

    if content_length:
        try:
            length_val = int(content_length)
        except ValueError:
            length_val = None
        else:
            if length_val > MAX_PDF_SIZE_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Cannot be Upload! Max File size is 100 MB",
                )
    else:
        length_val = None

    _check_duplicate(file_name)

    dest_path = _storage_path(file_name)
    bytes_written = await _stream_to_disk(request.stream(), dest_path, MAX_PDF_SIZE_BYTES)
    LOGGER.info("Uploaded %s bytes to %s", bytes_written, dest_path)

    meta = FileMetadata(
        unique_id=uuid4(),
        file_name=file_name,
        storage_path=dest_path,
    )
    _write_metadata(meta)

    return UploadSuccess(
        status_code=status.HTTP_201_CREATED,
        message="Upload successful",
        file_name=file_name,
        unique_id=meta.unique_id,
        stored_at=str(dest_path),
    )

