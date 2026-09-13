import asyncio
from contextlib import asynccontextmanager
import logging
import time
import uuid

from fastapi import Depends, FastAPI, Request, Response, Query, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.consumer import is_consumer_running, start_consumer
from app.db import get_db
from app.logging import setup_logging
from app.models import Notification
from app.schemas import NotificationOut

setup_logging("notification-service")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi động Kafka consumer chạy nền
    consumer_task = asyncio.create_task(start_consumer())
    try:
        yield
    finally:
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Notification Service",
    description="Microservice quản lý thông báo người dùng qua Kafka event stream.",
    lifespan=lifespan,
)


# ── Tracing & Logging Middleware ─────────────────────────────────────────────
@app.middleware("http")
async def tracing_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    start_time = time.perf_counter()

    logger.info(
        "Incoming request",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
        },
    )

    try:
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response.headers["X-Request-ID"] = request_id

        logger.info(
            "Request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response
    except Exception as exc:
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.error(
            "Request error: %s",
            exc,
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": 500,
                "duration_ms": duration_ms,
            },
            exc_info=True,
        )
        raise


# ── Health check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"], summary="Health check cho notification-service")
@app.get("/notifications/health", tags=["Health"], summary="Health check qua proxy /notifications/health")
def health_check(response: Response, db: Session = Depends(get_db)):
    db_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        logger.warning("DB health check error: %s", exc)
        db_status = "error"

    kafka_status = "ok" if is_consumer_running() else "error"

    all_ok = db_status == "ok" and kafka_status == "ok"
    if not all_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ok" if all_ok else "error",
        "db": db_status,
        "kafka": kafka_status,
    }


# ── Notification Endpoints ───────────────────────────────────────────────────
@app.get(
    "/notifications/{user_id}",
    response_model=list[NotificationOut],
    tags=["Notifications"],
    summary="Lấy danh sách thông báo của user",
)
def get_user_notifications(
    user_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = (
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())
