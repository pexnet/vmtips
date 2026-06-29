"""
Tests for the authentication endpoints (register, login, me).
"""
import pytest
from fastapi.testclient import TestClient

from main import app
from database import Base
from models import User


def test_register_user(client):
    """A new user can be registered and receives an id."""
    response = client.post("/auth/register", json={
        "email": "alice@example.com",
        "password": "secret123",
        "display_name": "Alice",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "alice@example.com"
    assert data["display_name"] == "Alice"
    assert "id" in data
    assert "password_hash" not in data


def test_register_duplicate_email(client):
    """Registering the same email twice returns 409."""
    payload = {"email": "bob@example.com", "password": "secret123", "display_name": "Bob"}
    r1 = client.post("/auth/register", json=payload)
    assert r1.status_code == 201

    r2 = client.post("/auth/register", json=payload)
    assert r2.status_code == 409
    assert r2.json()["detail"] == "email_already_registered"


def test_login_success(client):
    """A registered user can log in and receives a JWT."""
    client.post("/auth/register", json={
        "email": "carol@example.com",
        "password": "secret123",
        "display_name": "Carol",
    })
    response = client.post("/auth/login", json={
        "email": "carol@example.com",
        "password": "secret123",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client):
    """Login with wrong password returns 401."""
    client.post("/auth/register", json={
        "email": "dave@example.com",
        "password": "secret123",
        "display_name": "Dave",
    })
    response = client.post("/auth/login", json={
        "email": "dave@example.com",
        "password": "wrongpassword",
    })
    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_credentials"


def test_me_endpoint(client):
    """The /me endpoint returns the authenticated user."""
    register = client.post("/auth/register", json={
        "email": "eve@example.com",
        "password": "secret123",
        "display_name": "Eve",
    })
    assert register.status_code == 201

    login = client.post("/auth/login", json={
        "email": "eve@example.com",
        "password": "secret123",
    })
    token = login.json()["access_token"]

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "eve@example.com"
    assert me.json()["display_name"] == "Eve"
    assert me.json()["avatar_url"] is None


def test_update_profile_fields(client):
    """The /me endpoint supports first name, last name, email, and nickname updates."""
    client.post("/auth/register", json={
        "email": "profile@example.com",
        "password": "secret123",
        "display_name": "Profile",
    })
    login = client.post("/auth/login", json={
        "email": "profile@example.com",
        "password": "secret123",
    })
    token = login.json()["access_token"]

    response = client.patch(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "email": "new-profile@example.com",
            "first_name": "Ada",
            "last_name": "Lovelace",
            "display_name": "Countess",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "new-profile@example.com"
    assert data["first_name"] == "Ada"
    assert data["last_name"] == "Lovelace"
    assert data["display_name"] == "Countess"


def test_upload_and_delete_avatar(client):
    """The current user can upload and remove an optional avatar."""
    client.post("/auth/register", json={
        "email": "avatar@example.com",
        "password": "secret123",
        "display_name": "Avatar User",
    })
    login = client.post("/auth/login", json={
        "email": "avatar@example.com",
        "password": "secret123",
    })
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    upload = client.post(
        "/auth/me/avatar",
        headers=headers,
        files={"file": ("avatar.png", b"\x89PNG\r\n\x1a\n", "image/png")},
    )
    assert upload.status_code == 200
    assert upload.json()["avatar_url"] == f"/api/users/{upload.json()['id']}/avatar"

    delete = client.delete("/auth/me/avatar", headers=headers)
    assert delete.status_code == 200
    assert delete.json()["avatar_url"] is None


def test_upload_avatar_rejects_non_image(client):
    """Avatar uploads only allow supported image content types."""
    client.post("/auth/register", json={
        "email": "avatar-invalid@example.com",
        "password": "secret123",
        "display_name": "Invalid Avatar",
    })
    login = client.post("/auth/login", json={
        "email": "avatar-invalid@example.com",
        "password": "secret123",
    })
    token = login.json()["access_token"]

    upload = client.post(
        "/auth/me/avatar",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("avatar.txt", b"not an image", "text/plain")},
    )
    assert upload.status_code == 400
    assert upload.json()["detail"] == "avatar_file_type_not_supported"


def test_me_no_token(client):
    """Calling /me without a token returns 401."""
    response = client.get("/auth/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "not_authenticated"


def test_avatar_serving_endpoint(client):
    """GET /users/{id}/avatar serves the raw image with cache headers."""
    import base64

    client.post("/auth/register", json={
        "email": "avatar-serve@example.com",
        "password": "secret123",
        "display_name": "Avatar Serve",
    })
    login = client.post("/auth/login", json={
        "email": "avatar-serve@example.com",
        "password": "secret123",
    })
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Upload a tiny PNG
    png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50
    upload = client.post(
        "/auth/me/avatar",
        headers=headers,
        files={"file": ("avatar.png", png_bytes, "image/png")},
    )
    user_id = upload.json()["id"]
    assert upload.json()["avatar_url"] == f"/api/users/{user_id}/avatar"

    # Serve the avatar
    resp = client.get(f"/users/{user_id}/avatar")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert "max-age=604800" in resp.headers["cache-control"]
    assert "immutable" in resp.headers["cache-control"]
    assert resp.headers["etag"]
    # Verify the bytes match the uploaded image
    assert resp.content == png_bytes

    # 304 on ETag match
    etag = resp.headers["etag"]
    resp2 = client.get(
        f"/users/{user_id}/avatar",
        headers={"If-None-Match": etag},
    )
    assert resp2.status_code == 304

    # 404 for user with no avatar
    resp3 = client.get("/users/99999/avatar")
    assert resp3.status_code == 404
