from fastapi import status

from app.core.security import create_access_token
from app.crud.user import create_user
from app.schemas.user import UserCreate


def test_create_post_success(client, test_user, auth_headers):
    payload = {
        "title": "Bai viet dau tien",
        "content": "Noi dung bai viet dau tien rat hay va chi tiet.",
    }
    response = client.post("/posts", headers=auth_headers, json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["title"] == payload["title"]
    assert data["content"] == payload["content"]
    assert data["user_id"] == test_user.id
    assert data["author_name"] == test_user.name
    assert data["view_count"] == 0
    assert data["tags"] == []


def test_create_post_unauthorized_and_invalid_user(client):
    payload = {"title": "Post Title", "content": "Post Content"}

    # Không gửi Token -> 401
    res_no_auth = client.post("/posts", json=payload)
    assert res_no_auth.status_code == status.HTTP_401_UNAUTHORIZED

    # Token của user không tồn tại -> 401
    invalid_token = create_access_token(subject=99999)
    res_bad_user = client.post(
        "/posts",
        headers={"Authorization": f"Bearer {invalid_token}"},
        json=payload,
    )
    assert res_bad_user.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_post_by_id_with_author_and_tags(client, test_user, auth_headers):
    # Tạo post
    post_res = client.post(
        "/posts",
        headers=auth_headers,
        json={"title": "Post with tags", "content": "Content here"},
    )
    post_id = post_res.json()["id"]

    # Gắn tags vào post
    client.post(
        f"/posts/{post_id}/tags",
        json={"tag_names": ["python", "fastapi"]},
    )

    # Lấy thông tin chi tiết post
    get_res = client.get(f"/posts/{post_id}")
    assert get_res.status_code == status.HTTP_200_OK
    data = get_res.json()
    assert data["id"] == post_id
    assert data["author_name"] == test_user.name
    assert sorted(data["tags"]) == ["fastapi", "python"]


def test_update_post(client, auth_headers):
    # Tạo post
    post_res = client.post(
        "/posts",
        headers=auth_headers,
        json={"title": "Original Title", "content": "Original Content"},
    )
    post_id = post_res.json()["id"]

    # Update title
    update_res = client.patch(
        f"/posts/{post_id}",
        json={"title": "Updated Title"},
    )
    assert update_res.status_code == status.HTTP_200_OK
    data = update_res.json()
    assert data["title"] == "Updated Title"
    assert data["content"] == "Original Content"


def test_delete_post(client, auth_headers):
    # Tạo post
    post_res = client.post(
        "/posts",
        headers=auth_headers,
        json={"title": "To be deleted", "content": "Will be deleted soon"},
    )
    post_id = post_res.json()["id"]

    # Xoá post -> 204
    delete_res = client.delete(f"/posts/{post_id}")
    assert delete_res.status_code == status.HTTP_204_NO_CONTENT

    # Truy vấn lại post -> 404
    get_res = client.get(f"/posts/{post_id}")
    assert get_res.status_code == status.HTTP_404_NOT_FOUND


def test_list_posts_pagination(client, auth_headers):
    # Tạo 15 posts
    for i in range(15):
        client.post(
            "/posts",
            headers=auth_headers,
            json={"title": f"Post {i+1}", "content": f"Content {i+1}"},
        )

    # Lấy trang 1: skip=0, limit=5
    res1 = client.get("/posts?skip=0&limit=5")
    assert res1.status_code == status.HTTP_200_OK
    data1 = res1.json()
    assert len(data1["items"]) == 5
    assert data1["total"] == 15
    assert data1["skip"] == 0
    assert data1["limit"] == 5

    # Lấy trang 3: skip=10, limit=10
    res2 = client.get("/posts?skip=10&limit=10")
    assert res2.status_code == status.HTTP_200_OK
    data2 = res2.json()
    assert len(data2["items"]) == 5
    assert data2["total"] == 15


def test_list_posts_filter(client, db_session, test_user, auth_headers):
    # Tạo user B
    user_b = create_user(
        db_session,
        UserCreate(
            email="userb@example.com", password="password123", name="User B"
        ),
    )
    auth_headers_b = {
        "Authorization": f"Bearer {create_access_token(subject=user_b.id)}"
    }

    # Post 1 (User A, tag: python)
    p1 = client.post(
        "/posts",
        headers=auth_headers,
        json={"title": "Python A", "content": "Content A1"},
    ).json()
    client.post(f"/posts/{p1['id']}/tags", json={"tag_names": ["python"]})

    # Post 2 (User A, tag: sql)
    p2 = client.post(
        "/posts",
        headers=auth_headers,
        json={"title": "SQL A", "content": "Content A2"},
    ).json()
    client.post(f"/posts/{p2['id']}/tags", json={"tag_names": ["sql"]})

    # Post 3 (User B, tag: python)
    p3 = client.post(
        "/posts",
        headers=auth_headers_b,
        json={"title": "Python B", "content": "Content B1"},
    ).json()
    client.post(f"/posts/{p3['id']}/tags", json={"tag_names": ["python"]})

    # Filter theo author_id = user_b.id
    res_author = client.get(f"/posts?author_id={user_b.id}")
    items_author = res_author.json()["items"]
    assert len(items_author) == 1
    assert items_author[0]["id"] == p3["id"]

    # Filter theo tag = python
    res_tag = client.get("/posts?tag=python")
    items_tag = res_tag.json()["items"]
    assert len(items_tag) == 2
    post_ids = [p["id"] for p in items_tag]
    assert p1["id"] in post_ids
    assert p3["id"] in post_ids

    # Filter cả author_id và tag
    res_both = client.get(f"/posts?author_id={test_user.id}&tag=python")
    items_both = res_both.json()["items"]
    assert len(items_both) == 1
    assert items_both[0]["id"] == p1["id"]
