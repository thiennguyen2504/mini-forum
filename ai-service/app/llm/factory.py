from typing import Optional

from app.config import Settings, get_settings
from app.llm.base import LLMClient
from app.llm.fake import FakeLLMClient
from app.llm.gemini_client import GeminiClient


def get_llm_client(settings: Optional[Settings] = None) -> LLMClient:
    """
    Factory tạo LLMClient tương ứng với biến môi trường LLM_PROVIDER.
    - 'gemini': gọi Gemini API thật qua google-genai.
    - 'fake': dùng FakeLLMClient (chế độ heuristic cho demo, scripted cho test).
    """
    if settings is None:
        settings = get_settings()

    if settings.LLM_PROVIDER == "fake":
        return FakeLLMClient(mode="heuristic", model=settings.GEMINI_MODEL)

    return GeminiClient(
        api_key=settings.GEMINI_API_KEY,
        model=settings.GEMINI_MODEL,
        safety_level=settings.GEMINI_SAFETY_LEVEL,
        timeout_seconds=settings.LLM_TIMEOUT_SECONDS,
        max_output_tokens=settings.LLM_MAX_OUTPUT_TOKENS,
    )
