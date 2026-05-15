"""
Teams router: list all seeded teams.
"""
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import Team
from schemas import TeamOut

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("", response_model=list[TeamOut])
def list_teams(db: Session = Depends(get_db)):
    """Return all seeded teams, ordered by group then name."""
    return db.query(Team).order_by(Team.group, Team.name).all()
