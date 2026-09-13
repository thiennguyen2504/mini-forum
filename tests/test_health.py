from fastapi import status


def test_forum_health_check_redis_offline(client):
    # Khi Redis không chạy trong môi trường test -> trả về 503 với redis: error, db: ok
    res = client.get("/health")
    assert res.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    data = res.json()
    assert data["status"] == "error"
    assert data["db"] == "ok"
    assert data["redis"] == "error"
    assert "x-request-id" in res.headers


def test_forum_health_check_all_ok(client, monkeypatch):
    # Giả lập Redis ping thành công -> trả về 200 OK
    from app.core import cache

    monkeypatch.setattr(cache.redis_client, "ping", lambda: True)

    res = client.get("/health")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["status"] == "ok"
    assert data["db"] == "ok"
    assert data["redis"] == "ok"
    assert "x-request-id" in res.headers


def test_request_id_tracing_middleware(client):
    # Gửi kèm header X-Request-ID tuỳ chọn -> API phải giữ nguyên header đó
    custom_id = "test-request-id-12345"
    res = client.get("/health", headers={"X-Request-ID": custom_id})
    assert res.headers["x-request-id"] == custom_id
