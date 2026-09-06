# Mini Blog API

Dự án FastAPI backend hoàn chỉnh cho ứng dụng Mini Blog RESTful API với SQLAlchemy 2.0, Alembic migration, JWT Authentication, Pytest suite, Postman collection và Docker Compose (PostgreSQL).

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
├── docker-compose.yml  # File cấu hình Docker Compose (PostgreSQL & FastAPI)
├── Dockerfile          # Containerize ứng dụng FastAPI
├── requirements.txt    # Các thư viện phụ thuộc
└── README.md           # Hướng dẫn sử dụng
```

---

## 🐳 Cấu hình Database & Docker Compose

Dự án linh hoạt hỗ trợ nhiều tuỳ chọn kết nối cơ sở dữ liệu:

### **Cách 1: Chỉ chạy PostgreSQL bằng Docker Compose (Khuyên dùng khi dev trên máy)**

1. Khởi chạy duy nhất container PostgreSQL ở chế độ ngầm (`detached`):
   ```bash
   docker compose up -d db
   ```
2. Cấu hình file `.env` trên máy host:
   ```ini
   DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/mini_blog
   SECRET_KEY=your-super-secret-key-change-in-production
   ```
3. Chạy migration và khởi động server trên máy local:
   ```bash
   alembic upgrade head
   uvicorn app.main:app --reload
   ```

---

### **Cách 2: Chạy toàn bộ ứng dụng (FastAPI + PostgreSQL) bằng Docker Compose**

Chạy duy nhất 1 lệnh để build và khởi chạy cả ứng dụng FastAPI và DB PostgreSQL trong Docker:
```bash
docker compose up --build
```
> Server sẽ tự động chờ DB sẵn sàng, tự chạy `alembic upgrade head` và khởi động server tại [http://localhost:8000](http://localhost:8000).

- Tắt các containers:
  ```bash
  docker compose down
  ```
- Tắt và xoá sạch dữ liệu DB container:
  ```bash
  docker compose down -v
  ```

---

### **Cách 3: Kết nối với SQLite cục bộ (Không cần cài/chạy PostgreSQL)**

Trong file `.env`, chuyển sang dùng SQLite:
```ini
DATABASE_URL=sqlite:///./mini_blog.db
```
Chạy migration và ứng dụng trực tiếp:
```bash
alembic upgrade head
uvicorn app.main:app --reload
```

---

## 🚀 Hướng dẫn cài đặt thủ công (Không dùng Docker)

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

### 3. Khởi chạy ứng dụng

Sau khi khởi chạy server thành công (truy cập cổng `8000`):
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
   - Mở Postman -> Bấm **Import** -> Chọn file `postman/mini-blog-api.postman_collection.json`.
2. **Import Environment**:
   - Chọn **Environments** -> Bấm **Import** -> Chọn file `postman/mini-blog-api.postman_environment.json`.
3. **Sử dụng**:
   - Chọn Environment **Mini Blog API Environment** góc trên bên phải.
   - Chạy request `/auth/register` để đăng ký.
   - Chạy request `/auth/token` để đăng nhập (Tự động lưu `access_token`).
