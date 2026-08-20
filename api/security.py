"""Security primitives for the web API layer (specs/002-web-frontend/research.md
R1/R2/R3): password hashing, session token generation, and at-rest encryption
for per-user integration secrets.

Nothing in this module ever logs a plaintext secret, password, or token
(constitution VIII, extended per-user in feature 002).
"""

from __future__ import annotations

import hashlib
import os
import secrets

import bcrypt
from cryptography.fernet import Fernet, InvalidToken

_MIN_PASSWORD_LENGTH = 8


class WeakPasswordError(ValueError):
    pass


def hash_password(password: str) -> str:
    if len(password) < _MIN_PASSWORD_LENGTH:
        raise WeakPasswordError(f"Password must be at least {_MIN_PASSWORD_LENGTH} characters")
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        # Malformed/legacy hash (e.g. the disabled legacy-user marker, research.md R7)
        return False


def generate_session_token() -> str:
    """The value actually stored in the cookie — only its hash is persisted
    (research.md R2), so a leaked DB row alone never yields a usable session."""
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _get_fernet() -> Fernet:
    key = os.environ.get("APP_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError(
            "APP_ENCRYPTION_KEY is not set — generate one with "
            '`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`'
        )
    return Fernet(key.encode("utf-8"))


def encrypt_secret(plaintext: str) -> bytes:
    return _get_fernet().encrypt(plaintext.encode("utf-8"))


def decrypt_secret(ciphertext: bytes) -> str:
    try:
        return _get_fernet().decrypt(ciphertext).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Stored credential could not be decrypted") from exc


def mask_secret(plaintext: str, *, visible: int = 4) -> str:
    """Display-only hint (FR-010) — never enough to reconstruct the secret."""
    if len(plaintext) <= visible:
        return "*" * len(plaintext)
    return f"{'*' * 4}...{plaintext[-visible:]}"
