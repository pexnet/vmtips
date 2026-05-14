"""
Tests verifying the seed script inserts the expected WC 2026 data.
"""
import pytest
from sqlalchemy import inspect

from database import engine, Base, SessionLocal
from models import Team, Match
from seed import main as seed_main


@pytest.fixture(scope="function")
def seeded_db():
    """Drop all tables, recreate, run seed, yield session, then cleanup."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_main()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_seed_creates_48_teams(seeded_db):
    assert seeded_db.query(Team).count() == 48


def test_seed_creates_104_matches(seeded_db):
    assert seeded_db.query(Match).count() == 104


def test_seed_creates_72_group_matches(seeded_db):
    assert seeded_db.query(Match).filter(Match.round == "group").count() == 72


def test_seed_creates_32_knockout_matches(seeded_db):
    knockout = ["ro32", "ro16", "qf", "sf", "3rd", "final"]
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
        .filter(Match.round == "ro32")
        .first()
    )
    assert ko.home_team_id is None
    assert ko.away_team_id is None
    assert ko.home_team_placeholder.startswith("1") or ko.home_team_placeholder.startswith("2") or ko.home_team_placeholder.startswith("3")
