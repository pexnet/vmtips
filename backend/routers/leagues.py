"""
League router: create, join, list, and view leagues.
"""
import random
import string

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from errors import NotFoundError, ForbiddenError, ConflictError
from models import League, LeagueMember, User
from schemas import LeagueCreate, LeagueJoin, LeagueOut, LeagueDetailOut, LeaguePublicOut
from security import fetch_current_user

router = APIRouter(prefix="/leagues", tags=["leagues"])


def _generate_invite_code(length: int = 6) -> str:
    """Generate a random uppercase alphanumeric invite code."""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


def _league_to_dict(league: League) -> dict:
    """Serialize a League row."""
    return {
        "id": league.id,
        "name": league.name,
        "invite_code": league.invite_code,
        "created_at": league.created_at.isoformat() if league.created_at else None,
        "admin_user_id": league.admin_user_id,
    }


@router.post("", response_model=LeagueOut, status_code=201)
def create_league(
    payload: LeagueCreate,
    current_user: User = Depends(fetch_current_user),
    db: Session = Depends(get_db),
):
    """Create a new league. Current user becomes admin. Invite code auto-generated."""
    code = _generate_invite_code()
    # Ensure uniqueness
    while db.query(League).filter(League.invite_code == code).first():
        code = _generate_invite_code()

    league = League(
        name=payload.name,
        invite_code=code,
        is_public=payload.is_public,
        admin_user_id=current_user.id,
    )
    db.add(league)
    db.commit()
    db.refresh(league)

    # Auto-add creator as member
    member = LeagueMember(league_id=league.id, user_id=current_user.id)
    db.add(member)
    db.commit()

    return _league_to_dict(league)


@router.post("/{league_id}/join", status_code=200)
def join_league(
    league_id: int,
    payload: LeagueJoin,
    current_user: User = Depends(fetch_current_user),
    db: Session = Depends(get_db),
):
    """Join a league using its invite code."""
    league = db.query(League).filter(League.id == league_id).first()
    if not league:
        raise NotFoundError(detail="league_not_found", error_code="league_not_found")

    if league.invite_code != payload.invite_code:
        raise ForbiddenError(detail="invalid_invite_code", error_code="invalid_invite_code")

    # Check if already a member
    existing = (
        db.query(LeagueMember)
        .filter(
            LeagueMember.league_id == league_id,
            LeagueMember.user_id == current_user.id,
        )
        .first()
    )
    if existing:
        raise ConflictError(detail="already_member", error_code="already_member")

    member = LeagueMember(league_id=league_id, user_id=current_user.id)
    db.add(member)
    db.commit()

    return {"joined": True, "league_id": league_id}


@router.get("", response_model=list[LeagueOut])
def list_my_leagues(
    current_user: User = Depends(fetch_current_user),
    db: Session = Depends(get_db),
):
    """List all leagues the current user is a member of."""
    memberships = (
        db.query(LeagueMember)
        .filter(LeagueMember.user_id == current_user.id)
        .all()
    )
    league_ids = [m.league_id for m in memberships]
    leagues = db.query(League).filter(League.id.in_(league_ids)).all()
    return [_league_to_dict(l) for l in leagues]


@router.get("/public", response_model=list[LeaguePublicOut])
def list_public_leagues(db: Session = Depends(get_db)):
    """List all public leagues. No authentication required.
    Returns league name, id, member count, and creation date (no invite_code)."""
    public_leagues = db.query(League).filter(League.is_public == True).all()
    result = []
    for league in public_leagues:
        member_count = (
            db.query(LeagueMember)
            .filter(LeagueMember.league_id == league.id)
            .count()
        )
        result.append({
            "id": league.id,
            "name": league.name,
            "member_count": member_count,
            "created_at": league.created_at.isoformat() if league.created_at else None,
        })
    return result


@router.get("/{league_id}", response_model=LeagueDetailOut)
def get_league(
    league_id: int,
    current_user: User = Depends(fetch_current_user),
    db: Session = Depends(get_db),
):
    """Get league details including member list. Only members can view."""
    league = db.query(League).filter(League.id == league_id).first()
    if not league:
        raise NotFoundError(detail="league_not_found", error_code="league_not_found")

    # Check if user is a member
    is_member = (
        db.query(LeagueMember)
        .filter(
            LeagueMember.league_id == league_id,
            LeagueMember.user_id == current_user.id,
        )
        .first()
    )
    if not is_member:
        raise ForbiddenError(detail="not_a_member", error_code="not_a_member")

    members = (
        db.query(User)
        .join(LeagueMember, User.id == LeagueMember.user_id)
        .filter(LeagueMember.league_id == league_id)
        .all()
    )

    return {
        "id": league.id,
        "name": league.name,
        "invite_code": league.invite_code,
        "created_at": league.created_at.isoformat() if league.created_at else None,
        "admin_user_id": league.admin_user_id,
        "is_admin": league.admin_user_id == current_user.id,
        "members": [
            {
                "id": u.id,
                "display_name": u.display_name,
            }
            for u in members
        ],
    }
