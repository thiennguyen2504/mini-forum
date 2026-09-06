from fastapi import FastAPI

from app.routers.auth import router as auth_router
from app.routers.users import router as users_router
from app.routers.posts import router as posts_router
from app.routers.comments import router as comments_router

app = FastAPI(
    title="Mini Blog API",
    description=(
        "RESTful API cho ứng dụng blog đơn giản hỗ trợ Xác thực JWT (JWT Authentication).\n\n"
        "## Tính năng\n"
        "- **Auth** — Đăng ký (`/auth/register`) và Đăng nhập (`/auth/token`) lấy JWT token\n"
        "- **Users** — Đăng ký và tra cứu tài khoản\n"
        "- **Posts** — Tạo (yêu cầu Token), đọc, cập nhật, xoá bài viết; gắn tag\n"
        "- **Comments** — Bình luận dưới bài viết (yêu cầu Token)\n\n"
        "## Hướng dẫn Auth\n"
        "1. Tạo tài khoản tại `/auth/register` hoặc đùng API `/auth/token` với `username` (là email) và `password`.\n"
        "2. Bấm **Authorize 🔒** góc trên SwaggerUI, nhập Bearer token để gọi các API yêu cầu đăng nhập."
    ),
    version="0.2.0",
    contact={"name": "Mini Blog Dev Team"},
    license_info={"name": "MIT"},
)

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(posts_router)
app.include_router(comments_router)


# ── Health check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"], summary="Kiểm tra trạng thái server")
def health_check():
    return {"status": "ok"}
