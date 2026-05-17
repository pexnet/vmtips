"""
Teams router: list all seeded teams and actual knockout advancements.
"""
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import Team, KnockoutAdvancement
from schemas import TeamOut

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("", response_model=list[TeamOut])
def list_teams(db: Session = Depends(get_db)):
    """Return all seeded teams, ordered by group then name."""
    return db.query(Team).order_by(Team.group, Team.name).all()


@router.get("/knockout-advancements")
def get_actual_knockout_advancements(db: Session = Depends(get_db)):
    """Return all actual knockout advancement teams (public endpoint)."""
    advancements = db.query(KnockoutAdvancement).all()
    team_ids = {a.team_id for a in advancements}
    teams_map = {t.id: t for t in db.query(Team).filter(Team.id.in_(team_ids)).all()}

    result = []
    for a in advancements:
        team = teams_map.get(a.team_id)
        if team:
            result.append({
                "team_id": a.team_id,
                "team_name": team.name,
                "team_code": team.code,
                "round": a.round,
                "match_number": a.match_number,
                "flag_emoji": team.flag_emoji,
            })

    return {"advancements": result}
