#!/bin/bash
set -e

# Create data directory if missing
mkdir -p /app/data

# Run database migrations via Alembic
alembic upgrade head

# Fallback: create all tables directly (use only if Alembic is unavailable)
# python -c "from database import engine, Base; import models; Base.metadata.create_all(bind=engine)"

# Seed the database on first start (if no teams exist)
python -c "
from database import SessionLocal
from models import Team
from seed import seed_teams, seed_group_matches, seed_knockout_matches

db = SessionLocal()
try:
    if db.query(Team).first() is None:
        print('[startup] Seeding database...')
        seed_teams(db)
        seed_group_matches(db)
        seed_knockout_matches(db)
        print('[startup] Done.')
    else:
        print('[startup] Database already seeded.')
finally:
    db.close()
"

# Start the application
exec uvicorn main:app --host 0.0.0.0 --port 8000