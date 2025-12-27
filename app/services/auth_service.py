# Authentication logic
from sqlalchemy.orm import Session
from typing import Optional

from app.models.user import User
from app.core.security import verify_password


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """Authenticate a user by username and password.
    
    Returns User object if credentials are valid, None otherwise.
    """
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        return None
    
    if not verify_password(password, user.password_hash):
        return None
    
    return user
