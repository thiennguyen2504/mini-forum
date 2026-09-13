import json
import logging
import os
import time
from typing import Any, Optional

import redis

logger = logging.getLogger(__name__)

# Đọc cấu hình REDIS_URL từ môi trường (mặc định 127.0.0.1 để tránh delay phân giải IPv6 trên Windows)
_raw_redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
if "://localhost:" in _raw_redis_url:
    _raw_redis_url = _raw_redis_url.replace("://localhost:", "://127.0.0.1:")

REDIS_URL = _raw_redis_url

redis_client: redis.Redis = redis.from_url(
    REDIS_URL,
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


def get_json(key: str) -> Optional[Any]:
    """
    Lấy dữ liệu JSON từ Redis theo key.
    Nếu không có hoặc Redis gặp lỗi kết nối, trả về None và log warning.
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
        logger.warning("Redis connection error in get_json('%s'): %s", key, exc)
        return None
    except (redis.RedisError, json.JSONDecodeError) as exc:
        logger.warning("Redis error in get_json('%s'): %s", key, exc)
        return None


def set_json(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """
    Lưu dữ liệu vào Redis dưới dạng chuỗi JSON kèm TTL (giây).
    Hỗ trợ Pydantic model, dict, list, datetime.
    Nếu Redis gặp lỗi kết nối, trả về False và log warning.
    """
    if _is_offline():
        return False

    try:
        if hasattr(value, "model_dump"):
            payload = value.model_dump(mode="json")
        else:
            payload = value
        serialized = json.dumps(payload, default=str)
        if ttl:
            redis_client.setex(key, ttl, serialized)
        else:
            redis_client.set(key, serialized)
        _mark_online()
        return True
    except (redis.ConnectionError, redis.TimeoutError) as exc:
        _mark_offline()
        logger.warning("Redis connection error in set_json('%s'): %s", key, exc)
        return False
    except (redis.RedisError, TypeError) as exc:
        logger.warning("Redis error in set_json('%s'): %s", key, exc)
        return False


def delete_prefix(prefix: str) -> int:
    """
    Xoá tất cả các key có tiền tố prefix bằng lệnh SCAN (scan_iter).
    Không dùng KEYS để tránh block Redis server.
    Nếu Redis gặp lỗi kết nối, trả về 0 và log warning.
    """
    if _is_offline():
        return 0

    try:
        deleted = 0
        batch: list[str] = []
        pattern = f"{prefix}*"
        for key in redis_client.scan_iter(match=pattern, count=100):
            batch.append(key)
            if len(batch) >= 100:
                deleted += redis_client.delete(*batch)
                batch = []
        if batch:
            deleted += redis_client.delete(*batch)
        _mark_online()
        return deleted
    except (redis.ConnectionError, redis.TimeoutError) as exc:
        _mark_offline()
        logger.warning("Redis connection error in delete_prefix('%s'): %s", prefix, exc)
        return 0
    except redis.RedisError as exc:
        logger.warning("Redis error in delete_prefix('%s'): %s", prefix, exc)
        return 0


def delete_key(key: str) -> bool:
    """
    Xoá một key đơn lẻ khỏi Redis.
    Nếu Redis gặp lỗi kết nối, trả về False và log warning.
    """
    if _is_offline():
        return False

    try:
        redis_client.delete(key)
        _mark_online()
        return True
    except (redis.ConnectionError, redis.TimeoutError) as exc:
        _mark_offline()
        logger.warning("Redis connection error in delete_key('%s'): %s", key, exc)
        return False
    except redis.RedisError as exc:
        logger.warning("Redis error in delete_key('%s'): %s", key, exc)
        return False
