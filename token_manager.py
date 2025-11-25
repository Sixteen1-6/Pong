# =================================================================================================
# Contributing Authors:     Shubhanshu Pokharel, Aaron Lin, Ayham Yousef
# Email Addresses:          spo283@uky.edu, ayli222@uky.edu, afyo223@uky.edu
# Date:                     11/25/2025
# Purpose:                  Session token management for secure user authentication
# Misc:                     Tokens expire after 10 minutes of inactivity
# =================================================================================================

import secrets
import time
from typing import Optional, Dict

# Token storage: {token: (username, expiration_time)}
active_tokens: Dict[str, tuple[str, float]] = {}

TOKEN_EXPIRATION = 600  # 10 minutes



# Author:       Shubhanshu Pokharel, Aaron Lin, Ayham Yousef
# Purpose:      Generate a secure session token for a user
# Pre:          username (str) - valid username to associate with token
# Post:         Returns str - secure token, token stored in active_tokens with expiration time
def generate_token(username: str) -> str:
    """Generate a secure session token for a user."""
    token = secrets.token_urlsafe(32)
    expiration = time.time() + TOKEN_EXPIRATION
    active_tokens[token] = (username, expiration)
    return token


# Author:       Shubhanshu Pokharel, Aaron Lin, Ayham Yousef
# Purpose:      Verify a token and return the associated username if valid
# Pre:          token (str) - session token to verify
# Post:         Returns str - username if token valid, None if invalid or expired, expired tokens removed
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




# Author:       Shubhanshu Pokharel, Aaron Lin, Ayham Yousef
# Purpose:      Revoke a session token (logout)
# Pre:          token (str) - session token to revoke
# Post:         Token removed from active_tokens if it exists
def revoke_token(token: str) -> None:
    """Revoke a token."""
    if token in active_tokens:
        del active_tokens[token]






# Author:       Shubhanshu Pokharel, Aaron Lin, Ayham Yousef
# Purpose:      Remove all expired tokens from storage
# Pre:          active_tokens may contain expired tokens
# Post:         All expired tokens removed from active_tokens dictionary
def cleanup_expired_tokens() -> None:
    """Remove all expired tokens."""
    current_time = time.time()
    expired = [token for token, (_, exp) in active_tokens.items() if current_time > exp]
    for token in expired:
        del active_tokens[token]