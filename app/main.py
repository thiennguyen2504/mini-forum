from contextlib import asynccontextmanager
import logging
import time
import uuid

from fastapi import Depends, FastAPI, Request, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.events import shutdown_producer
from app.core.logging import setup_logging
from app.deps import get_db
from app.routers.auth import router as auth_router
from app.routers.comments import router as comments_router
from app.routers.posts import router as posts_router
from app.routers.users import router as users_router

setup_logging("forum-service")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    try:
        await shutdown_producer()
    except Exception as exc:
        logger.warning("Error during lifespan shutdown: %s", exc)


app = FastAPI(
    title="Mini Blog API",
    description=(
        "RESTful API cho ứng dụng blog đơn giản.\n\n"
        "## Tính năng\n"
        "- **Auth** — Đăng ký (`/auth/register`) và Đăng nhập (`/auth/token`) lấy JWT token\n"
        "- **Users** — Đăng ký và tra cứu tài khoản\n"
        "- **Posts** — Tạo (yêu cầu Token), đọc, cập nhật, xoá bài viết; gắn tag\n"
        "- **Comments** — Bình luận dưới bài viết (yêu cầu Token)\n\n"
    ),
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


# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(posts_router)
app.include_router(comments_router)


# ── Health check ─────────────────────────────────────────────────────────────
@app.get(
    "/health",
    tags=["Health"],
    summary="Kiểm tra trạng thái server, DB và Redis",
)
def health_check(response: Response, db: Session = Depends(get_db)):
    db_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        logger.warning("DB health check error: %s", exc)
        db_status = "error"

    redis_status = "ok"
    try:
        from app.core.cache import redis_client

        if not redis_client.ping():
            redis_status = "error"
    except Exception as exc:
        logger.warning("Redis health check error: %s", exc)
        redis_status = "error"

    all_ok = db_status == "ok" and redis_status == "ok"
    if not all_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ok" if all_ok else "error",
        "db": db_status,
        "redis": redis_status,
    }
