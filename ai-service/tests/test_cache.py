from unittest.mock import MagicMock
import redis

from app import cache
from app.cache import (
    _mark_offline,
    _mark_online,
    check_redis,
    get_analysis,
    set_analysis,
)


def test_cache_set_and_get_memory(monkeypatch):
    store = {}
    mock_redis = MagicMock()
    mock_redis.get.side_effect = lambda k: store.get(k)
    mock_redis.setex.side_effect = lambda k, ttl, v: store.update({k: v})
    mock_redis.ping.return_value = True

    monkeypatch.setattr(cache, "redis_client", mock_redis)
    _mark_online()

    sample_val = {
        "summary": "Tóm tắt",
        "tags": ["python"],
        "topic": "tech",
        "sentiment": "neutral",
        "language": "vi",
        "moderation": {"is_safe": True, "categories": [], "severity": "none", "reason": ""},
    }

    assert set_analysis("test_key", sample_val, ttl=60) is True
    res = get_analysis("test_key")
    assert res == sample_val
    assert check_redis() is True


def test_cache_fail_open_on_connection_error(monkeypatch):
    mock_redis = MagicMock()
    mock_redis.get.side_effect = redis.ConnectionError("Connection refused")
    mock_redis.setex.side_effect = redis.ConnectionError("Connection refused")
    mock_redis.ping.side_effect = redis.ConnectionError("Connection refused")

    monkeypatch.setattr(cache, "redis_client", mock_redis)
    _mark_online()

    # Fail open: không raise lỗi, trả về None / False
    assert get_analysis("some_key") is None
    assert set_analysis("some_key", {"data": 123}, ttl=60) is False
    assert check_redis() is False

    _mark_online()  # Reset cooldown sau test
