"""
Tests for the league bonus questions CRUD endpoints.
"""


def _register_and_login(client, email, password, name):
    """Helper: register a user and return the JWT token."""
    client.post("/auth/register", json={
        "email": email,
        "password": password,
        "display_name": name,
    })
    r = client.post("/auth/login", json={"email": email, "password": password})
    return r.json()["access_token"]


def _create_league(client, token, name="Test League"):
    """Helper: create a league and return its id and invite_code."""
    r = client.post(
        "/leagues",
        json={"name": name},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    return r.json()["id"], r.json()["invite_code"]


# ── Create ────────────────────────────────────────────────────


def test_create_bonus_question(client):
    """League admin can create a bonus question."""
    token = _register_and_login(client, "admin1@example.com", "secret123", "Admin1")
    league_id, _ = _create_league(client, token)

    r = client.post(
        f"/leagues/{league_id}/bonus-questions",
        json={"question_text": "Who will win the tournament?", "points_value": 5},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["question_text"] == "Who will win the tournament?"
    assert data["points_value"] == 5
    assert data["league_id"] == league_id
    assert data["answer"] is None
    assert data["id"] is not None


def test_create_bonus_question_not_admin(client):
    """Non-admin member cannot create a bonus question."""
    admin_token = _register_and_login(client, "admin2@example.com", "secret123", "Admin2")
    league_id, invite_code = _create_league(client, token=admin_token)

    member_token = _register_and_login(client, "member2@example.com", "secret123", "Member2")
    # Join the league
    client.post(
        f"/leagues/{league_id}/join",
        json={"invite_code": invite_code},
        headers={"Authorization": f"Bearer {member_token}"},
    )

    r = client.post(
        f"/leagues/{league_id}/bonus-questions",
        json={"question_text": "Test?", "points_value": 3},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "not_league_admin"


def test_create_bonus_question_league_not_found(client):
    """Creating a bonus question in a non-existent league returns 404."""
    token = _register_and_login(client, "admin3@example.com", "secret123", "Admin3")

    r = client.post(
        "/leagues/9999/bonus-questions",
        json={"question_text": "Test?", "points_value": 3},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404


# ── List ───────────────────────────────────────────────────────


def test_list_bonus_questions(client):
    """League members can list bonus questions."""
    admin_token = _register_and_login(client, "admin4@example.com", "secret123", "Admin4")
    league_id, invite_code = _create_league(client, token=admin_token)

    # Create two questions
    client.post(
        f"/leagues/{league_id}/bonus-questions",
        json={"question_text": "Q1", "points_value": 3},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    client.post(
        f"/leagues/{league_id}/bonus-questions",
        json={"question_text": "Q2", "points_value": 5},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    r = client.get(
        f"/leagues/{league_id}/bonus-questions",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    assert data[0]["question_text"] == "Q1"
    assert data[1]["question_text"] == "Q2"


def test_list_bonus_questions_not_member(client):
    """Non-member cannot list bonus questions."""
    admin_token = _register_and_login(client, "admin5@example.com", "secret123", "Admin5")
    league_id, _ = _create_league(client, token=admin_token)

    outsider_token = _register_and_login(client, "outsider1@example.com", "secret123", "Outsider1")
    r = client.get(
        f"/leagues/{league_id}/bonus-questions",
        headers={"Authorization": f"Bearer {outsider_token}"},
    )
    assert r.status_code == 403


def test_list_bonus_questions_hides_answer_from_members(client):
    """Members can see the question but not the admin's answer."""
    admin_token = _register_and_login(client, "adminhide@example.com", "secret123", "AdminHide")
    league_id, invite_code = _create_league(client, token=admin_token)
    create_r = client.post(
        f"/leagues/{league_id}/bonus-questions",
        json={"question_text": "Secret?", "points_value": 3, "answer": "France"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_r.status_code == 201
    assert create_r.json()["answer"] == "France"

    member_token = _register_and_login(client, "memberhide@example.com", "secret123", "MemberHide")
    client.post(
        f"/leagues/{league_id}/join",
        json={"invite_code": invite_code},
        headers={"Authorization": f"Bearer {member_token}"},
    )

    listed = client.get(
        f"/leagues/{league_id}/bonus-questions",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert listed.status_code == 200
    assert listed.json()[0]["answer"] is None


# ── Get ────────────────────────────────────────────────────────


def test_get_bonus_question(client):
    """A league member can get a single bonus question."""
    admin_token = _register_and_login(client, "admin6@example.com", "secret123", "Admin6")
    league_id, _ = _create_league(client, token=admin_token)

    create_r = client.post(
        f"/leagues/{league_id}/bonus-questions",
        json={"question_text": "Top scorer?", "points_value": 10},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    question_id = create_r.json()["id"]

    r = client.get(
        f"/leagues/{league_id}/bonus-questions/{question_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == question_id
    assert data["question_text"] == "Top scorer?"
    assert data["points_value"] == 10


def test_get_bonus_question_not_found(client):
    """Getting a non-existent bonus question returns 404."""
    admin_token = _register_and_login(client, "admin7@example.com", "secret123", "Admin7")
    league_id, _ = _create_league(client, token=admin_token)

    r = client.get(
        f"/leagues/{league_id}/bonus-questions/9999",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 404


def test_get_bonus_question_wrong_league(client):
    """Getting a bonus question from a different league returns 404."""
    admin_token = _register_and_login(client, "admin8@example.com", "secret123", "Admin8")
    league1_id, _ = _create_league(client, token=admin_token, name="League 1")
    league2_id, _ = _create_league(client, token=admin_token, name="League 2")

    create_r = client.post(
        f"/leagues/{league1_id}/bonus-questions",
        json={"question_text": "L1 Question", "points_value": 3},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    question_id = create_r.json()["id"]

    # Looking for league1's question in league2's context should 404
    r = client.get(
        f"/leagues/{league2_id}/bonus-questions/{question_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 404


# ── Update ─────────────────────────────────────────────────────


def test_update_bonus_question(client):
    """League admin can update a bonus question."""
    admin_token = _register_and_login(client, "admin9@example.com", "secret123", "Admin9")
    league_id, _ = _create_league(client, token=admin_token)

    create_r = client.post(
        f"/leagues/{league_id}/bonus-questions",
        json={"question_text": "Original?", "points_value": 3},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    question_id = create_r.json()["id"]

    r = client.patch(
        f"/leagues/{league_id}/bonus-questions/{question_id}",
        json={"question_text": "Updated?", "points_value": 5},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["question_text"] == "Updated?"
    assert data["points_value"] == 5


def test_update_bonus_question_set_answer(client):
    """League admin can set the answer on a bonus question."""
    admin_token = _register_and_login(client, "admin10@example.com", "secret123", "Admin10")
    league_id, _ = _create_league(client, token=admin_token)

    create_r = client.post(
        f"/leagues/{league_id}/bonus-questions",
        json={"question_text": "Who wins?", "points_value": 5},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    question_id = create_r.json()["id"]

    r = client.patch(
        f"/leagues/{league_id}/bonus-questions/{question_id}",
        json={"answer": "France"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    assert r.json()["answer"] == "France"


def test_member_bonus_answer_is_hidden_until_group_lock(client, set_phase):
    """Correctness and points are hidden until league bonus answers lock."""
    admin_token = _register_and_login(client, "bonusadmin@example.com", "secret123", "BonusAdmin")
    league_id, invite_code = _create_league(client, token=admin_token)
    create_r = client.post(
        f"/leagues/{league_id}/bonus-questions",
        json={"question_text": "Winner?", "points_value": 5, "answer": "France"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    question_id = create_r.json()["id"]

    member_token = _register_and_login(client, "bonusmember@example.com", "secret123", "BonusMember")
    client.post(
        f"/leagues/{league_id}/join",
        json={"invite_code": invite_code},
        headers={"Authorization": f"Bearer {member_token}"},
    )

    answer_r = client.put(
        f"/leagues/{league_id}/bonus-questions/{question_id}/answer",
        json={"answer_text": "france"},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert answer_r.status_code == 200
    assert answer_r.json()["is_correct"] is None
    assert answer_r.json()["points_awarded"] is None

    score_r = client.get(
        f"/leaderboard/me?league_id={league_id}",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert score_r.status_code == 200
    assert score_r.json()["league_bonus_points"] == 0
    assert score_r.json()["total_points"] == 0

    set_phase("group_closed")
    answer_r = client.get(
        f"/leagues/{league_id}/bonus-questions/{question_id}/answer",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert answer_r.json()["is_correct"] is True
    assert answer_r.json()["points_awarded"] == 5

    score_r = client.get(
        f"/leaderboard/me?league_id={league_id}",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert score_r.json()["league_bonus_points"] == 5
    assert score_r.json()["total_points"] == 5


def test_member_cannot_change_bonus_answer_after_group_lock(client, set_phase):
    admin_token = _register_and_login(client, "lockadmin@example.com", "secret123", "LockAdmin")
    league_id, invite_code = _create_league(client, token=admin_token)
    question_id = client.post(
        f"/leagues/{league_id}/bonus-questions",
        json={"question_text": "Winner?", "points_value": 5, "answer": "France"},
        headers={"Authorization": f"Bearer {admin_token}"},
    ).json()["id"]
    member_token = _register_and_login(client, "lockmember@example.com", "secret123", "LockMember")
    client.post(
        f"/leagues/{league_id}/join",
        json={"invite_code": invite_code},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    set_phase("group_closed")

    r = client.put(
        f"/leagues/{league_id}/bonus-questions/{question_id}/answer",
        json={"answer_text": "France"},
        headers={"Authorization": f"Bearer {member_token}"},
    )

    assert r.status_code == 403
    assert r.json()["error"] == "bonus_answers_locked"


def test_update_bonus_question_not_admin(client):
    """Non-admin cannot update a bonus question."""
    admin_token = _register_and_login(client, "admin11@example.com", "secret123", "Admin11")
    league_id, invite_code = _create_league(client, token=admin_token)

    create_r = client.post(
        f"/leagues/{league_id}/bonus-questions",
        json={"question_text": "Test?", "points_value": 3},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    question_id = create_r.json()["id"]

    member_token = _register_and_login(client, "member11@example.com", "secret123", "Member11")
    client.post(
        f"/leagues/{league_id}/join",
        json={"invite_code": invite_code},
        headers={"Authorization": f"Bearer {member_token}"},
    )

    r = client.patch(
        f"/leagues/{league_id}/bonus-questions/{question_id}",
        json={"question_text": "Hacked?"},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert r.status_code == 403


def test_update_bonus_question_empty_payload(client):
    """Updating with no fields returns a validation error."""
    admin_token = _register_and_login(client, "admin12@example.com", "secret123", "Admin12")
    league_id, _ = _create_league(client, token=admin_token)

    create_r = client.post(
        f"/leagues/{league_id}/bonus-questions",
        json={"question_text": "Test?", "points_value": 3},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    question_id = create_r.json()["id"]

    r = client.patch(
        f"/leagues/{league_id}/bonus-questions/{question_id}",
        json={},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 400


# ── Delete ─────────────────────────────────────────────────────


def test_delete_bonus_question(client):
    """League admin can delete a bonus question."""
    admin_token = _register_and_login(client, "admin13@example.com", "secret123", "Admin13")
    league_id, _ = _create_league(client, token=admin_token)

    create_r = client.post(
        f"/leagues/{league_id}/bonus-questions",
        json={"question_text": "Delete me", "points_value": 2},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    question_id = create_r.json()["id"]

    r = client.delete(
        f"/leagues/{league_id}/bonus-questions/{question_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    assert r.json()["deleted"] is True
    assert r.json()["question_id"] == question_id

    # Verify it's gone
    get_r = client.get(
        f"/leagues/{league_id}/bonus-questions/{question_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_r.status_code == 404


def test_delete_bonus_question_not_admin(client):
    """Non-admin cannot delete a bonus question."""
    admin_token = _register_and_login(client, "admin14@example.com", "secret123", "Admin14")
    league_id, invite_code = _create_league(client, token=admin_token)

    create_r = client.post(
        f"/leagues/{league_id}/bonus-questions",
        json={"question_text": "Protected", "points_value": 3},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    question_id = create_r.json()["id"]

    member_token = _register_and_login(client, "member14@example.com", "secret123", "Member14")
    client.post(
        f"/leagues/{league_id}/join",
        json={"invite_code": invite_code},
        headers={"Authorization": f"Bearer {member_token}"},
    )

    r = client.delete(
        f"/leagues/{league_id}/bonus-questions/{question_id}",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert r.status_code == 403


def test_delete_bonus_question_not_found(client):
    """Deleting a non-existent bonus question returns 404."""
    admin_token = _register_and_login(client, "admin15@example.com", "secret123", "Admin15")
    league_id, _ = _create_league(client, token=admin_token)

    r = client.delete(
        f"/leagues/{league_id}/bonus-questions/9999",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 404
