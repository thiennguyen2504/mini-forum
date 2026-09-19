import pytest
from pydantic import ValidationError

from app.schemas import (
    AnalyzeOptions,
    AnalyzeRequest,
    Moderation,
    PostAnalysis,
)


def test_moderation_valid_safe():
    m = Moderation(is_safe=True, categories=[], severity="none", reason="Bài viết chuẩn mực")
    assert m.is_safe is True
    assert m.categories == []
    assert m.severity == "none"


def test_moderation_valid_unsafe():
    m = Moderation(is_safe=False, categories=["spam"], severity="medium", reason="Chứa link tiếp thị")
    assert m.is_safe is False
    assert m.categories == ["spam"]
    assert m.severity == "medium"


def test_moderation_invalid_safe_with_categories():
    with pytest.raises(ValidationError) as exc:
        Moderation(is_safe=True, categories=["spam"], severity="none", reason="")
    assert "categories phải rỗng" in str(exc.value)


def test_moderation_invalid_safe_with_severity():
    with pytest.raises(ValidationError) as exc:
        Moderation(is_safe=True, categories=[], severity="low", reason="")
    assert "severity phải là 'none'" in str(exc.value)


def test_moderation_invalid_unsafe_with_none_severity():
    with pytest.raises(ValidationError) as exc:
        Moderation(is_safe=False, categories=["toxicity"], severity="none", reason="Chửi thề")
    assert "severity không thể là 'none'" in str(exc.value)


def test_moderation_invalid_unsafe_with_empty_categories():
    with pytest.raises(ValidationError) as exc:
        Moderation(is_safe=False, categories=[], severity="high", reason="Vi phạm")
    assert "phải chỉ rõ ít nhất 1 danh mục vi phạm" in str(exc.value)


def test_post_analysis_valid():
    analysis = PostAnalysis(
        summary="Hướng dẫn cài đặt FastAPI",
        tags=["fastapi", "python"],
        topic="tech",
        sentiment="positive",
        language="vi",
        moderation=Moderation(is_safe=True, categories=[], severity="none", reason="Hợp lệ"),
    )
    assert analysis.topic == "tech"
    assert len(analysis.tags) == 2


def test_post_analysis_invalid_topic():
    with pytest.raises(ValidationError):
        PostAnalysis(
            summary="Test",
            tags=["tag1"],
            topic="invalid_topic",  # type: ignore[arg-type]
            sentiment="neutral",
            language="vi",
            moderation=Moderation(is_safe=True, categories=[], severity="none"),
        )


def test_post_analysis_summary_too_long():
    with pytest.raises(ValidationError):
        PostAnalysis(
            summary="a" * 301,
            tags=["tag1"],
            topic="tech",
            sentiment="neutral",
            language="vi",
            moderation=Moderation(is_safe=True, categories=[], severity="none"),
        )


def test_post_analysis_too_many_tags():
    with pytest.raises(ValidationError):
        PostAnalysis(
            summary="Test",
            tags=["tag1", "tag2", "tag3", "tag4", "tag5", "tag6"],
            topic="tech",
            sentiment="neutral",
            language="vi",
            moderation=Moderation(is_safe=True, categories=[], severity="none"),
        )


def test_analyze_request_valid():
    req = AnalyzeRequest(
        title="Lập trình Python",
        content="Nội dung bài viết",
        options=AnalyzeOptions(max_tags=3, skip_cache=True),
    )
    assert req.title == "Lập trình Python"
    assert req.options.max_tags == 3
    assert req.options.skip_cache is True


def test_analyze_request_content_none_valid():
    req = AnalyzeRequest(title="Chỉ có tiêu đề", content=None)
    assert req.content is None
    assert req.options.max_tags == 5


def test_analyze_request_empty_title_invalid():
    with pytest.raises(ValidationError):
        AnalyzeRequest(title="")


def test_analyze_options_invalid_max_tags():
    with pytest.raises(ValidationError):
        AnalyzeOptions(max_tags=0)
    with pytest.raises(ValidationError):
        AnalyzeOptions(max_tags=6)
