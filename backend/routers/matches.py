"""
Matches router: list all matches, filter by group/knockout, and fetch single match.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Match
from schemas import MatchOut

router = APIRouter(prefix="/matches", tags=["matches"])


def _match_to_dict(match: Match) -> dict:
    """Serialize a Match ORM row into a dict matching MatchOut."""
    return {
        "id": match.id,
        "match_number": match.match_number,
        "group": match.group,
        "round": match.round,
        "home_team": {
            "id": match.home_team.id,
            "name": match.home_team.name,
            "code": match.home_team.code,
            "group": match.home_team.group,
            "flag_emoji": match.home_team.flag_emoji,
        } if match.home_team else None,
        "away_team": {
            "id": match.away_team.id,
            "name": match.away_team.name,
            "code": match.away_team.code,
            "group": match.away_team.group,
            "flag_emoji": match.away_team.flag_emoji,
        } if match.away_team else None,
        "home_team_placeholder": match.home_team_placeholder,
        "away_team_placeholder": match.away_team_placeholder,
        "home_goals": match.home_goals,
        "away_goals": match.away_goals,
        "match_date": match.match_date.isoformat() if match.match_date else None,
        "status": match.status,
    }


@router.get("", response_model=list[MatchOut])
def list_matches(db: Session = Depends(get_db)):
    """Return every match in the tournament with team details."""
    matches = db.query(Match).order_by(Match.match_number).all()
    return [_match_to_dict(m) for m in matches]


@router.get("/groups", response_model=list[MatchOut])
def list_group_matches(db: Session = Depends(get_db)):
    """Return only group-stage matches."""
    matches = (
        db.query(Match)
        .filter(Match.round == "group")
        .order_by(Match.match_number)
        .all()
    )
    return [_match_to_dict(m) for m in matches]


@router.get("/knockout", response_model=list[MatchOut])
def list_knockout_matches(db: Session = Depends(get_db)):
    """Return only knockout-stage matches (Round of 32 and beyond)."""
    matches = (
        db.query(Match)
        .filter(Match.round != "group")
        .order_by(Match.match_number)
        .all()
    )
    return [_match_to_dict(m) for m in matches]


@router.get("/{match_id}", response_model=MatchOut)
def get_match(match_id: int, db: Session = Depends(get_db)):
    """Return a single match by its database id."""
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="match_not_found")
    return _match_to_dict(match)
