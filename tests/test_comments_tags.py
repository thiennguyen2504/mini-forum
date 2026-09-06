from fastapi import status


def test_create_and_get_comments(client, test_user, auth_headers):
    # 1. Tạo post
    post_res = client.post(
        "/posts",
        headers=auth_headers,
        json={"title": "Post cho comments", "content": "Noi dung bai viet"},
    )
    post_id = post_res.json()["id"]

    # 2. Tạo comment 1
    c1_res = client.post(
        f"/posts/{post_id}/comments",
        headers=auth_headers,
        json={"content": "Binh luan 1"},
    )
    assert c1_res.status_code == status.HTTP_201_CREATED
    c1_data = c1_res.json()
    assert c1_data["post_id"] == post_id
    assert c1_data["user_id"] == test_user.id
    assert c1_data["content"] == "Binh luan 1"

    # 3. Tạo comment 2
    c2_res = client.post(
        f"/posts/{post_id}/comments",
        headers=auth_headers,
        json={"content": "Binh luan 2"},
    )
    assert c2_res.status_code == status.HTTP_201_CREATED

    # 4. Lấy danh sách comment của post
    list_res = client.get(f"/posts/{post_id}/comments")
    assert list_res.status_code == status.HTTP_200_OK
    comments = list_res.json()
    assert len(comments) == 2
    assert comments[0]["content"] == "Binh luan 1"
    assert comments[1]["content"] == "Binh luan 2"


def test_comments_non_existent_post(client, auth_headers):
    # Tạo comment vào post 99999 không tồn tại -> 404
    res = client.post(
        "/posts/99999/comments",
        headers=auth_headers,
        json={"content": "Binh luan mồ côi"},
    )
    assert res.status_code == status.HTTP_404_NOT_FOUND

    # Lấy danh sách comment từ post 99999 -> 404
    res_list = client.get("/posts/99999/comments")
    assert res_list.status_code == status.HTTP_404_NOT_FOUND


def test_attach_new_and_existing_tags_transaction(client, auth_headers):
    # 1. Tạo post 1 và post 2
    p1_res = client.post(
        "/posts",
        headers=auth_headers,
        json={"title": "Post 1", "content": "Content 1"},
    )
    p1_id = p1_res.json()["id"]

    p2_res = client.post(
        "/posts",
        headers=auth_headers,
        json={"title": "Post 2", "content": "Content 2"},
    )
    p2_id = p2_res.json()["id"]

    # 2. Gắn tag "python" và "fastapi" vào Post 1 (tạo mới cả 2 tag)
    tag_res1 = client.post(
        f"/posts/{p1_id}/tags",
        json={"tag_names": ["python", "fastapi"]},
    )
    assert tag_res1.status_code == status.HTTP_200_OK
    data1 = tag_res1.json()
    assert data1["post_id"] == p1_id
    assert sorted(data1["tags"]) == ["fastapi", "python"]

    # 3. Gắn tag "python" (đã tồn tại) và "docker" (mới) vào Post 2
    tag_res2 = client.post(
        f"/posts/{p2_id}/tags",
        json={"tag_names": ["python", "docker"]},
    )
    assert tag_res2.status_code == status.HTTP_200_OK
    data2 = tag_res2.json()
    assert data2["post_id"] == p2_id
    assert sorted(data2["tags"]) == ["docker", "python"]

    # 4. Kiểm tra lại post 1 và post 2 giữ đúng tag
    post1_detail = client.get(f"/posts/{p1_id}").json()
    assert sorted(post1_detail["tags"]) == ["fastapi", "python"]

    post2_detail = client.get(f"/posts/{p2_id}").json()
    assert sorted(post2_detail["tags"]) == ["docker", "python"]
