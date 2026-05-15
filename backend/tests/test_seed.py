"""
Tests verifying the seed script inserts the expected WC 2026 data.
"""
import pytest
from sqlalchemy import inspect

from models import Team, Match


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