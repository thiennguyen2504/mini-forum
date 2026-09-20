import os
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Cấu hình cho microservice ai-service.
    Tự động đọc từ biến môi trường hoặc file .env nếu có.
    """

    # Gemini & LLM settings
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_SAFETY_LEVEL: str = "BLOCK_ONLY_HIGH"
    LLM_PROVIDER: Literal["gemini", "fake"] = "gemini"
    LLM_TIMEOUT_SECONDS: float = 20.0
    LLM_MAX_RETRIES: int = 2
    LLM_MAX_OUTPUT_TOKENS: int = 1024

    # AI Service application settings
    AI_CACHE_TTL_SECONDS: int = 21600  # 6 giờ
    AI_REQUIRE_AUTH: bool = True
    AI_MAX_INPUT_CHARS: int = 6000
    AI_PROMPT_VERSION: str = "v2"

    # Security & Auth (khớp với forum-service)
    SECRET_KEY: str = "mini-blog-secret-key-change-in-production"
    ALGORITHM: str = "HS256"

    # Redis Cache
    REDIS_URL: str = "redis://127.0.0.1:6379/0"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def get_redis_url(self) -> str:
        """Chuẩn hoá localhost thành 127.0.0.1 trên Windows nếu cần."""
        url = self.REDIS_URL
        if "://localhost:" in url:
            url = url.replace("://localhost:", "://127.0.0.1:")
        return url


@lru_cache
def get_settings() -> Settings:
    """Trả về singleton instance của cấu hình."""
    # Hỗ trợ fallback linh hoạt từ os.environ
    raw_auth = os.getenv("AI_REQUIRE_AUTH")
    auth_bool = True
    if raw_auth is not None:
        auth_bool = raw_auth.lower() in ("true", "1", "yes")

    settings = Settings(
        GEMINI_API_KEY=os.getenv("GEMINI_API_KEY", ""),
        GEMINI_MODEL=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        GEMINI_SAFETY_LEVEL=os.getenv("GEMINI_SAFETY_LEVEL", "BLOCK_ONLY_HIGH"),
        LLM_PROVIDER=os.getenv("LLM_PROVIDER", "gemini"),  # type: ignore[arg-type]
        LLM_TIMEOUT_SECONDS=float(os.getenv("LLM_TIMEOUT_SECONDS", "20.0")),
        LLM_MAX_RETRIES=int(os.getenv("LLM_MAX_RETRIES", "2")),
        LLM_MAX_OUTPUT_TOKENS=int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "1024")),
        AI_CACHE_TTL_SECONDS=int(os.getenv("AI_CACHE_TTL_SECONDS", "21600")),
        AI_REQUIRE_AUTH=auth_bool,
        AI_MAX_INPUT_CHARS=int(os.getenv("AI_MAX_INPUT_CHARS", "6000")),
        AI_PROMPT_VERSION=os.getenv("AI_PROMPT_VERSION", "v2"),
        SECRET_KEY=os.getenv("SECRET_KEY", "mini-blog-secret-key-change-in-production"),
        ALGORITHM=os.getenv("ALGORITHM", "HS256"),
        REDIS_URL=os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"),
    )
    return settings
