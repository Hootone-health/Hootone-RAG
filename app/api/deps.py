# Dependency injection (JWT verification)
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict

from app.core.security import decode_token
from app.models.user import UserRole

security = HTTPBearer()


def get_current_admin_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, str]:
    """
    Extract and verify JWT token, check if user has Admin role.
    Returns user info if valid Admin, raises HTTPException otherwise.
    
    - Returns 401 if JWT is invalid/corrupted
    - Returns 403 if role is not "Admin"
    - Returns user info (user_id, role) if valid Admin
    """
    token = credentials.credentials
    
    # Decode JWT token
    payload = decode_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or corrupted JWT token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extract role directly from JWT payload (not from database)
    role = payload.get("role")
    
    if role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required.",
        )
    
    # Return user info extracted from JWT
    return {
        "user_id": payload.get("user_id"),
        "role": role,
        "sub": payload.get("sub")
    }
