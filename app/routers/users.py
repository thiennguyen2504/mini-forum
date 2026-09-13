from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud
from app.deps import get_db
from app.schemas.user import UserCreate, UserOut, UserUpdate

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)

_404 = {"description": "User không tồn tại"}
_409 = {"description": "Email đã được đăng ký"}
_422 = {"description": "Dữ liệu đầu vào không hợp lệ"}


@router.post(
    "",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo user mới",
    description="Tạo một tài khoản người dùng mới. Email phải là duy nhất trong hệ thống.",
    response_description="User vừa được tạo",
    responses={
        409: _409,
        422: _422,
    },
)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_user(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get(
    "/{user_id}",
    response_model=UserOut,
    status_code=status.HTTP_200_OK,
    summary="Lấy thông tin user",
    description="Trả về thông tin chi tiết của một user theo ID.",
    response_description="Thông tin user",
    responses={
        404: _404,
    },
)
def get_user(user_id: int, db: Session = Depends(get_db)):
    try:
        return crud.get_user(db, user_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.patch(
    "/{user_id}",
    response_model=UserOut,
    status_code=status.HTTP_200_OK,
    summary="Cập nhật thông tin user (PATCH)",
    description="Cập nhật một phần thông tin user (email, name, password).",
    response_description="User sau khi cập nhật",
    responses={
        404: _404,
        409: _409,
        422: _422,
    },
)
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db)):
    try:
        return crud.update_user(db, user_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xoá user",
    description="Xoá tài khoản user và toàn bộ bài viết, bình luận liên quan (cascade).",
    response_description="Xoá thành công, không có body",
    responses={
        404: _404,
    },
)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    try:
        crud.delete_user(db, user_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
