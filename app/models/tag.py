from __future__ import annotations

from typing import TYPE_CHECKING, List

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.post import Post


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    # Relationships
    posts: Mapped[List["Post"]] = relationship("Post", secondary="post_tags", back_populates="tags")
