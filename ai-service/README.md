# AI Service (Gemini API & Structured Output)

Microservice độc lập trong hệ sinh thái Mini Blog, cung cấp tính năng phân tích bài viết thông minh sử dụng mô hình ngôn ngữ lớn (Google Gemini) kết hợp kỹ thuật **Structured Output** chặt chẽ và hệ thống **Cache-Aside** trên Redis.

---

## 1. Tính năng chính

- **Trích xuất thông tin có cấu trúc**:
  - Tóm tắt nội dung bài viết (tối đa 300 ký tự).
  - Gợi ý danh sách tag chuẩn hoá (ASCII, lowercase kebab-case, 2–30 ký tự, khử trùng lặp).
  - Phân loại chủ đề (`tech`, `question`, `news`, `discussion`, `life`, `other`).
  - Phân tích sắc thái cảm xúc (`positive`, `neutral`, `negative`).
  - Nhận diện ngôn ngữ (`vi`, `en`, `other`).
- **Kiểm duyệt nội dung an toàn (Content Moderation)**:
  - Đánh giá `is_safe` (True/False).
  - Phân loại vi phạm: `spam`, `toxicity`, `adult`, `scam`, `off_topic`.
  - Mức độ nghiêm trọng: `none`, `low`, `medium`, `high`.
  - Ràng buộc nhất quán: khi `is_safe=True` thì `categories=[]` và `severity="none"`; khi `is_safe=False` thì `severity != "none"` và bắt buộc có danh mục vi phạm.
- **Phòng thủ chống Prompt Injection**:
  - Đóng gói dữ liệu trong thẻ XML `<post><title>...</title><content>...</content></post>`.
  - Vô hiệu hoá chuỗi thoát thẻ `</post>`.
  - Chỉ dẫn hệ thống coi dữ liệu bên trong là dữ liệu tĩnh, phớt lờ mọi mệnh lệnh can thiệp.
- **Tối ưu hiệu năng & Chi phí**:
  - Cache-aside bằng Redis (TTL mặc định 6 giờ) với key SHA-256 theo nội dung, phiên bản prompt, mô hình và số lượng tag.
  - Cơ chế Circuit Breaker fail-open: Redis gặp sự cố không làm gián đoạn phân tích của service.
  - Cơ chế thử lại (Retry) với exponential backoff khi LLM trả lỗi định dạng JSON hoặc timeout.

---

## 2. Bảng biến môi trường (Environment Variables)

| Biến môi trường | Kiểu dữ liệu | Mặc định | Ý nghĩa & Ghi chú |
|---|---|---|---|
| `GEMINI_API_KEY` | `str` | `""` | Khóa API của Google Gemini (để trống nếu dùng fake provider) |
| `GEMINI_MODEL` | `str` | `gemini-2.5-flash` | Tên mô hình Gemini sử dụng |
| `GEMINI_SAFETY_LEVEL` | `str` | `BLOCK_ONLY_HIGH` | Cấu hình lọc an toàn: `BLOCK_NONE`, `BLOCK_ONLY_HIGH`, v.v. |
| `LLM_PROVIDER` | `str` | `gemini` | `gemini` (gọi API thật) hoặc `fake` (chạy offline / test) |
| `LLM_TIMEOUT_SECONDS` | `float` | `20.0` | Thời gian timeout mỗi lần gọi LLM (giây) |
| `LLM_MAX_RETRIES` | `int` | `2` | Số lần thử lại tối đa khi LLM trả JSON hỏng / timeout |
| `AI_CACHE_TTL_SECONDS` | `int` | `21600` | Thời gian lưu cache Redis (giây, mặc định 6 giờ) |
| `AI_REQUIRE_AUTH` | `bool` | `true` | Bắt buộc xác thực JWT Bearer Token |
| `AI_MAX_INPUT_CHARS` | `int` | `6000` | Giới hạn độ dài ký tự tối đa đầu vào |
| `AI_PROMPT_VERSION` | `str` | `v2` | Phiên bản prompt: `v1` (baseline) hoặc `v2` (cải tiến) |
| `SECRET_KEY` | `str` | `...` | Khóa bí mật giải mã JWT (đồng bộ với forum-service) |
| `REDIS_URL` | `str` | `redis://127.0.0.1:6379/0` | Địa chỉ kết nối Redis cache |

