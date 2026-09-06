from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Payload để tạo user mới."""

    email: EmailStr = Field(..., description="Địa chỉ email hợp lệ, phải là duy nhất")
    name: Optional[str] = Field(None, max_length=255, description="Tên hiển thị (tuỳ chọn)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "alice@example.com",
                "name": "Alice Nguyen",
            }
        }
    )


class UserOut(BaseModel):
    """Response trả về cho User."""

    id: int
    email: EmailStr
    name: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
