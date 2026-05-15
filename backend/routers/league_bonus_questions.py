"""
League Bonus Questions router: CRUD for bonus questions within a league.

Only the league admin can create, update, or delete bonus questions.
Any league member can list and view bonus questions.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from errors import NotFoundError, ForbiddenError, ValidationError
from models import League, LeagueBonusQuestion, LeagueMember, User
from schemas import (
    LeagueBonusQuestionCreate,
    LeagueBonusQuestionUpdate,
    LeagueBonusQuestionOut,
)
from security import fetch_current_user

router = APIRouter(prefix="/leagues", tags=["league-bonus-questions"])


def _verify_admin(league: League, user: User):
    """Raise ForbiddenError if the user is not the league admin."""
    if league.admin_user_id != user.id:
        raise ForbiddenError(
            detail="not_league_admin",
            error_code="not_league_admin",
        )


def _verify_member(league_id: int, user: User, db: Session):
    """Raise ForbiddenError if the user is not a member of the league."""
    is_member = (
        db.query(LeagueMember)
        .filter(
            LeagueMember.league_id == league_id,
            LeagueMember.user_id == user.id,
        )
        .first()
    )
    if not is_member:
        raise ForbiddenError(detail="not_a_member", error_code="not_a_member")


def _question_to_dict(q: LeagueBonusQuestion) -> dict:
    """Serialize a LeagueBonusQuestion row."""
    return {
        "id": q.id,
        "league_id": q.league_id,
        "question_text": q.question_text,
        "points_value": q.points_value,
        "answer": q.answer,
        "created_at": q.created_at.isoformat() if q.created_at else None,
    }


@router.post(
    "/{league_id}/bonus-questions",
    response_model=LeagueBonusQuestionOut,
    status_code=201,
)
def create_bonus_question(
    league_id: int,
    payload: LeagueBonusQuestionCreate,
    current_user: User = Depends(fetch_current_user),
    db: Session = Depends(get_db),
):
    """Create a new bonus question in a league. Only the league admin can do this."""
    league = db.query(League).filter(League.id == league_id).first()
    if not league:
        raise NotFoundError(detail="league_not_found", error_code="league_not_found")

    _verify_admin(league, current_user)

    question = LeagueBonusQuestion(
        league_id=league_id,
        question_text=payload.question_text,
        points_value=payload.points_value,
    )
    db.add(question)
    db.commit()
    db.refresh(question)

    return _question_to_dict(question)


@router.get(
    "/{league_id}/bonus-questions",
    response_model=list[LeagueBonusQuestionOut],
)
def list_bonus_questions(
    league_id: int,
    current_user: User = Depends(fetch_current_user),
    db: Session = Depends(get_db),
):
    """List all bonus questions for a league. Only members can view."""
    league = db.query(League).filter(League.id == league_id).first()
    if not league:
        raise NotFoundError(detail="league_not_found", error_code="league_not_found")

    _verify_member(league_id, current_user, db)

    questions = (
        db.query(LeagueBonusQuestion)
        .filter(LeagueBonusQuestion.league_id == league_id)
        .order_by(LeagueBonusQuestion.id)
        .all()
    )
    return [_question_to_dict(q) for q in questions]


@router.get(
    "/{league_id}/bonus-questions/{question_id}",
    response_model=LeagueBonusQuestionOut,
)
def get_bonus_question(
    league_id: int,
    question_id: int,
    current_user: User = Depends(fetch_current_user),
    db: Session = Depends(get_db),
):
    """Get a single bonus question. Only members can view."""
    league = db.query(League).filter(League.id == league_id).first()
    if not league:
        raise NotFoundError(detail="league_not_found", error_code="league_not_found")

    _verify_member(league_id, current_user, db)

    question = (
        db.query(LeagueBonusQuestion)
        .filter(
            LeagueBonusQuestion.id == question_id,
            LeagueBonusQuestion.league_id == league_id,
        )
        .first()
    )
    if not question:
        raise NotFoundError(
            detail="bonus_question_not_found",
            error_code="bonus_question_not_found",
        )

    return _question_to_dict(question)


@router.patch(
    "/{league_id}/bonus-questions/{question_id}",
    response_model=LeagueBonusQuestionOut,
)
def update_bonus_question(
    league_id: int,
    question_id: int,
    payload: LeagueBonusQuestionUpdate,
    current_user: User = Depends(fetch_current_user),
    db: Session = Depends(get_db),
):
    """Update a bonus question. Only the league admin can do this."""
    league = db.query(League).filter(League.id == league_id).first()
    if not league:
        raise NotFoundError(detail="league_not_found", error_code="league_not_found")

    _verify_admin(league, current_user)

    question = (
        db.query(LeagueBonusQuestion)
        .filter(
            LeagueBonusQuestion.id == question_id,
            LeagueBonusQuestion.league_id == league_id,
        )
        .first()
    )
    if not question:
        raise NotFoundError(
            detail="bonus_question_not_found",
            error_code="bonus_question_not_found",
        )

    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise ValidationError(
            detail="no_fields_to_update",
            error_code="no_fields_to_update",
        )

    for field, value in update_data.items():
        setattr(question, field, value)

    db.commit()
    db.refresh(question)

    return _question_to_dict(question)


@router.delete(
    "/{league_id}/bonus-questions/{question_id}",
    status_code=200,
)
def delete_bonus_question(
    league_id: int,
    question_id: int,
    current_user: User = Depends(fetch_current_user),
    db: Session = Depends(get_db),
):
    """Delete a bonus question. Only the league admin can do this."""
    league = db.query(League).filter(League.id == league_id).first()
    if not league:
        raise NotFoundError(detail="league_not_found", error_code="league_not_found")

    _verify_admin(league, current_user)

    question = (
        db.query(LeagueBonusQuestion)
        .filter(
            LeagueBonusQuestion.id == question_id,
            LeagueBonusQuestion.league_id == league_id,
        )
        .first()
    )
    if not question:
        raise NotFoundError(
            detail="bonus_question_not_found",
            error_code="bonus_question_not_found",
        )

    db.delete(question)
    db.commit()

    return {"deleted": True, "question_id": question_id}