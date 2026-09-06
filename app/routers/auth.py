from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import crud
from app.core import security
from app.deps import get_db
from app.schemas.user import TokenOut, UserCreate, UserOut

router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Đăng ký tài khoản",
    description="Đăng ký một tài khoản người dùng mới. Email phải là duy nhất.",
    response_description="User vừa được tạo",
    responses={
        409: {"description": "Email đã được đăng ký"},
        422: {"description": "Dữ liệu đầu vào không hợp lệ"},
    },
)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_user(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post(
    "/token",
    response_model=TokenOut,
    status_code=status.HTTP_200_OK,
    summary="Đăng nhập lấy JWT access token",
    description="Đăng nhập bằng email và password để nhận JWT access token.",
    response_description="Access token",
    responses={
        401: {"description": "Sai email hoặc mật khẩu"},
    },
)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = crud.authenticate_user(
        db, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = security.create_access_token(subject=user.id)
    return TokenOut(access_token=access_token, token_type="bearer")
