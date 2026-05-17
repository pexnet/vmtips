"""
Admin router: protected endpoints for manual result entry, sync, scoring,
group standings, knockout advancement, and phase management.
All endpoints require admin status.
"""
import os
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from errors import NotFoundError, ForbiddenError
from models import (
    Match, User, Prediction, Score, BracketPrediction, TournamentResult,
    TournamentBonus, TournamentPhase, GroupStanding, KnockoutAdvancement, Team,
    League, LeagueMember,
)
from schemas import (
    MatchResultUpdate, TournamentResultUpdate, PhaseUpdate,
    KnockoutAdvancementCreate, GroupStandingOut, PhaseOut,
    KnockoutAdvancementOut, ScoreDetailOut,
)
from security import fetch_current_user
from scoring import (
    calculate_match_points, calculate_bracket_points, calculate_tournament_bonus_points,
    BRACKET_ROUND_POINTS, BONUS_POINTS,
)

router = APIRouter(prefix="/admin", tags=["admin"])


def _is_admin(current_user: User) -> bool:
    """Check if current user is the designated admin."""
    if current_user.is_admin:
        return True
    admin_id_env = os.environ.get("ADMIN_USER_ID")
    if admin_id_env:
        return str(current_user.id) == admin_id_env
    return current_user.id == 1


def require_admin(current_user: User = Depends(fetch_current_user)) -> User:
    """Dependency: raises 403 if user is not admin."""
    if not _is_admin(current_user):
        raise ForbiddenError(detail="admin_only", error_code="admin_only")
    return current_user


# ═══════════════════════════════════════════════════════════════
# Tournament results (bonus answers)
# ═══════════════════════════════════════════════════════════════

