"""
Pydantic schemas for request/response validation.
"""
from pydantic import BaseModel, EmailStr, Field


# ── Auth ────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
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


class LeagueJoin(BaseModel):
    invite_code: str


class LeagueMemberOut(BaseModel):
    id: int
    display_name: str | None = None
    email: str


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
