"""Unit tests for auth helper functions that require no DB or network."""
from __future__ import annotations

import pytest
from unittest.mock import patch


# ── _validate_password ────────────────────────────────────────────────────────

def _validate(pw: str):
    from src.auth.router import _validate_password
    return _validate_password(pw)


def test_valid_password_returns_none():
    assert _validate("Secure@123") is None


def test_too_short_fails():
    assert _validate("Ab1!") is not None


def test_missing_uppercase_fails():
    assert _validate("secure@123") is not None


def test_missing_lowercase_fails():
    assert _validate("SECURE@123") is not None


def test_missing_digit_fails():
    assert _validate("Secure@abc") is not None


def test_missing_special_char_fails():
    assert _validate("Secure1234") is not None


def test_exactly_8_chars_with_all_requirements_passes():
    assert _validate("Aa1!aaaa") is None


def test_empty_string_fails():
    assert _validate("") is not None


# ── decode_token ──────────────────────────────────────────────────────────────

def test_decode_token_valid():
    from src.auth.router import _make_access_token, decode_token
    token = _make_access_token("test@example.com", "tenant-123", "owner")
    payload = decode_token(token)
    assert payload["sub"] == "test@example.com"
    assert payload["tenant_id"] == "tenant-123"
    assert payload["role"] == "owner"


def test_decode_token_invalid_raises():
    from fastapi import HTTPException
    from src.auth.router import decode_token
    with pytest.raises(HTTPException) as exc:
        decode_token("not.a.valid.token")
    assert exc.value.status_code == 401


def test_decode_token_tampered_raises():
    from fastapi import HTTPException
    from src.auth.router import _make_access_token, decode_token
    token = _make_access_token("test@example.com", "tenant-123", "owner")
    tampered = token[:-5] + "XXXXX"
    with pytest.raises(HTTPException) as exc:
        decode_token(tampered)
    assert exc.value.status_code == 401
