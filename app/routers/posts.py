from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.deps import get_current_user, get_post_service
from app.models.user import User
from app.schemas.post import PostCreate, PostOut, PostUpdate
from app.services.post_service import PostListOut, PostService, TagsOut

router = APIRouter(
    prefix="/posts",
    tags=["Posts"],
)

_404_post = {"description": "Bài viết không tồn tại"}
_404_user = {"description": "User (tác giả) không tồn tại"}
_401 = {"description": "Chưa đăng nhập hoặc Token không hợp lệ"}
_422 = {"description": "Dữ liệu đầu vào không hợp lệ"}


# ---------------------------------------------------------------------------
# Input schema cho POST /posts/{id}/tags
# ---------------------------------------------------------------------------

class TagNamesIn(BaseModel):
    tag_names: list[str]

    model_config = {
        "json_schema_extra": {
            "example": {"tag_names": ["python", "fastapi", "tutorial"]}
        }
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=PostOut,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo bài viết mới",
    description=(
        "Tạo một bài viết mới cho user đang đăng nhập (thông qua Bearer JWT Token)."
    ),
    response_description="Bài viết vừa được tạo",
    responses={
        401: _401,
        404: _404_user,
        422: _422,
    },
)
def create_post(
    payload: PostCreate,
    current_user: User = Depends(get_current_user),
    service: PostService = Depends(get_post_service),
):
    try:
        return service.create_post(payload, user_id=current_user.id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


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
    service: PostService = Depends(get_post_service),
):
    return service.list_posts(skip=skip, limit=limit, tag=tag, author_id=author_id)


@router.get(
    "/{post_id}",
    response_model=PostOut,
    status_code=status.HTTP_200_OK,
    summary="Chi tiết bài viết",
    description="Lấy thông tin chi tiết một bài viết kèm tên tác giả và danh sách tag.",
    response_description="Bài viết với author_name và tags",
    responses={404: _404_post},
)
def get_post(
    post_id: int,
    service: PostService = Depends(get_post_service),
):
    try:
        return service.get_post(post_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


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
def update_post(
    post_id: int,
    payload: PostUpdate,
    service: PostService = Depends(get_post_service),
):
    try:
        return service.update_post(post_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete(
    "/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xoá bài viết",
    description="Xoá bài viết và toàn bộ comment liên quan (cascade). Trả về 204 No Content.",
    response_description="Xoá thành công, không có body",
    responses={404: _404_post},
)
def delete_post(
    post_id: int,
    service: PostService = Depends(get_post_service),
):
    try:
        service.delete_post(post_id)
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
        "nếu có lỗi giữa chừng, không có tag nào được tạo ra."
    ),
    response_description="Danh sách tag hiện tại của bài viết sau khi cập nhật",
    responses={
        400: {"description": "Lỗi transaction khi gắn tag"},
        404: _404_post,
        422: _422,
    },
)
def attach_tags(
    post_id: int,
    payload: TagNamesIn,
    service: PostService = Depends(get_post_service),
):
    try:
        return service.attach_tags_to_post(post_id, payload.tag_names)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tag transaction failed: {exc}",
        )
