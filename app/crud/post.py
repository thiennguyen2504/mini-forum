from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.post import Post
from app.models.user import User
from app.schemas.post import PostCreate, PostUpdate


def _base_query_with_relations():
    """Trả về select statement đã eager-load author + tags (dùng lại ở get_post / get_posts)."""
    return select(Post).options(
        selectinload(Post.author),
        selectinload(Post.tags),
    )


def create_post(db: Session, payload: PostCreate, user_id: int) -> Post:
    """
    Tạo bài viết mới cho user_id.

    Raises:
        LookupError: Nếu user_id không tồn tại (→ router trả 404).
    """
    if db.get(User, user_id) is None:
        raise LookupError(f"User id={user_id} not found.")

    post = Post(
        user_id=user_id,
        title=payload.title,
        content=payload.content,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def get_post(db: Session, post_id: int) -> Post:
    """
    Lấy một bài viết kèm author + tags (selectinload, tránh N+1).

    Raises:
        LookupError: Nếu không tìm thấy (→ router trả 404).
    """
    stmt = _base_query_with_relations().where(Post.id == post_id)
    post = db.execute(stmt).scalars().first()
    if post is None:
        raise LookupError(f"Post id={post_id} not found.")
    return post


def get_posts(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 20,
    tag_name: Optional[str] = None,
    author_id: Optional[int] = None,
) -> list[Post]:
    """
    Lấy danh sách bài viết có phân trang, tuỳ chọn filter theo tag và/hoặc tác giả.
    Dùng selectinload để tránh N+1 khi render danh sách.

    Args:
        skip: offset (default 0).
        limit: số bản ghi tối đa (default 20).
        tag_name: lọc bài viết có tag tên này.
        author_id: lọc bài viết của user này.
    """
    stmt = _base_query_with_relations()

    if author_id is not None:
        stmt = stmt.where(Post.user_id == author_id)

    if tag_name is not None:
        # JOIN vào bảng tags qua association post_tags để filter
        from app.models.tag import Tag

        stmt = stmt.join(Post.tags).where(Tag.name == tag_name)

    stmt = stmt.order_by(Post.created_at.desc()).offset(skip).limit(limit)
    return list(db.execute(stmt).scalars().unique().all())


def update_post(db: Session, post_id: int, payload: PostUpdate) -> Post:
    """
    Cập nhật một phần bài viết (PATCH — chỉ field nào được set mới thay đổi).

    Raises:
        LookupError: Nếu không tìm thấy (→ router trả 404).
    """
    post = db.get(Post, post_id)
    if post is None:
        raise LookupError(f"Post id={post_id} not found.")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(post, field, value)

    db.commit()
    db.refresh(post)
    return post


def delete_post(db: Session, post_id: int) -> None:
    """
    Xoá bài viết (cascade xoá comments qua DB constraint).

    Raises:
        LookupError: Nếu không tìm thấy (→ router trả 404).
    """
    post = db.get(Post, post_id)
    if post is None:
        raise LookupError(f"Post id={post_id} not found.")

    db.delete(post)
    db.commit()
