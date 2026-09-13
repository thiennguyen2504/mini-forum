from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.deps import get_comment_service, get_current_user
from app.models.user import User
from app.schemas.comment import CommentCreate, CommentOut, CommentUpdate
from app.services.comment_service import CommentService

router = APIRouter(
    prefix="/posts",
    tags=["Comments"],
)

_404_post = {"description": "Bài viết không tồn tại"}
_404_comment = {"description": "Bình luận không tồn tại"}
_401 = {"description": "Chưa đăng nhập hoặc Token không hợp lệ"}
_422 = {"description": "Dữ liệu đầu vào không hợp lệ"}


@router.post(
    "/{post_id}/comments",
    response_model=CommentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo comment",
    description=(
        "Thêm một bình luận vào bài viết. "
        "Yêu cầu người dùng đã đăng nhập (JWT Bearer Token)."
    ),
    response_description="Comment vừa được tạo",
    responses={
        401: _401,
        404: _404_post,
        422: _422,
    },
)
def create_comment(
    post_id: int,
    payload: CommentCreate,
    current_user: User = Depends(get_current_user),
    service: CommentService = Depends(get_comment_service),
):
    try:
        return service.create_comment(post_id, payload, user_id=current_user.id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get(
    "/{post_id}/comments",
    response_model=list[CommentOut],
    status_code=status.HTTP_200_OK,
    summary="Danh sách comment của bài viết",
    description="Lấy toàn bộ bình luận của một bài viết, sắp xếp từ cũ đến mới.",
    response_description="Danh sách comment",
    responses={
        404: _404_post,
    },
)
def list_comments(
    post_id: int,
    skip: int = Query(0, ge=0, description="Số bản ghi bỏ qua"),
    limit: int = Query(50, ge=1, le=200, description="Số bản ghi tối đa"),
    service: CommentService = Depends(get_comment_service),
):
    try:
        return service.list_comments(post_id, skip=skip, limit=limit)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.patch(
    "/comments/{comment_id}",
    response_model=CommentOut,
    status_code=status.HTTP_200_OK,
    summary="Cập nhật bình luận (PATCH)",
    description="Cập nhật nội dung một bình luận theo comment_id.",
    response_description="Comment sau khi cập nhật",
    responses={
        404: _404_comment,
        422: _422,
    },
)
def update_comment(
    comment_id: int,
    payload: CommentUpdate,
    service: CommentService = Depends(get_comment_service),
):
    try:
        return service.update_comment(comment_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xoá bình luận",
    description="Xoá một bình luận theo comment_id. Trả về 204 No Content.",
    response_description="Xoá thành công, không có body",
    responses={
        404: _404_comment,
    },
)
def delete_comment(
    comment_id: int,
    service: CommentService = Depends(get_comment_service),
):
    try:
        service.delete_comment(comment_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
