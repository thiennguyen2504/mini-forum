from fastapi import status


def test_create_user_success(client):
    payload = {
        "email": "newuser@example.com",
        "password": "password123",
        "name": "New User",
    }
    response = client.post("/users", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["name"] == "New User"
    assert "id" in data
    assert "created_at" in data
    assert "password" not in data
    assert "hashed_password" not in data


def test_create_user_duplicate_email(client, test_user):
    payload = {
        "email": test_user.email,
        "password": "password123",
        "name": "Duplicate User",
    }
    response = client.post("/users", json=payload)
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "already registered" in response.json()["detail"].lower()


def test_create_user_missing_fields(client):
    # Thiếu email
    response_no_email = client.post(
        "/users", json={"password": "password123", "name": "No Email"}
    )
    assert response_no_email.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Thiếu password
    response_no_pwd = client.post(
        "/users", json={"email": "nopass@example.com", "name": "No Pwd"}
    )
    assert response_no_pwd.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Format email không hợp lệ
    response_invalid_email = client.post(
        "/users", json={"email": "not-an-email", "password": "password123"}
    )
    assert response_invalid_email.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_get_user_success(client, test_user):
    response = client.get(f"/users/{test_user.id}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == test_user.id
    assert data["email"] == test_user.email
    assert data["name"] == test_user.name


def test_get_user_not_found(client):
    response = client.get("/users/99999")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_user_success(client, test_user):
    payload = {
        "name": "Updated User Name",
        "email": "updated_email@example.com",
    }
    response = client.patch(f"/users/{test_user.id}", json=payload)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "Updated User Name"
    assert data["email"] == "updated_email@example.com"


def test_delete_user_success(client, test_user):
    # Xoá user
    del_res = client.delete(f"/users/{test_user.id}")
    assert del_res.status_code == status.HTTP_204_NO_CONTENT

    # Lấy lại -> 404
    get_res = client.get(f"/users/{test_user.id}")
    assert get_res.status_code == status.HTTP_404_NOT_FOUND
