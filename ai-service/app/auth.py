from typing import Optional
from fastapi import Request
from jose import JWTError, jwt

from app.config import get_settings
from app.errors import UnauthorizedError


def verify_token(token: str) -> Optional[dict]:
    """Giải mã và xác thực chữ ký JWT token."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


async def require_auth(request: Request) -> Optional[str]:
    """
    FastAPI dependency kiểm tra quyền truy cập qua Bearer Token:
    - Nếu AI_REQUIRE_AUTH=False: cho phép bỏ qua xác thực.
    - Nếu AI_REQUIRE_AUTH=True: bắt buộc có header Authorization: Bearer <token>.
    """
    settings = get_settings()
    if not settings.AI_REQUIRE_AUTH:
        return None

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise UnauthorizedError("Thiếu header Authorization hoặc không đúng định dạng Bearer")

    token = auth_header.split(" ", 1)[1].strip()
    payload = verify_token(token)
    if not payload:
        raise UnauthorizedError("Token không hợp lệ hoặc đã hết hạn")

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedError("Token thiếu thông tin người dùng (sub)")

    return str(user_id)
