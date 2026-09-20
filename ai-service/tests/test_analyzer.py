from unittest.mock import MagicMock
import pytest

from app import cache
from app.cache import _mark_online
from app.config import Settings
from app.errors import (
    ContentBlockedError,
    LLMInvalidOutputError,
    LLMTimeoutError,
    LLMUnavailableError,
)
from app.llm.fake import FakeLLMClient
from app.schemas import AnalyzeOptions, AnalyzeRequest
from app.services.analyzer import AnalyzerService

VALID_ANALYSIS_DICT = {
    "summary": "Tóm tắt bài viết hướng dẫn lập trình FastAPI",
    "tags": ["FastAPI", "Python", "Web"],
    "topic": "tech",
    "sentiment": "positive",
    "language": "vi",
    "moderation": {
        "is_safe": True,
        "categories": [],
        "severity": "none",
        "reason": "Bài viết kỹ thuật tốt",
    },
}


@pytest.fixture(autouse=True)
def clean_cache(monkeypatch):
    """Giả lập in-memory store cho Redis cache trong các test của analyzer."""
    store = {}
    mock_redis = MagicMock()
    mock_redis.get.side_effect = lambda k: store.get(k)
    mock_redis.setex.side_effect = lambda k, ttl, v: store.update({k: v})
    mock_redis.ping.return_value = True

    monkeypatch.setattr(cache, "redis_client", mock_redis)
    _mark_online()
    yield


@pytest.mark.asyncio
async def test_analyzer_first_try_success():
    fake_client = FakeLLMClient(mode="scripted", scripted_responses=[VALID_ANALYSIS_DICT])
    service = AnalyzerService(client=fake_client)

    req = AnalyzeRequest(title="FastAPI cơ bản", content="Nội dung bài viết")
    res = await service.analyze(req, request_id="req-1")

    assert res.data.summary == VALID_ANALYSIS_DICT["summary"]
    # Tags được normalize: lowercase, kebab-case
    assert res.data.tags == ["fastapi", "python", "web"]
    assert res.meta.cached is False
    assert res.meta.retries == 0
    assert fake_client.call_count == 1


@pytest.mark.asyncio
async def test_analyzer_retry_on_malformed_json_then_success():
    fake_client = FakeLLMClient(
        mode="scripted",
        scripted_responses=[
            "Đây không phải là JSON",  # Lần 1: JSON hỏng
            VALID_ANALYSIS_DICT,  # Lần 2: Thành công
        ],
    )
    service = AnalyzerService(client=fake_client)

    req = AnalyzeRequest(title="FastAPI nâng cao", content="Nội dung bài viết")
    res = await service.analyze(req, request_id="req-2")

    assert res.meta.retries == 1
    assert fake_client.call_count == 2
    assert res.data.topic == "tech"


@pytest.mark.asyncio
async def test_analyzer_retry_on_schema_violation_then_success():
    invalid_schema = {
        "summary": "Tóm tắt",
        # Thiếu tags, topic sai
        "topic": "invalid_topic",
        "sentiment": "neutral",
        "language": "vi",
        "moderation": {"is_safe": True, "categories": [], "severity": "none", "reason": ""},
    }
    fake_client = FakeLLMClient(
        mode="scripted",
        scripted_responses=[
            invalid_schema,  # Lần 1: sai schema
            VALID_ANALYSIS_DICT,  # Lần 2: hợp lệ
        ],
    )
    service = AnalyzerService(client=fake_client)

    req = AnalyzeRequest(title="Kiểm thử schema", content="Test")
    res = await service.analyze(req, request_id="req-3")

    assert res.meta.retries == 1
    assert fake_client.call_count == 2


@pytest.mark.asyncio
async def test_analyzer_schema_violation_exhausts_retries():
    invalid_schema = {
        "summary": "Tóm tắt",
        "topic": "invalid_topic",
        "sentiment": "neutral",
        "language": "vi",
        "moderation": {"is_safe": True, "categories": [], "severity": "none", "reason": ""},
    }
    settings = Settings(LLM_MAX_RETRIES=2)
    fake_client = FakeLLMClient(
        mode="scripted",
        scripted_responses=[invalid_schema, invalid_schema, invalid_schema],
    )
    service = AnalyzerService(settings=settings, client=fake_client)

    req = AnalyzeRequest(title="Kiểm thử sai schema liên tục", content="Test")
    with pytest.raises(LLMInvalidOutputError) as exc:
        await service.analyze(req, request_id="req-4")

    assert "sau 2 lần thử" in str(exc.value)
    assert fake_client.call_count == 3


