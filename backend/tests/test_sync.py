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


    def test_parse_openfootball_2026_group_score_shape(self):
        """openfootball 2026 group rows use score.ft and may lack explicit num."""
        from sync_service import _parse_openfootball_match

        raw = {
            "round": "Matchday 1",
            "date": "2026-06-11",
            "time": "13:00 UTC-6",
            "team1": "Mexico",
            "team2": "South Africa",
            "score": {"ft": [2, 0], "ht": [1, 0]},
            "goals1": [{"name": "Julián Quiñones", "minute": "9"}],
            "goals2": [],
            "group": "Group A",
            "ground": "Mexico City",
            "__match_number": 1,
        }

        result = _parse_openfootball_match(raw)

        assert result is not None
        assert result["match_number"] == 1
        assert result["home_name"] == "Mexico"
        assert result["away_name"] == "South Africa"
        assert result["home_goals"] == 2
        assert result["away_goals"] == 0
        assert result["status"] == "finished"

    def test_parse_openfootball_2026_scheduled_group_row(self):
        """Unplayed openfootball rows should map to scheduled matches without goals."""
        from sync_service import _parse_openfootball_match

        raw = {
            "round": "Matchday 1",
            "date": "2026-06-12",
            "time": "18:00 UTC-5",
            "team1": "United States",
            "team2": "Paraguay",
            "score": None,
            "group": "Group D",
            "__match_number": 10,
        }

        result = _parse_openfootball_match(raw)

        assert result is not None
        assert result["match_number"] == 10
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


    def test_fetch_openfootball_assigns_match_numbers_by_file_order(self):
        """The 2026 openfootball file has group rows without num; order maps to 1..104."""
        from sync_service import _fetch_openfootball
        import json

        mock_data = {
            "name": "World Cup 2026",
            "matches": [
                {"team1": "Mexico", "team2": "South Africa", "score": {"ft": [2, 0]}},
                {"team1": "Canada", "team2": "Qatar", "score": None},
            ],
        }
        mock_body = json.dumps(mock_data).encode("utf-8")

        with patch("sync_service.urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = mock_body
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            result = _fetch_openfootball("http://test.local/openfootball.json")

        assert [row["match_number"] for row in result] == [1, 2]
        assert result[0]["home_goals"] == 2
        assert result[0]["away_goals"] == 0

    def test_fetch_matches_http_error(self):
        from sync_service import _fetch_json, SyncError
        import urllib.error

        with patch("sync_service.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.HTTPError(
                url="http://test.local/api",
                code=500,
                msg="Server Error",
                hdrs={},
                fp=None,
            )
            with pytest.raises(SyncError, match="HTTP 500|HTTP error 500"):
                _fetch_json("http://test.local/api")

    def test_fetch_matches_url_error(self):
        from sync_service import _fetch_json, SyncError
        import urllib.error

        with patch("sync_service.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.URLError("Connection refused")
            with pytest.raises(SyncError, match="Cannot reach"):
                _fetch_json("http://test.local/api")


class TestSyncMatchResults:
    """Integration tests for sync_match_results with test database."""

    def test_sync_updates_finished_match(self, seeded_db):
        from sync_service import sync_match_results
        from models import Match

        # Simulate a finished match from the external API
        mock_api_data = [
            {
                "match_number": 1,
                "home_code": "MEX",
                "home_name": "Mexico",
                "away_code": "RSA",
                "away_name": "South Africa",
                "status": "finished",
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
                "home_code": "MEX",
                "home_name": "Mexico",
                "away_code": "RSA",
                "away_name": "South Africa",
                "status": "scheduled",
                "home_goals": None,
                "away_goals": None,
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
                "home_code": "MEX",
                "home_name": "Mexico",
                "away_code": "SUI",
                "away_name": "Switzerland",
                "status": "finished",
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
                "home_code": "TST",
                "home_name": "Testland",
                "away_code": "TST2",
                "away_name": "Testland2",
                "status": "finished",
                "home_goals": 3,
                "away_goals": 2,
            }
        ]

        with patch("sync_service._fetch_matches", return_value=mock_api_data):
            result = sync_match_results(seeded_db)

        assert result["synced"] is True
        assert result["updated"] == 0


    def test_sync_does_not_downgrade_finished_match_to_scheduled(self, seeded_db):
        from sync_service import sync_match_results
        from models import Match

        match = seeded_db.query(Match).filter(Match.match_number == 1).first()
        match.status = "finished"
        match.home_goals = 2
        match.away_goals = 0
        seeded_db.commit()

        mock_api_data = [
            {
                "match_number": 1,
                "home_code": "",
                "home_name": "Mexico",
                "away_code": "",
                "away_name": "South Africa",
                "status": "scheduled",
                "home_goals": None,
                "away_goals": None,
            }
        ]

        with patch("sync_service._fetch_matches", return_value=mock_api_data):
            result = sync_match_results(seeded_db)

        seeded_db.refresh(match)
        assert result["updated"] == 0
        assert match.status == "finished"
        assert match.home_goals == 2
        assert match.away_goals == 0


class TestAdminSyncEndpoint:
    """Tests for the POST /admin/sync-results endpoint."""

    def test_sync_endpoint_success(self, client):
        """Admin can trigger sync and get results back."""
        import json

        r = client.post("/auth/login", json={"email": "admin@vmtips.se", "password": "admin"})
        token = r.json()["access_token"]

        mock_api_data = [
            {
                "match_number": 1,
                "home_code": "MEX",
                "home_name": "Mexico",
                "away_code": "RSA",
                "away_name": "South Africa",
                "status": "scheduled",
                "home_goals": None,
                "away_goals": None,
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

        r = client.post("/auth/login", json={"email": "admin@vmtips.se", "password": "admin"})
        token = r.json()["access_token"]

        with patch("sync_service._fetch_matches", side_effect=SyncError("Connection timeout")):
            r = client.post(
                "/admin/sync-results",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert r.status_code == 200
        data = r.json()
        assert data["synced"] is False
        assert "Connection timeout" in data["message"]

class TestAutoSyncRunner:
    """Tests for the automatic score-sync scheduler helper."""

    def test_run_auto_sync_once_skips_when_disabled(self, seeded_db):
        from models import SyncConfig
        from sync_scheduler import run_auto_sync_once

        seeded_db.add(SyncConfig(source="openfootball", auto_sync_enabled=False, auto_sync_interval_minutes=5))
        seeded_db.commit()

        with patch("sync_scheduler.sync_match_results") as mock_sync:
            result = run_auto_sync_once(lambda: seeded_db)

        assert result["ran"] is False
        assert result["reason"] == "disabled"
        mock_sync.assert_not_called()

    def test_run_auto_sync_once_runs_when_enabled(self, seeded_db):
        from models import SyncConfig
        from sync_scheduler import run_auto_sync_once

        seeded_db.add(SyncConfig(source="openfootball", auto_sync_enabled=True, auto_sync_interval_minutes=5))
        seeded_db.commit()

        with patch("sync_scheduler.sync_match_results", return_value={"synced": True, "updated": 2}) as mock_sync:
            result = run_auto_sync_once(lambda: seeded_db)

        assert result["ran"] is True
        assert result["result"] == {"synced": True, "updated": 2}
        mock_sync.assert_called_once_with(seeded_db, source="openfootball")
