"""
Tests for the matches endpoints.
"""
import pytest
from fastapi.testclient import TestClient

from main import app
from database import engine, Base
from seed import main as seed_main


@pytest.fixture(scope="function")
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_main()
    yield TestClient(app)
    Base.metadata.drop_all(bind=engine)


def test_list_matches(client):
    """GET /matches returns all 104 matches."""
    response = client.get("/matches")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 104
    assert data[0]["match_number"] == 1


def test_list_group_matches(client):
    """GET /matches/groups returns only group-stage matches."""
    response = client.get("/matches/groups")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 72
    for m in data:
        assert m["round"] == "group"
        assert m["home_team"] is not None
        assert m["away_team"] is not None


def test_list_knockout_matches(client):
    """GET /matches/knockout returns only knockout matches."""
    response = client.get("/matches/knockout")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 32
    for m in data:
        assert m["round"] != "group"
        assert m["home_team_placeholder"] is not None


def test_get_single_match(client):
    """GET /matches/{id} returns a specific match."""
    response = client.get("/matches/1")
    assert response.status_code == 200
    data = response.json()
    assert data["match_number"] == 1
    assert "home_team" in data


def test_get_match_not_found(client):
    """GET /matches/{id} with invalid id returns 404."""
    response = client.get("/matches/99999")
    assert response.status_code == 404
    assert response.json()["detail"] == "match_not_found"
