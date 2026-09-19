from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from jose import jwt
import pytest

from app.auth import require_auth, verify_token
from app.config import Settings
from app.errors import UnauthorizedError


def _create_test_token(sub: str, secret: str = "mini-blog-secret-key-change-in-production", expire_minutes: int = 30) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    return jwt.encode({"sub": sub, "exp": exp}, secret, algorithm="HS256")


def test_verify_token_valid():
    token = _create_test_token(sub="10")
    payload = verify_token(token)
    assert payload is not None
    assert payload["sub"] == "10"


def test_verify_token_invalid_secret():
    token = _create_test_token(sub="10", secret="wrong-secret")
    payload = verify_token(token)
    assert payload is None


def test_verify_token_expired():
    token = _create_test_token(sub="10", expire_minutes=-5)
    payload = verify_token(token)
    assert payload is None


@pytest.mark.asyncio
async def test_require_auth_success():
    token = _create_test_token(sub="42")
    request = MagicMock()
    request.headers.get.return_value = f"Bearer {token}"

    user_id = await require_auth(request)
    assert user_id == "42"


@pytest.mark.asyncio
async def test_require_auth_missing_header():
    request = MagicMock()
    request.headers.get.return_value = None

    with pytest.raises(UnauthorizedError) as exc:
        await require_auth(request)
    assert "Thiếu header Authorization" in str(exc.value)


@pytest.mark.asyncio
async def test_require_auth_invalid_token():
    request = MagicMock()
    request.headers.get.return_value = "Bearer invalid-token"

    with pytest.raises(UnauthorizedError) as exc:
        await require_auth(request)
    assert "Token không hợp lệ" in str(exc.value)


@pytest.mark.asyncio
async def test_require_auth_disabled(monkeypatch):
    from app import auth

    disabled_settings = Settings(AI_REQUIRE_AUTH=False)
    monkeypatch.setattr(auth, "get_settings", lambda: disabled_settings)

    request = MagicMock()
    request.headers.get.return_value = None

    user_id = await require_auth(request)
    assert user_id is None
