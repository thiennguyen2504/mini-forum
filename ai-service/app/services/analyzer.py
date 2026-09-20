import asyncio
import hashlib
import logging
import time
from typing import Optional
from pydantic import ValidationError

from app.cache import get_analysis, set_analysis
from app.config import Settings, get_settings
from app.errors import (
    AIServiceError,
    ContentBlockedError,
    LLMInvalidOutputError,
    LLMTimeoutError,
    LLMUnavailableError,
)
from app.llm.base import LLMClient
from app.llm.factory import get_llm_client
from app.normalize import normalize_tags, sanitize_post_input
from app.prompts.loader import load_prompt
from app.schemas import (
    AnalysisMeta,
    AnalyzeRequest,
    AnalyzeResponse,
    PostAnalysis,
)

logger = logging.getLogger(__name__)


class AnalyzerService:
    """
    Service điều phối phân tích bài viết:
    Sanitize -> Cache check -> Call LLM & Retry loop -> Schema Validation -> Tag normalization -> Log -> Cache save.
    """

    def __init__(self, settings: Optional[Settings] = None, client: Optional[LLMClient] = None):
        self.settings = settings or get_settings()
        self.client = client or get_llm_client(self.settings)

    async def analyze(self, payload: AnalyzeRequest, request_id: str) -> AnalyzeResponse:
        start_time = time.perf_counter()
        options = payload.options

        # 1. Sanitize input
        xml_input, truncated, raw_len = sanitize_post_input(
            title=payload.title,
            content=payload.content,
            max_chars=self.settings.AI_MAX_INPUT_CHARS,
        )

        content_raw = (payload.title.strip() + (payload.content or "").strip()).encode("utf-8")
        content_hash = hashlib.sha256(content_raw).hexdigest()
        content_sha256_prefix = content_hash[:8]

        prompt_version = self.settings.AI_PROMPT_VERSION
        system_prompt, _ = load_prompt(prompt_version)

        # 2. Kiểm tra Cache (nếu không skip_cache)
        model_name = getattr(self.client, "model", self.settings.GEMINI_MODEL)
        cache_key = f"ai:analyze:{prompt_version}:{model_name}:{options.max_tags}:{content_hash}"

        if not options.skip_cache:
            cached_data = get_analysis(cache_key)
            if cached_data is not None:
                try:
                    analysis_data = PostAnalysis.model_validate(cached_data)
                    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                    logger.info(
                        "Analysis served from cache",
                        extra={
                            "request_id": request_id,
                            "prompt_version": prompt_version,
                            "model": model_name,
                            "latency_ms": latency_ms,
                            "prompt_tokens": 0,
                            "completion_tokens": 0,
                            "retries": 0,
                            "cached": True,
                            "content_sha256_prefix": content_sha256_prefix,
                            "content_len": raw_len,
                            "truncated": truncated,
                        },
                    )
                    return AnalyzeResponse(
                        data=analysis_data,
                        meta=AnalysisMeta(
                            model=model_name,
                            prompt_version=prompt_version,
                            latency_ms=latency_ms,
                            cached=True,
                            retries=0,
                            request_id=request_id,
                        ),
                    )
                except Exception as exc:
                    logger.warning("Failed to validate cached analysis, falling back to LLM: %s", exc)

        # 3. Gọi LLM kèm Retry Loop
        max_retries = self.settings.LLM_MAX_RETRIES
        retries_done = 0
        last_error: Optional[Exception] = None
        user_input_attempt = xml_input

        analysis_data: Optional[PostAnalysis] = None

        total_prompt_tokens = 0
        total_completion_tokens = 0

        for attempt in range(max_retries + 1):
            if attempt > 0:
                retries_done += 1
                # Exponential backoff: 0.5s, 1.0s...
                backoff_time = 0.5 * (2 ** (attempt - 1))
                await asyncio.sleep(backoff_time)
                # Bổ sung thông điệp lỗi ngắn gọn vào prompt ở lần retry
                if last_error:
                    err_msg = str(last_error)[:200]
                    user_input_attempt = (
                        f"{xml_input}\n\n"
                        f"[NOTE: Previous attempt failed validation with error: '{err_msg}'. "
                        f"Please strictly comply with the requested JSON schema.]"
                    )

            try:
                llm_res = await self.client.generate(
                    system_instruction=system_prompt,
                    user_content=user_input_attempt,
                    schema=PostAnalysis,
                )
                total_prompt_tokens += llm_res.usage.prompt_tokens
                total_completion_tokens += llm_res.usage.completion_tokens

                # Validate chặt chẽ với Pydantic PostAnalysis
                analysis_data = PostAnalysis.model_validate(llm_res.data)
                break  # Thành công, thoát vòng lặp retry
            except ContentBlockedError:
                # Bị safety block: KHÔNG retry, không fake kết quả, raise ngay
                raise
            except (LLMInvalidOutputError, ValidationError) as exc:
                last_error = exc
                logger.warning("LLM attempt %d failed with schema/output error: %s", attempt + 1, exc)
            except LLMTimeoutError as exc:
                last_error = exc
                logger.warning("LLM attempt %d timed out: %s", attempt + 1, exc)
            except LLMUnavailableError as exc:
                last_error = exc
                if "Chưa cấu hình GEMINI_API_KEY" in str(exc):
                    # Lỗi cấu hình: KHÔNG retry
                    raise
                logger.warning("LLM attempt %d unavailable: %s", attempt + 1, exc)
            except Exception as exc:
                last_error = exc
                logger.warning("LLM attempt %d unexpected error: %s", attempt + 1, exc)

        # Nếu sau max_retries vẫn không có analysis_data
        if analysis_data is None:
            if isinstance(last_error, (ValidationError, LLMInvalidOutputError)):
                raise LLMInvalidOutputError(
                    f"Mô hình LLM không trả về kết quả đúng cấu trúc sau {max_retries} lần thử: {last_error}"
                )
            if isinstance(last_error, LLMTimeoutError):
                raise last_error
            if isinstance(last_error, LLMUnavailableError):
                raise last_error
            if isinstance(last_error, AIServiceError):
                raise last_error
            raise LLMInvalidOutputError(f"Không thể hoàn tất phân tích LLM: {last_error}")

        # 4. Chuẩn hoá Tags
        analysis_data.tags = normalize_tags(analysis_data.tags, max_tags=options.max_tags)

        # 5. Ghi Cache
        set_analysis(
            key=cache_key,
            value=analysis_data.model_dump(mode="json"),
            ttl=self.settings.AI_CACHE_TTL_SECONDS,
        )

        total_latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # 6. Structured JSON logging
        logger.info(
            "Post analysis completed",
            extra={
                "request_id": request_id,
                "prompt_version": prompt_version,
                "model": model_name,
                "latency_ms": total_latency_ms,
                "prompt_tokens": total_prompt_tokens,
                "completion_tokens": total_completion_tokens,
                "retries": retries_done,
                "cached": False,
                "content_sha256_prefix": content_sha256_prefix,
                "content_len": raw_len,
                "truncated": truncated,
            },
        )

        return AnalyzeResponse(
            data=analysis_data,
            meta=AnalysisMeta(
                model=model_name,
                prompt_version=prompt_version,
                latency_ms=total_latency_ms,
                cached=False,
                retries=retries_done,
                request_id=request_id,
            ),
        )
