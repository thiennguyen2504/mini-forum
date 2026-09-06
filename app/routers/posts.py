from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import crud
from app.deps import get_db
from app.schemas.post import PostCreate, PostOut, PostUpdate

router = APIRouter(
    prefix="/posts",
    tags=["Posts"],
)

_404_post = {"description": "Bài viết không tồn tại"}
_404_user = {"description": "User (tác giả) không tồn tại"}
_422 = {"description": "Dữ liệu đầu vào không hợp lệ"}


# ---------------------------------------------------------------------------
# Helper: ORM Post → PostOut (map author_name + tags thủ công)
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
# Response schema cho GET /posts (paginated list)
# ---------------------------------------------------------------------------

class PostListOut(BaseModel):
    items: list[PostOut]
    total: int
    skip: int
    limit: int


# ---------------------------------------------------------------------------
# Response schema cho POST /posts/{id}/tags
# ---------------------------------------------------------------------------

class TagNamesIn(BaseModel):
    tag_names: list[str]

    model_config = {
        "json_schema_extra": {
            "example": {"tag_names": ["python", "fastapi", "tutorial"]}
        }
    }


class TagsOut(BaseModel):
    post_id: int
    tags: list[str]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=PostOut,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo bài viết mới",
    description=(
        "Tạo một bài viết mới cho user có `user_id` trong query param. "
        "User phải tồn tại trước khi tạo bài viết."
    ),
    response_description="Bài viết vừa được tạo",
    responses={
        404: _404_user,
        422: _422,
    },
)
def create_post(
    user_id: int = Query(..., description="ID của tác giả"),
    payload: PostCreate = ...,
    db: Session = Depends(get_db),
):
    try:
        post = crud.create_post(db, payload, user_id=user_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    # Reload với selectinload để lấy author + tags
    post = crud.get_post(db, post.id)
    return _to_post_out(post)


@router.get(
    "",
    response_model=PostListOut,
    status_code=status.HTTP_200_OK,
    summary="Danh sách bài viết",
    description=(
        "Lấy danh sách bài viết có phân trang. "
        "Hỗ trợ filter theo tên tag (`tag`) và ID tác giả (`author_id`)."
    ),
    response_description="Danh sách bài viết kèm thông tin phân trang",
    responses={422: _422},
)
def list_posts(
    skip: int = Query(0, ge=0, description="Số bản ghi bỏ qua"),
    limit: int = Query(20, ge=1, le=100, description="Số bản ghi tối đa trả về"),
    tag: Optional[str] = Query(None, description="Lọc theo tên tag"),
    author_id: Optional[int] = Query(None, description="Lọc theo ID tác giả"),
    db: Session = Depends(get_db),
):
    posts = crud.get_posts(db, skip=skip, limit=limit, tag_name=tag, author_id=author_id)
    items = [_to_post_out(p) for p in posts]
    return PostListOut(items=items, total=len(items), skip=skip, limit=limit)


@router.get(
    "/{post_id}",
    response_model=PostOut,
    status_code=status.HTTP_200_OK,
    summary="Chi tiết bài viết",
    description="Lấy thông tin chi tiết một bài viết kèm tên tác giả và danh sách tag.",
    response_description="Bài viết với author_name và tags",
    responses={404: _404_post},
)
def get_post(post_id: int, db: Session = Depends(get_db)):
    try:
        post = crud.get_post(db, post_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return _to_post_out(post)


@router.patch(
    "/{post_id}",
    response_model=PostOut,
    status_code=status.HTTP_200_OK,
    summary="Cập nhật bài viết (PATCH)",
    description=(
        "Cập nhật một phần bài viết. Chỉ field nào được gửi lên mới thay đổi; "
        "field bỏ qua sẽ giữ nguyên giá trị cũ."
    ),
    response_description="Bài viết sau khi cập nhật",
    responses={
        404: _404_post,
        422: _422,
    },
)
def update_post(post_id: int, payload: PostUpdate, db: Session = Depends(get_db)):
    try:
        crud.update_post(db, post_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    post = crud.get_post(db, post_id)
    return _to_post_out(post)


@router.delete(
    "/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xoá bài viết",
    description="Xoá bài viết và toàn bộ comment liên quan (cascade). Trả về 204 No Content.",
    response_description="Xoá thành công, không có body",
    responses={404: _404_post},
)
def delete_post(post_id: int, db: Session = Depends(get_db)):
    try:
        crud.delete_post(db, post_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post(
    "/{post_id}/tags",
    response_model=TagsOut,
    status_code=status.HTTP_200_OK,
    summary="Gắn tag vào bài viết",
    description=(
        "Gán danh sách tag cho bài viết. Tag chưa tồn tại sẽ được tạo mới. "
        "Toàn bộ thao tác thực hiện trong một transaction duy nhất — "
        "nếu có lỗi giữa chừng, không có tag mồ côi nào được tạo ra."
    ),
    response_description="Danh sách tag hiện tại của bài viết sau khi cập nhật",
    responses={
        400: {"description": "Lỗi transaction khi gắn tag"},
        404: _404_post,
        422: _422,
    },
)
def attach_tags(post_id: int, payload: TagNamesIn, db: Session = Depends(get_db)):
    try:
        post = crud.attach_tags_to_post(db, post_id, payload.tag_names)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tag transaction failed: {exc}",
        )
    return TagsOut(post_id=post.id, tags=[t.name for t in post.tags])
