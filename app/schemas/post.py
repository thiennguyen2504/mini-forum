from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PostCreate(BaseModel):
    """Payload để tạo bài viết mới."""

    title: str = Field(..., min_length=1, max_length=200, description="Tiêu đề bài viết (1–200 ký tự)")
    content: Optional[str] = Field(None, description="Nội dung bài viết (Markdown, tuỳ chọn)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Giới thiệu FastAPI",
                "content": "FastAPI là một web framework hiện đại, nhanh, dựa trên Python 3.8+...",
            }
        }
    )


class PostUpdate(BaseModel):
    """Payload để cập nhật một phần bài viết (PATCH)."""

    title: Optional[str] = Field(None, min_length=1, max_length=200, description="Tiêu đề mới")
    content: Optional[str] = Field(None, description="Nội dung mới")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Giới thiệu FastAPI – Cập nhật",
                "content": None,
            }
        }
    )


class PostOut(BaseModel):
    """Response trả về cho Post, bao gồm tên tác giả và danh sách tag."""

    id: int
    user_id: int
    title: str
    content: Optional[str] = None
    view_count: int
    created_at: datetime

    # Các field này sẽ được map thủ công ở tầng router/CRUD
    author_name: Optional[str] = Field(None, description="Tên tác giả lấy từ User.name")
    tags: list[str] = Field(default_factory=list, description="Danh sách tên tag của bài viết")

    model_config = ConfigDict(from_attributes=True)
