"""Admin user-management endpoint tests."""


def _login(client, identifier, password):
    return client.post(
        "/auth/login",
        json={"identifier": identifier, "password": password},
    )


def _admin_headers(client):
    response = _login(client, "admin", "admin")
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_admin_can_create_user_with_league_membership(client):
    headers = _admin_headers(client)
    leagues = client.get("/admin/leagues", headers=headers).json()
    league_id = leagues[0]["id"]

    response = client.post(
        "/admin/users",
        headers=headers,
        json={
            "email": "alex@example.com",
            "password": "initial123",
            "display_name": "Alex",
            "first_name": "Alex",
            "is_active": True,
            "league_ids": [league_id],
        },
    )

    assert response.status_code == 201
    assert response.json()["league_ids"] == [league_id]
    assert _login(client, "alex", "initial123").status_code == 200


def test_non_admin_cannot_list_or_create_users(client):
    client.post(
        "/auth/register",
        json={
            "email": "regular@example.com",
            "password": "secret123",
            "display_name": "Regular",
        },
    )
    token = _login(client, "regular", "secret123").json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/admin/users", headers=headers).status_code == 403
    assert client.post(
        "/admin/users",
        headers=headers,
        json={
            "email": "blocked@example.com",
            "password": "secret123",
            "display_name": "Blocked",
        },
    ).status_code == 403


def test_admin_can_edit_password_identity_and_disable_user(client):
    headers = _admin_headers(client)
    created = client.post(
        "/admin/users",
        headers=headers,
        json={
            "email": "emma@example.com",
            "password": "initial123",
            "display_name": "Emma",
        },
    ).json()

    updated = client.patch(
        f"/admin/users/{created['id']}",
        headers=headers,
        json={
            "email": "emma-new@example.com",
            "display_name": "Em",
            "first_name": "Emma",
            "last_name": "Example",
            "password": "changed123",
            "is_active": False,
        },
    )

    assert updated.status_code == 200
    assert updated.json()["display_name"] == "Em"
    assert updated.json()["is_active"] is False
    disabled_login = _login(client, "em", "changed123")
    assert disabled_login.status_code == 403
    assert disabled_login.json()["detail"] == "user_disabled"

    enabled = client.patch(
        f"/admin/users/{created['id']}",
        headers=headers,
        json={"is_active": True},
    )
    assert enabled.status_code == 200
    assert _login(client, "EMMA-NEW@EXAMPLE.COM", "changed123").status_code == 200


def test_admin_update_rejects_taken_nickname(client):
    headers = _admin_headers(client)
    first = client.post(
        "/admin/users",
        headers=headers,
        json={
            "email": "first@example.com",
            "password": "secret123",
            "display_name": "First",
        },
    ).json()
    client.post(
        "/admin/users",
        headers=headers,
        json={
            "email": "second@example.com",
            "password": "secret123",
            "display_name": "Second",
        },
    )

    response = client.patch(
        f"/admin/users/{first['id']}",
        headers=headers,
        json={"display_name": "SECOND"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "nickname_taken"
