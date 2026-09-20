# Mini Blog API & Microservices Architecture

[![pipeline status](https://gitlab.com/thiennguyen2504/mini-forum/badges/main/pipeline.svg)](https://gitlab.com/thiennguyen2504/mini-forum/-/commits/main)

Dự án FastAPI backend hoàn chỉnh cho hệ thống Mini Blog RESTful API & Microservices:
- **forum-service**: FastAPI + SQLAlchemy 2.0 + Alembic + JWT Auth + Redis Cache + Kafka Event Publisher.
- **notification-service**: FastAPI + SQLAlchemy + Alembic + Kafka Consumer (lắng nghe event `comment.created` và lưu thông báo).
- **ai-service**: FastAPI + Google Gemini API (Structured Output) + Redis Cache-Aside + Content Moderation + Auto Tagging.
- **nginx**: Reverse Proxy (Port `8081` mapping sang Port `80`) định tuyến `/api/*`, `/notifications/*`, `/ai/*`, kèm Gzip nén dữ liệu và Rate Limiting riêng biệt.
- **db** (PostgreSQL 15), **redis** (Redis 7), **kafka** (Apache Kafka 3.7 KRaft mode), **kafka-ui** (Port `8080`).

---

## 🏗️ Sơ đồ kiến trúc hệ thống

```
                    Client (Browser / Postman / cURL)
                                   │
                                   ▼
                    ┌─────────────────────────────┐
                    │     Nginx Reverse Proxy     │
                    │        (Port 80/8081)       │
                    │   Rate Limit 10r/s + Gzip   │
                    └──────────────┬──────────────┘
                                   │
      ┌────────────────────────────┼────────────────────────────┐
      │ /api/* (strip prefix)      │ /notifications/*           │ /ai/* (giữ prefix)
      ▼                            ▼                            ▼
┌───────────────────┐    ┌───────────────────────────┐    ┌───────────────────────────┐
│   forum-service   │    │   notification-service    │    │        ai-service         │
│     (Port 8000)   │    │        (Port 8000)        │    │        (Port 8000)        │
└────┬─────────┬────┘    └─────────────┬─────────────┘    └─────────────┬─────────────┘
     │         │                       │                                │
     │         │ (httpx, JWT)          │                                │ (google-genai)
     │         ├───────────────────────┼────────────────────────────────┤
     │         ▼                       ▼                                ▼
     │   ┌───────────┐           ┌───────────┐                    ┌───────────┐
     │   │   Redis   │           │   Kafka   │                    │  Gemini   │
     │   │  (Cache)  │           │  (KRaft)  │                    │ Flash API │
     │   └───────────┘           └───────────┘                    └───────────┘
     │         ▲
     │         │ (ai:analyze:*)
     │         └────────────────────────────────────────────────────────┘
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
│   ├── core/                   # Security, Redis Cache, Kafka Events, AI Client
│   ├── crud/                   # Tương tác Database trực tiếp
│   ├── services/               # Service layer (PostService, CommentService)
│   ├── models/                 # SQLAlchemy ORM Models
│   ├── routers/                # API Routers (Auth, Users, Posts, Comments)
│   ├── schemas/                # Pydantic v2 schemas
│   ├── deps.py                 # Dependencies injection
│   └── main.py                 # Entrypoint forum-service
├── ai-service/                 # Microservice phân tích bài viết bằng AI (Gemini)
│   ├── app/
│   │   ├── config.py           # Đọc biến môi trường & cài đặt
│   │   ├── logging.py          # JSON structured logging kèm X-Request-ID
│   │   ├── auth.py             # Xác thực JWT Bearer Token
│   │   ├── cache.py            # Redis Cache-Aside & Circuit Breaker
│   │   ├── errors.py           # AIServiceError & handlers lỗi chuẩn
│   │   ├── schemas.py          # PostAnalysis, AnalyzeRequest, Response
│   │   ├── normalize.py        # Sanitize input, chuẩn hoá tag, thoát XML
│   │   ├── llm/                # LLM Client layer (Base, Fake, Gemini, Factory)
│   │   ├── prompts/            # Versioned prompts (v1, v2) & loader
│   │   ├── services/           # Analyzer orchestration service
│   │   └── routers/            # Router /ai/analyze, /ai/health
│   ├── eval/                   # Dataset & Runner đánh giá chất lượng prompt
│   │   ├── cases.jsonl         # 28 ca kiểm thử thực tế
│   │   ├── run_eval.py         # Bộ chạy đánh giá tự động
│   │   └── reports/            # Thư mục lưu báo cáo JSON/Markdown
│   ├── tests/                  # Bộ test tự động pytest cho ai-service
│   ├── Dockerfile
│   ├── requirements.txt
│   └── README.md
├── notification-service/       # Microservice thông báo độc lập
│   ├── app/                    # FastAPI app & Kafka Consumer
│   ├── alembic/                # Migration riêng cho bảng notifications
│   ├── Dockerfile
│   └── requirements.txt
├── demo/
│   └── demo.py                 # Kịch bản demo end-to-end tự động
├── docs/
│   └── PROMPT.md               # Tài liệu thiết kế prompt & phòng thủ injection
├── postman/                    # Postman collection & environment (kèm folder AI)
├── nginx/
│   └── nginx.conf              # Cấu hình Nginx Reverse Proxy (port 80)
├── tests/                      # Bộ test tự động pytest cho forum-service
├── docker-compose.yml          # Điều phối 8 services
├── requirements.txt            # Thư viện cho forum-service
└── README.md
```

---

## 🐳 Khởi chạy toàn bộ hệ thống bằng Docker Compose

### Cấu hình biến môi trường:
Sao chép `.env.example` thành `.env` và điền khóa `GEMINI_API_KEY`:

```bash
cp .env.example .env
```
*(Nếu chưa có `GEMINI_API_KEY`, bạn có thể đặt `LLM_PROVIDER=fake` để chạy hoàn toàn offline không tốn phí).*

### Khởi động cả 8 containers:
```bash
docker compose up --build -d
```

### Danh sách các container hoạt động:
1. `mini_blog_nginx`: Reverse Proxy (Port Host `8081` -> Container `80`).
2. `mini_blog_forum`: `forum-service` (gọi qua `http://localhost:8081/api/*`).
3. `mini_blog_notification`: `notification-service` (gọi qua `http://localhost:8081/notifications/*`).
4. `mini_blog_ai`: `ai-service` (gọi qua `http://localhost:8081/ai/*`).
5. `mini_blog_redis`: Redis 7 Cache (Port `6379`).
6. `mini_blog_kafka`: Apache Kafka 3.7 KRaft broker (Port `9092`).
7. `mini_blog_db`: PostgreSQL 15 Database (Port `5432`).
8. `mini_blog_kafka_ui`: Kafka UI trực quan hóa event topics (Port `8080`).

Dừng hệ thống:
```bash
docker compose down
```

---

## 🎬 Chạy Demo Kịch Bản Tự Động (Demo Script)

Kịch bản `demo/demo.py` tự động thực hiện: kiểm tra health check, đăng ký tài khoản, đăng nhập lấy JWT, tạo 4 bài viết mẫu (Tech, Question, Spam, Prompt Injection), phân tích bài viết bằng AI, tự động gắn tag, kiểm chứng Redis cache hit lần 2 và kiểm tra lỗi 401/422.

```bash
python demo/demo.py --base-url http://localhost:8081
```

*(Thêm cờ `--no-color` nếu terminal không hỗ trợ mã màu ANSI).*

---

## 📊 Đánh Giá Chất Lượng Prompt (Eval Suite)

Chạy đánh giá trên 28 mẫu kiểm thử thực tế bao gồm đa dạng chủ đề, tiếng Việt có dấu/không dấu, teencode, spam, scam, toxicity, adult, và các dạng tấn công prompt injection:

```bash
# Chạy offline với fake provider
python ai-service/eval/run_eval.py --provider fake --prompt-version v2

# So sánh phiên bản baseline v1 và cải tiến v2
python ai-service/eval/run_eval.py --provider fake --compare v1 v2

# Chạy với Gemini API thật (yêu cầu GEMINI_API_KEY)
python ai-service/eval/run_eval.py --provider gemini --prompt-version v2
```

Xem tài liệu chi tiết về prompt tại [docs/PROMPT.md](docs/PROMPT.md).

---

## 🧪 Chạy Kiểm Thử Tự Động (Pytest)

Tất cả các test đều độc lập, mock client LLM và không phụ thuộc vào kết nối mạng:

```bash
# 1. Kiểm thử forum-service (30 tests)
pytest tests/ -v

# 2. Kiểm thử notification-service (4 tests)
pytest notification-service/tests/ -v

# 3. Kiểm thử ai-service (69 tests)
pytest ai-service/tests/ -v

# 4. Kiểm tra mã nguồn với ruff
ruff check app/ notification-service/app/ ai-service/app/ ai-service/eval/ demo/
```
