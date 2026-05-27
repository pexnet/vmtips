"""
One-shot script: normalise existing match dates to real UTC-aware datetimes
from the worldcup2026_fixtures.json fixture file.
Usage: cd backend && uv run python scripts/normalise_match_dates.py
"""
import datetime
import json
import pathlib

import database
from database import SessionLocal
from models import Match


DATA_PATH = pathlib.Path(__file__).resolve().parent.parent / "data" / "worldcup2026_fixtures.json"


def main():
    database.Base.metadata.create_all(bind=database.engine)
    db = SessionLocal()
    try:
        fixtures = json.loads(DATA_PATH.read_text("utf-8"))
        updated = 0
        for f in fixtures:
            mn = f["match_number"]
            dt = datetime.datetime.fromisoformat(f["match_date_utc"])
            m = db.query(Match).filter(Match.match_number == mn).first()
            if m and m.match_date != dt:
                m.match_date = dt
                updated += 1
        db.commit()
        print(f"[normalise] Updated {updated} match dates with true-UTC datetimes")

        # Verify
        sample = db.query(Match).order_by(Match.match_number).first()
        print(f"[normalise] Sample MN{sample.match_number}: {sample.match_date.isoformat()}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
