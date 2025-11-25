# =================================================================================================
# Contributing Authors:     Authentication Module
# Purpose:                  Session token management
# =================================================================================================

import secrets
import time
from typing import Optional, Dict

# Token storage: {token: (username, expiration_time)}
active_tokens: Dict[str, tuple[str, float]] = {}

TOKEN_EXPIRATION = 600  # 10 minutes

def generate_token(username: str) -> str:
    """Generate a secure session token for a user."""
    token = secrets.token_urlsafe(32)
    expiration = time.time() + TOKEN_EXPIRATION
    active_tokens[token] = (username, expiration)
    return token

def verify_token(token: str) -> Optional[str]:
    """
    Verify a token and return the username if valid.
    Returns None if token is invalid or expired.
    """
    if token not in active_tokens:
        return None
    
    username, expiration = active_tokens[token]
    
    if time.time() > expiration:
        # Token expired
        del active_tokens[token]
        return None
    
    return username

def revoke_token(token: str) -> None:
    """Revoke a token."""
    if token in active_tokens:
        del active_tokens[token]

def cleanup_expired_tokens() -> None:
    """Remove all expired tokens."""
    current_time = time.time()
    expired = [token for token, (_, exp) in active_tokens.items() if current_time > exp]
    for token in expired:
        del active_tokens[token]