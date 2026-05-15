"""
Tests for bracket prediction endpoints and bracket scoring integration.
"""


def _register_and_login(client, email, password, name):
    client.post("/auth/register", json={
        "email": email, "password": password, "display_name": name,
    })
    r = client.post("/auth/login", json={"email": email, "password": password})
    return r.json()["access_token"]


class TestBracketPredictionEndpoints:
    def test_save_bracket_predictions(self, client):
        """User can save bracket predictions."""
        token = _register_and_login(client, "bracket1@example.com", "secret123", "BracketUser1")

        r = client.post(
            "/predictions/bracket",
            json={
                "entries": [
                    {"team_id": 1, "round": "round_of_16"},
                    {"team_id": 2, "round": "quarter_final"},
                    {"team_id": 3, "round": "semi_final"},
                ]
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert r.json()["saved"] == 3

    def test_get_bracket_predictions(self, client):
        """User can retrieve their bracket predictions."""
        token = _register_and_login(client, "bracket2@example.com", "secret123", "BracketUser2")

        # Save some first
        client.post(
            "/predictions/bracket",
            json={
                "entries": [
                    {"team_id": 1, "round": "round_of_32"},
                    {"team_id": 2, "round": "final"},
                ]
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        r = client.get(
            "/predictions/bracket",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 2
        rounds = {e["round"] for e in data}
        assert "round_of_32" in rounds
        assert "final" in rounds

    def test_invalid_round_rejected(self, client):
        """Invalid round name returns 400."""
        token = _register_and_login(client, "bracket3@example.com", "secret123", "BracketUser3")

        r = client.post(
            "/predictions/bracket",
            json={
                "entries": [
                    {"team_id": 1, "round": "invalid_round"},
                ]
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 400

    def test_bracket_predictions_require_auth(self, client):
        """Bracket endpoints require authentication."""
        r = client.get("/predictions/bracket")
        assert r.status_code == 401

        r = client.post(
            "/predictions/bracket",
            json={"entries": [{"team_id": 1, "round": "final"}]},
        )
        assert r.status_code == 401

    def test_duplicate_bracket_prediction_idempotent(self, client):
        """Saving the same bracket prediction twice is idempotent."""
        token = _register_and_login(client, "bracket4@example.com", "secret123", "BracketUser4")

        # First save
        client.post(
            "/predictions/bracket",
            json={"entries": [{"team_id": 1, "round": "final"}]},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Second save (same entry)
        r = client.post(
            "/predictions/bracket",
            json={"entries": [{"team_id": 1, "round": "final"}]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert r.json()["saved"] == 1

        # Still only one in DB
        r = client.get(
            "/predictions/bracket",
            headers={"Authorization": f"Bearer {token}"},
        )
        data = r.json()
        assert len(data) == 1


class TestBracketScoringIntegration:
    """Test bracket scoring in the recalculation endpoint."""

    def test_recalculate_includes_bracket_points(self, client):
        """Admin recalculate endpoint now reports bracket_points."""
        token = _register_and_login(client, "bracket5@example.com", "secret123", "Admin")

        r = client.post(
            "/admin/scores/recalculate",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["recalculated"] is True
        assert "total_bracket_points" in data
        assert "total_match_points" in data
        assert "total_tournament_bonus_points" in data

    def test_bracket_points_in_leaderboard_me(self, client):
        """Leaderboard /me includes bracket_points and bracket_details."""
        token = _register_and_login(client, "bracket6@example.com", "secret123", "LeaderUser")

        r = client.get(
            "/leaderboard/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        data = r.json()
        assert "match_points" in data
        assert "bracket_points" in data
        assert "bracket_details" in data