#Run this command to start the server: uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

"""
FastAPI app with leaky-bucket rate limiting and streamed PDF upload.

Constraints:
- PDF only, max 100 MB, no UploadFile. Uses request.stream().
- Duplicate filenames (case-sensitive) are rejected.
- Metadata is written to disk and synced to PostgreSQL for each allowed request.
- Rate limiting uses a simple in-memory leaky bucket (capacity=2, leak_rate=0.016 req/sec).
"""
from __future__ import annotations

import asyncio
import logging
import time
import traceback
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

from src.models.api_models import (
    BusyError,
    LeakyBucketConfig,
    RateLimitStatus,
    UploadSuccess,
)
from src.services import db_manager
from src.services.file_handler import handle_pdf_upload

LOGGER = logging.getLogger(__name__)
app = FastAPI(title="RAG Hootone API")

# ---- Leaky bucket (in-memory) ---------------------------------------------

bucket_cfg = LeakyBucketConfig()
_bucket_level = 0.0
_bucket_updated_at = time.monotonic()
_bucket_lock = asyncio.Lock()


async def enforce_rate_limit() -> RateLimitStatus:
    """
    Simple leaky-bucket implementation.
    """
    global _bucket_level, _bucket_updated_at
    async with _bucket_lock:
        now = time.monotonic()
        elapsed = now - _bucket_updated_at
        leaked = bucket_cfg.leak_rate * elapsed
        _bucket_level = max(0.0, _bucket_level - leaked)
        _bucket_updated_at = now

        if _bucket_level >= bucket_cfg.capacity:
            LOGGER.warning("Rate limit exceeded: level=%.3f", _bucket_level)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Server is Busy",
            )

        _bucket_level += 1.0

        return RateLimitStatus(
            allowed=True,
            reason=None,
            status_code=status.HTTP_200_OK,
            bucket_capacity=bucket_cfg.capacity,
            bucket_leak_rate=bucket_cfg.leak_rate,
        )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/rate-limit", response_model=RateLimitStatus)
async def rate_limit_status(_: RateLimitStatus = Depends(enforce_rate_limit)) -> RateLimitStatus:
    """
    Returns current rate-limit status (also counts as a token, for parity).
    """
    return _


@app.post("/upload/pdf")
async def upload_pdf(
    request: Request,
    _: RateLimitStatus = Depends(enforce_rate_limit),
) -> JSONResponse:
    """
    Stream a PDF upload, enforce constraints, persist metadata, and sync to DB.
    """
    result: UploadSuccess = await handle_pdf_upload(request)
    inserted = db_manager.sync_metadata_directory_to_db()

    payload = {
        "message": result.message,
        "file_name": result.file_name,
        "unique_id": str(result.unique_id),
        "stored_at": result.stored_at,
        "db_rows_inserted": inserted,
    }
    return JSONResponse(status_code=result.status_code, content=payload)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    LOGGER.error("HTTP error on %s %s: %s", request.method, request.url.path, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail, "status_code": exc.status_code},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Catch-all exception handler for unhandled errors.
    Logs the full traceback and returns a 500 error.
    """
    LOGGER.error(
        "Unhandled exception on %s %s: %s\n%s",
        request.method,
        request.url.path,
        exc,
        traceback.format_exc(),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "message": "Internal Server Error",
            "detail": str(exc) if LOGGER.level <= logging.DEBUG else "An unexpected error occurred",
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
        },
    )
