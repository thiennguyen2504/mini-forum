from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class AnalyzeOptions(BaseModel):
    """Tuỳ chọn phân tích."""

    max_tags: int = Field(default=5, ge=1, le=5, description="Số lượng tag tối đa gợi ý (1–5)")
    skip_cache: bool = Field(default=False, description="Bỏ qua đọc cache (vẫn ghi cache nếu thành công)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "max_tags": 5,
                "skip_cache": False,
            }
        }
    )


class AnalyzeRequest(BaseModel):
    """Payload yêu cầu phân tích bài viết."""

    title: str = Field(..., min_length=1, max_length=200, description="Tiêu đề bài viết (1–200 ký tự)")
    content: Optional[str] = Field(default=None, description="Nội dung bài viết (tuỳ chọn hoặc null)")
    options: AnalyzeOptions = Field(default_factory=AnalyzeOptions, description="Các tuỳ chọn thêm")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Hướng dẫn FastAPI và Pydantic v2",
                "content": "FastAPI là framework hiện đại, hiệu năng cao để xây dựng API với Python 3.8+...",
                "options": {
                    "max_tags": 5,
                    "skip_cache": False,
                },
            }
        }
    )


class Moderation(BaseModel):
    """Kết quả kiểm duyệt nội dung."""

    is_safe: bool = Field(..., description="Nội dung an toàn, không vi phạm quy chuẩn")
    categories: list[Literal["spam", "toxicity", "adult", "scam", "off_topic"]] = Field(
        default_factory=list,
        description="Các danh mục vi phạm phát hiện được",
    )
    severity: Literal["none", "low", "medium", "high"] = Field(
        default="none",
        description="Mức độ nghiêm trọng của vi phạm",
    )
    reason: str = Field(
        default="",
        max_length=200,
        description="Lý do tóm tắt cho đánh giá kiểm duyệt (tối đa 200 ký tự)",
    )

    @model_validator(mode="after")
    def validate_consistency(self) -> "Moderation":
        """
        Ràng buộc nhất quán:
        - is_safe = True => categories = [] và severity = 'none'
        - is_safe = False => severity != 'none' và categories có ít nhất 1 mục
        """
        if self.is_safe:
            if self.categories or self.severity != "none":
                raise ValueError("Khi is_safe=True, categories phải rỗng và severity phải là 'none'")
        else:
            if self.severity == "none":
                raise ValueError("Khi is_safe=False, severity không thể là 'none'")
            if not self.categories:
                raise ValueError("Khi is_safe=False, phải chỉ rõ ít nhất 1 danh mục vi phạm trong categories")
        return self


class PostAnalysis(BaseModel):
    """Cấu trúc dữ liệu phân tích bài viết trả về từ LLM."""

    summary: str = Field(..., max_length=300, description="Tóm tắt ngắn gọn bài viết (tối đa 300 ký tự)")
    tags: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="Danh sách tag liên quan (tối đa 5 tag)",
    )
    topic: Literal["tech", "question", "news", "discussion", "life", "other"] = Field(
        ...,
        description="Chủ đề chính của bài viết",
    )
    sentiment: Literal["positive", "neutral", "negative"] = Field(
        ...,
        description="Sắc thái cảm xúc của bài viết",
    )
    language: Literal["vi", "en", "other"] = Field(
        ...,
        description="Ngôn ngữ chính (vi: tiếng Việt, en: tiếng Anh, other: khác)",
    )
    moderation: Moderation = Field(..., description="Đánh giá kiểm duyệt an toàn nội dung")


class AnalysisMeta(BaseModel):
    """Metadata về quá trình phân tích."""

    model: str = Field(..., description="Tên mô hình LLM đã dùng")
    prompt_version: str = Field(..., description="Phiên bản prompt được áp dụng")
    latency_ms: float = Field(..., description="Thời gian thực thi tính bằng mili-giây")
    cached: bool = Field(..., description="Kết quả lấy từ cache hay gọi mới")
    retries: int = Field(default=0, description="Số lần đã thử lại khi phân tích")
    request_id: str = Field(..., description="ID truy vết request")


class AnalyzeResponse(BaseModel):
    """Response trả về thành công cho endpoint /ai/analyze."""

    data: PostAnalysis
    meta: AnalysisMeta


class ErrorDetail(BaseModel):
    """Chi tiết lỗi chuẩn hoá."""

    code: str
    message: str
    request_id: str


class ErrorResponse(BaseModel):
    """Format body lỗi chuẩn của ai-service."""

    error: ErrorDetail


class HealthResponse(BaseModel):
    """Response cho endpoint /ai/health."""

    status: Literal["ok", "degraded", "error"]
    provider: str
    model: str
    redis: Literal["ok", "error"]
