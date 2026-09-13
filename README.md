# Mini Blog API & Microservices Architecture

Dự án FastAPI backend hoàn chỉnh cho hệ thống Mini Blog RESTful API & Notification Microservice:
- **forum-service**: FastAPI + SQLAlchemy 2.0 + Alembic + JWT Auth + Redis Cache + Kafka Event Publisher.
- **notification-service**: FastAPI + SQLAlchemy + Alembic + Kafka Consumer (lắng nghe event `comment.created` và lưu thông báo).
- **nginx**: Reverse Proxy (Port 80) định tuyến `/api/*` và `/notifications/*`, kèm Gzip nén dữ liệu và Rate Limiting.
- **db** (PostgreSQL 15), **redis** (Redis 7), **kafka** (Apache Kafka 3.7 KRaft mode).

---

## 🏗️ Sơ đồ kiến trúc hệ thống

```
                    Client (Browser / Postman / cURL)
                                   │
                                   ▼
                    ┌─────────────────────────────┐
                    │     Nginx Reverse Proxy     │
                    │         (Port 80)           │
                    │   Rate Limit 10r/s + Gzip   │
                    └──────────────┬──────────────┘
                                   │
            ┌──────────────────────┴──────────────────────┐
            │ /api/* (strip prefix)                       │ /notifications/*
            ▼                                             ▼
  ┌───────────────────┐                         ┌───────────────────────────┐
  │   forum-service   │                         │   notification-service    │
  │     (Port 8000)   │                         │        (Port 8000)        │
  └────┬─────────┬────┘                         └─────────────┬─────────────┘
       │         │                                            │
       │         │ 1. Produce "comment.created"               │ 2. Consume event
       │         ▼                                            ▼
       │   ┌───────────┐       Event Stream             ┌───────────┐
       │   │   Redis   │   ─────────────────────────►   │   Kafka   │
       │   │  (Cache)  │                                │  (KRaft)  │
       │   └───────────┘                                └───────────┘
       │
       ▼
 ┌───────────────┐
 │  PostgreSQL   │ ◄─── (Cùng lưu trữ: forum data & notifications table)
 │   Database    │
 └───────────────┘
```

---

## 📁 Cấu trúc thư mục dự án

```text
mini-blog-api/
├── app/                        # Mã nguồn forum-service
│   ├── core/                   # Security, Redis Cache, Kafka Events Publisher
│   ├── crud/                   # Tương tác Database trực tiếp
│   ├── services/               # Service layer (PostService, CommentService)
│   ├── models/                 # SQLAlchemy ORM Models
│   ├── routers/                # API Routers (Auth, Users, Posts, Comments)
│   ├── schemas/                # Pydantic v2 schemas
│   ├── deps.py                 # Dependencies injection
│   └── main.py                 # Entrypoint forum-service
├── notification-service/       # Microservice thông báo độc lập
│   ├── app/
│   │   ├── config.py           # Cấu hình DB & Kafka
│   │   ├── consumer.py         # Kafka consumer worker chạy nền
│   │   ├── db.py & models.py   # SQLAlchemy model Notification
│   │   ├── schemas.py          # NotificationOut schema
│   │   └── main.py             # FastAPI app (GET /health, GET /notifications/{user_id})
│   ├── alembic/                # Migration riêng cho bảng notifications
│   ├── Dockerfile
│   └── requirements.txt
├── nginx/
│   └── nginx.conf              # Cấu hình Nginx Reverse Proxy (port 80)
├── alembic/                    # Migration cho forum-service
├── tests/                      # Bộ test tự động pytest
├── docker-compose.yml          # Điều phối 6 services (db, redis, kafka, 2 apps, nginx)
├── requirements.txt            # Thư viện cho forum-service
└── README.md
```

---

## 🐳 Khởi chạy toàn bộ hệ thống bằng Docker Compose

Chạy một lệnh duy nhất để build và khởi động cả 6 services:

```bash
docker compose up --build -d
```

Kiểm tra trạng thái các container:
```bash
docker compose ps
```

Các container sẽ hoạt động đồng bộ:
- `mini_blog_nginx`: Port `80` (Cổng truy cập chính của toàn bộ hệ thống).
- `mini_blog_forum`: `forum-service` (gọi qua `http://localhost/api/*`).
- `mini_blog_notification`: `notification-service` (gọi qua `http://localhost/notifications/*`).
- `mini_blog_kafka`: Kafka KRaft broker (Port `9092`).
- `mini_blog_redis`: Redis Cache (Port `6379`).
- `mini_blog_db`: PostgreSQL Database (Port `5432`).

Dừng hệ thống:
```bash
docker compose down
```

Dừng và xoá sạch dữ liệu:
```bash
docker compose down -v
```

---

## 🧪 Chạy Kiểm thử Tự động (Pytest)

Toàn bộ 18 test cases của `forum-service` kiểm tra CRUD, Service Layer, Redis Fallback, Tags, Comments và Users:

```bash
pytest -v
```
