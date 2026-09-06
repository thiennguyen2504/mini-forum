from typing import Optional

from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserCreate


def create_user(db: Session, payload: UserCreate) -> User:
    """
    Tạo user mới với mật khẩu được băm.

    Raises:
        ValueError: Nếu email đã tồn tại trong DB (→ router trả 409).
    """
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise ValueError(f"Email '{payload.email}' already registered.")

    hashed_pwd = hash_password(payload.password)
    user = User(
        email=payload.email,
        hashed_password=hashed_pwd,
        name=payload.name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """
    Xác thực user bằng email và password.
    Trả về User nếu thành công, None nếu thất bại.
    """
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def get_user(db: Session, user_id: int) -> User:
    """
    Lấy user theo id.

    Raises:
        LookupError: Nếu không tìm thấy (→ router trả 404).
    """
    user = db.get(User, user_id)
    if user is None:
        raise LookupError(f"User id={user_id} not found.")
    return user


def get_user_by_email(db: Session, email: str) -> User:
    """
    Lấy user theo email.

    Raises:
        LookupError: Nếu không tìm thấy (→ router trả 404).
    """
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise LookupError(f"User with email='{email}' not found.")
    return user
