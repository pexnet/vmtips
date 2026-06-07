"""Tournament and per-question deadline tests for league bonus questions."""
from datetime import datetime, timedelta, timezone

from models import LeagueBonusQuestion, Match, TournamentPhase


def _register_and_login(client, email, name):
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "secret123",
            "display_name": name,
        },
    )
    assert response.status_code == 201
    login = client.post(
        "/auth/login",
        json={"identifier": email, "password": "secret123"},
    )
    return login.json()["access_token"]


def _create_league(client, token):
    response = client.post(
        "/leagues",
        json={"name": "Lock Test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    return response.json()


def test_tournament_lock_blocks_question_creation(client, db):
    token = _register_and_login(client, "lock-owner@example.com", "Lock Owner")
    league = _create_league(client, token)
    phase = db.query(TournamentPhase).first()
    phase.extra_questions_lock_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()

    response = client.post(
        f"/leagues/{league['id']}/bonus-questions",
        json={"question_text": "Too late?", "points_value": 3},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["error"] == "extra_questions_locked"


def test_future_tournament_lock_keeps_questions_open(client, db):
    token = _register_and_login(client, "future-owner@example.com", "Future Owner")
    league = _create_league(client, token)
    phase = db.query(TournamentPhase).first()
    phase.extra_questions_lock_at = datetime.now(timezone.utc) + timedelta(days=1)
    db.commit()

    response = client.post(
        f"/leagues/{league['id']}/bonus-questions",
        json={"question_text": "Still open?", "points_value": 3},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    assert response.json()["is_closed"] is False


def test_per_question_deadline_blocks_answer(client, db):
    owner_token = _register_and_login(
        client,
        "question-owner@example.com",
        "Question Owner",
    )
    league = _create_league(client, owner_token)
    question_response = client.post(
        f"/leagues/{league['id']}/bonus-questions",
        json={"question_text": "Closed early?", "points_value": 3},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    question_id = question_response.json()["id"]
    question = db.query(LeagueBonusQuestion).filter(
        LeagueBonusQuestion.id == question_id
    ).one()
    question.closed_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()

    member_token = _register_and_login(
        client,
        "question-member@example.com",
        "Question Member",
    )
    client.post(
        f"/leagues/{league['id']}/join",
        json={"invite_code": league["invite_code"]},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    response = client.put(
        f"/leagues/{league['id']}/bonus-questions/{question_id}/answer",
        json={"answer_text": "No"},
        headers={"Authorization": f"Bearer {member_token}"},
    )

    assert response.status_code == 403
    assert response.json()["error"] == "extra_questions_locked"


def test_list_reports_effective_closed_state(client, db):
    token = _register_and_login(client, "state-owner@example.com", "State Owner")
    league = _create_league(client, token)
    question = client.post(
        f"/leagues/{league['id']}/bonus-questions",
        json={"question_text": "State?", "points_value": 3},
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    phase = db.query(TournamentPhase).first()
    phase.extra_questions_lock_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()

    response = client.get(
        f"/leagues/{league['id']}/bonus-questions",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()[0]["id"] == question["id"]
    assert response.json()[0]["is_closed"] is True


def test_admin_can_override_and_reset_tournament_lock(client, db):
    login = client.post(
        "/auth/login",
        json={"identifier": "admin", "password": "admin"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    override = datetime.now(timezone.utc) + timedelta(days=30)

    updated = client.post(
        "/admin/phase",
        headers=headers,
        json={"extra_questions_lock_at": override.isoformat()},
    )
    assert updated.status_code == 200

    phase_response = client.get("/admin/phase")
    assert phase_response.status_code == 200
    assert phase_response.json()["extra_questions_lock_is_override"] is True

    reset = client.post(
        "/admin/phase/reset-extra-questions-lock",
        headers=headers,
    )
    first_match = db.query(Match.match_date).order_by(Match.match_date).first()[0]

    assert reset.status_code == 200
    assert reset.json()["extra_questions_lock_is_override"] is False
    assert datetime.fromisoformat(
        reset.json()["extra_questions_lock_at"]
    ).replace(tzinfo=None) == first_match.replace(tzinfo=None)
