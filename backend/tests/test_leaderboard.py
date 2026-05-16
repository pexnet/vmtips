"""
Tests for the leaderboard endpoints.
Scoring rules (7p max per match):
  - Correct outcome: 3p
  - Correct home score: 2p
  - Correct away score: 2p
  - Perfect (all 3): 7p
"""


def _register_and_login(client, email, password, name):
    client.post("/auth/register", json={
        "email": email, "password": password, "display_name": name,
    })
    r = client.post("/auth/login", json={"email": email, "password": password})
    return r.json()["access_token"]


def _save_predictions(client, token, predictions):
    client.post(
        "/predictions/batch",
        json={"predictions": predictions},
        headers={"Authorization": f"Bearer {token}"},
    )


class TestGlobalLeaderboard:
    def test_empty_leaderboard(self, client):
        """No predictions made yet = all users at 0 points."""
        token = _register_and_login(client, "alice@example.com", "secret123", "Alice")
        r = client.get("/leaderboard/global", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        data = r.json()
        assert len(data["leaderboard"]) >= 1
        assert data["leaderboard"][0]["total_points"] == 0

    def test_leaderboard_with_scores(self, client, set_match_result):
        """Two users with predictions on a finished match.

        Alice predicts 2-1, actual 2-1 = perfect (outcome 3 + home 2 + away 2 = 7p)
        Bob predicts 1-0, actual 2-1 = outcome only (3p)
        """
        set_match_result(1, 2, 1)

        alice_token = _register_and_login(client, "alice2@example.com", "secret123", "Alice")
        bob_token = _register_and_login(client, "bob2@example.com", "secret123", "Bob")

        _save_predictions(client, alice_token, [{"match_id": 1, "home_goals": 2, "away_goals": 1}])
        _save_predictions(client, bob_token, [{"match_id": 1, "home_goals": 1, "away_goals": 0}])

        r = client.get("/leaderboard/global")
        data = r.json()
        # Seeded admin user (0 points) is also in the leaderboard
        assert len(data["leaderboard"]) >= 2

        # Alice should be first (7 points), Bob second (3 points)
        alice = next(u for u in data["leaderboard"] if u["display_name"] == "Alice")
        assert alice["total_points"] == 7
        assert alice["rank"] == 1

        bob = next(u for u in data["leaderboard"] if u["display_name"] == "Bob")
        assert bob["total_points"] == 3
        assert bob["rank"] == 2


class TestPersonalScores:
    def test_my_scores(self, client, set_match_result):
        """GET /leaderboard/me returns my score breakdown.

        Carol predicts match1: 2-1 (actual 2-1) = 7p (perfect)
        Carol predicts match2: 1-1 (actual 0-0) = 3p (draw correct outcome, wrong scores)
        Total = 10p
        """
        set_match_result(1, 2, 1)
        set_match_result(2, 0, 0)

        token = _register_and_login(client, "carol@example.com", "secret123", "Carol")

        _save_predictions(client, token, [
            {"match_id": 1, "home_goals": 2, "away_goals": 1},
            {"match_id": 2, "home_goals": 1, "away_goals": 1},
        ])

        r = client.get("/leaderboard/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        data = r.json()

        assert data["display_name"] == "Carol"
        assert data["total_points"] == 10
        assert data["predictions_made"] == 2
        assert data["matches_scored"] == 2
        assert data["perfect_predictions"] == 1
        assert len(data["breakdown"]) == 2
        assert data["breakdown"][0]["perfect"] is True
        assert data["breakdown"][0]["points"] == 7

    def test_my_scores_no_auth(self, client):
        """GET /leaderboard/me without token returns 401."""
        r = client.get("/leaderboard/me")
        assert r.status_code == 401


class TestLeagueLeaderboard:
    def test_league_leaderboard(self, client, set_match_result):
        """Members-only leaderboard for a league.

        Alice predicts 2-1 (actual 2-1) = 7p
        Bob predicts 1-0 (actual 2-1) = 3p
        """
        set_match_result(1, 2, 1)

        alice_token = _register_and_login(client, "a@example.com", "secret123", "Alice")
        bob_token = _register_and_login(client, "b@example.com", "secret123", "Bob")

        create_r = client.post("/leagues", json={"name": "My League"}, headers={"Authorization": f"Bearer {alice_token}"})
        league_id = create_r.json()["id"]
        invite_code = create_r.json()["invite_code"]

        client.post(f"/leagues/{league_id}/join", json={"invite_code": invite_code}, headers={"Authorization": f"Bearer {bob_token}"})

        _save_predictions(client, alice_token, [{"match_id": 1, "home_goals": 2, "away_goals": 1}])
        _save_predictions(client, bob_token, [{"match_id": 1, "home_goals": 1, "away_goals": 0}])

        r = client.get(f"/leaderboard/league/{league_id}", headers={"Authorization": f"Bearer {alice_token}"})
        assert r.status_code == 200
        data = r.json()

        assert data["league_name"] == "My League"
        assert len(data["leaderboard"]) == 2
        assert data["leaderboard"][0]["total_points"] == 7
        assert data["leaderboard"][1]["total_points"] == 3

    def test_league_not_member(self, client):
        """Non-member cannot view league leaderboard."""
        alice_token = _register_and_login(client, "aa@example.com", "secret123", "Alice")
        outsider_token = _register_and_login(client, "oo@example.com", "secret123", "Outsider")

        create_r = client.post("/leagues", json={"name": "Private"}, headers={"Authorization": f"Bearer {alice_token}"})
        league_id = create_r.json()["id"]

        r = client.get(f"/leaderboard/league/{league_id}", headers={"Authorization": f"Bearer {outsider_token}"})
        assert r.status_code == 403
        assert r.json()["detail"] == "not_a_member"

    def test_league_not_found(self, client):
        token = _register_and_login(client, "zz@example.com", "secret123", "Z")
        r = client.get("/leaderboard/league/99999", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 404
        assert r.json()["detail"] == "league_not_found"