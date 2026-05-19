"""
Predictions router: save batch predictions, bracket predictions, and tournament bonuses.
Phase-gated: group stage predictions locked after group deadline, knockout predictions
only allowed during knockout phase.
All predictions are scoped per league (league_id required on save, optional on list).
"""
import math
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from errors import ForbiddenError, ValidationError
from models import Prediction, Match, TournamentBonus, BracketPrediction, TournamentPhase, LeagueMember
from schemas import PredictionBatchCreate, TournamentBonusCreate, BracketPredictionBatch
from routers.auth import fetch_current_user
from bracket_engine import save_generated_bracket
from scoring import BRACKET_ROUND_POINTS

router = APIRouter(prefix="/predictions", tags=["predictions"])
logger = logging.getLogger("vmtips")


def _get_phase(db: Session) -> TournamentPhase:
    """Get or create the tournament phase row."""
    phase = db.query(TournamentPhase).first()
    if not phase:
        phase = TournamentPhase(phase="group_open")
        db.add(phase)
        db.commit()
        db.flush()
    return phase


def _resolve_league_id(db: Session, user_id: int, requested_league_id: int | None) -> int:
    """Resolve optional league_id to the user's first joined league."""
    if requested_league_id is not None:
        return requested_league_id

    membership = (
        db.query(LeagueMember)
        .filter(LeagueMember.user_id == user_id)
        .order_by(LeagueMember.joined_at.desc(), LeagueMember.id.desc())
        .first()
    )
    if not membership:
        raise ForbiddenError(detail="not_league_member", error_code="not_league_member")
    return membership.league_id


def _can_predict_group(phase: TournamentPhase) -> bool:
    """Check if group stage predictions are allowed."""
    if phase.phase == "group_open":
        # If no deadline set, group is always open
        if phase.group_deadline is None:
            return True
        # If deadline set, check if it's passed
        deadline = phase.group_deadline
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) < deadline
    return False


def _can_predict_bracket(phase: TournamentPhase) -> bool:
    """Check if knockout bracket predictions are allowed."""
    if phase.phase == "knockout_open":
        return True
    if phase.phase == "group_closed":
        # Bracket opens when group stage is closed (may have a scheduled open time)
        if phase.knockout_opens_at is not None:
            opens = phase.knockout_opens_at
            if opens.tzinfo is None:
                opens = opens.replace(tzinfo=timezone.utc)
            return datetime.now(timezone.utc) >= opens
        return False  # Not yet open
    return False


def _pred_to_dict(pred: Prediction) -> dict:
    """Serialize a Prediction ORM row."""
    return {
        "id": pred.id,
        "league_id": pred.league_id,
        "match_id": pred.match_id,
        "home_goals": pred.home_goals,
        "away_goals": pred.away_goals,
        "created_at": pred.created_at,
        "updated_at": pred.updated_at,
        "match": {
            "match_number": pred.match.match_number,
            "round": pred.match.round,
            "group": pred.match.group,
            "home_team": {"name": pred.match.home_team.name, "flag_emoji": pred.match.home_team.flag_emoji},
            "away_team": {"name": pred.match.away_team.name, "flag_emoji": pred.match.away_team.flag_emoji},
        },
    }


@router.get("")
def list_predictions(
    league_id: Optional[int] = Query(None, description="Filter predictions by league"),
    page: Optional[int] = Query(None, ge=1, description="Page number (1-indexed)"),
    per_page: Optional[int] = Query(None, ge=1, le=200, description="Items per page"),
    current_user=Depends(fetch_current_user),
    db: Session = Depends(get_db),
):
    """Return predictions for the authenticated user, optionally filtered by league."""
    query = db.query(Prediction).filter(Prediction.user_id == current_user.id)
    if league_id is not None:
        query = query.filter(Prediction.league_id == league_id)
    total = query.count()

    if page is None or per_page is None:
        preds = query.all()
        return [_pred_to_dict(p) for p in preds]

    offset = (page - 1) * per_page
    preds = query.offset(offset).limit(per_page).all()
    total_pages = math.ceil(total / per_page) if per_page > 0 else 1
    return {
        "items": [_pred_to_dict(p) for p in preds],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
    }


