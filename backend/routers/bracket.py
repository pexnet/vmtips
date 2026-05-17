"""
Bracket router: view and generate bracket from group-stage predictions.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from errors import ForbiddenError
from models import LeagueMember
from security import fetch_current_user
from bracket_engine import save_generated_bracket, get_bracket_view

router = APIRouter(prefix="/bracket", tags=["bracket"])


@router.post("/generate")
def generate_bracket(
    league_id: int,
    current_user=Depends(fetch_current_user),
    db: Session = Depends(get_db),
):
    """Generate bracket predictions from the user's group-stage predictions."""
    member = db.query(LeagueMember).filter(
        LeagueMember.league_id == league_id,
        LeagueMember.user_id == current_user.id,
    ).first()
    if not member:
        raise ForbiddenError(detail="not_league_member", error_code="not_league_member")

    result = save_generated_bracket(db, current_user.id, league_id)
    return {"generated": result["created"], "message": "Bracket generated from group predictions"}


@router.get("/view")
def view_bracket(
    league_id: int,
    current_user=Depends(fetch_current_user),
    db: Session = Depends(get_db),
):
    """Get full bracket view with predicted teams, actual teams, and group standings."""
    member = db.query(LeagueMember).filter(
        LeagueMember.league_id == league_id,
        LeagueMember.user_id == current_user.id,
    ).first()
    if not member:
        raise ForbiddenError(detail="not_league_member", error_code="not_league_member")

    return get_bracket_view(db, current_user.id, league_id)
