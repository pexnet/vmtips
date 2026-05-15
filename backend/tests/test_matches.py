"""
Tests for the matches endpoints.
"""


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


def test_get_single_match(client):
    """GET /matches/{id} returns a specific match."""
    response = client.get("/matches/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["match_number"] == 1


def test_get_match_not_found(client):
    """GET /matches/{id} with invalid id returns 404."""
    response = client.get("/matches/99999")
    assert response.status_code == 404