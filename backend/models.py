"""
SQLAlchemy ORM models for the VMTips application.
"""
import datetime
from datetime import timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
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
    created_at = Column(DateTime, default=_utcnow)

    predictions = relationship("Prediction", back_populates="user", cascade="all, delete-orphan")
    tournament_bonuses = relationship("TournamentBonus", back_populates="user", uselist=False, cascade="all, delete-orphan")
    league_memberships = relationship("LeagueMember", back_populates="user", cascade="all, delete-orphan")
    scores = relationship("Score", back_populates="user", cascade="all, delete-orphan")


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
    round = Column(String, nullable=False)  # group / ro32 / ro16 / qf / sf / final / 3rd
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
        UniqueConstraint("user_id", "match_id", name="uq_user_match_prediction"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    home_goals = Column(Integer, nullable=False)
    away_goals = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    user = relationship("User", back_populates="predictions")
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

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    winner_team_id = Column(Integer, ForeignKey("teams.id"))
    top_scorer_name = Column(String)
    top_assist_name = Column(String)
    total_goals = Column(Integer)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    user = relationship("User", back_populates="tournament_bonuses")
    winner_team = relationship("Team")


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


class Score(Base):
    __tablename__ = "scores"

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
