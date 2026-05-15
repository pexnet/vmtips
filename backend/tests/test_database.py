"""
Unit tests verifying database setup and table creation.
"""
import datetime

import pytest
from sqlalchemy import inspect

from database import Base
from models import (
    User,
    Team,
    Match,
    Prediction,
    League,
    LeagueMember,
    TournamentBonus,
    LeagueBonusQuestion,
    LeagueBonusAnswer,
    Score,
)


def test_all_tables_exist(db, test_engine_fixture):
    """Ensure every expected table is present in the SQLite database."""
    inspector = inspect(test_engine_fixture)
    expected = {
        "users",
        "teams",
        "matches",
        "predictions",
        "leagues",
        "league_members",
        "tournament_bonuses",
        "league_bonus_questions",
        "league_bonus_answers",
        "scores",
    }
    actual = set(inspector.get_table_names())
    assert expected <= actual, f"Missing tables: {expected - actual}"


def test_create_user(db):
    """Users can be persisted and retrieved."""
    user = User(email="alice@example.com", password_hash="secret", display_name="Alice")
    db.add(user)
    db.commit()
    db.refresh(user)

    assert user.id is not None
    assert user.created_at is not None


def test_create_team(db):
    """Teams can be persisted with flag metadata."""
    team = Team(name="Sweden", code="SWE", group="A", flag_emoji="🇸🇪")
    db.add(team)
    db.commit()
    db.refresh(team)

    assert team.id is not None
    assert team.flag_emoji == "🇸🇪"


def test_create_match(db):
    """Matches can reference teams and include placeholders."""
    home = Team(name="Germany", code="GER", group="B")
    away = Team(name="France", code="FRA", group="B")
    db.add_all([home, away])
    db.commit()

    match = Match(
        match_number=1,
        group="B",
        round="group",
        home_team_id=home.id,
        away_team_id=away.id,
        match_date=datetime.datetime(2026, 6, 12, 16, 0, 0),
    )
    db.add(match)
    db.commit()

    assert match.id is not None
    assert match.status == "scheduled"


def test_prediction_unique_constraint(db):
    """Duplicate predictions for the same user+match are rejected."""
    user = User(email="bob@example.com", password_hash="secret", display_name="Bob")
    team = Team(name="Spain", code="ESP", group="C")
    db.add_all([user, team])
    db.commit()

    match = Match(
        match_number=2,
        round="group",
        home_team_id=team.id,
        away_team_id=team.id,
        match_date=datetime.datetime(2026, 6, 12, 16, 0, 0),
    )
    db.add(match)
    db.commit()

    pred1 = Prediction(user_id=user.id, match_id=match.id, home_goals=2, away_goals=1)
    db.add(pred1)
    db.commit()

    pred2 = Prediction(user_id=user.id, match_id=match.id, home_goals=3, away_goals=0)
    db.add(pred2)
    with pytest.raises(Exception):
        db.commit()