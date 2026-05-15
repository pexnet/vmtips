#!/bin/bash
set -e

# Create data directory if missing
mkdir -p /app/data

# Seed the database on first start (if no teams exist)
python -c "
from database import SessionLocal, engine, Base
from models import Team
from seed import seed_teams, seed_matches

Base.metadata.create_all(bind=engine)

db = SessionLocal()
try:
    if db.query(Team).first() is None:
        print('[startup] Seeding database...')
        seed_teams(db)
        seed_matches(db)
        print('[startup] Done.')
    else:
        print('[startup] Database already seeded.')
finally:
    db.close()
"

# Start the application
exec uvicorn main:app --host 0.0.0.0 --port 8000
