import re
import unicodedata
from typing import Optional


def remove_vietnamese_accents(text: str) -> str:
    """
    Bỏ dấu tiếng Việt, chuyển đ/Đ thành d/D, giữ lại các ký tự ASCII cơ bản.
    """
    # Thay thế thủ công đ/Đ trước vì NFKD không tách đ thành d + dấu
    text = text.replace("đ", "d").replace("Đ", "D")
    # Tách các ký tự có dấu thành ký tự gốc + combining mark
    normalized = unicodedata.normalize("NFKD", text)
    # Loại bỏ các combining mark (dấu thanh, mũ...)
    stripped = "".join(c for c in normalized if not unicodedata.combining(c))
    return stripped


def normalize_tag(tag: str) -> Optional[str]:
    """
    Chuẩn hoá 1 tag:
    - Bỏ dấu tiếng Việt (đ -> d)
    - Chuyển chữ thường (lowercase)
    - Thay thế khoảng trắng và dấu gạch dưới bằng '-'
    - Chỉ giữ các ký tự a-z, 0-9 và dấu '-'
    - Gộp các dấu '-' liên tiếp, loại bỏ '-' ở đầu và cuối
    - Độ dài hợp lệ: từ 2 đến 30 ký tự
    Trả về tag chuẩn hoá hoặc None nếu không hợp lệ.
    """
    if not tag or not isinstance(tag, str):
        return None

    cleaned = remove_vietnamese_accents(tag).lower().strip()
    # Thay khoảng trắng và dấu gạch dưới bằng '-'
    cleaned = re.sub(r"[\s_]+", "-", cleaned)
    # Loại bỏ ký tự không thuộc a-z, 0-9, '-'
    cleaned = re.sub(r"[^a-z0-9-]", "", cleaned)
    # Rút gọn nhiều dấu '-' liên tiếp thành 1 dấu '-'
    cleaned = re.sub(r"-+", "-", cleaned)
    # Cắt bỏ '-' ở hai đầu
    cleaned = cleaned.strip("-")

    if 2 <= len(cleaned) <= 30:
        return cleaned
    return None


def normalize_tags(raw_tags: list[str], max_tags: int = 5) -> list[str]:
    """
    Chuẩn hoá danh sách tags:
    - Chuẩn hoá từng tag
    - Khử trùng lặp và giữ nguyên thứ tự xuất hiện
    - Giới hạn tối đa max_tags (mặc định 5)
    """
    seen: set[str] = set()
    result: list[str] = []

    for tag in raw_tags:
        norm = normalize_tag(tag)
        if norm and norm not in seen:
            seen.add(norm)
            result.append(norm)
            if len(result) >= max_tags:
                break

    return result


def sanitize_post_input(
    title: str,
    content: Optional[str] = None,
    max_chars: int = 6000,
) -> tuple[str, bool, int]:
    """
    Tiền xử lý và làm sạch dữ liệu đầu vào:
    1. Strip tiêu đề và nội dung.
    2. Nếu content là None => gán thành chuỗi rỗng.
    3. Tránh prompt escape: vô hiệu hoá chuỗi '</post>' thành '[/post]' hoặc loại bỏ.
    4. Cắt ngắn nếu tổng độ dài (title + content) vượt quá max_chars (ghi nhận cờ truncated).
    5. Đóng gói trong thẻ XML: <post><title>...</title><content>...</content></post>.

    Trả về:
    - xml_wrapped_input: chuỗi XML đóng gói
    - truncated: True nếu nội dung bị cắt ngắn
    - total_raw_len: độ dài thực tế trước khi cắt
    """
    clean_title = (title or "").strip()
    clean_content = (content or "").strip()

    # Vô hiệu hoá thẻ thoát XML </post> trong cả title và content
    clean_title = re.sub(r"<\s*/\s*post\s*>", "[/post]", clean_title, flags=re.IGNORECASE)
    clean_content = re.sub(r"<\s*/\s*post\s*>", "[/post]", clean_content, flags=re.IGNORECASE)

    raw_len = len(clean_title) + len(clean_content)
    truncated = False

    # Giới hạn ký tự
    if raw_len > max_chars:
        truncated = True
        # Ưu tiên giữ toàn bộ title (tối đa 200 ký tự), chỉ cắt ngắn content
        title_len = len(clean_title)
        available_content_len = max(0, max_chars - title_len)
        clean_content = clean_content[:available_content_len]

    xml_wrapped = f"<post>\n<title>{clean_title}</title>\n<content>{clean_content}</content>\n</post>"
    return xml_wrapped, truncated, raw_len
