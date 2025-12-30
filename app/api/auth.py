# Login endpoints
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.schemas import LoginRequest, LoginResponse
from app.models.user import UserRole
from app.services.auth_service import authenticate_user
from app.core.security import create_access_token
from app.core.rate_limit import check_rate_limit

router = APIRouter()


@router.post("/admin/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(
    login_data: LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Login endpoint for admin authentication.
    
    No JWT authentication required for this endpoint.
    Returns JWT token with user_id and role if credentials are valid.
    """
    # Apply rate limiting
    check_rate_limit(request)
    
    try:
        # Authenticate user
        user = authenticate_user(db, login_data.username, login_data.password)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )

        if user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to access this resource"
            )
        
        # Create JWT token with user_id and role
        token_data = {
            "sub": str(user.user_id),
            "user_id": str(user.user_id),
            "role": user.role.value
        }
        access_token = create_access_token(data=token_data)
        
        return LoginResponse(
            token=access_token,
            user_id=user.user_id,
            role=user.role.value
        )
    
    except HTTPException:
        # Re-raise HTTP exceptions (like 401)
        raise
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/users/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def users_login(
    login_data: LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Login endpoint for user authentication (ADMIN and EMPLOYEE roles only).
    
    No JWT authentication required for this endpoint.
    Returns JWT token with user_id and role if credentials are valid.
    Only users with ADMIN or EMPLOYEE roles are allowed.
    """
    # Apply rate limiting (5 requests per minute)
    check_rate_limit(request)
    
    try:
        # Authenticate user
        user = authenticate_user(db, login_data.username, login_data.password)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )

        # Only allow ADMIN and EMPLOYEE roles
        if user.role not in [UserRole.ADMIN, UserRole.EMPLOYEE]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        # Create JWT token with user_id and role
        token_data = {
            "sub": str(user.user_id),
            "user_id": str(user.user_id),
            "role": user.role.value
        }
        access_token = create_access_token(data=token_data)
        
        return LoginResponse(
            token=access_token,
            user_id=user.user_id,
            role=user.role.value
        )
    
    except HTTPException:
        # Re-raise HTTP exceptions (like 401)
        raise
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )