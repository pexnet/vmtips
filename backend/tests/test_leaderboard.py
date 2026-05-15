"""
Tests for the leaderboard endpoints.
"""
import pytest
from fastapi.testclient import TestClient

from main import app
from database import engine, Base, SessionLocal
from seed import main as seed_main


@pytest.fixture(scope="function")
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_main()
    yield TestClient(app)
    Base.metadata.drop_all(bind=engine)


def _register_and_login(client, email, password, name):
    client.post("/auth/register", json={
        "email": email, "password": password, "display_name": name,
    })
    r = client.post("/auth/login", json={"email": email, "password": password})
    return r.json()["access_token"]


def _set_match_result(match_id, home, away):
    db = SessionLocal()
    from models import Match
    m = db.query(Match).filter(Match.id == match_id).first()
    m.home_goals = home
    m.away_goals = away
    m.status = "finished"
    db.commit()
    db.close()


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

    def test_leaderboard_with_scores(self, client):
        """Two users with predictions on a finished match."""
        # Set match 1 result: 2-1
        _set_match_result(1, 2, 1)

        alice_token = _register_and_login(client, "alice2@example.com", "secret123", "Alice")
        bob_token = _register_and_login(client, "bob2@example.com", "secret123", "Bob")

        # Alice predicts 2-1 (perfect = 9 pts)
        _save_predictions(client, alice_token, [{"match_id": 1, "home_goals": 2, "away_goals": 1}])
        # Bob predicts 1-0 (outcome + margin = 3+1 = 4 pts)
        _save_predictions(client, bob_token, [{"match_id": 1, "home_goals": 1, "away_goals": 0}])

        r = client.get("/leaderboard/global")
        data = r.json()
        assert len(data["leaderboard"]) == 2

        # Alice first
        assert data["leaderboard"][0]["display_name"] == "Alice"
        assert data["leaderboard"][0]["total_points"] == 9
        assert data["leaderboard"][0]["rank"] == 1

        # Bob second
        assert data["leaderboard"][1]["display_name"] == "Bob"
        assert data["leaderboard"][1]["total_points"] == 4
        assert data["leaderboard"][1]["rank"] == 2


class TestPersonalScores:
    def test_my_scores(self, client):
        """GET /leaderboard/me returns my score breakdown."""
        _set_match_result(1, 2, 1)
        _set_match_result(2, 0, 0)

        token = _register_and_login(client, "carol@example.com", "secret123", "Carol")

        _save_predictions(client, token, [
            {"match_id": 1, "home_goals": 2, "away_goals": 1},  # perfect
            {"match_id": 2, "home_goals": 1, "away_goals": 1},  # draw wrong scores
        ])

        r = client.get("/leaderboard/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        data = r.json()

        assert data["display_name"] == "Carol"
        assert data["total_points"] == 13  # 9 + 4
        assert data["predictions_made"] == 2
        assert data["matches_scored"] == 2
        assert data["perfect_predictions"] == 1
        assert len(data["breakdown"]) == 2
        assert data["breakdown"][0]["perfect"] is True
        assert data["breakdown"][0]["points"] == 9

    def test_my_scores_no_auth(self, client):
        """GET /leaderboard/me without token returns 401."""
        r = client.get("/leaderboard/me")
        assert r.status_code == 401


class TestLeagueLeaderboard:
    def test_league_leaderboard(self, client):
        """Members-only leaderboard for a league."""
        _set_match_result(1, 2, 1)

        alice_token = _register_and_login(client, "a@example.com", "secret123", "Alice")
        bob_token = _register_and_login(client, "b@example.com", "secret123", "Bob")

        # Create league
        create_r = client.post("/leagues", json={"name": "My League"}, headers={"Authorization": f"Bearer {alice_token}"})
        league_id = create_r.json()["id"]
        invite_code = create_r.json()["invite_code"]

        # Bob joins
        client.post(f"/leagues/{league_id}/join", json={"invite_code": invite_code}, headers={"Authorization": f"Bearer {bob_token}"})

        # Both predict
        _save_predictions(client, alice_token, [{"match_id": 1, "home_goals": 2, "away_goals": 1}])
        _save_predictions(client, bob_token, [{"match_id": 1, "home_goals": 1, "away_goals": 0}])

        r = client.get(f"/leaderboard/league/{league_id}", headers={"Authorization": f"Bearer {alice_token}"})
        assert r.status_code == 200
        data = r.json()

        assert data["league_name"] == "My League"
        assert len(data["leaderboard"]) == 2
        assert data["leaderboard"][0]["total_points"] == 9
        assert data["leaderboard"][1]["total_points"] == 4

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