@router.get("/tournament-result")
def get_tournament_result(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get the currently set actual tournament results."""
    result = db.query(TournamentResult).first()
    if not result:
        return {
            "winner_team_id": None,
            "top_scorer_name": None,
            "bronze_winner_team_id": None,
            "most_goals_team_id": None,
            "most_conceded_team_id": None,
            "custom_bonus_1_answer": None,
            "custom_bonus_2_answer": None,
            "updated_at": None,
        }
    return {
        "winner_team_id": result.winner_team_id,
        "top_scorer_name": result.top_scorer_name,
        "bronze_winner_team_id": result.bronze_winner_team_id,
        "most_goals_team_id": result.most_goals_team_id,
        "most_conceded_team_id": result.most_conceded_team_id,
        "custom_bonus_1_answer": result.custom_bonus_1_answer,
        "custom_bonus_2_answer": result.custom_bonus_2_answer,
        "updated_at": result.updated_at.isoformat() if result.updated_at else None,
    }


@router.post("/tournament-result")
def set_tournament_result(
    payload: TournamentResultUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Set the actual tournament results (for bonus scoring). Admin only."""
    result = db.query(TournamentResult).first()
    update_fields = {
        "winner_team_id": payload.winner_team_id,
        "top_scorer_name": payload.top_scorer_name,
        "bronze_winner_team_id": payload.bronze_winner_team_id,
        "most_goals_team_id": payload.most_goals_team_id,
        "most_conceded_team_id": payload.most_conceded_team_id,
        "custom_bonus_1_answer": payload.custom_bonus_1_answer,
        "custom_bonus_2_answer": payload.custom_bonus_2_answer,
    }

    if result:
        for field, value in update_fields.items():
            if value is not None:
                setattr(result, field, value)
    else:
        # Filter out None values for creation
        create_fields = {k: v for k, v in update_fields.items() if v is not None}
        result = TournamentResult(**create_fields)
        db.add(result)
    db.commit()
    return {"saved": True}


# ═══════════════════════════════════════════════════════════════
# Match results
# ═══════════════════════════════════════════════════════════════

@router.post("/matches/{match_id}/result")
def set_match_result(
    match_id: int,
    payload: MatchResultUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Manually set the result for a specific match. Also triggers knockout team resolution for group matches."""
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise NotFoundError(detail="match_not_found", error_code="match_not_found")

    match.home_goals = payload.home_goals
    match.away_goals = payload.away_goals
    match.status = "finished"
    db.commit()

    return {
        "match_id": match_id,
        "result": f"{payload.home_goals}-{payload.away_goals}",
        "status": "finished",
    }


@router.post("/sync-results")
def sync_results(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Trigger a sync of match results from external API."""
    from sync_service import sync_match_results, SyncError

    try:
        result = sync_match_results(db)
    except SyncError as exc:
        return {
            "synced": False,
            "message": str(exc),
            "updated": 0,
            "total_finished": 0,
            "errors": [str(exc)],
        }

    return result


@router.get("/sync-config")
def get_sync_config(admin: User = Depends(require_admin)):
    """Return current sync configuration (read-only for admin)."""
    return {
        "source": settings.sync_source,
        "auto_sync_enabled": settings.auto_sync_enabled,
        "auto_sync_interval_minutes": settings.auto_sync_interval_minutes,
        "world_cup_json_url": settings.world_cup_json_url,
        "openfootball_url": settings.openfootball_url,
    }


class SyncConfigUpdate(BaseModel):
    source: str | None = None
    auto_sync_enabled: bool | None = None
    auto_sync_interval_minutes: int | None = None


@router.post("/sync-config")
def update_sync_config(
    payload: SyncConfigUpdate,
    admin: User = Depends(require_admin),
):
    """Update sync configuration. Admin only. Requires restart to take full effect."""
    if payload.source is not None:
        if payload.source not in ("worldcupjson", "openfootball"):
            raise HTTPException(status_code=422, detail="source must be 'worldcupjson' or 'openfootball'")
        settings.sync_source = payload.source
    if payload.auto_sync_enabled is not None:
        settings.auto_sync_enabled = payload.auto_sync_enabled
    if payload.auto_sync_interval_minutes is not None:
        if payload.auto_sync_interval_minutes < 1:
            raise HTTPException(status_code=422, detail="interval must be >= 1")
        settings.auto_sync_interval_minutes = payload.auto_sync_interval_minutes

    return {
        "saved": True,
        "source": settings.sync_source,
        "auto_sync_enabled": settings.auto_sync_enabled,
        "auto_sync_interval_minutes": settings.auto_sync_interval_minutes,
    }


# ═══════════════════════════════════════════════════════════════
# Score recalculation
# ═══════════════════════════════════════════════════════════════

@router.post("/scores/recalculate")
def recalculate_scores(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Recalculate and update cached total scores for all users.

    Computes:
      - match_points: from match prediction scoring (outcome 3p + correct home/away 2p each, max 7p)
      - bracket_points: from knockout bracket team placement scoring
      - tournament_bonus_points: from tournament bonus predictions (Excel scoring)
      - league_bonus_points: unchanged here (managed per league)

    Then sets total_points = match_points + bracket_points + tournament_bonus_points + league_bonus_points
    """
    from scoring import calculate_tournament_bonus_points

    # ── 1. Match-result points ──────────────────────────────────────
    finished_matches = db.query(Match).filter(Match.status == "finished").all()

    user_match_points = {}
    for match in finished_matches:
        predictions = db.query(Prediction).filter(Prediction.match_id == match.id).all()
        for pred in predictions:
            if pred.home_goals is None or pred.away_goals is None:
                continue
            pts = calculate_match_points(
                pred.home_goals,
                pred.away_goals,
                match.home_goals,
                match.away_goals,
            )["points"]
            user_match_points[pred.user_id] = user_match_points.get(pred.user_id, 0) + pts

    # ── 2. Bracket points ───────────────────────────────────────────
    actual_advancements = _build_actual_advancements(db)

    bracket_preds = db.query(BracketPrediction).all()
    user_bracket_points = {}
    for bp in bracket_preds:
        key = (bp.team_id, bp.round)
        if key in actual_advancements:
            round_pts = BRACKET_ROUND_POINTS.get(bp.round, 0)
            user_bracket_points[bp.user_id] = user_bracket_points.get(bp.user_id, 0) + round_pts

    # ── 3. Tournament bonus points ──────────────────────────────────
    bonuses = db.query(TournamentBonus).all()
    actual_result = db.query(TournamentResult).first()
    actual_winner_id = actual_result.winner_team_id if actual_result else None
    actual_top_scorer = actual_result.top_scorer_name if actual_result else None
    actual_bronze_winner_id = actual_result.bronze_winner_team_id if actual_result else None
    actual_most_goals_team_id = actual_result.most_goals_team_id if actual_result else None
    actual_most_conceded_team_id = actual_result.most_conceded_team_id if actual_result else None
    actual_custom_bonus_1 = actual_result.custom_bonus_1_answer if actual_result else None
    actual_custom_bonus_2 = actual_result.custom_bonus_2_answer if actual_result else None

    user_bonus_points = {}
    for bonus in bonuses:
        result = calculate_tournament_bonus_points(
            pred_winner_id=bonus.winner_team_id,
            actual_winner_id=actual_winner_id,
            pred_top_scorer=bonus.top_scorer_name,
            actual_top_scorer=actual_top_scorer,
            pred_bronze_winner_id=bonus.bronze_winner_team_id,
            actual_bronze_winner_id=actual_bronze_winner_id,
            pred_most_goals_team_id=bonus.most_goals_team_id,
            actual_most_goals_team_id=actual_most_goals_team_id,
            pred_most_conceded_team_id=bonus.most_conceded_team_id,
            actual_most_conceded_team_id=actual_most_conceded_team_id,
            pred_custom_bonus_1=bonus.custom_bonus_1,
            actual_custom_bonus_1=actual_custom_bonus_1,
            pred_custom_bonus_2=bonus.custom_bonus_2,
            actual_custom_bonus_2=actual_custom_bonus_2,
        )
        user_bonus_points[bonus.user_id] = result["points"]

    # ── 4. Update Score rows ────────────────────────────────────────
    all_user_ids = set(user_match_points) | set(user_bracket_points) | set(user_bonus_points)

    # Include users with existing scores who may have 0 points in all categories
    existing_scores = db.query(Score).all()
    for score_row in existing_scores:
        all_user_ids.add(score_row.user_id)

    total_updated = 0

    for user_id in all_user_ids:
        mp = user_match_points.get(user_id, 0)
        bp = user_bracket_points.get(user_id, 0)
        tbp = user_bonus_points.get(user_id, 0)

        score_row = db.query(Score).filter(Score.user_id == user_id).first()
        if score_row:
            score_row.match_points = mp
            score_row.bracket_points = bp
            score_row.tournament_bonus_points = tbp
            score_row.total_points = (
                mp + bp + tbp + score_row.league_bonus_points
            )
        else:
            total = mp + bp + tbp
            score_row = Score(
                user_id=user_id,
                match_points=mp,
                bracket_points=bp,
                tournament_bonus_points=tbp,
                total_points=total,
            )
            db.add(score_row)
        total_updated += 1

    db.commit()

    return {
        "recalculated": True,
        "matches_processed": len(finished_matches),
        "users_updated": total_updated,
        "total_match_points": sum(user_match_points.values()),
        "total_bracket_points": sum(user_bracket_points.values()),
        "total_tournament_bonus_points": sum(user_bonus_points.values()),
    }


def _build_actual_advancements(db) -> set[tuple[int, str]]:
    """
    Determine which teams actually advanced to each knockout round.

    Uses KnockoutAdvancement table if populated, otherwise falls back
    to inspecting finished knockout matches.
    """
    # Prefer explicit advancements from admin
    advancements = db.query(KnockoutAdvancement).all()
    if advancements:
        return {(a.team_id, a.round) for a in advancements}

    # Fallback: derive from finished knockout matches
    finished_knockout = (
        db.query(Match)
        .filter(
            Match.status == "finished",
            Match.round != "group",
        )
        .all()
    )

    result = set()
    for match in finished_knockout:
        if match.home_team_id is not None:
            result.add((match.home_team_id, match.round))
        if match.away_team_id is not None:
            result.add((match.away_team_id, match.round))

    return result


# ═══════════════════════════════════════════════════════════════
# Group standings computation
# ═══════════════════════════════════════════════════════════════

@router.post("/compute-standings")
def compute_group_standings(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Recompute group standings from finished group matches and cache in GroupStanding.
    Returns the standings for all 12 groups.
    """
    # Clear existing standings
    db.query(GroupStanding).delete()

    # Get all teams with their group
    teams = db.query(Team).all()
    team_map = {t.id: t for t in teams}

    # Get all finished group matches
    finished = db.query(Match).filter(
        Match.round == "group",
        Match.status == "finished",
    ).all()

    # Initialize standings for each team
    standings = {}
    for team in teams:
        standings[team.id] = {
            "team_id": team.id,
            "group": team.group,
            "played": 0, "won": 0, "drawn": 0, "lost": 0,
            "goals_for": 0, "goals_against": 0, "points": 0,
        }

    # Process each match
    for match in finished:
        hid, aid = match.home_team_id, match.away_team_id
        if hid is None or aid is None:
            continue
        hg, ag = match.home_goals, match.away_goals
        if hg is None or ag is None:
            continue

        if hid in standings:
            s = standings[hid]
            s["played"] += 1
            s["goals_for"] += hg
            s["goals_against"] += ag
            if hg > ag:
                s["won"] += 1
                s["points"] += 3
            elif hg == ag:
                s["drawn"] += 1
                s["points"] += 1
            else:
                s["lost"] += 1

        if aid in standings:
            s = standings[aid]
            s["played"] += 1
            s["goals_for"] += ag
            s["goals_against"] += hg
            if ag > hg:
                s["won"] += 1
                s["points"] += 3
            elif hg == ag:
                s["drawn"] += 1
                s["points"] += 1
            else:
                s["lost"] += 1

    # Group and sort by: points desc, goal_diff desc, goals_for desc
    groups = {}
    for s in standings.values():
        grp = s["group"]
        if grp not in groups:
            groups[grp] = []
        groups[grp].append(s)

    results = []
    for grp in sorted(groups.keys()):
        group_teams = groups[grp]
        group_teams.sort(key=lambda x: (x["points"], x["goals_for"] - x["goals_against"], x["goals_for"]), reverse=True)
        for i, s in enumerate(group_teams):
            gd = s["goals_for"] - s["goals_against"]
            gs = GroupStanding(
                team_id=s["team_id"],
                group=s["group"],
                position=i + 1,
                played=s["played"],
                won=s["won"],
                drawn=s["drawn"],
                lost=s["lost"],
                goals_for=s["goals_for"],
                goals_against=s["goals_against"],
                goal_difference=gd,
                points=s["points"],
            )
            db.add(gs)
            results.append({
                "team_id": s["team_id"],
                "team_name": team_map[s["team_id"]].name if s["team_id"] in team_map else "",
                "group": s["group"],
                "position": i + 1,
                "played": s["played"],
                "won": s["won"],
                "drawn": s["drawn"],
                "lost": s["lost"],
                "goals_for": s["goals_for"],
                "goals_against": s["goals_against"],
                "goal_difference": gd,
                "points": s["points"],
            })

    db.commit()
    return {"computed": True, "standings": results}


@router.get("/group-standings")
def get_group_standings(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get cached group standings. Must call /compute-standings first."""
    rows = db.query(GroupStanding).order_by(GroupStanding.group, GroupStanding.position).all()
    if not rows:
        return {"standings": [], "message": "No standings computed yet. Call POST /admin/compute-standings first."}

    team_ids = [r.team_id for r in rows]
    teams = db.query(Team).filter(Team.id.in_(team_ids)).all()
    team_map = {t.id: t for t in teams}

    result = []
    for r in rows:
        t = team_map.get(r.team_id)
        result.append({
            "team_id": r.team_id,
            "team_name": t.name if t else "",
            "team_code": t.code if t else "",
            "group": r.group,
            "position": r.position,
            "played": r.played,
            "won": r.won,
            "drawn": r.drawn,
            "lost": r.lost,
            "goals_for": r.goals_for,
            "goals_against": r.goals_against,
            "goal_difference": r.goal_difference,
            "points": r.points,
        })

    return {"standings": result}


# ═══════════════════════════════════════════════════════════════
# Knockout advancement management
# ═══════════════════════════════════════════════════════════════

@router.get("/knockout-advancements")
def get_knockout_advancements(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get all knockout advancements (teams that have advanced to each round)."""
    advancements = db.query(KnockoutAdvancement).all()
    team_ids = [a.team_id for a in advancements]
    teams = db.query(Team).filter(Team.id.in_(team_ids)).all() if team_ids else []
    team_map = {t.id: t for t in teams}

    result = []
    for a in advancements:
        t = team_map.get(a.team_id)
        result.append({
            "id": a.id,
            "team_id": a.team_id,
            "team_name": t.name if t else "",
            "team_code": t.code if t else "",
            "round": a.round,
            "match_number": a.match_number,
        })

    return {"advancements": result}


@router.post("/set-advancement")
def set_knockout_advancement(
    payload: KnockoutAdvancementCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Manually set which team advanced to a knockout round. Admin only."""
    # Upsert: remove existing entry for this team+round, then add
    existing = db.query(KnockoutAdvancement).filter(
        KnockoutAdvancement.team_id == payload.team_id,
        KnockoutAdvancement.round == payload.round,
    ).first()
    if existing:
        existing.match_number = payload.match_number
    else:
        advancement = KnockoutAdvancement(
            team_id=payload.team_id,
            round=payload.round,
            match_number=payload.match_number,
        )
        db.add(advancement)
    db.commit()

    return {"saved": True, "team_id": payload.team_id, "round": payload.round}


@router.post("/resolve-knockout-teams")
def resolve_knockout_teams(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Resolve knockout match team slots from group standings.
    Fills in home_team_id and away_team_id for Round of 32 matches
    based on computed group standings.

    Requires group standings to be computed first (POST /admin/compute-standings).
    """
    # Get group standings
    standings = db.query(GroupStanding).order_by(GroupStanding.group, GroupStanding.position).all()
    if not standings:
        return {"error": "No group standings computed yet. Call POST /admin/compute-standings first."}

    # Build lookup: (group, position) -> team_id
    position_map = {}
    for s in standings:
        position_map[(s.group, s.position)] = s.team_id

    # Best 3rd-place teams logic would go here — for now, use placeholders
    # This requires the third-place combination logic from Excel

    # Get Round of 32 matches that have placeholders
    r32_matches = db.query(Match).filter(
        Match.round == "round_of_32",
    ).all()

    resolved = 0
    for match in r32_matches:
        changed = False

        # Resolve "1A" style placeholders (group winner/runner-up)
        home_resolved = _resolve_placeholder(match.home_team_placeholder, position_map)
        away_resolved = _resolve_placeholder(match.away_team_placeholder, position_map)

        if home_resolved is not None and match.home_team_id is None:
            match.home_team_id = home_resolved
            changed = True
        if away_resolved is not None and match.away_team_id is None:
            match.away_team_id = away_resolved
            changed = True

        if changed:
            resolved += 1

    db.commit()
    return {"resolved": resolved, "message": f"Resolved {resolved} Round of 32 matches with known teams. Best 3rd-place teams require manual advancement entry."}


def _resolve_placeholder(placeholder: str | None, position_map: dict) -> int | None:
    """Resolve a placeholder like '1A', '2B', '3A/B/C/D/F' to a team_id."""
    if not placeholder:
        return None

    # Simple cases: "1A" = winner of group A, "2B" = runner-up of group B
    if len(placeholder) == 2 and placeholder[0] in "12" and placeholder[1].isalpha():
        pos = int(placeholder[0])
        group = placeholder[1].upper()
        return position_map.get((group, pos))

    # Third-place teams like "3A/B/C/D/F" — cannot auto-resolve without best 3rd logic
    if placeholder.startswith("3"):
        return None

    # Winner/loser of match references like "W73", "L101" — resolve later
    if placeholder.startswith(("W", "L")):
        return None

    return None


# ═══════════════════════════════════════════════════════════════
# Tournament phase management
# ═══════════════════════════════════════════════════════════════

@router.get("/phase")
def get_phase(
    db: Session = Depends(get_db),
):
    """Get the current tournament phase (public endpoint)."""
    phase_row = db.query(TournamentPhase).first()
    if not phase_row:
        return PhaseOut(phase="group_open")

    return PhaseOut(
        phase=phase_row.phase,
        group_deadline=phase_row.group_deadline.isoformat() if phase_row.group_deadline else None,
        knockout_opens_at=phase_row.knockout_opens_at.isoformat() if phase_row.knockout_opens_at else None,
        knockout_deadline=phase_row.knockout_deadline.isoformat() if phase_row.knockout_deadline else None,
    )


@router.post("/phase")
def update_phase(
    payload: PhaseUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update the current tournament phase. Admin only."""
    phase_row = db.query(TournamentPhase).first()
    if not phase_row:
        phase_row = TournamentPhase(phase="group_open")
        db.add(phase_row)
        db.flush()

    if payload.phase is not None:
        valid_phases = ("group_open", "group_closed", "knockout_open", "knockout_closed")
        if payload.phase not in valid_phases:
            raise HTTPException(422, f"phase must be one of {valid_phases}")
        phase_row.phase = payload.phase

    if payload.group_deadline is not None:
        phase_row.group_deadline = datetime.fromisoformat(payload.group_deadline)
    if payload.knockout_opens_at is not None:
        phase_row.knockout_opens_at = datetime.fromisoformat(payload.knockout_opens_at)
    if payload.knockout_deadline is not None:
        phase_row.knockout_deadline = datetime.fromisoformat(payload.knockout_deadline)

    db.commit()

    return {
        "phase": phase_row.phase,
        "group_deadline": phase_row.group_deadline.isoformat() if phase_row.group_deadline else None,
        "knockout_opens_at": phase_row.knockout_opens_at.isoformat() if phase_row.knockout_opens_at else None,
        "knockout_deadline": phase_row.knockout_deadline.isoformat() if phase_row.knockout_deadline else None,
    }


# ═══════════════════════════════════════════════════════════════
# Admin scoring overview
# ═══════════════════════════════════════════════════════════════

@router.get("/scoring-overview")
def scoring_overview(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Full scoring overview for admin dashboard.
    Returns all users with score breakdowns.
    """
    scores = db.query(Score).all()
    user_ids = [s.user_id for s in scores]
    users = db.query(User).filter(User.id.in_(user_ids)).all() if user_ids else []
    user_map = {u.id: u for u in users}

    result = []
    for s in scores:
        u = user_map.get(s.user_id)
        result.append({
            "user_id": s.user_id,
            "display_name": u.display_name if u else f"User {s.user_id}",
            "match_points": s.match_points,
            "bracket_points": s.bracket_points,
            "tournament_bonus_points": s.tournament_bonus_points,
            "league_bonus_points": s.league_bonus_points,
            "total_points": s.total_points,
        })

    # Include users without scores
    all_users = db.query(User).all()
    scored_ids = {s.user_id for s in scores}
    for u in all_users:
        if u.id not in scored_ids:
            result.append({
                "user_id": u.id,
                "display_name": u.display_name,
                "match_points": 0,
                "bracket_points": 0,
                "tournament_bonus_points": 0,
                "league_bonus_points": 0,
                "total_points": 0,
            })

    # Sort by total_points descending
    result.sort(key=lambda x: x["total_points"], reverse=True)

    return {"scores": result}


# ═══════════════════════════════════════════════════════════════
# Admin: view all users' predictions
# ═══════════════════════════════════════════════════════════════

@router.get("/all-predictions")
def all_predictions(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Return all users' predictions: match predictions, bracket predictions,
    and tournament bonuses. Grouped by user for easy admin review.
    """
    users = db.query(User).order_by(User.display_name).all()
    matches = db.query(Match).order_by(Match.match_number).all()
    match_map = {m.id: m for m in matches}

    # All predictions
    all_preds = db.query(Prediction).all()
    preds_by_user: dict = {}
    for p in all_preds:
        preds_by_user.setdefault(p.user_id, []).append(p)

    # All bracket predictions
    all_bracket = db.query(BracketPrediction).all()
    bracket_by_user: dict = {}
    for b in all_bracket:
        bracket_by_user.setdefault(b.user_id, []).append(b)

    # All tournament bonuses
    all_bonuses = db.query(TournamentBonus).all()
    bonus_by_user = {b.user_id: b for b in all_bonuses}

    # Teams map
    teams = db.query(Team).all()
    team_map = {t.id: t for t in teams}

    result = []
    for u in users:
        user_preds = preds_by_user.get(u.id, [])
        match_predictions = []
        for p in sorted(user_preds, key=lambda x: getattr(match_map.get(x.match_id), "match_number", 0)):
            m = match_map.get(p.match_id)
            if not m:
                continue
            match_predictions.append({
                "match_id": p.match_id,
                "match_number": m.match_number,
                "group": m.group,
                "round": m.round,
                "home_team": m.home_team.name if m.home_team else None,
                "home_flag": m.home_team.flag_emoji if m.home_team else None,
                "away_team": m.away_team.name if m.away_team else None,
                "away_flag": m.away_team.flag_emoji if m.away_team else None,
                "home_goals": p.home_goals,
                "away_goals": p.away_goals,
            })

        user_bracket = bracket_by_user.get(u.id, [])
        bracket_predictions = []
        for b in sorted(user_bracket, key=lambda x: (list(BRACKET_ROUND_POINTS.keys()).index(x.round) if x.round in BRACKET_ROUND_POINTS else 99, 0)):
            team = team_map.get(b.team_id)
            bracket_predictions.append({
                "team_id": b.team_id,
                "team_name": team.name if team else "?",
                "team_flag": team.flag_emoji if team else None,
                "round": b.round,
                "points": BRACKET_ROUND_POINTS.get(b.round, 0),
            })

        user_bonus = bonus_by_user.get(u.id)
        tournament_bonuses = None
        if user_bonus:
            _wt = team_map.get(user_bonus.winner_team_id) if user_bonus.winner_team_id else None
            _bt = team_map.get(user_bonus.bronze_winner_team_id) if user_bonus.bronze_winner_team_id else None
            _mg = team_map.get(user_bonus.most_goals_team_id) if user_bonus.most_goals_team_id else None
            _mc = team_map.get(user_bonus.most_conceded_team_id) if user_bonus.most_conceded_team_id else None
            tournament_bonuses = {
                "winner_team_id": user_bonus.winner_team_id,
                "winner_team_name": _wt.name if _wt else None,
                "winner_team_flag": _wt.flag_emoji if _wt else None,
                "top_scorer_name": user_bonus.top_scorer_name,
                "bronze_winner_team_id": user_bonus.bronze_winner_team_id,
                "bronze_winner_team_name": _bt.name if _bt else None,
                "most_goals_team_id": user_bonus.most_goals_team_id,
                "most_goals_team_name": _mg.name if _mg else None,
                "most_conceded_team_id": user_bonus.most_conceded_team_id,
                "most_conceded_team_name": _mc.name if _mc else None,
                "custom_bonus_1": user_bonus.custom_bonus_1,
                "custom_bonus_2": user_bonus.custom_bonus_2,
            }

        result.append({
            "user_id": u.id,
            "display_name": u.display_name,
            "match_predictions": match_predictions,
            "bracket_predictions": bracket_predictions,
            "tournament_bonuses": tournament_bonuses,
        })

    return {"users": result}

# ═══════════════════════════════════════════════════════════════
# League management
# ═══════════════════════════════════════════════════════════════

@router.get("/leagues")
def list_leagues(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all leagues."""
    leagues = db.query(League).all()
    return [
        {
            "id": l.id,
            "name": l.name,
            "invite_code": l.invite_code,
            "is_public": l.is_public,
            "admin_user_id": l.admin_user_id,
            "member_count": len(l.members),
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in leagues
    ]


class LeagueUpdate(BaseModel):
    name: str | None = None
    is_public: bool | None = None


@router.patch("/leagues/{league_id}")
def update_league(
    league_id: int,
    payload: LeagueUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update a league name or visibility."""
    league = db.query(League).filter(League.id == league_id).first()
    if not league:
        raise NotFoundError(detail="league_not_found", error_code="league_not_found")
    if payload.name is not None:
        league.name = payload.name
    if payload.is_public is not None:
        league.is_public = payload.is_public
    db.commit()
    return {"updated": True}


@router.delete("/leagues/{league_id}")
def delete_league(
    league_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete a league and all related data (members, scores, predictions)."""
    league = db.query(League).filter(League.id == league_id).first()
    if not league:
        raise NotFoundError(detail="league_not_found", error_code="league_not_found")
    if league.name == "VM2026":
        raise ForbiddenError(detail="cannot_delete_default_league", error_code="cannot_delete_default_league")
    db.delete(league)
    db.commit()
    return {"deleted": True}
