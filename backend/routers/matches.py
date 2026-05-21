"""
Matches router: list all matches, filter by group/knockout, and fetch single match.
"""
import math
from datetime import timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from errors import NotFoundError
from models import Match
from schemas import MatchOut

router = APIRouter(prefix="/matches", tags=["matches"])


def _match_to_dict(match: Match) -> dict:
    """Serialize a Match ORM row into a dict."""
    home = match.home_team
    away = match.away_team
    match_date = match.match_date
    if match_date and match_date.tzinfo is None:
        match_date = match_date.replace(tzinfo=timezone.utc)
    return {
        "id": match.id,
        "match_number": match.match_number,
        "group": match.group,
        "round": match.round,
        "home_team": {
            "id": home.id,
            "name": home.name,
            "code": home.code,
            "group": home.group,
            "flag_emoji": home.flag_emoji,
        } if home else {
            "id": 0,
            "name": match.home_team_placeholder or "TBD",
            "code": "",
            "group": "",
            "flag_emoji": "❓",
        },
        "away_team": {
            "id": away.id,
            "name": away.name,
            "code": away.code,
            "group": away.group,
            "flag_emoji": away.flag_emoji,
        } if away else {
            "id": 0,
            "name": match.away_team_placeholder or "TBD",
            "code": "",
            "group": "",
            "flag_emoji": "❓",
        },
        "home_goals": match.home_goals,
        "away_goals": match.away_goals,
        "match_date": match_date.isoformat() if match_date else None,
        "status": match.status,
    }


@router.get("")
def list_matches(
    page: Optional[int] = Query(None, ge=1, description="Page number (1-indexed)"),
    per_page: Optional[int] = Query(None, ge=1, le=200, description="Items per page"),
    db: Session = Depends(get_db),
):
    """Return every match in the tournament with team details.
    
    If page and per_page are provided, returns a paginated response.
    Otherwise returns the full list (backward compatible).
    """
    query = db.query(Match).order_by(Match.match_number)
    total = query.count()

    # If no pagination params given, return full list (backward compatible)
    if page is None or per_page is None:
        matches = query.all()
        return [_match_to_dict(m) for m in matches]

    # Paginated response
    offset = (page - 1) * per_page
    matches = query.offset(offset).limit(per_page).all()
    total_pages = math.ceil(total / per_page) if per_page > 0 else 1
    return {
        "items": [_match_to_dict(m) for m in matches],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
    }


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
        raise NotFoundError(detail="match_not_found", error_code="match_not_found")
    return _match_to_dict(match)
