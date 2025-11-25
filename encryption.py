# =================================================================================================
# Contributing Authors:     Authentication Module
# Purpose:                  Simple encryption for network communication
# =================================================================================================

from cryptography.fernet import Fernet
import base64
import hashlib

def generate_key_from_password(password: str = "pong_game_2024") -> bytes:
    """Generate a Fernet key from a password."""
    key = hashlib.sha256(password.encode()).digest()
    return base64.urlsafe_b64encode(key)

# Shared encryption key (same on client and server)
ENCRYPTION_KEY = generate_key_from_password()
cipher = Fernet(ENCRYPTION_KEY)

def encrypt_message(message: str) -> bytes:
    """Encrypt a string message."""
    return cipher.encrypt(message.encode())

def decrypt_message(encrypted: bytes) -> str:
    """Decrypt a message."""
    return cipher.decrypt(encrypted).decode()