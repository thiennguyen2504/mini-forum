from collections.abc import Generator

from sqlalchemy.orm import Session

from app.db import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency trả về một DB session cho mỗi request,
    đảm bảo session được đóng dù có lỗi hay không.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
