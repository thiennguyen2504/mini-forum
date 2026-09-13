import logging
from typing import Optional

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import crud
from app.core.cache import delete_key, delete_prefix, get_json, set_json
from app.schemas.post import PostCreate, PostOut, PostUpdate

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class PostListOut(BaseModel):
    items: list[PostOut]
    total: int
    skip: int
    limit: int


class TagsOut(BaseModel):
    post_id: int
    tags: list[str]


# ---------------------------------------------------------------------------
# Helper: ORM Post → PostOut
# ---------------------------------------------------------------------------

def _to_post_out(post) -> PostOut:
    return PostOut(
        id=post.id,
        user_id=post.user_id,
        title=post.title,
        content=post.content,
        view_count=post.view_count,
        created_at=post.created_at,
        author_name=post.author.name if post.author else None,
        tags=[tag.name for tag in post.tags],
    )


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class PostService:
    def __init__(self, db: Session):
        self.db = db

    def list_posts(
        self,
        skip: int = 0,
        limit: int = 20,
        tag: Optional[str] = None,
        author_id: Optional[int] = None,
    ) -> PostListOut:
        """
        Lấy danh sách bài viết có phân trang và filter.
        Sử dụng cache-aside với key: posts:list:{skip}:{limit}:{tag}:{author_id}, TTL 30s.
        """
        cache_key = f"posts:list:{skip}:{limit}:{tag}:{author_id}"
        cached = get_json(cache_key)
        if cached is not None:
            logger.info("[CACHE HIT] %s", cache_key)
            return PostListOut.model_validate(cached)

        logger.info("[CACHE MISS] %s", cache_key)
        posts = crud.get_posts(
            self.db,
            skip=skip,
            limit=limit,
            tag_name=tag,
            author_id=author_id,
        )
        total = crud.count_posts(self.db, tag_name=tag, author_id=author_id)
        items = [_to_post_out(p) for p in posts]
        result = PostListOut(items=items, total=total, skip=skip, limit=limit)

        set_json(cache_key, result, ttl=30)
        return result

    def get_post(self, post_id: int) -> PostOut:
        """
        Lấy chi tiết một bài viết.
        Sử dụng cache-aside với key: posts:detail:{post_id}, TTL 60s.
        Raises:
            LookupError: Nếu post_id không tồn tại.
        """
        cache_key = f"posts:detail:{post_id}"
        cached = get_json(cache_key)
        if cached is not None:
            logger.info("[CACHE HIT] %s", cache_key)
            return PostOut.model_validate(cached)

        logger.info("[CACHE MISS] %s", cache_key)
        post = crud.get_post(self.db, post_id)
        result = _to_post_out(post)

        set_json(cache_key, result, ttl=60)
        return result

    def create_post(self, payload: PostCreate, user_id: int) -> PostOut:
        """
        Tạo bài viết mới.
        Sau khi ghi DB thành công: xoá cache posts:list:* và posts:detail:{post_id}.
        Raises:
            LookupError: Nếu user_id không tồn tại.
        """
        post = crud.create_post(self.db, payload, user_id=user_id)
        # Reload với selectinload để eager-load author + tags
        post = crud.get_post(self.db, post.id)
        result = _to_post_out(post)

        # Invalidate cache
        delete_prefix("posts:list:")
        delete_key(f"posts:detail:{post.id}")

        return result

    def update_post(self, post_id: int, payload: PostUpdate) -> PostOut:
        """
        Cập nhật bài viết.
        Sau khi ghi DB thành công: xoá cache posts:list:* và posts:detail:{post_id}.
        Raises:
            LookupError: Nếu post_id không tồn tại.
        """
        crud.update_post(self.db, post_id, payload)
        post = crud.get_post(self.db, post_id)
        result = _to_post_out(post)

        # Invalidate cache
        delete_prefix("posts:list:")
        delete_key(f"posts:detail:{post_id}")

        return result

    def delete_post(self, post_id: int) -> None:
        """
        Xoá bài viết.
        Sau khi ghi DB thành công: xoá cache posts:list:* và posts:detail:{post_id}.
        Raises:
            LookupError: Nếu post_id không tồn tại.
        """
        crud.delete_post(self.db, post_id)

        # Invalidate cache
        delete_prefix("posts:list:")
        delete_key(f"posts:detail:{post_id}")

    def attach_tags_to_post(self, post_id: int, tag_names: list[str]) -> TagsOut:
        """
        Gắn tags vào bài viết trong một transaction.
        Sau khi ghi DB thành công: xoá cache posts:list:* và posts:detail:{post_id}.
        Raises:
            LookupError: Nếu post_id không tồn tại.
            Exception: Lỗi transaction database.
        """
        post = crud.attach_tags_to_post(self.db, post_id, tag_names)

        # Invalidate cache
        delete_prefix("posts:list:")
        delete_key(f"posts:detail:{post_id}")

        return TagsOut(post_id=post.id, tags=[t.name for t in post.tags])
