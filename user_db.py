# =================================================================================================
# Contributing Authors:     Authentication Module
# Purpose:                  Simple user database management with password hashing
# =================================================================================================

import json
import hashlib
import os
from typing import Optional, Dict

USER_DB_FILE = "users.json"

def hash_password(password: str, salt: str) -> str:
    """Hash password with salt using SHA-256."""
    return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()

def generate_salt() -> str:
    """Generate a random salt."""
    return os.urandom(16).hex()

def load_users() -> Dict:
    """Load users from database file."""
    if not os.path.exists(USER_DB_FILE):
        return {}
    
    try:
        with open(USER_DB_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_users(users: Dict) -> None:
    """Save users to database file."""
    with open(USER_DB_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def register_user(username: str, password: str) -> tuple[bool, str]:
    """
    Register a new user.
    Returns (success, message)
    """
    if not username or not password:
        return False, "Username and password required"
    
    if not username.isalnum():
        return False, "Username must be alphanumeric"
    
    if len(password) < 4:
        return False, "Password must be at least 4 characters"
    
    users = load_users()
    
    if username in users:
        return False, "Username already exists"
    
    salt = generate_salt()
    hashed = hash_password(password, salt)
    
    users[username] = {
        "password_hash": hashed,
        "salt": salt,
        "wins": 0
    }
    
    save_users(users)
    return True, "Registration successful"

def verify_user(username: str, password: str) -> tuple[bool, str]:
    """
    Verify user credentials.
    Returns (success, message)
    """
    users = load_users()
    
    if username not in users:
        return False, "Invalid username or password"
    
    user = users[username]
    hashed = hash_password(password, user["salt"])
    
    if hashed == user["password_hash"]:
        return True, "Login successful"
    else:
        return False, "Invalid username or password"

def get_user_wins(username: str) -> int:
    """Get user's win count."""
    users = load_users()
    if username in users:
        return users[username].get("wins", 0)
    return 0

def increment_wins(username: str) -> None:
    """Increment user's win count."""
    users = load_users()
    if username in users:
        users[username]["wins"] = users[username].get("wins", 0) + 1
        save_users(users)