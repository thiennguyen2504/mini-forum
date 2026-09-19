from typing import Any, Optional
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    """Lớp ngoại lệ cơ sở cho ai-service."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class UnauthorizedError(AIServiceError):
    def __init__(self, message: str = "Chưa xác thực hoặc token không hợp lệ"):
        super().__init__(
            message=message,
            code="UNAUTHORIZED",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class InvalidInputError(AIServiceError):
    def __init__(self, message: str = "Dữ liệu đầu vào không hợp lệ"):
        super().__init__(
            message=message,
            code="INVALID_INPUT",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class ContentBlockedError(AIServiceError):
    def __init__(self, message: str = "Nội dung bị chặn bởi bộ lọc an toàn"):
        super().__init__(
            message=message,
            code="CONTENT_BLOCKED",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class LLMInvalidOutputError(AIServiceError):
    def __init__(self, message: str = "Phản hồi từ mô hình LLM không hợp lệ sau các lần thử"):
        super().__init__(
            message=message,
            code="LLM_INVALID_OUTPUT",
            status_code=status.HTTP_502_BAD_GATEWAY,
        )


class LLMUnavailableError(AIServiceError):
    def __init__(self, message: str = "Dịch vụ LLM tạm thời không khả dụng hoặc chưa cấu hình API key"):
        super().__init__(
            message=message,
            code="LLM_UNAVAILABLE",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


class LLMTimeoutError(AIServiceError):
    def __init__(self, message: str = "Hết thời gian chờ phản hồi từ mô hình LLM"):
        super().__init__(
            message=message,
            code="LLM_TIMEOUT",
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        )


def _get_request_id(request: Request) -> str:
    """Lấy request_id từ request.state hoặc header X-Request-ID."""
    if hasattr(request.state, "request_id") and request.state.request_id:
        return str(request.state.request_id)
    return request.headers.get("X-Request-ID", "")


def make_error_payload(code: str, message: str, request_id: str) -> dict[str, Any]:
    """Tạo body lỗi chuẩn theo hợp đồng API."""
    return {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id,
        }
    }


def register_exception_handlers(app: FastAPI) -> None:
    """Đăng ký toàn bộ exception handlers cho FastAPI app."""

    @app.exception_handler(AIServiceError)
    async def ai_service_error_handler(request: Request, exc: AIServiceError):
        req_id = _get_request_id(request)
        return JSONResponse(
            status_code=exc.status_code,
            content=make_error_payload(exc.code, exc.message, req_id),
            headers={"X-Request-ID": req_id} if req_id else None,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        req_id = _get_request_id(request)
        errors = exc.errors()
        err_msg = "; ".join(f"{e.get('loc', ())}: {e.get('msg', '')}" for e in errors)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=make_error_payload("INVALID_INPUT", f"Dữ liệu không đúng schema: {err_msg}", req_id),
            headers={"X-Request-ID": req_id} if req_id else None,
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        req_id = _get_request_id(request)
        code = "HTTP_ERROR"
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            code = "UNAUTHORIZED"
        elif exc.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
            code = "INVALID_INPUT"
        elif exc.status_code == status.HTTP_502_BAD_GATEWAY:
            code = "LLM_INVALID_OUTPUT"
        elif exc.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            code = "LLM_UNAVAILABLE"
        elif exc.status_code == status.HTTP_504_GATEWAY_TIMEOUT:
            code = "LLM_TIMEOUT"

        msg = str(exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content=make_error_payload(code, msg, req_id),
            headers={"X-Request-ID": req_id} if req_id else None,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        req_id = _get_request_id(request)
        logger.error("Unhandled error occurred: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=make_error_payload("INTERNAL_ERROR", "Lỗi máy chủ nội bộ", req_id),
            headers={"X-Request-ID": req_id} if req_id else None,
        )
