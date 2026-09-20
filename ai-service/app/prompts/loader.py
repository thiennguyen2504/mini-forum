import hashlib
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent


def load_prompt(version: str = "v2") -> tuple[str, str]:
    """
    Đọc nội dung file prompt theo phiên bản (ví dụ 'v1', 'v2')
    và tính mã băm SHA256 của nội dung file.

    Returns:
        tuple[content, sha256_hash]

    Raises:
        FileNotFoundError: Nếu file prompt theo phiên bản không tồn tại.
    """
    file_path = PROMPTS_DIR / f"post_analyzer_{version}.md"
    if not file_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file prompt cho phiên bản: '{version}' tại {file_path}")

    content = file_path.read_text(encoding="utf-8")
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return content, content_hash
