"""
Unit tests for backend/auth.py:
  - hash_password / verify_password
  - create_token / decode_token
  - get_current_user FastAPI dependency
"""

import time
import pytest
from fastapi import HTTPException
from starlette.testclient import TestClient
from starlette.requests import Request
from unittest.mock import MagicMock

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from auth import (
    hash_password, verify_password,
    create_token, decode_token,
    get_current_user,
)
from config import settings


# ── Password hashing ──────────────────────────────────────────────────────────

class TestPasswordHashing:
    def test_hash_returns_string(self):
        h = hash_password("mySecret")
        assert isinstance(h, str)
        assert len(h) > 0

    def test_hash_is_not_plaintext(self):
        h = hash_password("mySecret")
        assert h != "mySecret"

    def test_verify_correct_password(self):
        h = hash_password("correct")
        assert verify_password("correct", h) is True

    def test_verify_wrong_password(self):
        h = hash_password("correct")
        assert verify_password("wrong", h) is False

    def test_empty_password_roundtrip(self):
        h = hash_password("")
        assert verify_password("", h) is True
        assert verify_password("x", h) is False

    def test_unicode_password(self):
        pw = "密码123!@#"
        h = hash_password(pw)
        assert verify_password(pw, h) is True
        assert verify_password("密码", h) is False

    def test_same_password_different_hash(self):
        """BCrypt generates a new salt each time."""
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2
        assert verify_password("same", h1)
        assert verify_password("same", h2)


# ── JWT ───────────────────────────────────────────────────────────────────────

class TestJWT:
    def test_create_and_decode(self):
        token = create_token(1, "alice", ["ADMIN"])
        payload = decode_token(token)
        assert payload is not None
        assert payload["userId"] == 1
        assert payload["sub"] == "alice"
        assert "ADMIN" in payload["roles"]

    def test_payload_contains_expiry(self):
        token = create_token(1, "alice", [])
        payload = decode_token(token)
        assert "exp" in payload
        assert "iat" in payload

    def test_decode_invalid_token(self):
        assert decode_token("not.a.token") is None

    def test_decode_tampered_token(self):
        token = create_token(1, "alice", [])
        tampered = token[:-4] + "xxxx"
        assert decode_token(tampered) is None

    def test_multiple_roles_preserved(self):
        roles = ["EDITOR", "REVIEWER"]
        token = create_token(5, "bob", roles)
        payload = decode_token(token)
        assert set(payload["roles"]) == set(roles)


# ── get_current_user dependency ───────────────────────────────────────────────

class TestGetCurrentUser:
    def _mock_request(self, authorization: str = "") -> MagicMock:
        req = MagicMock(spec=Request)
        req.headers = {"Authorization": authorization}
        req.state = MagicMock()
        return req

    @pytest.mark.asyncio
    async def test_valid_token_sets_state(self):
        token = create_token(42, "charlie", ["MANAGER"])
        req = self._mock_request(f"Bearer {token}")
        payload = await get_current_user(req)
        assert payload["userId"] == 42
        assert req.state.user_id == 42
        assert req.state.username == "charlie"
        assert "MANAGER" in req.state.roles

    @pytest.mark.asyncio
    async def test_missing_header_raises_401(self):
        req = self._mock_request("")
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(req)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_bearer_raises_401(self):
        req = self._mock_request("Bearer invalid.token.here")
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(req)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_non_bearer_scheme_raises_401(self):
        token = create_token(1, "alice", [])
        req = self._mock_request(f"Basic {token}")
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(req)
        assert exc_info.value.status_code == 401
