"""
Clean seed script: wipes DB, recreates tables, seeds data, creates test user,
and optionally fills group-stage predictions.
"""
import sys
from database import engine, Base, SessionLocal
from seed import (
    seed_teams,
    seed_group_matches,
    seed_knockout_matches,
    seed_admin,
    seed_tournament_phase,
    seed_tournament_result,
    seed_default_league,
)
from security import get_password_hash
from models import User, League, LeagueMember, Prediction, Team, Match

TEST_EMAIL = "test@vmtips.se"
TEST_PASSWORD = "test123"
TEST_NAME = "Testare"


def clean_seed():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("[clean_seed] Database wiped and tables recreated")

    db = SessionLocal()
    try:
        seed_teams(db)
        seed_group_matches(db)
        seed_knockout_matches(db)
        seed_admin(db)
        seed_tournament_phase(db)
        seed_tournament_result(db)
        seed_default_league(db)

        # Create test user
        test_user = User(
            email=TEST_EMAIL,
            password_hash=get_password_hash(TEST_PASSWORD),
            display_name=TEST_NAME,
        )
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        print(f"[clean_seed] Created test user: {TEST_EMAIL} / {TEST_PASSWORD}")

        # Join VM2026 league
        default_league = db.query(League).filter(League.name == "VM2026").first()
        if default_league:
            member = LeagueMember(league_id=default_league.id, user_id=test_user.id)
            db.add(member)
            db.commit()
            print(f"[clean_seed] Test user joined league VM2026")

        return db, test_user, default_league
    except Exception:
        db.close()
        raise


def fill_group_predictions(db, user, league):
    group_matches = (
        db.query(Match)
        .filter(Match.round == "group")
        .order_by(Match.match_number)
        .all()
    )

    predictions = []
    for i, m in enumerate(group_matches):
        # Use deterministic but varied scores based on match number
        h = ((i * 3) % 5)
        a = ((i * 7) % 4)
        predictions.append(
            Prediction(
                user_id=user.id,
                league_id=league.id,
                match_id=m.id,
                home_goals=h,
                away_goals=a,
            )
        )

    db.add_all(predictions)
    db.commit()
    print(f"[clean_seed] Inserted {len(predictions)} group-stage predictions for test user")


if __name__ == "__main__":
    db, user, league = clean_seed()
    try:
        if league:
            fill_group_predictions(db, user, league)
        print("[clean_seed] Done.")
    finally:
        db.close()