@router.post("/batch")
def save_batch(
    payload: PredictionBatchCreate,
    current_user=Depends(fetch_current_user),
    db: Session = Depends(get_db),
):
    """Upsert a batch of match predictions for the authenticated user in a specific league.

    Group stage: Only allowed when phase is 'group_open' (or no phase set).
    Knockout matches: Only allowed when phase is 'knockout_open'.
    """
    league_id = _resolve_league_id(db, current_user.id, payload.league_id)

    # Verify user is member of the league
    member = db.query(LeagueMember).filter(
        LeagueMember.league_id == league_id,
        LeagueMember.user_id == current_user.id
    ).first()
    if not member:
        raise ForbiddenError(detail="not_league_member", error_code="not_league_member")

    phase = _get_phase(db)
    match_ids = {p.match_id for p in payload.predictions}
    matches = {m.id: m for m in db.query(Match).filter(Match.id.in_(match_ids)).all()}
    missing = match_ids - set(matches.keys())
    if missing:
        raise ValidationError(detail="invalid_match_ids", error_code="invalid_match_ids")

    now = datetime.now(timezone.utc)

    # Validate ALL predictions before making any changes (atomicity)
    for pred_create in payload.predictions:
        match = matches[pred_create.match_id]

        # Phase-based validation
        if match.round == "group":
            if not _can_predict_group(phase):
                raise ForbiddenError(detail="group_predictions_locked", error_code="group_predictions_locked")
        else:
            # Knockout matches
            if not _can_predict_bracket(phase) and phase.phase != "group_open":
                raise ForbiddenError(detail="knockout_predictions_locked", error_code="knockout_predictions_locked")

        # Match deadline check
        kickoff = match.match_date
        if kickoff is not None and kickoff.tzinfo is None:
            kickoff = kickoff.replace(tzinfo=timezone.utc)
        if kickoff is not None and kickoff <= now:
            raise ForbiddenError(detail="match_locked", error_code="match_locked")

    # All validated — now upsert
    saved = 0
    try:
        for pred_create in payload.predictions:
            existing = (
                db.query(Prediction)
                .filter(
                    Prediction.user_id == current_user.id,
                    Prediction.match_id == pred_create.match_id,
                    Prediction.league_id == league_id,
                )
                .first()
            )
            if existing:
                existing.home_goals = pred_create.home_goals
                existing.away_goals = pred_create.away_goals
            else:
                db.add(
                    Prediction(
                        user_id=current_user.id,
                        league_id=league_id,
                        match_id=pred_create.match_id,
                        home_goals=pred_create.home_goals,
                        away_goals=pred_create.away_goals,
                    )
                )
            saved += 1
        db.commit()

        # Auto-generate bracket from group predictions if all group matches are tipped
        try:
            group_pred_count = (
                db.query(Prediction)
                .join(Match)
                .filter(
                    Prediction.user_id == current_user.id,
                    Prediction.league_id == league_id,
                    Match.round == "group",
                )
                .count()
            )
            if group_pred_count >= 72:
                save_generated_bracket(db, current_user.id, league_id)
        except Exception:
            logger.exception(
                "Failed to auto-generate bracket for user_id=%s league_id=%s",
                current_user.id,
                league_id,
            )
    except Exception:
        db.rollback()
        raise

    return {"saved": saved}


@router.get("/tournament")
def get_tournament_bonuses(
    league_id: Optional[int] = Query(None, description="Filter by league"),
    current_user=Depends(fetch_current_user), db: Session = Depends(get_db)
):
    """Return the authenticated user's tournament bonus predictions, optionally per league."""
    query = db.query(TournamentBonus).filter(TournamentBonus.user_id == current_user.id)
    if league_id is not None:
        query = query.filter(TournamentBonus.league_id == league_id)
    bonus = query.first()
    if not bonus:
        return None
    return {
        "winner_team_id": bonus.winner_team_id,
        "top_scorer_name": bonus.top_scorer_name,
        "bronze_winner_team_id": bonus.bronze_winner_team_id,
        "most_goals_team_id": bonus.most_goals_team_id,
        "most_conceded_team_id": bonus.most_conceded_team_id,
        "custom_bonus_1": bonus.custom_bonus_1,
        "custom_bonus_2": bonus.custom_bonus_2,
    }