---

## 3. Khởi chạy cục bộ (Local Development)

### Cài đặt thư viện:
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Chạy server FastAPI:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 4. API Endpoints

Router sử dụng prefix `/ai`.

### 4.1. `POST /ai/analyze`
Phân tích bài viết bằng AI.

**Headers**:
- `Authorization: Bearer <JWT_TOKEN>` (bắt buộc khi `AI_REQUIRE_AUTH=true`)
- `X-Request-ID: <UUID>` (tuỳ chọn, phục vụ distributed tracing)

**Request Body**:
```json
{
  "title": "Hướng dẫn tối ưu Redis Cache cho FastAPI",
  "content": "Nội dung bài viết chia sẻ về mô hình cache-aside...",
  "options": {
    "max_tags": 5,
    "skip_cache": false
  }
}
```

**Response 200 OK**:
```json
{
  "data": {
    "summary": "Chia sẻ phương pháp tối ưu hóa hiệu năng ứng dụng FastAPI thông qua mô hình cache-aside với Redis.",
    "tags": ["fastapi", "redis", "cache", "performance"],
    "topic": "tech",
    "sentiment": "positive",
    "language": "vi",
    "moderation": {
      "is_safe": true,
      "categories": [],
      "severity": "none",
      "reason": "Bài viết kỹ thuật hữu ích, chuẩn mực."
    }
  },
  "meta": {
    "model": "gemini-2.5-flash",
    "prompt_version": "v2",
    "latency_ms": 320.5,
    "cached": false,
    "retries": 0,
    "request_id": "0192e21b-4f40-7ab3-97ea-d8312019a12c"
  }
}
```

**Mã lỗi chuẩn**:
```json
{
  "error": {
    "code": "LLM_TIMEOUT",
    "message": "Quá thời gian 20.0s khi gọi Gemini API",
    "request_id": "0192e21b-4f40-7ab3-97ea-d8312019a12c"
  }
}
```

| HTTP Code | Error Code | Nguyên nhân |
|---|---|---|
| 401 | `UNAUTHORIZED` | Token JWT thiếu, không hợp lệ hoặc đã hết hạn |
| 422 | `INVALID_INPUT` | Input sai schema (ví dụ: title rỗng) |
| 422 | `CONTENT_BLOCKED` | Gemini chặn prompt/output vì vi phạm bộ lọc an toàn |
| 502 | `LLM_INVALID_OUTPUT` | Hết số lần retry mà LLM vẫn trả format sai |
| 503 | `LLM_UNAVAILABLE` | Gemini bị quá tải (429/5xx) hoặc chưa cấu hình API key |
| 504 | `LLM_TIMEOUT` | Quá thời gian chờ phản hồi từ LLM |

### 4.2. `GET /ai/health`
Kiểm tra sức khoẻ của service (không gọi Gemini để tránh phát sinh chi phí).

**Response 200 OK**:
```json
{
  "status": "ok",
  "provider": "gemini",
  "model": "gemini-2.5-flash",
  "redis": "ok"
}
```

---

## 5. Chạy Kiểm Thử (Unit & Integration Tests)

Bộ test tự động gồm 69 test cases độc lập, sử dụng `FakeLLMClient` và không phụ thuộc vào kết nối mạng:

```bash
pytest tests/ -v
```

---

## 6. Đánh Giá Chất Lượng Prompt (Eval Runner)

Hỗ trợ chạy đánh giá trên bộ test dataset 28 mẫu thực tế:

```bash
# Đánh giá chế độ offline với fake provider
python eval/run_eval.py --provider fake --prompt-version v2

# So sánh hiệu quả giữa phiên bản v1 và v2
python eval/run_eval.py --provider fake --compare v1 v2

# Chạy đánh giá thật với Gemini API (yêu cầu GEMINI_API_KEY)
GEMINI_API_KEY="your_key" python eval/run_eval.py --provider gemini --prompt-version v2
```

Báo cáo chi tiết sẽ được tự động kết xuất dưới dạng file JSON và Markdown trong thư mục `eval/reports/`.
