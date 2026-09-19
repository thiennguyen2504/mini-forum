from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from fastapi import status
from fastapi.testclient import TestClient
from jose import jwt
import pytest

from app import cache
from app.auth import get_settings
from app.cache import _mark_online
from app.errors import (
    ContentBlockedError,
    LLMInvalidOutputError,
    LLMTimeoutError,
    LLMUnavailableError,
)
from app.llm.fake import FakeLLMClient
from app.main import app
from app.routers.analyze import get_analyzer_service
from app.services.analyzer import AnalyzerService

VALID_ANALYSIS_DICT = {
    "summary": "Tóm tắt bài viết hướng dẫn FastAPI",
    "tags": ["fastapi", "python"],
    "topic": "tech",
    "sentiment": "positive",
    "language": "vi",
    "moderation": {
        "is_safe": True,
        "categories": [],
        "severity": "none",
        "reason": "Chuẩn mực",
    },
}


def _create_token(user_id: int = 1) -> str:
    settings = get_settings()
    exp = datetime.now(timezone.utc) + timedelta(minutes=30)
    return jwt.encode({"sub": str(user_id), "exp": exp}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


@pytest.fixture
def auth_headers():
    token = _create_token(user_id=10)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_client():
    return TestClient(app)


def test_analyze_success(test_client, auth_headers, monkeypatch):
    fake_client = FakeLLMClient(mode="scripted", scripted_responses=[VALID_ANALYSIS_DICT])
    service = AnalyzerService(client=fake_client)
    app.dependency_overrides[get_analyzer_service] = lambda: service

    try:
        res = test_client.post(
            "/ai/analyze",
            json={"title": "Học FastAPI", "content": "Nội dung bài viết"},
            headers=auth_headers,
        )
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert "data" in data
        assert "meta" in data
        assert data["data"]["summary"] == VALID_ANALYSIS_DICT["summary"]
        assert "X-Request-ID" in res.headers
        assert res.headers["X-Request-ID"] == data["meta"]["request_id"]
    finally:
        app.dependency_overrides.clear()


def test_analyze_unauthorized_missing_token(test_client):
    res = test_client.post(
        "/ai/analyze",
        json={"title": "Tiêu đề", "content": "Nội dung"},
    )
    assert res.status_code == status.HTTP_401_UNAUTHORIZED
    body = res.json()
    assert "error" in body
    assert body["error"]["code"] == "UNAUTHORIZED"
    assert "X-Request-ID" in res.headers


def test_analyze_unauthorized_invalid_token(test_client):
    res = test_client.post(
        "/ai/analyze",
        json={"title": "Tiêu đề", "content": "Nội dung"},
        headers={"Authorization": "Bearer invalid-jwt-token"},
    )
    assert res.status_code == status.HTTP_401_UNAUTHORIZED
    body = res.json()
    assert body["error"]["code"] == "UNAUTHORIZED"


def test_analyze_invalid_input_schema(test_client, auth_headers):
    # Missing title
    res = test_client.post(
        "/ai/analyze",
        json={"content": "Không có title"},
        headers=auth_headers,
    )
    assert res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    body = res.json()
    assert "error" in body
    assert body["error"]["code"] == "INVALID_INPUT"


def test_analyze_content_blocked(test_client, auth_headers):
    fake_client = FakeLLMClient(
        mode="scripted",
        scripted_responses=[ContentBlockedError("Nội dung chứa yếu tố độc hại")],
    )
    service = AnalyzerService(client=fake_client)
    app.dependency_overrides[get_analyzer_service] = lambda: service

    try:
        res = test_client.post(
            "/ai/analyze",
            json={"title": "Nội dung cấm", "content": "..."},
            headers=auth_headers,
        )
        assert res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        body = res.json()
        assert body["error"]["code"] == "CONTENT_BLOCKED"
        assert "độc hại" in body["error"]["message"]
    finally:
        app.dependency_overrides.clear()


def test_analyze_llm_invalid_output(test_client, auth_headers):
    err = LLMInvalidOutputError("JSON format corrupted")
    fake_client = FakeLLMClient(
        mode="scripted",
        scripted_responses=[err, err, err],
    )
    service = AnalyzerService(client=fake_client)
    app.dependency_overrides[get_analyzer_service] = lambda: service

    try:
        res = test_client.post(
            "/ai/analyze",
            json={"title": "Tiêu đề", "content": "Nội dung"},
            headers=auth_headers,
        )
        assert res.status_code == status.HTTP_502_BAD_GATEWAY
        body = res.json()
        assert body["error"]["code"] == "LLM_INVALID_OUTPUT"
    finally:
        app.dependency_overrides.clear()


def test_analyze_llm_unavailable(test_client, auth_headers):
    err = LLMUnavailableError("Chưa cấu hình GEMINI_API_KEY trong môi trường")
    fake_client = FakeLLMClient(
        mode="scripted",
        scripted_responses=[err, err, err],
    )
    service = AnalyzerService(client=fake_client)
    app.dependency_overrides[get_analyzer_service] = lambda: service

    try:
        res = test_client.post(
            "/ai/analyze",
            json={"title": "Tiêu đề", "content": "Nội dung"},
            headers=auth_headers,
        )
        assert res.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        body = res.json()
        assert body["error"]["code"] == "LLM_UNAVAILABLE"
    finally:
        app.dependency_overrides.clear()


def test_analyze_llm_timeout(test_client, auth_headers):
    err = LLMTimeoutError("Quá thời gian chờ")
    fake_client = FakeLLMClient(
        mode="scripted",
        scripted_responses=[err, err, err],
    )
    service = AnalyzerService(client=fake_client)
    app.dependency_overrides[get_analyzer_service] = lambda: service

    try:
        res = test_client.post(
            "/ai/analyze",
            json={"title": "Tiêu đề", "content": "Nội dung"},
            headers=auth_headers,
        )
        assert res.status_code == status.HTTP_504_GATEWAY_TIMEOUT
        body = res.json()
        assert body["error"]["code"] == "LLM_TIMEOUT"
    finally:
        app.dependency_overrides.clear()


def test_health_check_ok(test_client, monkeypatch):
    mock_redis = MagicMock()
    mock_redis.ping.return_value = True
    monkeypatch.setattr(cache, "redis_client", mock_redis)
    _mark_online()

    res = test_client.get("/ai/health")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert "status" in data
    assert "provider" in data
    assert "model" in data
    assert data["redis"] == "ok"


def test_health_check_redis_error_still_200(test_client, monkeypatch):
    import redis

    mock_redis = MagicMock()
    mock_redis.ping.side_effect = redis.ConnectionError("Redis offline")
    monkeypatch.setattr(cache, "redis_client", mock_redis)

    res = test_client.get("/ai/health")
    # Theo hợp đồng API: redis lỗi => vẫn 200 với redis:"error" (cache là tuỳ chọn)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["redis"] == "error"
