"""
Tests verifying the seed script inserts the expected WC 2026 data.
"""
import json
from pathlib import Path

from models import Team, Match, League, LeagueMember, TournamentPhase, User
from security import verify_password
from seed import load_start_users, main as seed_main, seed_default_users

TEST_START_USERS_FILE = (
    Path(__file__).resolve().parents[1] / "data" / "start_users.example.json"
)


def test_seed_creates_48_teams(seeded_db):
    assert seeded_db.query(Team).count() == 48


def test_seed_creates_104_matches(seeded_db):
    assert seeded_db.query(Match).count() == 104


def test_seed_creates_72_group_matches(seeded_db):
    assert seeded_db.query(Match).filter(Match.round == "group").count() == 72


def test_seed_creates_32_knockout_matches(seeded_db):
    knockout = ["round_of_32", "round_of_16", "quarter_final", "semi_final", "match_for_third_place", "final"]
    assert seeded_db.query(Match).filter(Match.round.in_(knockout)).count() == 32


def test_all_groups_have_4_teams(seeded_db):
    for g in "ABCDEFGHIJKL":
        count = seeded_db.query(Team).filter(Team.group == g).count()
        assert count == 4, f"Group {g} has {count} teams instead of 4"


def test_group_matches_reference_real_teams(seeded_db):
    group_match = (
        seeded_db.query(Match)
        .filter(Match.round == "group", Match.home_team_id.isnot(None))
        .first()
    )
    assert group_match is not None
    assert group_match.home_team is not None
    assert group_match.away_team is not None


def test_knockout_matches_use_placeholders(seeded_db):
    ko = (
        seeded_db.query(Match)
        .filter(Match.round == "round_of_32")
        .first()
    )
    assert ko.home_team_id is None
    assert ko.away_team_id is None
    assert ko.home_team_placeholder.startswith("1") or ko.home_team_placeholder.startswith("2") or ko.home_team_placeholder.startswith("3")


def test_seed_creates_release_users_league_and_lock(seeded_db):
    admin = seeded_db.query(User).filter(User.is_admin.is_(True)).one()
    expected_emails = {
        user["email"] for user in load_start_users(TEST_START_USERS_FILE)
    }
    users = seeded_db.query(User).filter(User.email.in_(expected_emails)).all()
    league = seeded_db.query(League).filter(League.name == "VM2026").one()
    member_ids = {
        user_id
        for (user_id,) in seeded_db.query(LeagueMember.user_id)
        .filter(LeagueMember.league_id == league.id)
        .all()
    }
    phase = seeded_db.query(TournamentPhase).one()
    first_match_at = seeded_db.query(Match.match_date).order_by(Match.match_date).first()[0]

    configured_users = load_start_users(TEST_START_USERS_FILE)
    configured_passwords = [user["password"] for user in configured_users]

    assert len(users) == 7
    assert len(set(configured_passwords)) == len(configured_passwords)
    assert all(not user.is_admin and user.is_active for user in users)
    assert {user.id for user in users} == member_ids
    assert admin.id not in member_ids
    assert phase.extra_questions_lock_at == first_match_at


def test_seed_is_idempotent(seeded_db):
    seed_main(
        session=seeded_db,
        start_users_file=TEST_START_USERS_FILE,
    )
    user_count = seeded_db.query(User).count()
    membership_count = seeded_db.query(LeagueMember).count()

    seed_main(
        session=seeded_db,
        start_users_file=TEST_START_USERS_FILE,
    )

    assert seeded_db.query(User).count() == user_count
    assert seeded_db.query(LeagueMember).count() == membership_count


def test_default_users_are_read_from_private_file(db, tmp_path):
    start_users_file = tmp_path / "start_users.json"
    start_users_file.write_text(
        json.dumps(
            [
                {
                    "username": "private-user",
                    "password": "private-password",
                    "display_name": "Private-User",
                    "email": "private@example.com",
                }
            ]
        ),
        encoding="utf-8",
    )

    configured = seed_default_users(db, start_users_file=start_users_file)
    user = db.query(User).filter(User.email == "private@example.com").one()

    assert len(configured) == 1
    assert user.display_name == "Private-User"
    assert verify_password("private-password", user.password_hash)


def test_missing_start_users_file_skips_default_users(db, tmp_path):
    configured = seed_default_users(
        db,
        start_users_file=tmp_path / "missing.json",
    )

    assert configured == []
    assert db.query(User).count() == 0


def test_start_users_file_rejects_short_password(db, tmp_path):
    start_users_file = tmp_path / "start_users.json"
    start_users_file.write_text(
        json.dumps([{"username": "bad", "password": "123"}]),
        encoding="utf-8",
    )

    try:
        seed_default_users(db, start_users_file=start_users_file)
    except ValueError as exc:
        assert "at least 6 characters" in str(exc)
    else:
        raise AssertionError("short start-user password was accepted")


def test_start_users_file_rejects_duplicate_passwords(db, tmp_path):
    start_users_file = tmp_path / "start_users.json"
    start_users_file.write_text(
        json.dumps(
            [
                {"username": "one", "password": "same-password"},
                {"username": "two", "password": "same-password"},
            ]
        ),
        encoding="utf-8",
    )

    try:
        seed_default_users(db, start_users_file=start_users_file)
    except ValueError as exc:
        assert "duplicate password" in str(exc)
    else:
        raise AssertionError("duplicate start-user password was accepted")
