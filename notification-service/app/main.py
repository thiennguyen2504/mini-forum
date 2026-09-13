import asyncio
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.consumer import start_consumer
from app.db import get_db
from app.models import Notification
from app.schemas import NotificationOut


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


@app.get("/health", tags=["Health"], summary="Health check cho notification-service")
@app.get("/notifications/health", tags=["Health"], summary="Health check qua proxy /notifications/*")
def health_check():
    return {"status": "ok", "service": "notification-service"}


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
