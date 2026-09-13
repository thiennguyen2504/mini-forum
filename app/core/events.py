import asyncio
import json
import logging
import os
import threading
from typing import Any, Optional

logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC_COMMENT_CREATED = "comment.created"

_loop: Optional[asyncio.AbstractEventLoop] = None
_producer = None
_lock = threading.Lock()


def _get_or_create_loop() -> asyncio.AbstractEventLoop:
    global _loop
    if _loop is None:
        with _lock:
            if _loop is None:
                loop = asyncio.new_event_loop()
                thread = threading.Thread(
                    target=loop.run_forever,
                    daemon=True,
                    name="KafkaProducerLoop",
                )
                thread.start()
                _loop = loop
    return _loop


async def _get_producer():
    global _producer
    if _producer is None:
        from aiokafka import AIOKafkaProducer

        producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            request_timeout_ms=2000,
            retry_backoff_ms=500,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
        )
        await producer.start()
        _producer = producer
    return _producer


async def _async_publish(payload: dict[str, Any]) -> None:
    global _producer
    try:
        producer = await _get_producer()
        await producer.send_and_wait(TOPIC_COMMENT_CREATED, payload)
        logger.info(
            "[Kafka] Published event to '%s': comment_id=%s, post_id=%s, to_user=%s",
            TOPIC_COMMENT_CREATED,
            payload.get("comment_id"),
            payload.get("post_id"),
            payload.get("post_owner_id"),
        )
    except Exception as exc:
        logger.warning("[Kafka] Failed to publish event to topic '%s': %s", TOPIC_COMMENT_CREATED, exc)
        if _producer is not None:
            try:
                await _producer.stop()
            except Exception:
                pass
            _producer = None


def publish_comment_created(
    comment_id: int,
    post_id: int,
    post_owner_id: int,
    comment_author_id: int,
    comment_author_name: str,
    content_preview: str,
    created_at: str,
) -> None:
    """
    Publish event comment.created lên Kafka theo cơ chế async/lazy non-blocking.
    Nếu Kafka tạm thời không sẵn sàng, ghi log warning và không raise exception.
    """
    payload = {
        "comment_id": comment_id,
        "post_id": post_id,
        "post_owner_id": post_owner_id,
        "comment_author_id": comment_author_id,
        "comment_author_name": comment_author_name,
        "content_preview": content_preview,
        "created_at": created_at,
    }
    try:
        loop = _get_or_create_loop()
        asyncio.run_coroutine_threadsafe(_async_publish(payload), loop)
    except Exception as exc:
        logger.warning("[Kafka] Error scheduling publish_comment_created: %s", exc)
