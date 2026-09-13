from sqlalchemy.orm import Session

from app.models.comment import Comment
from app.schemas.comment import CommentCreate, CommentUpdate


def create_comment(db: Session, payload: CommentCreate, post_id: int, user_id: int) -> Comment:
    """
    Tạo comment mới gắn vào post_id đã có.
    """
    comment = Comment(
        post_id=post_id,
        user_id=user_id,
        content=payload.content,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


def get_comment(db: Session, comment_id: int) -> Comment:
    """
    Lấy một comment theo ID.

    Raises:
        LookupError: Nếu không tìm thấy comment (→ 404).
    """
    comment = db.get(Comment, comment_id)
    if comment is None:
        raise LookupError(f"Comment id={comment_id} not found.")
    return comment


def get_comments_by_post(db: Session, post_id: int, *, skip: int = 0, limit: int = 50) -> list[Comment]:
    """
    Lấy tất cả comment của một bài viết, sắp xếp cũ → mới, có phân trang.
    """
    return (
        db.query(Comment)
        .filter(Comment.post_id == post_id)
        .order_by(Comment.created_at.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def update_comment(db: Session, comment_id: int, payload: CommentUpdate) -> Comment:
    """
    Cập nhật nội dung bình luận (PATCH).

    Raises:
        LookupError: Nếu không tìm thấy comment (→ 404).
    """
    comment = db.get(Comment, comment_id)
    if comment is None:
        raise LookupError(f"Comment id={comment_id} not found.")

    if payload.content is not None:
        comment.content = payload.content

    db.commit()
    db.refresh(comment)
    return comment


def delete_comment(db: Session, comment_id: int) -> None:
    """
    Xoá bình luận theo ID.

    Raises:
        LookupError: Nếu không tìm thấy comment (→ 404).
    """
    comment = db.get(Comment, comment_id)
    if comment is None:
        raise LookupError(f"Comment id={comment_id} not found.")

    db.delete(comment)
    db.commit()
