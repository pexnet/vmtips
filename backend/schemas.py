"""
Pydantic schemas for request/response validation.
"""
import math
from typing import Generic, TypeVar

from pydantic import BaseModel, EmailStr, Field

T = TypeVar("T")


# ── Pagination ─────────────────────────────────────────────

class PaginationParams(BaseModel):
    """Query parameters for paginated list endpoints."""
    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    per_page: int = Field(default=50, ge=1, le=200, description="Items per page")


class PaginatedResponse(BaseModel, Generic[T]):
    """Wrapper for paginated list responses."""
    items: list[T]
    total: int
    page: int
    per_page: int
    total_pages: int


# ── Auth ────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=72)
    display_name: str = Field(..., min_length=1, max_length=50)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: str
    display_name: str

    class Config:
        from_attributes = True


# ── Matches ─────────────────────────────────────────────────

class TeamOut(BaseModel):
    id: int
    name: str
    code: str
    group: str
    flag_emoji: str | None = None

    class Config:
        from_attributes = True


class MatchOut(BaseModel):
    id: int
    match_number: int
    group: str | None = None
    round: str
    home_team: TeamOut | None = None
    away_team: TeamOut | None = None
    home_team_placeholder: str | None = None
    away_team_placeholder: str | None = None
    home_goals: int | None = None
    away_goals: int | None = None
    match_date: str
    status: str

    class Config:
        from_attributes = True


# ── Predictions ─────────────────────────────────────────────

class PredictionCreate(BaseModel):
    match_id: int
    home_goals: int = Field(..., ge=0)
    away_goals: int = Field(..., ge=0)


class PredictionOut(BaseModel):
    id: int
    match_id: int
    home_goals: int
    away_goals: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class TournamentBonusCreate(BaseModel):
    winner_team_id: int | None = None
    top_scorer_name: str | None = None
    top_assist_name: str | None = None
    total_goals: int | None = None


class PredictionBatchCreate(BaseModel):
    predictions: list[PredictionCreate]


# ── Leagues ─────────────────────────────────────────────────

class LeagueCreate(BaseModel):
    name: str
    is_public: bool = False


class LeagueJoin(BaseModel):
    invite_code: str


class LeagueMemberOut(BaseModel):
    id: int
    display_name: str | None = None


class LeagueOut(BaseModel):
    id: int
    name: str
    invite_code: str
    created_at: str | None = None
    admin_user_id: int

    class Config:
        from_attributes = True


class LeagueDetailOut(LeagueOut):
    is_admin: bool
    members: list[LeagueMemberOut]


class LeaguePublicOut(BaseModel):
    """Public league info returned to unauthenticated users (no invite_code)."""
    id: int
    name: str
    member_count: int
    created_at: str | None = None

    class Config:
        from_attributes = True


# ── League Bonus Questions ────────────────────────────────────

class LeagueBonusQuestionCreate(BaseModel):
    question_text: str = Field(..., min_length=1, max_length=500)
    points_value: int = Field(..., ge=1)


class LeagueBonusQuestionUpdate(BaseModel):
    question_text: str | None = Field(None, min_length=1, max_length=500)
    points_value: int | None = Field(None, ge=1)
    answer: str | None = None


class LeagueBonusQuestionOut(BaseModel):
    id: int
    league_id: int
    question_text: str
    points_value: int
    answer: str | None = None
    created_at: str | None = None

    class Config:
        from_attributes = True


# ── Admin ─────────────────────────────────────────────────────

class MatchResultUpdate(BaseModel):
    home_goals: int = Field(..., ge=0, le=30)
    away_goals: int = Field(..., ge=0, le=30)


# ── Bracket Predictions ───────────────────────────────────────

class BracketPredictionEntry(BaseModel):
    """Single team placement in a knockout round."""
    team_id: int
    round: str  # round_of_32 / round_of_16 / quarter_final / semi_final / final


class BracketPredictionBatch(BaseModel):
    """Batch of bracket predictions for the authenticated user."""
    entries: list[BracketPredictionEntry]


class BracketPredictionOut(BaseModel):
    id: int
    team_id: int
    round: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True
