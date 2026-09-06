from fastapi import FastAPI

from app.routers.users import router as users_router
from app.routers.posts import router as posts_router
from app.routers.comments import router as comments_router

app = FastAPI(
    title="Mini Blog API",
    description=(
        "RESTful API cho ứng dụng blog đơn giản.\n\n"
        "## Tính năng\n"
        "- **Users** — Đăng ký và tra cứu tài khoản\n"
        "- **Posts** — Tạo, đọc, cập nhật, xoá bài viết; gắn tag\n"
        "- **Comments** — Bình luận dưới bài viết\n\n"
        "## Lưu ý\n"
        "API chưa có xác thực (auth). `user_id` được truyền thủ công qua query param "
        "trong giai đoạn phát triển."
    ),
    version="0.1.0",
    contact={"name": "Mini Blog Dev Team"},
    license_info={"name": "MIT"},
)

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(users_router)
app.include_router(posts_router)
app.include_router(comments_router)


# ── Health check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"], summary="Kiểm tra trạng thái server")
def health_check():
    return {"status": "ok"}
