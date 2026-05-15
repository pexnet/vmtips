"""
Tests for optional pagination on list endpoints.
Backward compatibility: no pagination params = same response shape as before.
With pagination params = wrapped in PaginatedResponse.
"""
import math


# ── Matches pagination ──────────────────────────────────────


class TestMatchesPagination:
    def test_no_pagination_returns_list(self, client):
        """Without page/per_page, GET /matches returns a plain list (backward compat)."""
        response = client.get("/matches")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 104

    def test_paginated_matches_page1(self, client):
        """With page=1&per_page=10, response is wrapped with pagination metadata."""
        response = client.get("/matches?page=1&per_page=10")
        assert response.status_code == 200
        data = response.json()

        # Should be a dict with pagination keys, not a list
        assert isinstance(data, dict)
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        assert "total_pages" in data

        assert data["total"] == 104
        assert data["page"] == 1
        assert data["per_page"] == 10
        assert data["total_pages"] == math.ceil(104 / 10)
        assert len(data["items"]) == 10
        assert data["items"][0]["match_number"] == 1

    def test_paginated_matches_last_page(self, client):
        """Last page should have the remaining items."""
        response = client.get("/matches?page=11&per_page=10")
        assert response.status_code == 200
        data = response.json()
        # 104 items / 10 per page = 10 full pages + 1 page with 4 items
        assert data["page"] == 11
        assert len(data["items"]) == 4
        assert data["total_pages"] == 11

    def test_paginated_matches_per_page_50(self, client):
        """Default-ish per_page=50 should give 3 total pages for 104 matches."""
        response = client.get("/matches?page=1&per_page=50")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 104
        assert data["per_page"] == 50
        assert data["total_pages"] == 3  # ceil(104/50) = 3
        assert len(data["items"]) == 50

    def test_paginated_matches_page2(self, client):
        """Page 2 returns the next batch."""
        r1 = client.get("/matches?page=1&per_page=50")
        r2 = client.get("/matches?page=2&per_page=50")
        ids1 = {m["id"] for m in r1.json()["items"]}
        ids2 = {m["id"] for m in r2.json()["items"]}
        # Pages should not overlap
        assert ids1.isdisjoint(ids2)
        assert r2.json()["items"][0]["match_number"] == 51

    def test_only_page_param_no_per_page_returns_list(self, client):
        """Providing only page (not per_page) should still return full list."""
        response = client.get("/matches?page=2")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 104

    def test_only_per_page_param_no_page_returns_list(self, client):
        """Providing only per_page (not page) should still return full list."""
        response = client.get("/matches?per_page=10")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 104


# ── Predictions pagination ──────────────────────────────────


class TestPredictionsPagination:
    def _register_and_login(self, client, email, password, name):
        client.post("/auth/register", json={
            "email": email, "password": password, "display_name": name,
        })
        r = client.post("/auth/login", json={"email": email, "password": password})
        return r.json()["access_token"]

    def test_no_pagination_returns_list(self, client):
        """Without pagination params, predictions returns a plain list."""
        token = self._register_and_login(client, "pag1@example.com", "secret123", "PagUser1")
        # Save some predictions
        client.post(
            "/predictions/batch",
            json={"predictions": [
                {"match_id": 1, "home_goals": 2, "away_goals": 1},
                {"match_id": 2, "home_goals": 0, "away_goals": 0},
                {"match_id": 3, "home_goals": 1, "away_goals": 1},
            ]},
            headers={"Authorization": f"Bearer {token}"},
        )
        response = client.get("/predictions", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3

    def test_paginated_predictions(self, client):
        """With page/per_page, predictions returns paginated wrapper."""
        token = self._register_and_login(client, "pag2@example.com", "secret123", "PagUser2")
        # Save 5 predictions
        client.post(
            "/predictions/batch",
            json={"predictions": [
                {"match_id": i, "home_goals": i, "away_goals": 0} for i in range(1, 6)
            ]},
            headers={"Authorization": f"Bearer {token}"},
        )
        response = client.get("/predictions?page=1&per_page=2",
                              headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, dict)
        assert "items" in data
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["per_page"] == 2
        assert data["total_pages"] == 3  # ceil(5/2) = 3
        assert len(data["items"]) == 2

    def test_paginated_predictions_page2(self, client):
        """Page 2 of predictions returns the next batch."""
        token = self._register_and_login(client, "pag3@example.com", "secret123", "PagUser3")
        client.post(
            "/predictions/batch",
            json={"predictions": [
                {"match_id": i, "home_goals": i, "away_goals": 0} for i in range(1, 6)
            ]},
            headers={"Authorization": f"Bearer {token}"},
        )
        response = client.get("/predictions?page=2&per_page=2",
                              headers={"Authorization": f"Bearer {token}"})
        data = response.json()
        assert data["page"] == 2
        assert len(data["items"]) == 2  # items 3 and 4

    def test_paginated_predictions_last_page(self, client):
        """Last page of predictions has remaining items."""
        token = self._register_and_login(client, "pag4@example.com", "secret123", "PagUser4")
        client.post(
            "/predictions/batch",
            json={"predictions": [
                {"match_id": i, "home_goals": i, "away_goals": 0} for i in range(1, 6)
            ]},
            headers={"Authorization": f"Bearer {token}"},
        )
        response = client.get("/predictions?page=3&per_page=2",
                              headers={"Authorization": f"Bearer {token}"})
        data = response.json()
        assert data["page"] == 3
        assert len(data["items"]) == 1  # 5th item only

    def test_paginated_predictions_empty(self, client):
        """Paginated predictions for a user with none returns empty page."""
        token = self._register_and_login(client, "pag5@example.com", "secret123", "PagUser5")
        response = client.get("/predictions?page=1&per_page=10",
                              headers={"Authorization": f"Bearer {token}"})
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
        assert data["total_pages"] == 0


# ── Leaderboard pagination ──────────────────────────────────


class TestLeaderboardPagination:
    def _register_and_login(self, client, email, password, name):
        client.post("/auth/register", json={
            "email": email, "password": password, "display_name": name,
        })
        r = client.post("/auth/login", json={"email": email, "password": password})
        return r.json()["access_token"]

    def test_no_pagination_returns_dict_with_leaderboard(self, client):
        """Without pagination, global leaderboard returns {leaderboard: [...]}."""
        token = self._register_and_login(client, "lb1@example.com", "secret123", "LB1")
        response = client.get("/leaderboard/global")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "leaderboard" in data
        # No pagination keys when not paginated
        assert "total" not in data or "page" not in data

    def test_paginated_leaderboard(self, client):
        """With page/per_page, global leaderboard includes pagination metadata."""
        # Register a few users so there's data
        for i in range(5):
            self._register_and_login(
                client, f"lbpage{i}@example.com", "secret123", f"LBPage{i}"
            )

        response = client.get("/leaderboard/global?page=1&per_page=2")
        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, dict)
        assert "leaderboard" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        assert "total_pages" in data

        assert data["page"] == 1
        assert data["per_page"] == 2
        assert len(data["leaderboard"]) == 2

    def test_paginated_leaderboard_page_beyond_data(self, client):
        """Requesting a page beyond the data returns empty leaderboard list."""
        token = self._register_and_login(client, "lbbeyond@example.com", "secret123", "LBBeyond")
        response = client.get("/leaderboard/global?page=100&per_page=10")
        assert response.status_code == 200
        data = response.json()
        assert data["leaderboard"] == []
        assert data["total"] >= 1  # at least the registered user