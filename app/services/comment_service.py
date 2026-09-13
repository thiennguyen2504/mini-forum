import logging
from typing import Optional

from sqlalchemy.orm import Session

from app import crud
from app.core.events import publish_comment_created
from app.models.comment import Comment
from app.schemas.comment import CommentCreate, CommentUpdate

logger = logging.getLogger(__name__)


class CommentService:
    def __init__(self, db: Session):
        self.db = db

    def create_comment(
        self,
        post_id: int,
        payload: CommentCreate,
        user_id: int,
    ) -> Comment:
        """
        Tạo comment mới cho post. Kiểm tra bài viết tồn tại trước.
        Sau khi lưu DB thành công: bắn event comment.created lên Kafka
        nếu tác giả comment khác chủ bài viết (user_id != post.user_id).
        Raises:
            LookupError: Nếu post_id không tồn tại.
        """
        # Kiểm tra post tồn tại
        post = crud.get_post(self.db, post_id)
        comment = crud.create_comment(
            self.db,
            payload,
            post_id=post_id,
            user_id=user_id,
        )

        # Bắn event Kafka khi comment_author_id != post_owner_id
        if user_id != post.user_id:
            try:
                user = crud.get_user(self.db, user_id=user_id)
                author_name = user.name if user else "Anonymous"
                publish_comment_created(
                    comment_id=comment.id,
                    post_id=post.id,
                    post_owner_id=post.user_id,
                    comment_author_id=user_id,
                    comment_author_name=author_name,
                    content_preview=payload.content[:100],
                    created_at=(
                        comment.created_at.isoformat()
                        if hasattr(comment.created_at, "isoformat")
                        else str(comment.created_at)
                    ),
                )
            except Exception as exc:
                logger.warning("Failed to publish comment created event: %s", exc)

        return comment

    def list_comments(
        self,
        post_id: int,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Comment]:
        """
        Lấy danh sách comment của bài viết theo thứ tự cũ -> mới.
        Raises:
            LookupError: Nếu post_id không tồn tại.
        """
        # Kiểm tra post tồn tại
        crud.get_post(self.db, post_id)
        return crud.get_comments_by_post(
            self.db,
            post_id,
            skip=skip,
            limit=limit,
        )

    def update_comment(
        self,
        comment_id: int,
        payload: CommentUpdate,
    ) -> Comment:
        """
        Cập nhật nội dung comment.
        Raises:
            LookupError: Nếu comment_id không tồn tại.
        """
        return crud.update_comment(self.db, comment_id, payload)

    def delete_comment(self, comment_id: int) -> None:
        """
        Xoá comment theo comment_id.
        Raises:
            LookupError: Nếu comment_id không tồn tại.
        """
        crud.delete_comment(self.db, comment_id)
