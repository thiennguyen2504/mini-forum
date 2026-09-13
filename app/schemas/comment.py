from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CommentCreate(BaseModel):
    """Payload để tạo comment mới trên một bài viết."""

    content: str = Field(..., min_length=1, description="Nội dung bình luận (không được để trống)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "content": "Bài viết rất hay, cảm ơn tác giả!",
            }
        }
    )


class CommentUpdate(BaseModel):
    """Payload để cập nhật bình luận (PATCH)."""

    content: Optional[str] = Field(None, min_length=1, description="Nội dung bình luận mới")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "content": "Bình luận đã được cập nhật.",
            }
        }
    )


class CommentOut(BaseModel):
    """Response trả về cho Comment."""

    id: int
    post_id: int
    user_id: int
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
