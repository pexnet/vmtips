"""
SQLAlchemy ORM models for the VMTips application.
"""
import datetime
from datetime import timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    Float,
)
from sqlalchemy.orm import relationship

from database import Base


def _utcnow():
    """Return current UTC time as a timezone-aware datetime."""
    return datetime.datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    avatar_url = Column(Text, nullable=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_utcnow)

    predictions = relationship("Prediction", back_populates="user", cascade="all, delete-orphan")
    tournament_bonuses = relationship("TournamentBonus", back_populates="user", uselist=False, cascade="all, delete-orphan")
    league_memberships = relationship("LeagueMember", back_populates="user", cascade="all, delete-orphan")
    scores = relationship("Score", back_populates="user", cascade="all, delete-orphan")
    bracket_predictions = relationship("BracketPrediction", back_populates="user", cascade="all, delete-orphan")


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    code = Column(String(3), unique=True, nullable=False)
    group = Column(String(1), nullable=False)
    flag_emoji = Column(String)
    flag_svg = Column(String)

    home_matches = relationship("Match", foreign_keys="Match.home_team_id", back_populates="home_team")
    away_matches = relationship("Match", foreign_keys="Match.away_team_id", back_populates="away_team")


class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    match_number = Column(Integer, unique=True, nullable=False)
    group = Column(String(1))
    round = Column(String, nullable=False)  # group / round_of_32 / round_of_16 / quarter_final / semi_final / match_for_third_place / final
    home_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    away_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    home_team_placeholder = Column(String)
    away_team_placeholder = Column(String)
    home_goals = Column(Integer)
    away_goals = Column(Integer)
    match_date = Column(DateTime, nullable=False)
    status = Column(String, default="scheduled")  # scheduled / ongoing / finished

    home_team = relationship("Team", foreign_keys=[home_team_id], back_populates="home_matches")
    away_team = relationship("Team", foreign_keys=[away_team_id], back_populates="away_matches")
    predictions = relationship("Prediction", back_populates="match", cascade="all, delete-orphan")


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (
        UniqueConstraint("user_id", "match_id", "league_id", name="uq_user_match_league_prediction"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=False, default=1)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    home_goals = Column(Integer, nullable=False)
    away_goals = Column(Integer, nullable=False)
    knockout_winner_side = Column(String, nullable=True)  # home / away when knockout full-time score is drawn
    knockout_resolution = Column(String, nullable=True)  # extra_time / penalties
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    user = relationship("User", back_populates="predictions")
    league = relationship("League")
    match = relationship("Match", back_populates="predictions")


class League(Base):
    __tablename__ = "leagues"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    invite_code = Column(String(6), unique=True, nullable=False)
    is_public = Column(Boolean, default=False)
    admin_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=_utcnow)

    admin = relationship("User")
    members = relationship("LeagueMember", back_populates="league", cascade="all, delete-orphan")
    bonus_questions = relationship("LeagueBonusQuestion", back_populates="league", cascade="all, delete-orphan")
    scores = relationship("Score", back_populates="league", cascade="all, delete-orphan")


class LeagueMember(Base):
    __tablename__ = "league_members"
    __table_args__ = (
        UniqueConstraint("league_id", "user_id", name="uq_league_user"),
    )

    id = Column(Integer, primary_key=True, index=True)
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    joined_at = Column(DateTime, default=_utcnow)

    league = relationship("League", back_populates="members")
    user = relationship("User", back_populates="league_memberships")


class TournamentBonus(Base):
    __tablename__ = "tournament_bonuses"
    __table_args__ = (
        UniqueConstraint("user_id", "league_id", name="uq_user_league_bonus"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=False)
    winner_team_id = Column(Integer, ForeignKey("teams.id"))
    top_scorer_name = Column(String)
    bronze_winner_team_id = Column(Integer, ForeignKey("teams.id"))
    most_goals_team_id = Column(Integer, ForeignKey("teams.id"))
    most_conceded_team_id = Column(Integer, ForeignKey("teams.id"))
    custom_bonus_1 = Column(String)
    custom_bonus_2 = Column(String)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    user = relationship("User", back_populates="tournament_bonuses")
    league = relationship("League")
    winner_team = relationship("Team", foreign_keys=[winner_team_id])
    bronze_winner_team = relationship("Team", foreign_keys=[bronze_winner_team_id])
    most_goals_team = relationship("Team", foreign_keys=[most_goals_team_id])
    most_conceded_team = relationship("Team", foreign_keys=[most_conceded_team_id])


class LeagueBonusQuestion(Base):
    __tablename__ = "league_bonus_questions"

    id = Column(Integer, primary_key=True, index=True)
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=False)
    question_text = Column(String, nullable=False)
    points_value = Column(Integer, nullable=False)
    answer = Column(String)
    created_at = Column(DateTime, default=_utcnow)

    league = relationship("League", back_populates="bonus_questions")
    answers = relationship("LeagueBonusAnswer", back_populates="question", cascade="all, delete-orphan")


