from typing import Optional

from sqlalchemy.orm import Session

from app import crud
from app.models.comment import Comment
from app.schemas.comment import CommentCreate, CommentUpdate


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
        Raises:
            LookupError: Nếu post_id không tồn tại.
        """
        # Kiểm tra post tồn tại
        crud.get_post(self.db, post_id)
        return crud.create_comment(
            self.db,
            payload,
            post_id=post_id,
            user_id=user_id,
        )

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
