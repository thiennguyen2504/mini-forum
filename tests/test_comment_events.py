from unittest.mock import AsyncMock, MagicMock

from fastapi import status
import pytest

from app.core import events
from app.core.security import create_access_token
from app.crud.user import create_user
from app.schemas.user import UserCreate


def test_publish_comment_created_event_when_author_is_different(client, db_session, test_user, auth_headers, monkeypatch):
    """
    Khi user A comment vào post của user B (khác chủ post):
    app.core.events.publish_comment_created phải được gọi đúng 1 lần
    với đúng post_id, post_owner_id (= B), comment_author_id (= A).
    """
    # 1. Tạo user B
    user_b = create_user(
        db_session,
        UserCreate(
            email="user_b@example.com",
            password="password123",
            name="User B",
        ),
    )
    auth_headers_b = {"Authorization": f"Bearer {create_access_token(subject=user_b.id)}"}

    # 2. User B tạo bài viết
    post_res = client.post(
        "/posts",
        headers=auth_headers_b,
        json={"title": "Post by User B", "content": "Content of post B"},
    )
    assert post_res.status_code == status.HTTP_201_CREATED
    post_id = post_res.json()["id"]

    # 3. Spy/Mock hàm publish_comment_created trong app.services.comment_service
    captured_calls = []

    def fake_publish_comment_created(**kwargs):
        captured_calls.append(kwargs)

    monkeypatch.setattr(
        "app.services.comment_service.publish_comment_created",
        fake_publish_comment_created,
    )

    # 4. User A (test_user) comment vào bài của user B
    comment_payload = {"content": "Hello user B, great article!"}
    res = client.post(
        f"/posts/{post_id}/comments",
        headers=auth_headers,
        json=comment_payload,
    )
    assert res.status_code == status.HTTP_201_CREATED
    comment_data = res.json()

    # 5. Kiểm tra publish_comment_created được gọi đúng 1 lần với tham số chính xác
    assert len(captured_calls) == 1
    call = captured_calls[0]
    assert call["comment_id"] == comment_data["id"]
    assert call["post_id"] == post_id
    assert call["post_owner_id"] == user_b.id
    assert call["comment_author_id"] == test_user.id
    assert call["comment_author_name"] == test_user.name
    assert call["content_preview"] == comment_payload["content"]
    assert "created_at" in call


def test_do_not_publish_comment_event_when_commenting_on_own_post(client, test_user, auth_headers, monkeypatch):
    """
    Khi user tự comment vào post của chính mình (comment_author_id == post_owner_id):
    publish_comment_created KHÔNG được gọi.
    """
    # 1. User A tạo bài viết của chính mình
    post_res = client.post(
        "/posts",
        headers=auth_headers,
        json={"title": "Self Post", "content": "Post by test_user"},
    )
    assert post_res.status_code == status.HTTP_201_CREATED
    post_id = post_res.json()["id"]

    # 2. Spy/Mock hàm publish_comment_created trong app.services.comment_service
    captured_calls = []

    def fake_publish_comment_created(**kwargs):
        captured_calls.append(kwargs)

    monkeypatch.setattr(
        "app.services.comment_service.publish_comment_created",
        fake_publish_comment_created,
    )

    # 3. User A comment vào chính bài viết của mình
    res = client.post(
        f"/posts/{post_id}/comments",
        headers=auth_headers,
        json={"content": "Author self comment"},
    )
    assert res.status_code == status.HTTP_201_CREATED

    # 4. Kiểm tra publish_comment_created KHÔNG được gọi
    assert len(captured_calls) == 0


@pytest.mark.asyncio
async def test_shutdown_producer_handles_none():
    """shutdown_producer() khi chưa khởi tạo producer phải chạy êm và không lỗi."""
    events._producer = None
    await events.shutdown_producer()
    assert events._producer is None


@pytest.mark.asyncio
async def test_shutdown_producer_calls_stop():
    """shutdown_producer() khi producer đang hoạt động phải gọi stop() và gán _producer = None."""
    fake_producer = MagicMock()
    fake_producer.stop = AsyncMock()
    events._producer = fake_producer

    # Đảm bảo loop đã khởi tạo
    events._get_or_create_loop()
    await events.shutdown_producer()

    assert events._producer is None
    fake_producer.stop.assert_called_once()
