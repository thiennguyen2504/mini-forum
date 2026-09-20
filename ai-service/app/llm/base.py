from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, runtime_checkable
from pydantic import BaseModel


@dataclass
class TokenUsage:
    """Thống kê token sử dụng trong lượt gọi LLM."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class LLMResult:
    """Kết quả trả về từ LLM client sau khi phân tích."""

    data: dict[str, Any]
    usage: TokenUsage = field(default_factory=TokenUsage)
    latency_ms: float = 0.0
    model: str = "unknown"
    raw_text: Optional[str] = None


@runtime_checkable
class LLMClient(Protocol):
    """Giao diện chuẩn (Protocol) cho các LLM client."""

    async def generate(
        self,
        system_instruction: str,
        user_content: str,
        schema: Optional[type[BaseModel]] = None,
    ) -> LLMResult:
        """
        Gọi LLM để sinh nội dung có cấu trúc theo schema.
        Raises:
            ContentBlockedError: Khi nội dung bị chặn bởi safety filter.
            LLMTimeoutError: Khi quá thời gian timeout.
            LLMUnavailableError: Khi dịch vụ LLM không khả dụng (429, 5xx hoặc thiếu key).
            LLMInvalidOutputError: Khi output rỗng hoặc JSON không hợp lệ.
        """
        ...
