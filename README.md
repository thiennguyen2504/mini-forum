# Mini Blog API

Dự án FastAPI backend hoàn chỉnh cho ứng dụng Mini Blog RESTful API với SQLAlchemy 2.0, Alembic migration, JWT Authentication, Pytest suite và Postman collection.

---

## 📁 Cấu trúc thư mục dự án

```text
mini-blog-api/
├── app/
│   ├── core/           # Module bảo mật (mã hoá bcrypt, tạo/mã hoá JWT token)
│   ├── crud/           # Tầng tương tác dữ liệu Database (User, Post, Comment, Tag)
│   ├── models/         # Các ORM models Declarative SQLAlchemy 2.0
│   ├── routers/        # Định tuyến API (Auth, Users, Posts, Comments)
│   ├── schemas/        # Validation schemas Pydantic v2
│   ├── db.py           # Khởi tạo DB Engine & SessionLocal
│   ├── deps.py         # Dependencies cho FastAPI (get_db, get_current_user)
│   └── main.py         # Entry point ứng dụng FastAPI
├── alembic/            # Thư mục quản lý Database Migrations
├── postman/            # Postman Collection & Environment JSON
├── tests/              # Bộ test cases tự động (pytest)
├── .env.example        # File mẫu cấu hình biến môi trường
├── alembic.ini         # Cấu hình Alembic
├── requirements.txt    # Các thư viện phụ thuộc
└── README.md           # Hướng dẫn sử dụng
```

---

## 🚀 Hướng dẫn cài đặt và chạy ứng dụng

### 1. Tạo và kích hoạt môi trường ảo (Virtual Environment)

**Trên Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Trên Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

---

### 2. Cài đặt các thư viện phụ thuộc

```bash
pip install -r requirements.txt
```

---

### 3. Cấu hình biến môi trường

Tạo file `.env` từ file mẫu `.env.example`:
```bash
cp .env.example .env
```
Nội dung mẫu file `.env`:
```ini
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/mini_blog
SECRET_KEY=your-super-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

---

### 4. Chạy Database Migration (Alembic)

Khởi tạo và cập nhật cấu trúc cơ sở dữ liệu lên phiên bản mới nhất:
```bash
alembic upgrade head
```

---

### 5. Chạy Server ở chế độ Development

```bash
uvicorn app.main:app --reload
```

Sau khi ứng dụng khởi chạy thành công:
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)
- **Interactive Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🧪 Chạy Kiểm thử (Unit & Integration Tests)

Dự án tích hợp bộ kiểm thử tự động với SQLite in-memory DB:

```bash
pytest -v
```

---

## 📬 Hướng dẫn Import Postman Collection & Environment

Trong thư mục `postman/` đã có sẵn các file cấu hình cho Postman:

1. **Import Collection**:
   - Mở Postman -> Bấm nút **Import** (góc trên bên trái).
   - Chọn file `postman/mini-blog-api.postman_collection.json`.

2. **Import Environment**:
   - Trong Postman, chọn phần **Environments** (cột bên trái) -> Bấm **Import**.
   - Chọn file `postman/mini-blog-api.postman_environment.json`.

3. **Sử dụng**:
   - Chọn Environment **Mini Blog API Environment** ở góc trên bên phải giao diện Postman.
   - Chạy request `/auth/register` để đăng ký tài khoản.
   - Chạy request `/auth/token` để đăng nhập: Test script sẽ **tự động lưu `access_token`** vào biến môi trường Postman.
   - Các request yêu cầu đăng nhập (tạo bài viết, bình luận) sẽ tự động đính kèm `Bearer {{access_token}}`.