class LeagueBonusAnswer(Base):
    __tablename__ = "league_bonus_answers"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("league_bonus_questions.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    answer_text = Column(String, nullable=False)
    is_correct = Column(Boolean)
    points_awarded = Column(Integer)

    question = relationship("LeagueBonusQuestion", back_populates="answers")


class BracketPrediction(Base):
    __tablename__ = "bracket_predictions"
    __table_args__ = (
        UniqueConstraint("user_id", "league_id", "team_id", "round", name="uq_user_league_team_round"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    round = Column(String, nullable=False)  # round_of_32 / round_of_16 / quarter_final / semi_final / match_for_third_place / final
    source = Column(String, default="knockout_prediction")  # group_prediction / knockout_prediction
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    user = relationship("User", back_populates="bracket_predictions")
    league = relationship("League")
    team = relationship("Team")


class TournamentResult(Base):
    __tablename__ = "tournament_results"

    id = Column(Integer, primary_key=True, index=True)
    winner_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    top_scorer_name = Column(String)
    bronze_winner_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    most_goals_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    most_conceded_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    custom_bonus_1_answer = Column(String)
    custom_bonus_2_answer = Column(String)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    winner_team = relationship("Team", foreign_keys=[winner_team_id])
    bronze_winner_team = relationship("Team", foreign_keys=[bronze_winner_team_id])
    most_goals_team = relationship("Team", foreign_keys=[most_goals_team_id])
    most_conceded_team = relationship("Team", foreign_keys=[most_conceded_team_id])


class KnockoutAdvancement(Base):
    """Tracks which teams have actually advanced to each knockout round."""
    __tablename__ = "knockout_advancements"
    __table_args__ = (
        UniqueConstraint("team_id", "round", name="uq_team_round_advancement"),
    )

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    round = Column(String, nullable=False)  # round_of_32 / round_of_16 / quarter_final / semi_final / match_for_third_place / final
    match_number = Column(Integer, nullable=True)  # The match where they appeared
    created_at = Column(DateTime, default=_utcnow)

    team = relationship("Team")


class TournamentPhase(Base):
    """Tracks the current phase of the tournament for prediction gating."""
    __tablename__ = "tournament_phases"

    id = Column(Integer, primary_key=True, index=True)
    phase = Column(String, default="group_open")  # group_open / group_closed / knockout_open / knockout_closed
    group_deadline = Column(DateTime, nullable=True)  # When group predictions close
    knockout_opens_at = Column(DateTime, nullable=True)  # When knockout predictions open
    knockout_deadline = Column(DateTime, nullable=True)  # When knockout predictions close
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)


class SyncConfig(Base):
    """Persisted admin-controlled sync settings."""
    __tablename__ = "sync_config"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, nullable=False, default="worldcupjson")
    auto_sync_enabled = Column(Boolean, default=False)
    auto_sync_interval_minutes = Column(Integer, default=5)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)


class GroupStanding(Base):
    """Cached group standings computed from finished group matches."""
    __tablename__ = "group_standings"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    group = Column(String(1), nullable=False)
    position = Column(Integer)  # 1-4 within group
    played = Column(Integer, default=0)
    won = Column(Integer, default=0)
    drawn = Column(Integer, default=0)
    lost = Column(Integer, default=0)
    goals_for = Column(Integer, default=0)
    goals_against = Column(Integer, default=0)
    goal_difference = Column(Integer, default=0)
    points = Column(Integer, default=0)

    team = relationship("Team")


class Score(Base):
    __tablename__ = "scores"
    __table_args__ = (
        UniqueConstraint("user_id", "league_id", name="uq_score_user_league"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=True)
    match_points = Column(Integer, default=0)
    bracket_points = Column(Integer, default=0)
    tournament_bonus_points = Column(Integer, default=0)
    league_bonus_points = Column(Integer, default=0)
    total_points = Column(Integer, default=0)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    user = relationship("User", back_populates="scores")
    league = relationship("League", back_populates="scores")
