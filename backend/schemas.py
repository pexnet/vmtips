"""
Pydantic schemas for request/response validation.
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

# ── Auth ────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=72)
    display_name: str = Field(..., min_length=1, max_length=50)
    first_name: str | None = Field(None, max_length=50)
    last_name: str | None = Field(None, max_length=50)

class UserProfileUpdate(BaseModel):
    email: EmailStr
    first_name: str = Field("", max_length=50)
    last_name: str = Field("", max_length=50)
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
    first_name: str | None = None
    last_name: str | None = None
    avatar_url: str | None = None
    is_admin: bool = False

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
    match_date: datetime
    status: str

    class Config:
        from_attributes = True


# ── Predictions ─────────────────────────────────────────────

class PredictionCreate(BaseModel):
    match_id: int
    home_goals: int = Field(..., ge=0, le=15)
    away_goals: int = Field(..., ge=0, le=15)
    knockout_winner_side: Literal["home", "away"] | None = None
    knockout_resolution: Literal["extra_time", "penalties"] | None = None

class PredictionOut(BaseModel):
    id: int
    match_id: int
    home_goals: int
    away_goals: int
    knockout_winner_side: str | None = None
    knockout_resolution: str | None = None
    created_at: datetime
    updated_at: datetime

class PredictionBatchCreate(BaseModel):
    league_id: int | None = None
    predictions: list[PredictionCreate]


class TournamentBonusCreate(BaseModel):
    league_id: int | None = None
    winner_team_id: int | None = None
    top_scorer_name: str | None = None
    bronze_winner_team_id: int | None = None
    most_goals_team_id: int | None = None
    most_conceded_team_id: int | None = None
    custom_bonus_1: str | None = None
    custom_bonus_2: str | None = None


# ── Bracket Predictions ───────────────────────────────────────

class BracketPredictionEntry(BaseModel):
    """Single team placement in a knockout round."""
    team_id: int
    round: str  # round_of_32 / round_of_16 / quarter_final / semi_final / match_for_third_place / final

class BracketPredictionBatch(BaseModel):
    """Batch of bracket predictions for the authenticated user."""
    league_id: int | None = None
    entries: list[BracketPredictionEntry]

class BracketPredictionOut(BaseModel):
    id: int
    team_id: int
    round: str
    source: str | None = "knockout_prediction"
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── League Bonus Questions ────────────────────────────────────

class LeagueBonusQuestionCreate(BaseModel):
    question_text: str = Field(..., min_length=1, max_length=500)
    points_value: int = Field(..., ge=1)
    answer: str | None = None

class LeagueBonusQuestionUpdate(BaseModel):
    question_text: str | None = Field(None, min_length=1, max_length=500)
    points_value: int | None = Field(None, ge=1)
    answer: str | None = None

class LeagueBonusAnswerCreate(BaseModel):
    answer_text: str = Field(..., min_length=1, max_length=500)

class LeagueBonusQuestionOut(BaseModel):
    id: int
    league_id: int
    question_text: str
    points_value: int
    answer: str | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True

class LeagueBonusAnswerOut(BaseModel):
    question_id: int
    answer_text: str | None = None
    is_correct: bool | None = None
    points_awarded: int | None = None

    class Config:
        from_attributes = True


# ── Leagues ─────────────────────────────────────────────────

class LeagueCreate(BaseModel):
    name: str
    is_public: bool = False

class LeagueJoin(BaseModel):
    invite_code: str

class LeagueMemberOut(BaseModel):
    id: int
    display_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    avatar_url: str | None = None

class LeagueOut(BaseModel):
    id: int
    name: str
    invite_code: str
    created_at: datetime | None = None
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
    created_at: datetime | None = None

    class Config:
        from_attributes = True


# ── Admin ─────────────────────────────────────────────────────

class MatchResultUpdate(BaseModel):
    home_goals: int = Field(..., ge=0, le=30)
    away_goals: int = Field(..., ge=0, le=30)

class TournamentResultUpdate(BaseModel):
    winner_team_id: int | None = None
    top_scorer_name: str | None = None
    bronze_winner_team_id: int | None = None
    most_goals_team_id: int | None = None
    most_conceded_team_id: int | None = None
    custom_bonus_1_answer: str | None = None
    custom_bonus_2_answer: str | None = None


# ── Phase ─────────────────────────────────────────────────────

class PhaseOut(BaseModel):
    """Current tournament phase for prediction gating."""
    phase: str  # group_open / group_closed / knockout_open / knockout_closed
    group_deadline: datetime | None = None
    knockout_opens_at: datetime | None = None
    knockout_deadline: datetime | None = None

    class Config:
        from_attributes = True

class PhaseUpdate(BaseModel):
    phase: str | None = None
    group_deadline: str | None = None  # ISO datetime
    knockout_opens_at: str | None = None  # ISO datetime
    knockout_deadline: str | None = None  # ISO datetime


# ── Group Standings ───────────────────────────────────────────

class GroupStandingOut(BaseModel):
    team_id: int
    team_name: str
    team_code: str
    group: str
    position: int | None = None
    played: int
    won: int
    drawn: int
    lost: int
    goals_for: int
    goals_against: int
    goal_difference: int
    points: int

    class Config:
        from_attributes = True


# ── Knockout Advancement ──────────────────────────────────────

class KnockoutAdvancementCreate(BaseModel):
    team_id: int
    round: str
    match_number: int | None = None

class KnockoutAdvancementOut(BaseModel):
    id: int
    team_id: int
    round: str
    match_number: int | None = None
    team_name: str | None = None
    team_code: str | None = None

    class Config:
        from_attributes = True


# ── Scoring Overview ─────────────────────────────────────────

class ScoreDetailOut(BaseModel):
    """Detailed score breakdown for a user."""
    user_id: int
    display_name: str
    match_points: int
    bracket_points: int
    tournament_bonus_points: int
    league_bonus_points: int
    total_points: int

    class Config:
        from_attributes = True
