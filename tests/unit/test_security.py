"""Unit tests for api/security.py: password hashing and session token hashing
(specs/002-web-frontend/tasks.md T020)."""

from __future__ import annotations

import pytest

from api.security import (
    WeakPasswordError,
    generate_session_token,
    hash_password,
    hash_session_token,
    mask_secret,
    verify_password,
)


def test_hash_password_roundtrip():
    hashed = hash_password("correct-horse-battery-staple")
    assert hashed != "correct-horse-battery-staple"
    assert verify_password("correct-horse-battery-staple", hashed)


def test_verify_password_rejects_wrong_password():
    hashed = hash_password("correct-horse-battery-staple")
    assert not verify_password("wrong-password", hashed)


def test_verify_password_rejects_malformed_hash():
    assert not verify_password("anything", "!disabled!")


def test_hash_password_rejects_short_password():
    with pytest.raises(WeakPasswordError):
        hash_password("short")


def test_session_token_hash_is_deterministic_and_lookup_safe():
    token = generate_session_token()
    assert hash_session_token(token) == hash_session_token(token)
    assert hash_session_token(token) != token


def test_generate_session_token_is_unique():
    assert generate_session_token() != generate_session_token()


def test_mask_secret_never_reveals_full_value():
    masked = mask_secret("super-secret-token-value")
    assert masked.endswith("alue")
    assert "super-secret-token-value" not in masked
