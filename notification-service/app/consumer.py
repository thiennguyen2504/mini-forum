import asyncio
import json
import logging
from aiokafka import AIOKafkaConsumer

from app.config import KAFKA_BOOTSTRAP_SERVERS, KAFKA_GROUP_ID, KAFKA_TOPIC
from app.db import SessionLocal
from app.models import Notification

logger = logging.getLogger(__name__)

_consumer_active: bool = False


def is_consumer_running() -> bool:
    """Trả về trạng thái hoạt động của Kafka consumer."""
    return _consumer_active


async def start_consumer():
    """
    Kafka consumer background loop.
    Lắng nghe event từ topic comment.created và tạo notification tương ứng.
    Tự động retry kết nối nếu Kafka chưa sẵn sàng.
    """
    global _consumer_active
    logger.info("Khởi động Kafka Consumer cho topic '%s'...", KAFKA_TOPIC)

    while True:
        consumer = None
        try:
            consumer = AIOKafkaConsumer(
                KAFKA_TOPIC,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                group_id=KAFKA_GROUP_ID,
                auto_offset_reset="earliest",
                enable_auto_commit=True,
                auto_commit_interval_ms=1000,
            )
            await consumer.start()
            _consumer_active = True
            logger.info("Kafka Consumer đã kết nối thành công tới %s!", KAFKA_BOOTSTRAP_SERVERS)

            async for msg in consumer:
                try:
                    payload = json.loads(msg.value.decode("utf-8"))
                    logger.info("Nhận event Kafka comment.created: %s", payload)

                    post_owner_id = payload.get("post_owner_id")
                    if not post_owner_id:
                        continue

                    comment_author_name = payload.get("comment_author_name", "Anonymous")
                    post_id = payload.get("post_id")
                    content_preview = payload.get("content_preview", "")

                    message_text = (
                        f"User '{comment_author_name}' đã bình luận về bài viết #{post_id}: {content_preview}"
                    )

                    db = SessionLocal()
                    try:
                        notif = Notification(
                            user_id=post_owner_id,
                            message=message_text,
                            is_read=False,
                        )
                        db.add(notif)
                        db.commit()
                        logger.info("Đã tạo notification id=%s cho user_id=%s", notif.id, post_owner_id)
                    finally:
                        db.close()

                except Exception as exc:
                    logger.error("Lỗi khi xử lý message Kafka: %s", exc)

        except asyncio.CancelledError:
            logger.info("Kafka Consumer nhận tín hiệu dừng.")
            _consumer_active = False
            if consumer:
                await consumer.stop()
            break
        except Exception as exc:
            _consumer_active = False
            logger.warning("Kafka Consumer mất kết nối hoặc lỗi: %s. Thử lại sau 3s...", exc)
            if consumer:
                try:
                    await consumer.stop()
                except Exception:
                    pass
            await asyncio.sleep(3)
