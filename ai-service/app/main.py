import logging
import time
import uuid
from fastapi import FastAPI, Request

from app.errors import register_exception_handlers
from app.logging import setup_logging
from app.routers.analyze import router as analyze_router

# Khởi tạo structured JSON logging
setup_logging("ai-service")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Mini Blog - AI Microservice",
    description=(
        "Microservice phân tích bài viết bằng LLM (Gemini) với Structured Output, "
        "hỗ trợ gợi ý tag, tóm tắt, phát hiện chủ đề, cảm xúc và kiểm duyệt nội dung an toàn."
    ),
    version="1.0.0",
)

# Đăng ký exception handlers định dạng lỗi chuẩn
register_exception_handlers(app)


# Middleware Tracing & Logging
@app.middleware("http")
async def tracing_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
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


# Gắn router
app.include_router(analyze_router)
