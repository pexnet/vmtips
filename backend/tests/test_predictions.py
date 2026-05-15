"""
Tests for the predictions endpoints.
"""
import pytest


def _register_and_login(client, email, password, name):
    """Helper: register a user and return the JWT token."""
    client.post("/auth/register", json={
        "email": email,
        "password": password,
        "display_name": name,
    })
    r = client.post("/auth/login", json={"email": email, "password": password})
    return r.json()["access_token"]


def test_list_predictions_empty(client):
    """GET /predictions returns empty list for a new user."""
    token = _register_and_login(client, "alice@example.com", "secret123", "Alice")
    response = client.get("/predictions", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == []


def test_save_and_list_predictions(client):
    """Batch-save predictions and then list them."""
    token = _register_and_login(client, "bob@example.com", "secret123", "Bob")
    r = client.post(
        "/predictions/batch",
        json={"predictions": [
            {"match_id": 1, "home_goals": 2, "away_goals": 1},
            {"match_id": 2, "home_goals": 0, "away_goals": 0},
        ]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["saved"] == 2

    predictions = client.get("/predictions", headers={"Authorization": f"Bearer {token}"})
    assert predictions.status_code == 200
    data = predictions.json()
    assert len(data) == 2


def test_update_existing_prediction(client):
    """Saving the same match again updates the previous prediction."""
    token = _register_and_login(client, "carol@example.com", "secret123", "Carol")
    client.post(
        "/predictions/batch",
        json={"predictions": [{"match_id": 1, "home_goals": 2, "away_goals": 1}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    r = client.post(
        "/predictions/batch",
        json={"predictions": [{"match_id": 1, "home_goals": 3, "away_goals": 0}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200

    preds = client.get("/predictions", headers={"Authorization": f"Bearer {token}"})
    assert preds.json()[0]["home_goals"] == 3
    assert preds.json()[0]["away_goals"] == 0


def test_invalid_match_id(client):
    """Batch-save with a non-existent match id returns 400."""
    token = _register_and_login(client, "dave@example.com", "secret123", "Dave")
    r = client.post(
        "/predictions/batch",
        json={"predictions": [{"match_id": 99999, "home_goals": 1, "away_goals": 0}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400


def test_tournament_bonuses(client):
    """Save and retrieve tournament bonus predictions."""
    token = _register_and_login(client, "eve@example.com", "secret123", "Eve")
    save_r = client.post(
        "/predictions/tournament",
        json={"winner_team_id": 1, "top_scorer_name": "Mbappe", "total_goals": 170},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert save_r.status_code == 200

    get_r = client.get("/predictions/tournament", headers={"Authorization": f"Bearer {token}"})
    assert get_r.status_code == 200
    data = get_r.json()
    assert data["winner_team_id"] == 1
    assert data["top_scorer_name"] == "Mbappe"
    assert data["total_goals"] == 170


def test_predictions_require_auth(client):
    """GET /predictions without token returns 401."""
    response = client.get("/predictions")
    assert response.status_code == 401
    assert response.json()["detail"] == "not_authenticated"