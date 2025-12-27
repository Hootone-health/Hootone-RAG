# Rate limiting logic
from datetime import datetime, timedelta
from typing import Dict
from fastapi import HTTPException, Request, status
from collections import defaultdict
from app.core.config import settings

# In-memory storage: {client_id: [(timestamp1, timestamp2, ...)]}
_rate_limit_store: Dict[str, list] = defaultdict(list)


def _clean_old_entries(client_id: str, window_seconds: int):
    """Remove entries older than the time window."""
    now = datetime.utcnow()
    cutoff = now - timedelta(seconds=window_seconds)
    _rate_limit_store[client_id] = [
        ts for ts in _rate_limit_store[client_id] if ts > cutoff
    ]


def _get_client_id(request: Request) -> str:
    """Get client identifier (IP address)."""
    if request.client:
        return request.client.host
    return "unknown"


def check_rate_limit(request: Request):
    """Check if the request exceeds rate limit. Raises HTTPException if exceeded."""
    client_id = _get_client_id(request)
    
    # Clean old entries
    _clean_old_entries(client_id, settings.RATE_LIMIT_WINDOW_SECONDS)
    
    # Check current count
    current_count = len(_rate_limit_store[client_id])
    
    if current_count >= settings.RATE_LIMIT_REQUESTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {settings.RATE_LIMIT_REQUESTS} requests per {settings.RATE_LIMIT_WINDOW_SECONDS} seconds"
        )
    
    # Add current request timestamp
    _rate_limit_store[client_id].append(datetime.utcnow())
