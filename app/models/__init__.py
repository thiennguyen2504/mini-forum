# Import all models here so they are registered with Base.metadata
from app.models.base import Base  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.post import Post, post_tags  # noqa: F401
from app.models.comment import Comment  # noqa: F401
from app.models.tag import Tag  # noqa: F401

__all__ = ["Base", "User", "Post", "Comment", "Tag", "post_tags"]
