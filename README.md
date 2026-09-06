# Mini Blog API

Dự án FastAPI backend cho ứng dụng Mini Blog.

## Cấu trúc dự án

```text
mini-blog-api/
├── app/
│   ├── main.py
│   ├── models/
│   ├── schemas/
│   ├── routers/
│   ├── crud/
│   ├── db.py
│   └── deps.py
├── tests/
├── alembic/
├── alembic.ini
├── requirements.txt
└── README.md
```

## Hướng dẫn cài đặt và chạy dự án

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

### 2. Cài đặt các thư viện phụ thuộc

```bash
pip install -r requirements.txt
```

### 3. Chạy server ở chế độ Development

```bash
uvicorn app.main:app --reload
```

Sau khi chạy server thành công, truy cập:
- **Health Check**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- **API Documentation (Swagger UI)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
