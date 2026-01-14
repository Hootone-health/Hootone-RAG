# File validation utilities
from fastapi import UploadFile, HTTPException, status

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB in bytes
PDF_MAGIC_NUMBER = b"%PDF"


def validate_pdf_file(file: UploadFile) -> None:
    """
    Validate PDF file by checking size and magic number.
    
    Args:
        file: FastAPI UploadFile object
        
    Raises:
        HTTPException: If file validation fails
    """
    # Check file size
    file_content = file.file.read()
    file.file.seek(0)  # Reset file pointer for later use
    
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum allowed size of 50MB. Current size: {len(file_content) / (1024 * 1024):.2f}MB"
        )
    
    # Check magic number (first 4 bytes should be %PDF)
    if len(file_content) < 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is too small to be a valid PDF"
        )
    
    if file_content[:4] != PDF_MAGIC_NUMBER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. File must be a valid PDF (magic number verification failed)"
        )

