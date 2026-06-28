import base64
import hashlib
import os

from cryptography.fernet import Fernet
from django.conf import settings


def _fernet() -> Fernet:
    """
    Load encryption key from AI_PROVIDER_KEK env var (recommended for production).
    Falls back to a key derived from SECRET_KEY so existing installs work without
    manual config — but AI_PROVIDER_KEK should be set and rotated independently.
    """
    kek = os.environ.get("AI_PROVIDER_KEK", "")
    if kek:
        return Fernet(kek.encode())
    # Derive 32-byte key from SECRET_KEY via SHA-256, then base64-encode for Fernet.
    raw = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    key = base64.urlsafe_b64encode(raw)
    return Fernet(key)


def encrypt_api_key(plaintext: str) -> str:
    """AES-128-CBC + HMAC via Fernet. Set AI_PROVIDER_KEK env var in production."""
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_api_key(ciphertext: str) -> str:
    return _fernet().decrypt(ciphertext.encode()).decode()
