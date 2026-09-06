from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import crud
from app.deps import get_db
from app.schemas.comment import CommentCreate, CommentOut

router = APIRouter(
    prefix="/posts",
    tags=["Comments"],
)

_404_post = {"description": "Bài viết không tồn tại"}
_422 = {"description": "Dữ liệu đầu vào không hợp lệ"}


@router.post(
    "/{post_id}/comments",
    response_model=CommentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo comment",
    description=(
        "Thêm một bình luận vào bài viết. "
        "Truyền `user_id` qua query param để xác định người bình luận."
    ),
    response_description="Comment vừa được tạo",
    responses={
        404: _404_post,
        422: _422,
    },
)
def create_comment(
    post_id: int,
    payload: CommentCreate,
    user_id: int = Query(..., description="ID của người bình luận"),
    db: Session = Depends(get_db),
):
    # Kiểm tra post tồn tại trước (tránh IntegrityError mơ hồ)
    try:
        crud.get_post(db, post_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    return crud.create_comment(db, payload, post_id=post_id, user_id=user_id)


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
    db: Session = Depends(get_db),
):
    # Kiểm tra post tồn tại
    try:
        crud.get_post(db, post_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    return crud.get_comments_by_post(db, post_id, skip=skip, limit=limit)
