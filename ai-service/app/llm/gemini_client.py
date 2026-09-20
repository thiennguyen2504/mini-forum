import asyncio
import json
import logging
import re
import time
from typing import Any, Optional
from pydantic import BaseModel

from app.errors import (
    ContentBlockedError,
    LLMInvalidOutputError,
    LLMTimeoutError,
    LLMUnavailableError,
)
from app.llm.base import LLMResult, TokenUsage

logger = logging.getLogger(__name__)


class GeminiClient:
    """
    Client kết nối trực tiếp với Google Gemini API thông qua google-genai SDK.
    Hỗ trợ cấu hình Structured Output, Safety Settings và timeout.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash",
        safety_level: str = "BLOCK_ONLY_HIGH",
        timeout_seconds: float = 20.0,
        max_output_tokens: int = 1024,
    ):
        self.api_key = api_key
        self.model = model
        self.safety_level = safety_level
        self.timeout_seconds = timeout_seconds
        self.max_output_tokens = max_output_tokens

        self._client = None
        if self.api_key:
            from google import genai

            self._client = genai.Client(api_key=self.api_key)

    def _build_safety_settings(self) -> list[Any]:
        """Xây dựng danh sách SafetySetting dựa trên safety_level cấu hình."""
        from google.genai import types

        threshold_map = {
            "BLOCK_NONE": types.HarmBlockThreshold.BLOCK_NONE,
            "BLOCK_ONLY_HIGH": types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
            "BLOCK_MEDIUM_AND_ABOVE": types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            "BLOCK_LOW_AND_ABOVE": types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
        }
        threshold = threshold_map.get(self.safety_level, types.HarmBlockThreshold.BLOCK_ONLY_HIGH)

        categories = [
            types.HarmCategory.HARM_CATEGORY_HARASSMENT,
            types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        ]

        return [types.SafetySetting(category=cat, threshold=threshold) for cat in categories]

    async def generate(
        self,
        system_instruction: str,
        user_content: str,
        schema: Optional[type[BaseModel]] = None,
    ) -> LLMResult:
        if not self.api_key or self._client is None:
            raise LLMUnavailableError("Chưa cấu hình GEMINI_API_KEY trong môi trường")

        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0.1,
            max_output_tokens=self.max_output_tokens,
            safety_settings=self._build_safety_settings(),
        )

        start_time = time.perf_counter()

        try:
            call_coro = self._client.aio.models.generate_content(
                model=self.model,
                contents=user_content,
                config=config,
            )
            response = await asyncio.wait_for(call_coro, timeout=self.timeout_seconds)
        except asyncio.TimeoutError:
            raise LLMTimeoutError(f"Quá thời gian {self.timeout_seconds}s khi gọi Gemini API")
        except Exception as exc:
            err_msg = str(exc)
            logger.warning("Gemini API call failed with exception: %s", exc)
            if "429" in err_msg or "ResourceExhausted" in err_msg or "503" in err_msg or "Unavailable" in err_msg:
                raise LLMUnavailableError(f"Gemini API quá tải hoặc không khả dụng: {exc}")
            if "SAFETY" in err_msg or "Blocked" in err_msg:
                raise ContentBlockedError(f"Gemini chặn yêu cầu vì lý do an toàn: {exc}")
            raise LLMUnavailableError(f"Lỗi khi giao tiếp với Gemini API: {exc}")

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # 1. Kiểm tra Prompt Feedback
        if hasattr(response, "prompt_feedback") and response.prompt_feedback:
            block_reason = getattr(response.prompt_feedback, "block_reason", None)
            if block_reason:
                raise ContentBlockedError(f"Gemini chặn prompt vì lý do an toàn: {block_reason}")

        # 2. Kiểm tra Candidate Finish Reason
        if hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]
            finish_reason = str(getattr(candidate, "finish_reason", ""))
            if any(term in finish_reason for term in ["SAFETY", "BLOCKLIST", "PROHIBITED_CONTENT"]):
                raise ContentBlockedError(f"Gemini chặn output vì lý do an toàn ({finish_reason})")
            if "MAX_TOKENS" in finish_reason and not (response.text and response.text.strip()):
                raise LLMInvalidOutputError("Gemini chạm giới hạn token (MAX_TOKENS) và trả về output rỗng")

        raw_text = getattr(response, "text", None)
        if not raw_text or not raw_text.strip():
            raise LLMInvalidOutputError("Gemini trả về phản hồi rỗng")

        # 3. Parse JSON từ text
        clean_text = raw_text.strip()
        # Loại bỏ markdown code block nếu Gemini có kèm ```json ... ```
        if clean_text.startswith("```"):
            clean_text = re.sub(r"^```(?:json)?\n?", "", clean_text)
            clean_text = re.sub(r"\n?```$", "", clean_text).strip()

        try:
            parsed_data = json.loads(clean_text)
        except json.JSONDecodeError as exc:
            raise LLMInvalidOutputError(f"Phản hồi từ Gemini không phải JSON hợp lệ: {exc}")

        # 4. Trích xuất Usage Metadata
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            meta = response.usage_metadata
            prompt_tokens = getattr(meta, "prompt_token_count", 0) or 0
            completion_tokens = getattr(meta, "candidates_token_count", 0) or 0
            total_tokens = getattr(meta, "total_token_count", 0) or (prompt_tokens + completion_tokens)

        return LLMResult(
            data=parsed_data,
            usage=TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            ),
            latency_ms=latency_ms,
            model=self.model,
            raw_text=raw_text,
        )
