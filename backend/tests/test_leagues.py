"""
Tests for the leagues endpoints.
"""


def _register_and_login(client, email, password, name):
    """Helper: register a user and return the JWT token."""
    client.post("/auth/register", json={
        "email": email,
        "password": password,
        "display_name": name,
    })
    r = client.post("/auth/login", json={"email": email, "password": password})
    return r.json()["access_token"]


def test_create_league(client):
    """A logged-in user can create a league and becomes admin."""
    token = _register_and_login(client, "alice@example.com", "secret123", "Alice")

    response = client.post(
        "/leagues",
        json={"name": "Alice's League"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Alice's League"
    assert len(data["invite_code"]) == 6
    assert data["admin_user_id"] == 2  # Seeded admin is id=1; Alice is id=2


def test_list_my_leagues(client):
    """GET /leagues returns leagues the user is a member of."""
    token = _register_and_login(client, "bob@example.com", "secret123", "Bob")

    create_r = client.post(
        "/leagues",
        json={"name": "Bob's League"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_r.status_code == 201

    list_r = client.get("/leagues", headers={"Authorization": f"Bearer {token}"})
    assert list_r.status_code == 200
    data = list_r.json()
    assert len(data) == 1
    assert data[0]["name"] == "Bob's League"


def test_join_league(client):
    """A user can join a league with the correct invite code."""
    admin_token = _register_and_login(client, "admin@example.com", "secret123", "Admin")
    create_r = client.post(
        "/leagues",
        json={"name": "Fun League"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    league_id = create_r.json()["id"]
    invite_code = create_r.json()["invite_code"]

    user_token = _register_and_login(client, "user@example.com", "secret123", "User")
    join_r = client.post(
        f"/leagues/{league_id}/join",
        json={"invite_code": invite_code},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert join_r.status_code == 200
    assert join_r.json()["joined"] is True


def test_join_wrong_code(client):
    """Joining with wrong invite code returns 403."""
    admin_token = _register_and_login(client, "admin2@example.com", "secret123", "Admin")
    create_r = client.post(
        "/leagues",
        json={"name": "Secret League"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    league_id = create_r.json()["id"]

    user_token = _register_and_login(client, "user2@example.com", "secret123", "User")
    join_r = client.post(
        f"/leagues/{league_id}/join",
        json={"invite_code": "WRONG"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert join_r.status_code == 403
    assert join_r.json()["detail"] == "invalid_invite_code"


def test_join_already_member(client):
    """Joining a league you're already in returns 409."""
    token = _register_and_login(client, "dave@example.com", "secret123", "Dave")
    create_r = client.post(
        "/leagues",
        json={"name": "Dave's League"},
        headers={"Authorization": f"Bearer {token}"},
    )
    league_id = create_r.json()["id"]
    invite_code = create_r.json()["invite_code"]

    join_r = client.post(
        f"/leagues/{league_id}/join",
        json={"invite_code": invite_code},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert join_r.status_code == 409
    assert join_r.json()["detail"] == "already_member"


def test_get_league_detail(client):
    """GET /leagues/{id} returns league with members."""
    token = _register_and_login(client, "eve@example.com", "secret123", "Eve")
    create_r = client.post(
        "/leagues",
        json={"name": "Eve's League"},
        headers={"Authorization": f"Bearer {token}"},
    )
    league_id = create_r.json()["id"]

    detail_r = client.get(
        f"/leagues/{league_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail_r.status_code == 200
    data = detail_r.json()
    assert data["name"] == "Eve's League"
    assert data["is_admin"] is True
    assert len(data["members"]) == 1
    assert data["members"][0]["display_name"] == "Eve"


def test_get_league_not_member(client):
    """Non-member cannot view league details."""
    admin_token = _register_and_login(client, "admin3@example.com", "secret123", "Admin")
    create_r = client.post(
        "/leagues",
        json={"name": "Private League"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    league_id = create_r.json()["id"]

    outsider_token = _register_and_login(client, "outsider@example.com", "secret123", "Outsider")
    detail_r = client.get(
        f"/leagues/{league_id}",
        headers={"Authorization": f"Bearer {outsider_token}"},
    )
    assert detail_r.status_code == 403
    assert detail_r.json()["detail"] == "not_a_member"


def test_list_public_leagues(client):
    """GET /leagues/public returns only public leagues without needing auth."""
    # Create a public league
    token = _register_and_login(client, "pubadmin@example.com", "secret123", "PubAdmin")
    create_r = client.post(
        "/leagues",
        json={"name": "Public League", "is_public": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_r.status_code == 201
    public_league_id = create_r.json()["id"]

    # Create a private league
    create_r2 = client.post(
        "/leagues",
        json={"name": "Private League", "is_public": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_r2.status_code == 201

    # Request without auth
    response = client.get("/leagues/public")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Public League"
    assert data[0]["id"] == public_league_id
    assert data[0]["member_count"] == 1  # creator is auto-added
    assert "invite_code" not in data[0]


def test_list_public_leagues_empty(client):
    """GET /leagues/public returns empty list when no public leagues exist."""
    token = _register_and_login(client, "nope@example.com", "secret123", "Nope")
    client.post(
        "/leagues",
        json={"name": "Private Only", "is_public": False},
        headers={"Authorization": f"Bearer {token}"},
    )

    response = client.get("/leagues/public")
    assert response.status_code == 200
    assert response.json() == []


def test_list_public_leagues_member_count(client):
    """GET /leagues/public member_count reflects all joined members."""
    admin_token = _register_and_login(client, "mcadmin@example.com", "secret123", "MCAdmin")
    create_r = client.post(
        "/leagues",
        json={"name": "Big Public League", "is_public": True},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    league_id = create_r.json()["id"]
    invite_code = create_r.json()["invite_code"]

    # Second user joins
    user_token = _register_and_login(client, "mcuser@example.com", "secret123", "MCUser")
    client.post(
        f"/leagues/{league_id}/join",
        json={"invite_code": invite_code},
        headers={"Authorization": f"Bearer {user_token}"},
    )

    response = client.get("/leagues/public")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["member_count"] == 2