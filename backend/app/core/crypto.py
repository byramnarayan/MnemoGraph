from __future__ import annotations

import base64
import hashlib
from cryptography.fernet import Fernet
from app.core.config import settings


def _get_fernet() -> Fernet:
    raw_key = settings.secret_key.get_secret_value().encode("utf-8")
    key = base64.urlsafe_b64encode(hashlib.sha256(raw_key).digest())
    return Fernet(key)


def encrypt_secret(secret_plaintext: str) -> str:
    """Encrypt a sensitive secret string using Fernet and app secret_key."""
    if not secret_plaintext:
        return ""
    f = _get_fernet()
    return f.encrypt(secret_plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(secret_encrypted: str) -> str:
    """Decrypt a ciphertext secret string using Fernet."""
    if not secret_encrypted:
        return ""
    f = _get_fernet()
    try:
        return f.decrypt(secret_encrypted.encode("utf-8")).decode("utf-8")
    except Exception:
        # Fallback if already plaintext or decrypt error
        return secret_encrypted

