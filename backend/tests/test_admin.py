"""
Tests for the admin endpoints.
"""
import pytest


def _register_and_login(client, email, password, name):
    client.post("/auth/register", json={
        "email": email, "password": password, "display_name": name,
    })
    r = client.post("/auth/login", json={"email": email, "password": password})
    return r.json()["access_token"]


class TestAdminMatchResult:
    def test_admin_sets_result(self, client):
        """First user (admin) can set match results."""
        token = _register_and_login(client, "admin@example.com", "secret123", "Admin")

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
        """Second user is not admin and gets 403."""
        _register_and_login(client, "admin2@example.com", "secret123", "Admin")
        user_token = _register_and_login(client, "user@example.com", "secret123", "User")

        r = client.post(
            "/admin/matches/1/result",
            json={"home_goals": 2, "away_goals": 0},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert r.status_code == 403
        assert r.json()["detail"] == "admin_only"

    def test_match_not_found(self, client):
        token = _register_and_login(client, "admin3@example.com", "secret123", "Admin")
        r = client.post(
            "/admin/matches/99999/result",
            json={"home_goals": 1, "away_goals": 0},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 404


class TestAdminSync:
    def test_sync_stub(self, client):
        """Sync endpoint returns useful info."""
        token = _register_and_login(client, "admin4@example.com", "secret123", "Admin")
        r = client.post(
            "/admin/sync-results",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert r.json()["synced"] is False
        assert "manual" in r.json()["message"].lower() or "not yet" in r.json()["message"].lower()

    def test_sync_non_admin(self, client):
        _register_and_login(client, "admin5@example.com", "secret123", "Admin")
        user_token = _register_and_login(client, "user2@example.com", "secret123", "User")
        r = client.post(
            "/admin/sync-results",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert r.status_code == 403


class TestAdminRecalculate:
    def test_recalculate(self, client):
        token = _register_and_login(client, "admin6@example.com", "secret123", "Admin")
        r = client.post(
            "/admin/scores/recalculate",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert r.json()["recalculated"] is True

    def test_recalculate_non_admin(self, client):
        _register_and_login(client, "admin7@example.com", "secret123", "Admin")
        user_token = _register_and_login(client, "user3@example.com", "secret123", "User")
        r = client.post(
            "/admin/scores/recalculate",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert r.status_code == 403