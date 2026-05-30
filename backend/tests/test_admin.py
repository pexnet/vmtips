"""
Tests for the admin endpoints.
The seed script creates an admin user: admin@vmtips.se / admin
"""
import pytest


def _login_admin(client):
    """Login with the seeded admin account."""
    r = client.post("/auth/login", json={"email": "admin@vmtips.se", "password": "admin"})
    assert r.status_code == 200, f"Admin login failed: {r.json()}"
    return r.json()["access_token"]


def _register_and_login(client, email, password, name):
    client.post("/auth/register", json={
        "email": email, "password": password, "display_name": name,
    })
    r = client.post("/auth/login", json={"email": email, "password": password})
    return r.json()["access_token"]


class TestAdminMatchResult:
    def test_admin_sets_result(self, client):
        """Seeded admin user can set match results."""
        token = _login_admin(client)

        # Before: match has no result
        before = client.get("/matches/1")
        assert before.json()["status"] == "scheduled"

        # Set result
        r = client.post(
            "/admin/matches/1/result",
            json={"home_goals": 3, "away_goals": 1},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert r.json()["result"] == "3-1"

        # After: match shows result
        after = client.get("/matches/1")
        assert after.json()["status"] == "finished"
        assert after.json()["home_goals"] == 3
        assert after.json()["away_goals"] == 1

    def test_non_admin_forbidden(self, client):
        """Non-admin user gets 403."""
        user_token = _register_and_login(client, "user@example.com", "secret123", "User")

        r = client.post(
            "/admin/matches/1/result",
            json={"home_goals": 2, "away_goals": 0},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert r.status_code == 403
        assert r.json()["detail"] == "admin_only"

    def test_match_not_found(self, client):
        token = _login_admin(client)
        r = client.post(
            "/admin/matches/99999/result",
            json={"home_goals": 1, "away_goals": 0},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 404


class TestAdminSync:
    def test_sync_stub(self, client):
        """Sync endpoint returns useful info (now actually implemented)."""
        token = _login_admin(client)
        r = client.post(
            "/admin/sync-results",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        data = r.json()
        # The sync endpoint is now implemented; it returns synced=True if
        # the external API was reachable, or synced=False with an error
        # message if it wasn't.
        assert "synced" in data
        assert "updated" in data

    def test_sync_non_admin(self, client):
        user_token = _register_and_login(client, "user2@example.com", "secret123", "User")
        r = client.post(
            "/admin/sync-results",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert r.status_code == 403


class TestAdminRecalculate:
    def test_recalculate(self, client):
        token = _login_admin(client)
        r = client.post(
            "/admin/scores/recalculate",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert r.json()["recalculated"] is True

    def test_recalculate_non_admin(self, client):
        user_token = _register_and_login(client, "user3@example.com", "secret123", "User")
        r = client.post(
            "/admin/scores/recalculate",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert r.status_code == 403


class TestAdminKnockoutResolution:
    def test_resolve_knockout_requires_computed_standings(self, client):
        token = _login_admin(client)

        r = client.post(
            "/admin/resolve-knockout-teams",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert r.status_code == 400
        assert "No group standings computed" in r.json()["detail"]
