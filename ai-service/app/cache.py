import json
import logging
import time
from typing import Any, Optional
import redis

from app.config import get_settings

logger = logging.getLogger(__name__)

_settings = get_settings()
_redis_url = _settings.get_redis_url()

redis_client: redis.Redis = redis.from_url(
    _redis_url,
    decode_responses=True,
    socket_connect_timeout=0.5,
    socket_timeout=0.5,
    retry_on_timeout=False,
)

# Cooldown circuit breaker khi Redis offline để tránh delay lặp lại trên mọi request
_offline_cooldown_until: float = 0.0


def _mark_offline() -> None:
    global _offline_cooldown_until
    _offline_cooldown_until = time.time() + 2.0


def _is_offline() -> bool:
    return time.time() < _offline_cooldown_until


def _mark_online() -> None:
    global _offline_cooldown_until
    _offline_cooldown_until = 0.0


def check_redis() -> bool:
    """Kiểm tra Redis sẵn sàng hay không (phục vụ health check)."""
    try:
        return bool(redis_client.ping())
    except Exception:
        return False


def get_analysis(key: str) -> Optional[dict[str, Any]]:
    """
    Lấy kết quả phân tích JSON từ Redis.
    Nếu không có hoặc Redis lỗi, trả về None (fail-open).
    """
    if _is_offline():
        return None

    try:
        raw_val = redis_client.get(key)
        _mark_online()
        if raw_val is None:
            return None
        return json.loads(raw_val)
    except (redis.ConnectionError, redis.TimeoutError) as exc:
        _mark_offline()
        logger.warning("Redis connection error in get_analysis('%s'): %s", key, exc)
        return None
    except (redis.RedisError, json.JSONDecodeError) as exc:
        logger.warning("Redis error in get_analysis('%s'): %s", key, exc)
        return None


def set_analysis(key: str, value: Any, ttl: int = 21600) -> bool:
    """
    Lưu kết quả phân tích vào Redis kèm TTL.
    Nếu Redis lỗi, ghi log warning và trả về False mà không làm hỏng flow.
    """
    if _is_offline():
        return False

    try:
        if hasattr(value, "model_dump"):
            payload = value.model_dump(mode="json")
        else:
            payload = value
        serialized = json.dumps(payload, ensure_ascii=False)
        redis_client.setex(key, ttl, serialized)
        _mark_online()
        return True
    except (redis.ConnectionError, redis.TimeoutError) as exc:
        _mark_offline()
        logger.warning("Redis connection error in set_analysis('%s'): %s", key, exc)
        return False
    except (redis.RedisError, TypeError) as exc:
        logger.warning("Redis error in set_analysis('%s'): %s", key, exc)
        return False
