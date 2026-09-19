from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel

from app.core.ai_client import AiServiceError, ai_client
from app.deps import get_current_user, get_post_service, oauth2_scheme
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
# Input & Output schemas cho Tags & AI Tags
# ---------------------------------------------------------------------------

class TagNamesIn(BaseModel):
    tag_names: list[str]

    model_config = {
        "json_schema_extra": {
            "example": {"tag_names": ["python", "fastapi", "tutorial"]}
        }
    }


class AiTagsOut(BaseModel):
    post_id: int
    tags: list[str]
    analysis: dict

    model_config = {
        "json_schema_extra": {
            "example": {
                "post_id": 1,
                "tags": ["fastapi", "python"],
                "analysis": {
                    "summary": "Tóm tắt bài viết giới thiệu FastAPI...",
                    "tags": ["fastapi", "python"],
                    "topic": "tech",
                    "sentiment": "positive",
                    "language": "vi",
                    "moderation": {"is_safe": True, "categories": [], "severity": "none", "reason": ""},
                },
            }
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


@router.post(
    "/{post_id}/ai-tags",
    response_model=AiTagsOut,
    status_code=status.HTTP_200_OK,
    summary="Gợi ý và tự động gắn tag bằng AI",
    description=(
        "Gọi microservice ai-service phân tích bài viết bằng mô hình Gemini để sinh tags "
        "và tự động gắn các tags này vào bài viết. Chỉ tác giả bài viết mới có quyền thực hiện."
    ),
    response_description="Danh sách tag đã được gắn kèm kết quả phân tích chi tiết",
    responses={
        401: _401,
        403: {"description": "Chỉ tác giả mới có quyền gắn tag tự động cho bài viết này"},
        404: _404_post,
        503: {"description": "Dịch vụ AI tạm thời không khả dụng, bài viết giữ nguyên không đổi"},
    },
)
def attach_ai_tags(
    post_id: int,
    request: Request,
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_user),
    service: PostService = Depends(get_post_service),
):
    try:
        post = service.get_post(post_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    # Kiểm tra quyền tác giả bài viết
    if post.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ tác giả mới có quyền gắn tag tự động bằng AI cho bài viết này",
        )

    req_id = request.headers.get("X-Request-ID")
    try:
        ai_result = ai_client.analyze_post(
            title=post.title,
            content=post.content,
            token=token,
            request_id=req_id,
        )
    except AiServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Dịch vụ AI tạm thời không khả dụng: {exc.message}",
        )

    suggested_tags = ai_result.get("data", {}).get("tags", [])
    if suggested_tags:
        service.attach_tags_to_post(post_id, suggested_tags)

    return AiTagsOut(
        post_id=post_id,
        tags=suggested_tags,
        analysis=ai_result.get("data", {}),
    )

