# Ingestion & status endpoints
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Request, Query, status
from typing import Dict, Optional
import uuid
import logging
import os

from app.api.deps import get_current_admin_user
from app.core.rate_limit import check_rate_limit
from app.core.file_validation import validate_pdf_file
from app.services.s3_service import get_s3_service
from app.services.valkey_service import get_valkey_service
from app.models.schemas import IngestDocumentResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/ingest")


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing path separators and other dangerous characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove path separators and keep only the base name
    filename = os.path.basename(filename)
    # Remove any remaining path separators or dangerous characters
    filename = filename.replace('/', '').replace('\\', '').replace('..', '')
    return filename


@router.post(
    "/document",
    response_model=IngestDocumentResponse,
    status_code=status.HTTP_201_CREATED
)
async def ingest_document(
    request: Request,
    file: UploadFile = File(...),
    filename: Optional[str] = Query(None, description="Custom filename for the uploaded file"),
    current_user: Dict[str, str] = Depends(get_current_admin_user)
):
    """
    Upload and ingest a PDF document.
    
    Requirements:
    - Rate limiting: 5 requests per minute
    - Authentication: JWT with Admin role only
    - File validation: PDF file < 50MB with magic number verification
    - Upload to S3 in ingestion_folder
    - Enqueue task in Valkey
    
    Args:
        filename: Optional custom filename. If not provided, uses the uploaded file's original name.
    
    Returns:
        task_id, status, and message
    """
    # Apply rate limiting (5 requests per minute)
    check_rate_limit(request)
    
    try:
        # Validate PDF file (size and magic number)
        validate_pdf_file(file)
        
        # Determine the filename to use
        if filename:
            # Use user-provided filename, sanitize it
            final_filename = sanitize_filename(filename)
            if not final_filename:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid filename provided"
                )
        else:
            # Use original filename or default
            original_filename = file.filename or "document.pdf"
            final_filename = sanitize_filename(original_filename)
        
        # Ensure filename has .pdf extension
        if not final_filename.lower().endswith('.pdf'):
            final_filename = f"{final_filename}.pdf"
        
        # Check if file already exists in S3
        s3_service = get_s3_service()
        try:
            if s3_service.file_exists(final_filename):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"A file with the name '{final_filename}' already exists in the ingestion folder"
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"File existence check failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to check file existence: {str(e)}"
            )
        
        # Read file content
        file_content = await file.read()
        
        # Upload to S3
        try:
            s3_uri = s3_service.upload_file(file_content, final_filename)
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload file to S3: {str(e)}"
            )
        
        # Generate UUID for task_id
        task_id = str(uuid.uuid4())
        
        # Determine initial status: PENDING (since it's being enqueued)
        initial_status = "PENDING"
        
        # Store payload in Valkey Hash
        valkey_service = get_valkey_service()
        try:
            store_success = valkey_service.store_task_payload(
                task_id=task_id,
                task_type="Ingestion",
                status=initial_status,
                s3_uri=s3_uri
            )
            if not store_success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to store task payload in Valkey"
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Valkey store failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to store task payload: {str(e)}"
            )
        
        # Enqueue task in Valkey List
        try:
            enqueue_success = valkey_service.enqueue_task(task_id)
            if not enqueue_success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to enqueue task in Valkey"
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Valkey enqueue failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to enqueue task: {str(e)}"
            )
        
        # Return success response
        return IngestDocumentResponse(
            task_id=task_id,
            status=initial_status,
            message="Document ingestion task created successfully"
        )
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Unexpected error in ingest_document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )
