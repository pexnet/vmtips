"""
Tests for the authentication endpoints (register, login, me).
"""
import pytest
from fastapi.testclient import TestClient

from main import app
from database import engine, Base, SessionLocal
from models import User


@pytest.fixture(scope="function")
def client():
    """Yield a TestClient with fresh tables for each test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield TestClient(app)
    Base.metadata.drop_all(bind=engine)


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


def test_me_no_token(client):
    """Calling /me without a token returns 401."""
    response = client.get("/auth/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "not_authenticated"