@pytest.mark.asyncio
async def test_analyzer_timeout_exhausts_retries():
    settings = Settings(LLM_MAX_RETRIES=1)
    fake_client = FakeLLMClient(
        mode="scripted",
        scripted_responses=[
            LLMTimeoutError("Hết thời gian lần 1"),
            LLMTimeoutError("Hết thời gian lần 2"),
        ],
    )
    service = AnalyzerService(settings=settings, client=fake_client)

    req = AnalyzeRequest(title="Timeout post", content="Test")
    with pytest.raises(LLMTimeoutError):
        await service.analyze(req, request_id="req-5")

    assert fake_client.call_count == 2


@pytest.mark.asyncio
async def test_analyzer_unavailable_exhausts_retries():
    settings = Settings(LLM_MAX_RETRIES=1)
    fake_client = FakeLLMClient(
        mode="scripted",
        scripted_responses=[
            LLMUnavailableError("503 Service Unavailable"),
            LLMUnavailableError("503 Service Unavailable"),
        ],
    )
    service = AnalyzerService(settings=settings, client=fake_client)

    req = AnalyzeRequest(title="Unavailable post", content="Test")
    with pytest.raises(LLMUnavailableError):
        await service.analyze(req, request_id="req-6")

    assert fake_client.call_count == 2


@pytest.mark.asyncio
async def test_analyzer_safety_block_no_retry():
    settings = Settings(LLM_MAX_RETRIES=2)
    fake_client = FakeLLMClient(
        mode="scripted",
        scripted_responses=[
            ContentBlockedError("Nội dung vi phạm bộ lọc an toàn nghiêm trọng"),
        ],
    )
    service = AnalyzerService(settings=settings, client=fake_client)

    req = AnalyzeRequest(title="Nội dung nguy hại", content="...")
    with pytest.raises(ContentBlockedError) as exc:
        await service.analyze(req, request_id="req-7")

    assert "bộ lọc an toàn" in str(exc.value)
    # KHÔNG được retry: call_count phải chính xác là 1!
    assert fake_client.call_count == 1


@pytest.mark.asyncio
async def test_analyzer_never_returns_safe_on_error():
    """Khẳng định tuyệt đối không bao giờ trả is_safe=True khi LLM lỗi."""
    fake_client = FakeLLMClient(
        mode="scripted",
        scripted_responses=[LLMUnavailableError("Crash")],
    )
    service = AnalyzerService(client=fake_client)

    req = AnalyzeRequest(title="Test", content="...")
    with pytest.raises(LLMUnavailableError):
        res = await service.analyze(req, request_id="req-8")
        # Dòng này không bao giờ được chạm tới
        assert res.data.moderation.is_safe is not True


@pytest.mark.asyncio
async def test_analyzer_caching_behavior():
    fake_client = FakeLLMClient(mode="scripted", scripted_responses=[VALID_ANALYSIS_DICT])
    service = AnalyzerService(client=fake_client)

    req = AnalyzeRequest(title="Bài viết cache", content="Nội dung cache")

    # Lần 1: Gọi LLM
    res1 = await service.analyze(req, request_id="req-cache-1")
    assert res1.meta.cached is False
    assert fake_client.call_count == 1

    # Lần 2: Lấy từ Cache
    res2 = await service.analyze(req, request_id="req-cache-2")
    assert res2.meta.cached is True
    # Client LLM không bị gọi thêm lần nào
    assert fake_client.call_count == 1
    assert res2.data.summary == res1.data.summary


@pytest.mark.asyncio
async def test_analyzer_skip_cache():
    fake_client = FakeLLMClient(
        mode="scripted",
        scripted_responses=[VALID_ANALYSIS_DICT, VALID_ANALYSIS_DICT],
    )
    service = AnalyzerService(client=fake_client)

    req_normal = AnalyzeRequest(title="Cache test", content="Same content")
    res1 = await service.analyze(req_normal, request_id="req-1")
    assert res1.meta.cached is False
    assert fake_client.call_count == 1

    # Yêu cầu bỏ qua cache
    req_skip = AnalyzeRequest(
        title="Cache test",
        content="Same content",
        options=AnalyzeOptions(skip_cache=True),
    )
    res2 = await service.analyze(req_skip, request_id="req-2")
    assert res2.meta.cached is False
    # LLM client được gọi lần 2
    assert fake_client.call_count == 2


@pytest.mark.asyncio
async def test_analyzer_fail_open_when_redis_offline(monkeypatch):
    import redis

    mock_redis = MagicMock()
    mock_redis.get.side_effect = redis.ConnectionError("Redis down")
    mock_redis.setex.side_effect = redis.ConnectionError("Redis down")
    monkeypatch.setattr(cache, "redis_client", mock_redis)

    fake_client = FakeLLMClient(mode="scripted", scripted_responses=[VALID_ANALYSIS_DICT])
    service = AnalyzerService(client=fake_client)

    req = AnalyzeRequest(title="Redis down test", content="Still works")
    res = await service.analyze(req, request_id="req-redis-down")

    # Vẫn thành công bình thường
    assert res.data.topic == "tech"
    assert res.meta.cached is False
