"""
Tests for the sync_service and the admin sync endpoint.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestSyncServiceParsing:
    """Unit tests for sync_service._parse_api_match and helper functions."""

    def test_normalize_status_scheduled(self):
        from sync_service import _normalize_status
        assert _normalize_status("scheduled") == "scheduled"
        assert _normalize_status("future") == "scheduled"

    def test_normalize_status_ongoing(self):
        from sync_service import _normalize_status
        assert _normalize_status("in_play") == "ongoing"
        assert _normalize_status("in_progress") == "ongoing"
        assert _normalize_status("live") == "ongoing"
        assert _normalize_status("half_time") == "ongoing"

    def test_normalize_status_finished(self):
        from sync_service import _normalize_status
        assert _normalize_status("finished") == "finished"
        assert _normalize_status("completed") == "finished"
        assert _normalize_status("completed_after_extra_time") == "finished"
        assert _normalize_status("completed_after_penalties") == "finished"

    def test_normalize_status_unknown(self):
        from sync_service import _normalize_status
        assert _normalize_status("unknown_status") == "scheduled"

    def test_parse_goals_int(self):
        from sync_service import _parse_goals
        assert _parse_goals(3) == 3

    def test_parse_goals_none(self):
        from sync_service import _parse_goals
        assert _parse_goals(None) is None

    def test_parse_goals_dict(self):
        from sync_service import _parse_goals
        assert _parse_goals({"full_time": 2, "half_time": 1}) == 2

    def test_parse_goals_string(self):
        from sync_service import _parse_goals
        assert _parse_goals("5") == 5

    def test_parse_api_match_worldcupjson_format(self):
        from sync_service import _parse_api_match
        raw = {
            "match_number": 1,
            "home_team": {"code": "MEX", "name": "Mexico", "goals": 1},
            "away_team": {"code": "RSA", "name": "South Africa", "goals": 1},
            "status": "completed",
        }
        result = _parse_api_match(raw)
        assert result is not None
        assert result["match_number"] == 1
        assert result["home_code"] == "MEX"
        assert result["away_code"] == "RSA"
        assert result["home_goals"] == 1
        assert result["away_goals"] == 1
        assert result["status"] == "finished"

    def test_parse_api_match_string_teams(self):
        from sync_service import _parse_api_match
        raw = {
            "match_number": 5,
            "home_team": "Mexico",
            "away_team": "South Korea",
            "home_goals": 2,
            "away_goals": 0,
            "status": "finished",
        }
        result = _parse_api_match(raw)
        assert result is not None
        assert result["home_code"] == "Mexico"
        assert result["away_code"] == "South Korea"
        assert result["home_goals"] == 2
        assert result["away_goals"] == 0
        assert result["status"] == "finished"

    def test_parse_api_match_match_number_from_fifa_id(self):
        from sync_service import _parse_api_match
        raw = {
            "fifa_id": 42,
            "home_team": {"code": "BRA", "name": "Brazil"},
            "away_team": {"code": "GER", "name": "Germany"},
            "status": "scheduled",
        }
        result = _parse_api_match(raw)
        assert result is not None
        assert result["match_number"] == 42

    def test_parse_api_match_unparseable(self):
        from sync_service import _parse_api_match
        result = _parse_api_match({"no_match_number": True, "home_team": 12345})
        # home_team is int, which is not str or dict, should return None
        assert result is None

    def test_parse_api_match_scheduled_no_goals(self):
        from sync_service import _parse_api_match
        raw = {
            "match_number": 10,
            "home_team": {"code": "CAN", "name": "Canada"},
            "away_team": {"code": "QAT", "name": "Qatar"},
            "status": "scheduled",
        }
        result = _parse_api_match(raw)
        assert result is not None
        assert result["home_goals"] is None
        assert result["away_goals"] is None
        assert result["status"] == "scheduled"


class TestSyncServiceFetch:
    """Tests for _fetch_matches with mocked HTTP calls."""

    def test_fetch_matches_success(self):
        from sync_service import _fetch_matches
        mock_data = [
            {
                "match_number": 1,
                "home_team": {"code": "MEX"},
                "away_team": {"code": "RSA"},
                "status": "completed",
                "home_goals": 1,
                "away_goals": 1,
            }
        ]
        import json
        mock_body = json.dumps(mock_data).encode("utf-8")

        with patch("sync_service.urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = mock_body
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            result = _fetch_matches("http://test.local/api")
            assert len(result) == 1
            assert result[0]["match_number"] == 1

    def test_fetch_matches_wrapped_in_matches_key(self):
        from sync_service import _fetch_matches
        import json
        mock_data = {"matches": [{"match_number": 3}]}
        mock_body = json.dumps(mock_data).encode("utf-8")

        with patch("sync_service.urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = mock_body
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            result = _fetch_matches("http://test.local/api")
            assert len(result) == 1
            assert result[0]["match_number"] == 3

    def test_fetch_matches_http_error(self):
        from sync_service import _fetch_matches, SyncError
        import urllib.error

        with patch("sync_service.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.HTTPError(
                url="http://test.local/api",
                code=500,
                msg="Server Error",
                hdrs={},
                fp=None,
            )
            with pytest.raises(SyncError, match="HTTP 500|External API HTTP error"):
                _fetch_matches("http://test.local/api")

    def test_fetch_matches_url_error(self):
        from sync_service import _fetch_matches, SyncError
        import urllib.error

        with patch("sync_service.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.URLError("Connection refused")
            with pytest.raises(SyncError, match="Cannot reach"):
                _fetch_matches("http://test.local/api")


class TestSyncMatchResults:
    """Integration tests for sync_match_results with test database."""

    def test_sync_updates_finished_match(self, seeded_db):
        from sync_service import sync_match_results
        from models import Match

        # Simulate a finished match from the external API
        mock_api_data = [
            {
                "match_number": 1,
                "home_team": {"code": "MEX", "name": "Mexico"},
                "away_team": {"code": "RSA", "name": "South Africa"},
                "status": "completed",
                "home_goals": 2,
                "away_goals": 0,
            }
        ]

        with patch("sync_service._fetch_matches", return_value=mock_api_data):
            result = sync_match_results(seeded_db)

        assert result["synced"] is True
        assert result["updated"] >= 1
        assert result["total_finished"] >= 1

        # Verify DB was updated
        match = seeded_db.query(Match).filter(Match.match_number == 1).first()
        assert match is not None
        assert match.home_goals == 2
        assert match.away_goals == 0
        assert match.status == "finished"

    def test_sync_no_changes_for_scheduled_matches(self, seeded_db):
        from sync_service import sync_match_results
        from models import Match

        # All matches still scheduled
        mock_api_data = [
            {
                "match_number": 1,
                "home_team": {"code": "MEX"},
                "away_team": {"code": "RSA"},
                "status": "scheduled",
            }
        ]

        with patch("sync_service._fetch_matches", return_value=mock_api_data):
            result = sync_match_results(seeded_db)

        assert result["synced"] is True
        # The match should still be scheduled, no goals
        match = seeded_db.query(Match).filter(Match.match_number == 1).first()
        assert match.status == "scheduled"

    def test_sync_resolves_placeholder_teams(self, seeded_db):
        from sync_service import sync_match_results
        from models import Match

        # Match 73 is a knockout match with placeholder teams
        mock_api_data = [
            {
                "match_number": 73,
                "home_team": {"code": "MEX", "name": "Mexico"},
                "away_team": {"code": "SUI", "name": "Switzerland"},
                "status": "completed",
                "home_goals": 1,
                "away_goals": 0,
            }
        ]

        with patch("sync_service._fetch_matches", return_value=mock_api_data):
            result = sync_match_results(seeded_db)

        match = seeded_db.query(Match).filter(Match.match_number == 73).first()
        assert match is not None
        assert match.home_team_id is not None
        assert match.away_team_id is not None
        assert match.home_team_placeholder is None
        assert match.away_team_placeholder is None

    def test_sync_skips_unknown_match_numbers(self, seeded_db):
        from sync_service import sync_match_results

        mock_api_data = [
            {
                "match_number": 9999,  # doesn't exist locally
                "home_team": {"code": "TST"},
                "away_team": {"code": "TST2"},
                "status": "completed",
                "home_goals": 3,
                "away_goals": 2,
            }
        ]

        with patch("sync_service._fetch_matches", return_value=mock_api_data):
            result = sync_match_results(seeded_db)

        assert result["synced"] is True
        assert result["updated"] == 0


class TestAdminSyncEndpoint:
    """Tests for the POST /admin/sync-results endpoint."""

    def test_sync_endpoint_success(self, client):
        """Admin can trigger sync and get results back."""
        import json

        def _register_and_login(client, email, password, name):
            client.post("/auth/register", json={
                "email": email, "password": password, "display_name": name,
            })
            r = client.post("/auth/login", json={"email": email, "password": password})
            return r.json()["access_token"]

        token = _register_and_login(client, "syncadmin@example.com", "secret123", "Admin")

        mock_api_data = [
            {
                "match_number": 1,
                "home_team": {"code": "MEX"},
                "away_team": {"code": "RSA"},
                "status": "scheduled",
            }
        ]

        with patch("sync_service._fetch_matches", return_value=mock_api_data):
            r = client.post(
                "/admin/sync-results",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert r.status_code == 200
        data = r.json()
        assert data["synced"] is True

    def test_sync_endpoint_api_failure(self, client):
        """When external API is unreachable, sync returns synced=False with error info."""
        from sync_service import SyncError

        def _register_and_login(client, email, password, name):
            client.post("/auth/register", json={
                "email": email, "password": password, "display_name": name,
            })
            r = client.post("/auth/login", json={"email": email, "password": password})
            return r.json()["access_token"]

        token = _register_and_login(client, "syncadmin2@example.com", "secret123", "Admin")

        with patch("sync_service._fetch_matches", side_effect=SyncError("Connection timeout")):
            r = client.post(
                "/admin/sync-results",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert r.status_code == 200
        data = r.json()
        assert data["synced"] is False
        assert "Connection timeout" in data["message"]