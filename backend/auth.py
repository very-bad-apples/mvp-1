"""
API Authentication for FastAPI endpoints
"""

from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader, APIKeyQuery
from typing import Optional
import os
import hashlib
import hmac
from config import settings

# API Key header name
API_KEY_HEADER = "X-API-Key"
API_KEY_QUERY = "api_key"

# Initialize API key security
api_key_header = APIKeyHeader(name=API_KEY_HEADER, auto_error=False)
api_key_query = APIKeyQuery(name=API_KEY_QUERY, auto_error=False)


def get_api_key_from_env() -> Optional[str]:
    """Get API key from environment variable"""
    return os.getenv("API_KEY", "")


def check_api_key(api_key: str) -> bool:
    """
    Verify API key against configured key
    
    Supports:
    - Single API key from environment variable
    - Multiple API keys (comma-separated)
    - Key hashing for secure comparison
    """
    configured_key = get_api_key_from_env()
    
    if not configured_key:
        # No API key configured - allow all requests (development mode)
        return True
    
    # Support multiple API keys (comma-separated)
    valid_keys = [key.strip() for key in configured_key.split(",")]
    
    # Direct match
    if api_key in valid_keys:
        return True
    
    # Optional: Hash-based comparison for extra security
    # This allows storing hashed keys in env vars
    for valid_key in valid_keys:
        if valid_key.startswith("hash:"):
            # Compare hash
            stored_hash = valid_key[5:]  # Remove "hash:" prefix
            provided_hash = hashlib.sha256(api_key.encode()).hexdigest()
            if hmac.compare_digest(stored_hash, provided_hash):
                return True
    
    return False


async def verify_api_key_header(
    api_key: Optional[str] = Security(api_key_header)
) -> str:
    """
    Verify API key from header

    Usage:
        @app.get("/protected")
        async def protected_route(api_key: str = Depends(verify_api_key_header)):
            return {"message": "Authenticated"}
    """
    # If no API key is configured, skip authentication (development mode)
    configured_key = get_api_key_from_env()
    if not configured_key:
        return ""

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key missing. Provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if not check_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return api_key


async def verify_api_key_query(
    api_key: Optional[str] = Security(api_key_query)
) -> str:
    """
    Verify API key from query parameter

    Usage:
        @app.get("/protected")
        async def protected_route(api_key: str = Depends(verify_api_key_query)):
            return {"message": "Authenticated"}
    """
    # If no API key is configured, skip authentication (development mode)
    configured_key = get_api_key_from_env()
    if not configured_key:
        return ""

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key missing. Provide ?api_key=YOUR_KEY",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if not check_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return api_key


async def verify_api_key_optional(
    api_key: Optional[str] = Security(api_key_header)
) -> Optional[str]:
    """
    Optional API key verification (for endpoints that work with or without auth)
    
    Usage:
        @app.get("/public-or-private")
        async def flexible_route(api_key: Optional[str] = Depends(verify_api_key_optional)):
            if api_key:
                # Authenticated user - return premium features
                return {"message": "Premium content"}
            else:
                # Public user - return basic features
                return {"message": "Basic content"}
    """
    if api_key and check_api_key(api_key):
        return api_key
    return None


# Convenience dependency that checks both header and query
async def verify_api_key(
    api_key_header: Optional[str] = Security(api_key_header),
    api_key_query: Optional[str] = Security(api_key_query)
) -> str:
    """
    Verify API key from either header or query parameter

    Usage:
        @app.get("/protected")
        async def protected_route(api_key: str = Depends(verify_api_key)):
            return {"message": "Authenticated"}
    """
    # If no API key is configured, skip authentication (development mode)
    configured_key = get_api_key_from_env()
    if not configured_key:
        return ""

    api_key = api_key_header or api_key_query

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key missing. Provide X-API-Key header or ?api_key=YOUR_KEY",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if not check_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return api_key

