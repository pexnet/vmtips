"""
League Bonus Questions router: CRUD for bonus questions within a league.

Only the league admin can create, update, or delete bonus questions.
Any league member can list and view bonus questions.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from errors import NotFoundError, ForbiddenError, ValidationError
from models import League, LeagueBonusAnswer, LeagueBonusQuestion, LeagueMember, TournamentPhase, User
from schemas import (
    LeagueBonusAnswerCreate,
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


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _is_locked(
    phase: TournamentPhase | None,
    question: LeagueBonusQuestion | None = None,
) -> bool:
    """Return whether the tournament or per-question deadline has passed."""
    now = datetime.now(timezone.utc)
    tournament_lock = _as_utc(
        phase.extra_questions_lock_at if phase else None
    )
    question_lock = _as_utc(question.closed_at if question else None)
    return bool(
        (tournament_lock is not None and now >= tournament_lock)
        or (question_lock is not None and now >= question_lock)
    )


def _ensure_unlocked(
    db: Session,
    question: LeagueBonusQuestion | None = None,
) -> None:
    phase = db.query(TournamentPhase).first()
    if _is_locked(phase, question):
        raise ForbiddenError(
            detail="extra_questions_locked",
            error_code="extra_questions_locked",
        )


def _question_to_dict(
    q: LeagueBonusQuestion,
    phase: TournamentPhase | None,
    include_answer: bool = True,
) -> dict:
    """Serialize a LeagueBonusQuestion row."""
    return {
        "id": q.id,
        "league_id": q.league_id,
        "question_text": q.question_text,
        "points_value": q.points_value,
        "answer": q.answer if include_answer else None,
        "closed_at": q.closed_at.isoformat() if q.closed_at else None,
        "is_closed": _is_locked(phase, q),
        "created_at": q.created_at.isoformat() if q.created_at else None,
    }


def _score_answer(question: LeagueBonusQuestion, answer_text: str) -> tuple[bool | None, int | None]:
    """Score a member answer if the admin answer has been set."""
    if question.answer is None or not question.answer.strip():
        return None, None
    is_correct = answer_text.strip().lower() == question.answer.strip().lower()
    return is_correct, question.points_value if is_correct else 0


def _answers_are_open(db: Session) -> bool:
    """League bonus answers share the group-stage prediction deadline."""
    phase = db.query(TournamentPhase).first()
    if phase is None:
        return True
    if phase.phase != "group_open":
        return False
    if phase.group_deadline is None:
        return True
    deadline = phase.group_deadline
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) < deadline


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
    _ensure_unlocked(db)

    question = LeagueBonusQuestion(
        league_id=league_id,
        question_text=payload.question_text,
        points_value=payload.points_value,
        answer=payload.answer,
        closed_at=payload.closed_at,
    )
    db.add(question)
    db.commit()
    db.refresh(question)

    return _question_to_dict(question, db.query(TournamentPhase).first())


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
    include_answer = league.admin_user_id == current_user.id
    phase = db.query(TournamentPhase).first()
    return [
        _question_to_dict(q, phase, include_answer=include_answer)
        for q in questions
    ]


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

    include_answer = league.admin_user_id == current_user.id
    return _question_to_dict(
        question,
        db.query(TournamentPhase).first(),
        include_answer=include_answer,
    )


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

    if "answer" in update_data:
        for member_answer in question.answers:
            is_correct, points_awarded = _score_answer(question, member_answer.answer_text)
            member_answer.is_correct = is_correct
            member_answer.points_awarded = points_awarded

    db.commit()
    db.refresh(question)

    return _question_to_dict(question, db.query(TournamentPhase).first())


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


@router.put(
    "/{league_id}/bonus-questions/{question_id}/answer",
    status_code=200,
)
def save_bonus_answer(
    league_id: int,
    question_id: int,
    payload: LeagueBonusAnswerCreate,
    current_user: User = Depends(fetch_current_user),
    db: Session = Depends(get_db),
):
    """Save or update the current member's answer for a league bonus question."""
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

    _ensure_unlocked(db, question)

    if not _answers_are_open(db):
        raise ForbiddenError(
            detail="bonus_answers_locked",
            error_code="bonus_answers_locked",
        )

    answer_text = payload.answer_text.strip()
    is_correct, points_awarded = _score_answer(question, answer_text)

    answer = (
        db.query(LeagueBonusAnswer)
        .filter(
            LeagueBonusAnswer.question_id == question_id,
            LeagueBonusAnswer.user_id == current_user.id,
        )
        .first()
    )
    if answer:
        answer.answer_text = answer_text
        answer.is_correct = is_correct
        answer.points_awarded = points_awarded
    else:
        answer = LeagueBonusAnswer(
            question_id=question_id,
            user_id=current_user.id,
            answer_text=answer_text,
            is_correct=is_correct,
            points_awarded=points_awarded,
        )
        db.add(answer)

    db.commit()
    return {
        "question_id": question_id,
        "answer_text": answer.answer_text,
        "is_correct": None,
        "points_awarded": None,
    }


@router.get(
    "/{league_id}/bonus-questions/{question_id}/answer",
    status_code=200,
)
def get_my_bonus_answer(
    league_id: int,
    question_id: int,
    current_user: User = Depends(fetch_current_user),
    db: Session = Depends(get_db),
):
    """Return the current member's answer for a league bonus question."""
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

    answer = (
        db.query(LeagueBonusAnswer)
        .filter(
            LeagueBonusAnswer.question_id == question_id,
            LeagueBonusAnswer.user_id == current_user.id,
        )
        .first()
    )
    if not answer:
        return {
            "question_id": question_id,
            "answer_text": None,
            "is_correct": None,
            "points_awarded": None,
        }
    answers_open = _answers_are_open(db)
    return {
        "question_id": question_id,
        "answer_text": answer.answer_text,
        "is_correct": None if answers_open else answer.is_correct,
        "points_awarded": None if answers_open else answer.points_awarded,
    }
