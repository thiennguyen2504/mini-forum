from fastapi import status

from app.core.ai_client import AiServiceUnavailableError, ai_client
from app.core.security import create_access_token
from app.crud.post import create_post
from app.crud.user import create_user
from app.schemas.post import PostCreate
from app.schemas.user import UserCreate

MOCK_AI_RESPONSE = {
    "data": {
        "summary": "Tóm tắt bài viết về FastAPI",
        "tags": ["fastapi", "python"],
        "topic": "tech",
        "sentiment": "positive",
        "language": "vi",
        "moderation": {
            "is_safe": True,
            "categories": [],
            "severity": "none",
            "reason": "Bài viết chuẩn mực",
        },
    },
    "meta": {
        "model": "gemini-2.5-flash",
        "prompt_version": "v2",
        "latency_ms": 150.0,
        "cached": False,
        "retries": 0,
        "request_id": "test-req-id",
    },
}


def test_ai_tags_success(client, db_session, test_user, auth_headers, monkeypatch):
    # 1. Tạo bài viết mẫu
    post = create_post(
        db_session,
        PostCreate(title="Học FastAPI cơ bản", content="Nội dung hướng dẫn chi tiết về FastAPI"),
        user_id=test_user.id,
    )

    # 2. Mock ai_client.analyze_post
    monkeypatch.setattr(ai_client, "analyze_post", lambda **kwargs: MOCK_AI_RESPONSE)

    # 3. Gọi endpoint POST /posts/{id}/ai-tags
    res = client.post(f"/posts/{post.id}/ai-tags", headers=auth_headers)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["post_id"] == post.id
    assert data["tags"] == ["fastapi", "python"]
    assert "analysis" in data
    assert data["analysis"]["summary"] == MOCK_AI_RESPONSE["data"]["summary"]

    # 4. Kiểm tra lại GET /posts/{id} để chắc chắn tags đã được lưu vào DB
    get_res = client.get(f"/posts/{post.id}")
    assert get_res.status_code == status.HTTP_200_OK
    assert set(get_res.json()["tags"]) == {"fastapi", "python"}


def test_ai_tags_unauthorized(client, db_session, test_user):
    post = create_post(
        db_session,
        PostCreate(title="Tiêu đề", content="Nội dung"),
        user_id=test_user.id,
    )
    # Gọi không có Authorization header
    res = client.post(f"/posts/{post.id}/ai-tags")
    assert res.status_code == status.HTTP_401_UNAUTHORIZED


def test_ai_tags_forbidden_not_author(client, db_session, test_user, monkeypatch):
    # Tạo bài viết thuộc về test_user (user 1)
    post = create_post(
        db_session,
        PostCreate(title="Bài viết của tác giả 1", content="Nội dung"),
        user_id=test_user.id,
    )

    # Tạo user thứ 2
    user2 = create_user(
        db_session,
        UserCreate(email="other_author@example.com", password="password123", name="Other User"),
    )
    user2_token = create_access_token(subject=user2.id)
    user2_headers = {"Authorization": f"Bearer {user2_token}"}

    # User 2 cố gắng gắn AI tags cho bài viết của user 1
    res = client.post(f"/posts/{post.id}/ai-tags", headers=user2_headers)
    assert res.status_code == status.HTTP_403_FORBIDDEN
    assert "Chỉ tác giả" in res.json()["detail"]


def test_ai_tags_post_not_found(client, auth_headers):
    res = client.post("/posts/999999/ai-tags", headers=auth_headers)
    assert res.status_code == status.HTTP_404_NOT_FOUND


def test_ai_tags_service_unavailable(client, db_session, test_user, auth_headers, monkeypatch):
    post = create_post(
        db_session,
        PostCreate(title="Bài viết test lỗi AI", content="Nội dung"),
        user_id=test_user.id,
    )

    def mock_fail(**kwargs):
        raise AiServiceUnavailableError("Dịch vụ AI đang mất kết nối")

    monkeypatch.setattr(ai_client, "analyze_post", mock_fail)

    res = client.post(f"/posts/{post.id}/ai-tags", headers=auth_headers)
    assert res.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert "Dịch vụ AI tạm thời không khả dụng" in res.json()["detail"]

    # Đảm bảo bài viết không bị thay đổi dữ liệu
    get_res = client.get(f"/posts/{post.id}")
    assert get_res.status_code == status.HTTP_200_OK
    assert get_res.json()["tags"] == []