@router.post("/tournament")
def save_tournament_bonuses(
    payload: TournamentBonusCreate,
    current_user=Depends(fetch_current_user),
    db: Session = Depends(get_db),
):
    """Save or update the authenticated user's tournament bonus predictions for a league.

    Only allowed during group_open or knockout_open phase (before deadlines).
    """
    phase = _get_phase(db)
    if phase.phase in ("group_closed", "knockout_closed"):
        raise ForbiddenError(detail="bonus_predictions_locked", error_code="bonus_predictions_locked")

    league_id = _resolve_league_id(db, current_user.id, payload.league_id)

    # Verify user is member of the league
    member = db.query(LeagueMember).filter(
        LeagueMember.league_id == league_id,
        LeagueMember.user_id == current_user.id
    ).first()
    if not member:
        raise ForbiddenError(detail="not_league_member", error_code="not_league_member")

    bonus = (
        db.query(TournamentBonus)
        .filter(
            TournamentBonus.user_id == current_user.id,
            TournamentBonus.league_id == league_id,
        )
        .first()
    )
    if bonus:
        if payload.winner_team_id is not None:
            bonus.winner_team_id = payload.winner_team_id
        if payload.top_scorer_name is not None:
            bonus.top_scorer_name = payload.top_scorer_name
        if payload.bronze_winner_team_id is not None:
            bonus.bronze_winner_team_id = payload.bronze_winner_team_id
        if payload.most_goals_team_id is not None:
            bonus.most_goals_team_id = payload.most_goals_team_id
        if payload.most_conceded_team_id is not None:
            bonus.most_conceded_team_id = payload.most_conceded_team_id
        if payload.custom_bonus_1 is not None:
            bonus.custom_bonus_1 = payload.custom_bonus_1
        if payload.custom_bonus_2 is not None:
            bonus.custom_bonus_2 = payload.custom_bonus_2
    else:
        bonus = TournamentBonus(
            user_id=current_user.id,
            league_id=league_id,
            winner_team_id=payload.winner_team_id,
            top_scorer_name=payload.top_scorer_name,
            bronze_winner_team_id=payload.bronze_winner_team_id,
            most_goals_team_id=payload.most_goals_team_id,
            most_conceded_team_id=payload.most_conceded_team_id,
            custom_bonus_1=payload.custom_bonus_1,
            custom_bonus_2=payload.custom_bonus_2,
        )
        db.add(bonus)
    db.commit()
    return {"saved": True}


# ── Bracket Predictions ─────────────────────────────────────────


@router.get("/bracket")
def get_bracket_predictions(
    league_id: Optional[int] = Query(None, description="Filter by league"),
    current_user=Depends(fetch_current_user), db: Session = Depends(get_db)
):
    """Return the authenticated user's bracket (knockout) predictions, optionally per league."""
    query = db.query(BracketPrediction).filter(BracketPrediction.user_id == current_user.id)
    if league_id is not None:
        query = query.filter(BracketPrediction.league_id == league_id)
    entries = query.all()
    return [
        {
            "id": e.id,
            "team_id": e.team_id,
            "round": e.round,
            "source": e.source,
            "created_at": e.created_at,
            "updated_at": e.updated_at,
        }
        for e in entries
    ]


@router.post("/bracket")
def save_bracket_predictions(
    payload: BracketPredictionBatch,
    current_user=Depends(fetch_current_user),
    db: Session = Depends(get_db),
):
    """
    Save or update bracket predictions for the authenticated user in a league.

    Only allowed during knockout_open phase.
    Each entry places a team in a specific knockout round.
    """
    phase = _get_phase(db)
    if not _can_predict_bracket(phase):
        raise ForbiddenError(detail="bracket_predictions_locked", error_code="bracket_predictions_locked")

    league_id = _resolve_league_id(db, current_user.id, payload.league_id)

    # Verify user is member of the league
    member = db.query(LeagueMember).filter(
        LeagueMember.league_id == league_id,
        LeagueMember.user_id == current_user.id
    ).first()
    if not member:
        raise ForbiddenError(detail="not_league_member", error_code="not_league_member")

    valid_rounds = set(BRACKET_ROUND_POINTS.keys())
    for entry in payload.entries:
        if entry.round not in valid_rounds:
            raise ValidationError(
                detail=f"invalid_round: {entry.round}",
                error_code="invalid_round",
            )

    saved = 0
    for entry in payload.entries:
        existing = (
            db.query(BracketPrediction)
            .filter(
                BracketPrediction.user_id == current_user.id,
                BracketPrediction.league_id == league_id,
                BracketPrediction.team_id == entry.team_id,
                BracketPrediction.round == entry.round,
            )
            .first()
        )
        if existing:
            existing.source = "knockout_prediction"
        else:
            db.add(BracketPrediction(
                user_id=current_user.id,
                league_id=league_id,
                team_id=entry.team_id,
                round=entry.round,
                source="knockout_prediction",
            ))
        saved += 1

    db.commit()
    return {"saved": saved}
