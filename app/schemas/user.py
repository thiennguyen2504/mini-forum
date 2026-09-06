from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Payload để tạo user mới (đăng ký)."""

    email: EmailStr = Field(..., description="Địa chỉ email hợp lệ, phải là duy nhất")
    password: str = Field(..., min_length=6, description="Mật khẩu tài khoản (tối thiểu 6 ký tự)")
    name: Optional[str] = Field(None, max_length=255, description="Tên hiển thị (tuỳ chọn)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "alice@example.com",
                "password": "secretpassword123",
                "name": "Alice Nguyen",
            }
        }
    )


class UserOut(BaseModel):
    """Response trả về cho User (không bao gồm password)."""

    id: int
    email: EmailStr
    name: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenOut(BaseModel):
    """Response trả về sau khi đăng nhập thành công."""

    access_token: str
    token_type: str = "bearer"
