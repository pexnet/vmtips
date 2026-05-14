"""
Predictions router: save batch predictions and tournament bonuses.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Prediction, Match, TournamentBonus
from schemas import PredictionBatchCreate, TournamentBonusCreate
from routers.auth import fetch_current_user

router = APIRouter(prefix="/predictions", tags=["predictions"])


def _pred_to_dict(pred: Prediction) -> dict:
    """Serialize a Prediction ORM row."""
    return {
        "id": pred.id,
        "match_id": pred.match_id,
        "home_goals": pred.home_goals,
        "away_goals": pred.away_goals,
        "created_at": pred.created_at.isoformat() if pred.created_at else None,
        "updated_at": pred.updated_at.isoformat() if pred.updated_at else None,
    }


@router.get("")
def list_predictions(current_user=Depends(fetch_current_user), db: Session = Depends(get_db)):
    """Return all predictions for the authenticated user."""
    preds = db.query(Prediction).filter(Prediction.user_id == current_user.id).all()
    return [_pred_to_dict(p) for p in preds]


@router.post("/batch")
def save_batch(
    payload: PredictionBatchCreate,
    current_user=Depends(fetch_current_user),
    db: Session = Depends(get_db),
):
    """Upsert a batch of match predictions for the authenticated user."""
    match_ids = {p.match_id for p in payload.predictions}
    existing_matches = {m.id for m in db.query(Match).filter(Match.id.in_(match_ids)).all()}
    missing = match_ids - existing_matches
    if missing:
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_match_ids", "ids": list(missing)},
        )

    saved = 0
    for pred_create in payload.predictions:
        existing = (
            db.query(Prediction)
            .filter(
                Prediction.user_id == current_user.id,
                Prediction.match_id == pred_create.match_id,
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
                    match_id=pred_create.match_id,
                    home_goals=pred_create.home_goals,
                    away_goals=pred_create.away_goals,
                )
            )
        saved += 1

    db.commit()
    return {"saved": saved}


@router.get("/tournament")
def get_tournament_bonuses(
    current_user=Depends(fetch_current_user), db: Session = Depends(get_db)
):
    """Return the authenticated user's tournament bonus predictions."""
    bonus = (
        db.query(TournamentBonus)
        .filter(TournamentBonus.user_id == current_user.id)
        .first()
    )
    if not bonus:
        return None
    return {
        "winner_team_id": bonus.winner_team_id,
        "top_scorer_name": bonus.top_scorer_name,
        "top_assist_name": bonus.top_assist_name,
        "total_goals": bonus.total_goals,
    }


@router.post("/tournament")
def save_tournament_bonuses(
    payload: TournamentBonusCreate,
    current_user=Depends(fetch_current_user),
    db: Session = Depends(get_db),
):
    """Save or update the authenticated user's tournament bonus predictions."""
    bonus = (
        db.query(TournamentBonus)
        .filter(TournamentBonus.user_id == current_user.id)
        .first()
    )
    if bonus:
        if payload.winner_team_id is not None:
            bonus.winner_team_id = payload.winner_team_id
        if payload.top_scorer_name is not None:
            bonus.top_scorer_name = payload.top_scorer_name
        if payload.top_assist_name is not None:
            bonus.top_assist_name = payload.top_assist_name
        if payload.total_goals is not None:
            bonus.total_goals = payload.total_goals
    else:
        bonus = TournamentBonus(
            user_id=current_user.id,
            winner_team_id=payload.winner_team_id,
            top_scorer_name=payload.top_scorer_name,
            top_assist_name=payload.top_assist_name,
            total_goals=payload.total_goals,
        )
        db.add(bonus)
    db.commit()
    return {"saved": True}
