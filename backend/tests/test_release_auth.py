"""Release authentication behavior: closed registration and nickname login."""
from config import settings
from models import User


def _register(client, email="petra@example.com", display_name="Petra"):
    return client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "secret123",
            "display_name": display_name,
        },
    )


def test_public_registration_is_disabled_when_setting_is_false(client):
    settings.allow_public_registration = False

    response = _register(client)

    assert response.status_code == 403
    assert response.json()["detail"] == "registration_disabled"


def test_public_registration_can_be_enabled(client):
    settings.allow_public_registration = True

    response = _register(client)

    assert response.status_code == 201


def test_login_accepts_case_insensitive_nickname(client):
    assert _register(client).status_code == 201

    response = client.post(
        "/auth/login",
        json={"identifier": "PETRA", "password": "secret123"},
    )

    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_accepts_case_insensitive_email(client):
    assert _register(client).status_code == 201

    response = client.post(
        "/auth/login",
        json={"identifier": "PETRA@EXAMPLE.COM", "password": "secret123"},
    )

    assert response.status_code == 200


def test_login_with_unknown_identifier_returns_401(client):
    response = client.post(
        "/auth/login",
        json={"identifier": "does-not-exist", "password": "secret123"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_credentials"


def test_successful_login_records_last_login(client, db):
    assert _register(client).status_code == 201

    response = client.post(
        "/auth/login",
        json={"identifier": "petra", "password": "secret123"},
    )
    db.expire_all()
    user = db.query(User).filter(User.email == "petra@example.com").one()

    assert response.status_code == 200
    assert user.last_login_at is not None


def test_duplicate_nickname_is_rejected_case_insensitively(client):
    assert _register(client).status_code == 201

    response = _register(
        client,
        email="other@example.com",
        display_name="pEtRa",
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "nickname_taken"


def test_disabled_user_cannot_log_in(client, db):
    assert _register(client).status_code == 201
    user = db.query(User).filter(User.email == "petra@example.com").first()
    user.is_active = False
    db.commit()

    response = client.post(
        "/auth/login",
        json={"identifier": "petra", "password": "secret123"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "user_disabled"
