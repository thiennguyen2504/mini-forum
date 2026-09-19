import uuid
from fastapi import APIRouter, Depends, Request, status

from app.auth import require_auth
from app.cache import check_redis
from app.config import Settings, get_settings
from app.schemas import AnalyzeRequest, AnalyzeResponse, HealthResponse
from app.services.analyzer import AnalyzerService

router = APIRouter(
    prefix="/ai",
    tags=["AI Analysis"],
)


def get_analyzer_service(settings: Settings = Depends(get_settings)) -> AnalyzerService:
    return AnalyzerService(settings=settings)


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Phân tích nội dung bài viết bằng LLM (Gemini)",
    description=(
        "Nhận tiêu đề và nội dung bài viết, gọi LLM phân tích có cấu trúc chặt chẽ "
        "(tóm tắt, tags gợi ý, chủ đề, sắc thái cảm xúc, ngôn ngữ, và kiểm duyệt an toàn nội dung). "
        "Hỗ trợ caching kết quả trên Redis để tối ưu độ trễ và chi phí."
    ),
    responses={
        401: {"description": "Chưa xác thực hoặc token không hợp lệ (khi AI_REQUIRE_AUTH=true)"},
        422: {"description": "Dữ liệu đầu vào sai schema hoặc nội dung bị chặn bởi bộ lọc an toàn"},
        502: {"description": "Phản hồi từ LLM không đúng định dạng schema sau các lần thử lại"},
        503: {"description": "Dịch vụ LLM không khả dụng (hết quota, 5xx) hoặc chưa cấu hình API key"},
        504: {"description": "Quá thời gian chờ phản hồi từ LLM"},
    },
)
async def analyze_post(
    request: Request,
    payload: AnalyzeRequest,
    user_id: str = Depends(require_auth),
    service: AnalyzerService = Depends(get_analyzer_service),
) -> AnalyzeResponse:
    request_id = getattr(request.state, "request_id", "") or request.headers.get("X-Request-ID") or str(uuid.uuid4())
    return await service.analyze(payload, request_id=request_id)


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Kiểm tra trạng thái sẵn sàng của ai-service",
    description="Trả về tình trạng hoạt động của service, provider, model và Redis (không gọi LLM thật để tránh chi phí).",
)
async def health_check(settings: Settings = Depends(get_settings)) -> HealthResponse:
    redis_ok = check_redis()
    redis_status = "ok" if redis_ok else "error"

    # Nếu LLM provider là gemini nhưng chưa có API key thì báo degraded
    if settings.LLM_PROVIDER == "gemini" and not settings.GEMINI_API_KEY:
        service_status = "degraded"
    else:
        service_status = "ok"

    return HealthResponse(
        status=service_status,
        provider=settings.LLM_PROVIDER,
        model=settings.GEMINI_MODEL,
        redis=redis_status,
    )
