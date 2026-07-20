import base64
import hashlib
import os

from cryptography.fernet import Fernet
from django.conf import settings


def _fernet() -> Fernet:
    """
    Load encryption key from APP_CHECK_KEK env var (recommended for production).
    Falls back to a key derived from SECRET_KEY so existing installs work without
    manual config -- but APP_CHECK_KEK should be set and rotated independently.
    Same pattern as ai/encryption.py's AI_PROVIDER_KEK.
    """
    kek = os.environ.get("APP_CHECK_KEK", "")
    if kek:
        return Fernet(kek.encode())
    raw = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    key = base64.urlsafe_b64encode(raw)
    return Fernet(key)


def encrypt_secret(plaintext: str) -> str:
    """Encrypts a Play Integrity service-account key or DeviceCheck private key before storage."""
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    return _fernet().decrypt(ciphertext.encode()).decode()
