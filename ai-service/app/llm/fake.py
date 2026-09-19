import asyncio
import json
import re
import time
from typing import Any, Literal, Optional, Union
from pydantic import BaseModel

from app.errors import (
    ContentBlockedError,
    LLMInvalidOutputError,
    LLMTimeoutError,
    LLMUnavailableError,
)
from app.llm.base import LLMResult, TokenUsage


class FakeLLMClient:
    """
    Client LLM giả lập:
    - Mode 'scripted': trả kết quả hoặc ném ngoại lệ theo kịch bản xác định (phục vụ test).
    - Mode 'heuristic': phân tích nội dung dựa trên từ khoá (phục vụ demo offline).
    """

    def __init__(
        self,
        mode: Literal["scripted", "heuristic"] = "heuristic",
        scripted_responses: Optional[list[Union[dict[str, Any], Exception, str]]] = None,
        model: str = "fake-llm",
    ):
        self.mode = mode
        self.queue: list[Union[dict[str, Any], Exception, str]] = list(scripted_responses or [])
        self.model = model
        self.call_count = 0

    def add_scripted_response(self, item: Union[dict[str, Any], Exception, str]) -> None:
        """Bổ sung một phản hồi hoặc ngoại lệ vào hàng đợi kịch bản."""
        self.queue.append(item)

    async def generate(
        self,
        system_instruction: str,
        user_content: str,
        schema: Optional[type[BaseModel]] = None,
    ) -> LLMResult:
        self.call_count += 1
        start_time = time.perf_counter()

        if self.mode == "scripted":
            if not self.queue:
                raise LLMUnavailableError("FakeLLMClient hết kịch bản phản hồi trong queue")

            item = self.queue.pop(0)

            # Mô phỏng một chút độ trễ
            await asyncio.sleep(0.01)

            if isinstance(item, Exception):
                raise item
            if isinstance(item, str):
                try:
                    parsed = json.loads(item)
                    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                    return LLMResult(
                        data=parsed,
                        usage=TokenUsage(prompt_tokens=50, completion_tokens=30, total_tokens=80),
                        latency_ms=latency_ms,
                        model=self.model,
                        raw_text=item,
                    )
                except json.JSONDecodeError as exc:
                    raise LLMInvalidOutputError(f"Phản hồi JSON không hợp lệ: {exc}")
            if isinstance(item, dict):
                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                return LLMResult(
                    data=item,
                    usage=TokenUsage(prompt_tokens=50, completion_tokens=30, total_tokens=80),
                    latency_ms=latency_ms,
                    model=self.model,
                    raw_text=json.dumps(item),
                )
            raise LLMInvalidOutputError(f"Dữ liệu kịch bản không xác định: {item}")

        # Mode: heuristic
        return self._generate_heuristic(user_content, start_time)

    def _generate_heuristic(self, user_content: str, start_time: float) -> LLMResult:
        content_lower = user_content.lower()

        # 1. Kiểm tra Prompt Injection
        injection_patterns = [
            "ignore previous instructions",
            "bỏ qua hướng dẫn",
            "hãy đặt is_safe=true",
            "set is_safe=true",
            "print system prompt",
            "in system prompt",
            "tiết lộ prompt",
            "admin tag",
            "bỏ qua quy tắc",
        ]
        is_injection = any(p in content_lower for p in injection_patterns)

        # 2. Kiểm tra spam / scam
        spam_patterns = [
            "http://",
            "https://",
            "kiếm tiền online",
            "kiem tien",
            "click link",
            "bấm vào đây",
            "nhận quà",
            "trúng thưởng",
            "cờ bạc",
            "casino",
            "lừa đảo",
            "mua ngay kẻo lỡ",
        ]
        is_spam = any(p in content_lower for p in spam_patterns)

        # 3. Kiểm tra toxicity
        toxic_patterns = ["đm", "đụ", "chó chết", "thằng ngu", "fuck", "bitch", "ngu xuẩn", "đồ khốn"]
        is_toxic = any(p in content_lower for p in toxic_patterns)

        # 4. Kiểm tra adult
        adult_patterns = ["khiêu dâm", "phim sex", "gái gọi", "porn", "xxx"]
        is_adult = any(p in content_lower for p in adult_patterns)

        # Trích xuất tiêu đề từ chuỗi XML nếu có
        title_match = re.search(r"<title>(.*?)</title>", user_content, re.DOTALL)
        title = title_match.group(1).strip() if title_match else "Bài viết"

        # Quyết định kết quả Moderation
        if is_spam:
            moderation = {
                "is_safe": False,
                "categories": ["spam", "scam"],
                "severity": "high",
                "reason": "Phát hiện nội dung quảng cáo rác, liên kết ngoài hoặc dấu hiệu lừa đảo.",
            }
            topic = "other"
            sentiment = "negative"
        elif is_toxic:
            moderation = {
                "is_safe": False,
                "categories": ["toxicity"],
                "severity": "high",
                "reason": "Nội dung chứa từ ngữ thô tục, xúc phạm hoặc công kích cá nhân.",
            }
            topic = "discussion"
            sentiment = "negative"
        elif is_adult:
            moderation = {
                "is_safe": False,
                "categories": ["adult"],
                "severity": "high",
                "reason": "Nội dung người lớn hoặc nhạy cảm.",
            }
            topic = "other"
            sentiment = "negative"
        elif is_injection:
            # Phòng thủ injection: ghi nhận không an toàn hoặc off_topic, không tuân theo lệnh chèn
            moderation = {
                "is_safe": False,
                "categories": ["off_topic"],
                "severity": "medium",
                "reason": "Phát hiện nỗ lực chèn lệnh can thiệp prompt hệ thống (prompt injection).",
            }
            topic = "tech"
            sentiment = "neutral"
        else:
            moderation = {
                "is_safe": True,
                "categories": [],
                "severity": "none",
                "reason": "Nội dung chuẩn mực, không vi phạm tiêu chuẩn cộng đồng.",
            }
            sentiment = "positive" if any(w in content_lower for w in ["tuyệt vời", "hay", "hữu ích", "great", "good"]) else "neutral"

            # Phân loại topic
            if "?" in user_content or any(q in content_lower for q in ["làm sao", "như thế nào", "tại sao", "how to", "why"]):
                topic = "question"
            elif any(t in content_lower for t in ["python", "fastapi", "docker", "postgres", "sql", "api", "code", "dev", "bug"]):
                topic = "tech"
            elif any(n in content_lower for n in ["tin tức", "ra mắt", "công bố", "news", "update"]):
                topic = "news"
            elif any(l in content_lower for l in ["cuộc sống", "chia sẻ", "tâm sự", "life", "gia đình"]):
                topic = "life"
            else:
                topic = "discussion"

        # Gợi ý tags
        tags: list[str] = []
        tech_keywords = [
            ("fastapi", "fastapi"),
            ("python", "python"),
            ("docker", "docker"),
            ("postgres", "postgresql"),
            ("redis", "redis"),
            ("kafka", "kafka"),
            ("api", "api"),
            ("sql", "sql"),
            ("security", "security"),
            ("linux", "linux"),
        ]
        for kw, tag in tech_keywords:
            if kw in content_lower:
                tags.append(tag)

        if not tags:
            if topic == "question":
                tags = ["hoi-dap", "thao-luan"]
            elif topic == "news":
                tags = ["tin-tuc", "cong-nghe"]
            elif topic == "tech":
                tags = ["cong-nghe", "lap-trinh"]
            else:
                tags = ["chia-se", "thao-luan"]

        # Ngôn ngữ
        has_vietnamese_accent = bool(re.search(r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]", content_lower))
        language = "vi" if has_vietnamese_accent or any(w in content_lower for w in ["la", "va", "cua", "trong", "cho"]) else "en"

        summary = f"Bài viết '{title}' thảo luận về chủ đề {topic}."
        if len(summary) > 280:
            summary = summary[:277] + "..."

        data = {
            "summary": summary,
            "tags": tags[:5],
            "topic": topic,
            "sentiment": sentiment,
            "language": language,
            "moderation": moderation,
        }

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return LLMResult(
            data=data,
            usage=TokenUsage(prompt_tokens=120, completion_tokens=80, total_tokens=200),
            latency_ms=latency_ms,
            model=self.model,
            raw_text=json.dumps(data, ensure_ascii=False),
        )
