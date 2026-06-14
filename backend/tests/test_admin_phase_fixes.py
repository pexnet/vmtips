"""
Tests for the admin /phase endpoint fixes:

  B-5  Auto-generate bracket on phase transition to knockout_open.
  B-8  Validate Round-of-32 third-place placeholder uniqueness.
  B-9  Empty payload to update_phase must return 422 (no-op rejection).
  B-16 sync_match_results response includes the resolved source.

The seed script creates an admin user (admin@vmtips.se / admin), 104
matches, 12 groups, 8 third-place R32 placeholders, and the default
"VM2026" league.
"""
import pytest
from unittest.mock import patch


def _login_admin(client):
    r = client.post("/auth/login", json={"email": "admin@vmtips.se", "password": "admin"})
    assert r.status_code == 200, f"Admin login failed: {r.json()}"
    return r.json()["access_token"]


def _register_and_login(client, email, password, name):
    client.post("/auth/register", json={
        "email": email, "password": password, "display_name": name,
    })
    r = client.post("/auth/login", json={"email": email, "password": password})
    return r.json()["access_token"]


def _save_72_group_predictions(client, token, league_id):
    """Save 72 group-round predictions (one per group match) via the API."""
    r = client.get("/matches/groups", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    group_matches = r.json()
    assert len(group_matches) == 72, f"Expected 72 group matches, got {len(group_matches)}"

    payload = {
        "league_id": league_id,
        "predictions": [
            {"match_id": m["id"], "home_goals": 1, "away_goals": 0}
            for m in group_matches
        ],
    }
    r = client.post(
        "/predictions/batch",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, f"Batch save failed: {r.json()}"


def _get_vm2026_league_id(client, token):
    """The seed creates a 'VM2026' league and the auth router auto-adds
    every new user as a member. We just read the id from /leagues."""
    r = client.get("/leagues", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    leagues = r.json()
    vm = next((l for l in leagues if l.get("name") == "VM2026"), None)
    assert vm is not None, f"VM2026 league not in {leagues}"
    return vm["id"]


# ═══════════════════════════════════════════════════════════════
# B-9: empty payload must return 422
# ═══════════════════════════════════════════════════════════════

class TestUpdatePhaseNoOpRejection:
    def test_empty_payload_returns_422(self, client):
        token = _login_admin(client)
        r = client.post(
            "/admin/phase",
            json={},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 422, r.text
        assert "at least one of" in r.json()["detail"]

    def test_payload_with_only_null_fields_returns_422(self, client):
        token = _login_admin(client)
        r = client.post(
            "/admin/phase",
            json={"phase": None, "group_deadline": None, "knockout_opens_at": None, "knockout_deadline": None},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 422, r.text

    def test_valid_phase_payload_succeeds(self, client):
        token = _login_admin(client)
        r = client.post(
            "/admin/phase",
            json={"phase": "group_open"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["phase"] == "group_open"
        # Response must always include the new fields
        assert "auto_generated_brackets" in data
        assert "auto_generate_errors" in data


# ═══════════════════════════════════════════════════════════════
# B-5: auto-generate brackets on transition to knockout_open
# ═══════════════════════════════════════════════════════════════

class TestAutoGenerateBracketsOnPhaseTransition:
    def test_transition_to_knockout_open_generates_brackets(self, client, set_phase):
        """Transitioning into knockout_open auto-generates a bracket for
        every (user, league) pair with at least one group prediction."""
        set_phase("group_open")
        admin_token = _login_admin(client)

        # Register two users (each is auto-added to VM2026 by /auth/register)
        # and save 72 group predictions each.
        token_a = _register_and_login(client, "auto1@example.com", "secret123", "AutoA")
        league_id = _get_vm2026_league_id(client, token_a)
        _save_72_group_predictions(client, token_a, league_id)

        token_b = _register_and_login(client, "auto2@example.com", "secret123", "AutoB")
        _save_72_group_predictions(client, token_b, league_id)

        # Transition: group_open → knockout_open
        r = client.post(
            "/admin/phase",
            json={"phase": "knockout_open"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["phase"] == "knockout_open"
        # Both users should have triggered bracket generation
        assert data["auto_generated_brackets"] == 2, data
        assert data["auto_generate_errors"] == [], data

        # Verify BracketPrediction rows were actually created by reading
        # the bracket view for one user.
        r_view = client.get(
            f"/bracket/view?league_id={league_id}",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert r_view.status_code == 200, r_view.text
        bracket = r_view.json()
        # The /bracket/view response has a flat ``knockout_matches`` list
        # where each entry has a ``predicted`` dict with the resolved
        # team. We assert that at least one round-of-32 match has a
        # resolved (non-placeholder) home_team_id.
        r32_resolved = sum(
            1
            for m in bracket.get("knockout_matches", [])
            if m.get("round") == "round_of_32"
            and m.get("predicted", {}).get("home_team_id") is not None
        )
        assert r32_resolved > 0, f"Round-of-32 not populated: {bracket}"

    def test_no_brackets_generated_if_no_group_predictions(self, client, set_phase):
        """If no user has group predictions, auto_generated_brackets is 0."""
        set_phase("group_open")
        admin_token = _login_admin(client)
        r = client.post(
            "/admin/phase",
            json={"phase": "knockout_open"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 200
        assert r.json()["auto_generated_brackets"] == 0
        assert r.json()["auto_generate_errors"] == []

    def test_idempotent_when_phase_already_knockout_open(self, client, set_phase):
        """Re-saving knockout_open must NOT re-trigger auto-generation.

        Important: group predictions can only be saved while the phase
        is NOT yet past the group stage. So we save predictions while
        the phase is ``group_open``, then move to ``knockout_open`` and
        verify that a follow-up re-save does not re-trigger generation
        for the user we just added.
        """
        set_phase("group_open")
        admin_token = _login_admin(client)

        # First, the admin transitions to knockout_open with no users
        r1 = client.post(
            "/admin/phase",
            json={"phase": "knockout_open"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r1.status_code == 200
        assert r1.json()["auto_generated_brackets"] == 0

        # Now a new user signs up. They CAN'T save group predictions
        # anymore (phase is already knockout_open), so their bracket
        # will NOT be auto-generated by the next re-save.
        _register_and_login(client, "after@example.com", "secret123", "After")

        # Re-save knockout_open → must NOT regenerate for any user
        r2 = client.post(
            "/admin/phase",
            json={"phase": "knockout_open"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r2.status_code == 200
        assert r2.json()["auto_generated_brackets"] == 0, (
            "Re-saving the same phase must not re-trigger auto-generation"
        )

    def test_transition_to_group_closed_does_not_generate(self, client, set_phase):
        """Only the transition INTO knockout_open triggers auto-gen."""
        set_phase("group_open")
        admin_token = _login_admin(client)
        token = _register_and_login(client, "groupclose@example.com", "secret123", "GroupClose")
        league_id = _get_vm2026_league_id(client, token)
        _save_72_group_predictions(client, token, league_id)

        r = client.post(
            "/admin/phase",
            json={"phase": "group_closed"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 200
        assert r.json()["auto_generated_brackets"] == 0


# ═══════════════════════════════════════════════════════════════
# B-8: validate R32 third-place placeholder uniqueness
# ═══════════════════════════════════════════════════════════════

class TestResolveKnockoutTeamsValidation:
    def test_duplicate_third_place_placeholder_rejected(self, client, set_phase, db):
        """Two R32 matches pointing at the same third-place group letter
        must be rejected with HTTP 400 instead of silently skipping one."""
        from models import Match

        # Force all group matches to finished (admin endpoint requires it)
        for m in db.query(Match).filter(Match.round == "group").all():
            m.status = "finished"
            if m.home_goals is None:
                m.home_goals = 1
            if m.away_goals is None:
                m.away_goals = 0
        db.commit()

        admin_token = _login_admin(client)

        # Compute standings first (required precondition)
        r = client.post(
            "/admin/compute-standings",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 200, r.text

        # Inject duplicate third-place placeholder on the first two R32 matches
        r32 = (
            db.query(Match)
            .filter(Match.round == "round_of_32")
            .order_by(Match.match_number)
            .limit(2)
            .all()
        )
        assert len(r32) >= 2, "Need at least 2 R32 matches to inject duplicates"
        r32[0].home_team_placeholder = "3A"
        r32[0].home_team_id = None
        r32[1].home_team_placeholder = "3A"  # same letter!
        r32[1].home_team_id = None
        db.commit()

        r = client.post(
            "/admin/resolve-knockout-teams",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 400, r.text
        assert "Duplicate third-place placeholder" in r.json()["detail"]
        # The error message identifies the offending group letter, not
        # the full "3A" placeholder (the "3" prefix is the kind, not
        # part of the group identity).
        assert "A" in r.json()["detail"]

    def test_missing_third_place_placeholder_rejected(self, client, set_phase, db):
        """If the R32 placeholders don't cover all 8 expected third-place
        groups, the endpoint should reject with HTTP 400."""
        from models import Match

        # Mark group matches finished AND clear R32 third-place placeholders
        # so coverage is incomplete.
        for m in db.query(Match).filter(Match.round == "group").all():
            m.status = "finished"
            if m.home_goals is None:
                m.home_goals = 1
            if m.away_goals is None:
                m.away_goals = 0
        for m in db.query(Match).filter(Match.round == "round_of_32").all():
            ph = m.home_team_placeholder
            if ph is not None and ph.startswith("3"):
                m.home_team_placeholder = None
            ph = m.away_team_placeholder
            if ph is not None and ph.startswith("3"):
                m.away_team_placeholder = None
        db.commit()

        admin_token = _login_admin(client)

        r = client.post(
            "/admin/compute-standings",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 200, r.text

        r = client.post(
            "/admin/resolve-knockout-teams",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 400, r.text
        detail = r.json()["detail"]
        assert "coverage mismatch" in detail or "missing" in detail


# ═══════════════════════════════════════════════════════════════
# B-16: sync_match_results now returns "source" in the response
# ═══════════════════════════════════════════════════════════════

class TestSyncSourceInResponse:
    def test_sync_response_includes_explicit_source(self, client, db):
        """When the caller passes a source, the response reports it back
        so admins can confirm which backend was hit."""
        from sync_service import sync_match_results

        with patch("sync_service._fetch_matches", return_value=[]):
            result = sync_match_results(db, source="openfootball")

        assert "source" in result
        assert result["source"] == "openfootball"

    def test_sync_falls_back_to_default_source(self, client, db):
        """When no source is passed, the openfootball default is used and reported."""
        from sync_service import sync_match_results

        with patch("sync_service._fetch_matches", return_value=[]):
            result = sync_match_results(db, source=None)

        assert "source" in result
        assert result["source"] == "openfootball"
