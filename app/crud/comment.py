from sqlalchemy.orm import Session

from app.models.comment import Comment
from app.schemas.comment import CommentCreate


def create_comment(db: Session, payload: CommentCreate, post_id: int, user_id: int) -> Comment:
    """
    Tạo comment mới gắn vào post_id đã có.

    Note:
        Không kiểm tra sự tồn tại của post/user tại đây —
        DB constraint (FK) sẽ raise IntegrityError nếu sai;
        router có thể bắt và trả 404 hoặc 422.
        Nếu muốn lỗi rõ hơn, router nên gọi crud.post.get_post trước.
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


def get_comments_by_post(db: Session, post_id: int, *, skip: int = 0, limit: int = 50) -> list[Comment]:
    """
    Lấy tất cả comment của một bài viết, sắp xếp cũ → mới, có phân trang.

    Args:
        post_id: ID bài viết cần lấy comment.
        skip: offset.
        limit: số bản ghi tối đa (default 50).
    """
    return (
        db.query(Comment)
        .filter(Comment.post_id == post_id)
        .order_by(Comment.created_at.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )
