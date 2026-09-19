import logging
import os
from typing import Any, Optional
import httpx

logger = logging.getLogger(__name__)

AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://ai-service:8000").rstrip("/")
AI_CLIENT_TIMEOUT = float(os.getenv("AI_CLIENT_TIMEOUT", "25.0"))


class AiServiceError(Exception):
    """Lỗi nghiệp vụ khi tương tác với AI service."""

    def __init__(self, message: str, status_code: int = 503):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class AiServiceUnavailableError(AiServiceError):
    """Lỗi khi AI service không phản hồi, timeout hoặc lỗi kết nối."""

    def __init__(self, message: str = "AI service tạm thời không khả dụng"):
        super().__init__(message=message, status_code=503)


class AiClient:
    """
    Client HTTP đồng bộ để forum-service giao tiếp với ai-service.
    Tự động chuyển tiếp token xác thực và X-Request-ID.
    """

    def __init__(self, base_url: str = AI_SERVICE_URL, timeout: float = AI_CLIENT_TIMEOUT):
        self.base_url = base_url
        self.timeout = timeout

    def analyze_post(
        self,
        title: str,
        content: Optional[str] = None,
        token: Optional[str] = None,
        request_id: Optional[str] = None,
        max_tags: int = 5,
        skip_cache: bool = False,
    ) -> dict[str, Any]:
        """
        Gửi yêu cầu phân tích bài viết sang ai-service: POST /ai/analyze.
        """
        url = f"{self.base_url}/ai/analyze"
        headers: dict[str, str] = {
            "Content-Type": "application/json",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if request_id:
            headers["X-Request-ID"] = request_id

        payload = {
            "title": title,
            "content": content,
            "options": {
                "max_tags": max_tags,
                "skip_cache": skip_cache,
            },
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, json=payload, headers=headers)
        except (httpx.ConnectError, httpx.NetworkError) as exc:
            logger.warning("[AI Client] Connection error to %s: %s", url, exc)
            raise AiServiceUnavailableError(f"Không thể kết nối đến AI Service tại {self.base_url}")
        except httpx.TimeoutException as exc:
            logger.warning("[AI Client] Timeout (%ss) calling %s: %s", self.timeout, url, exc)
            raise AiServiceUnavailableError(f"Hết thời gian chờ AI Service ({self.timeout}s)")
        except Exception as exc:
            logger.warning("[AI Client] Unexpected error calling %s: %s", url, exc)
            raise AiServiceUnavailableError(f"Lỗi không xác định khi gọi AI Service: {exc}")

        if response.status_code != 200:
            error_detail = response.text
            try:
                err_json = response.json()
                if "error" in err_json and "message" in err_json["error"]:
                    error_detail = err_json["error"]["message"]
            except Exception:
                pass
            logger.warning("[AI Client] AI Service returned HTTP %d: %s", response.status_code, error_detail)
            raise AiServiceUnavailableError(f"AI Service trả về lỗi ({response.status_code}): {error_detail}")

        return response.json()


# Singleton instance
ai_client = AiClient()
