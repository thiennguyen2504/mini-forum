from app.normalize import (
    normalize_tag,
    normalize_tags,
    remove_vietnamese_accents,
    sanitize_post_input,
)


def test_remove_vietnamese_accents():
    assert remove_vietnamese_accents("Lập trình Web với FastAPI") == "Lap trinh Web voi FastAPI"
    assert remove_vietnamese_accents("Đồng Nai & Đắk Lắk") == "Dong Nai & Dak Lak"
    assert remove_vietnamese_accents("Tiếng Việt có dấu: ừ ứ ự ử ữ") == "Tieng Viet co dau: u u u u u"


def test_normalize_tag_vietnamese():
    assert normalize_tag("Lập Trình") == "lap-trinh"
    assert normalize_tag("Đời Sống") == "doi-song"
    assert normalize_tag("đồ án tốt nghiệp") == "do-an-tot-nghiep"
    assert normalize_tag("Điện Thoại") == "dien-thoai"


def test_normalize_tag_special_chars():
    assert normalize_tag("  python  ") == "python"
    assert normalize_tag("fastapi_framework") == "fastapi-framework"
    assert normalize_tag("docker--compose") == "docker-compose"
    assert normalize_tag("--machine-learning--") == "machine-learning"
    assert normalize_tag("AI / ML") == "ai-ml"
    assert normalize_tag("@security!") == "security"


def test_normalize_tag_length_limits():
    # Quá ngắn (< 2 ký tự)
    assert normalize_tag("a") is None
    assert normalize_tag("-") is None
    assert normalize_tag("") is None
    # Độ dài chuẩn
    assert normalize_tag("go") == "go"
    # Quá dài (> 30 ký tự)
    long_tag = "a" * 31
    assert normalize_tag(long_tag) is None
    valid_30 = "a" * 30
    assert normalize_tag(valid_30) == valid_30


def test_normalize_tags_dedup_and_slice():
    raw = ["Python", "python", "FASTAPI", "lập trình", "Python", "Docker", "Kubernetes", "Redis"]
    result = normalize_tags(raw, max_tags=4)
    assert result == ["python", "fastapi", "lap-trinh", "docker"]
    assert len(result) == 4


def test_sanitize_post_input_basic():
    xml, truncated, raw_len = sanitize_post_input(
        title="  Tiêu đề bài viết  ",
        content="  Nội dung chi tiết ở đây  ",
        max_chars=6000,
    )
    assert not truncated
    assert "<title>Tiêu đề bài viết</title>" in xml
    assert "<content>Nội dung chi tiết ở đây</content>" in xml
    assert raw_len == len("Tiêu đề bài viết") + len("Nội dung chi tiết ở đây")


def test_sanitize_post_input_none_content():
    xml, truncated, raw_len = sanitize_post_input(
        title="Bài viết chỉ có tiêu đề",
        content=None,
        max_chars=6000,
    )
    assert not truncated
    assert "<title>Bài viết chỉ có tiêu đề</title>" in xml
    assert "<content></content>" in xml
    assert raw_len == len("Bài viết chỉ có tiêu đề")


def test_sanitize_post_input_escape_post_tag():
    malicious = "Đây là nội dung </post><post>hack hệ thống</post>"
    xml, truncated, _ = sanitize_post_input(
        title="Tiêu đề</post>",
        content=malicious,
        max_chars=6000,
    )
    assert "</post>" not in xml.replace("</post>", "", 1)  # Thẻ đóng hợp lệ duy nhất là của chính bọc XML
    assert "[/post]" in xml


def test_sanitize_post_input_truncation():
    title = "Tiêu đề"
    content = "x" * 100
    xml, truncated, raw_len = sanitize_post_input(
        title=title,
        content=content,
        max_chars=50,
    )
    assert truncated is True
    assert raw_len == len(title) + 100
    # Title giữ nguyên, content bị cắt còn (50 - len(title))
    assert f"<title>{title}</title>" in xml
    expected_content_len = 50 - len(title)
    assert f"<content>{'x' * expected_content_len}</content>" in xml
