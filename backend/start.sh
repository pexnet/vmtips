#!/bin/bash
set -e

# ── Ensure the SQLite data directory exists with the right ownership ──
# The DATABASE_URL is normally sqlite:///app/data/vmtips.db (Docker) or
# sqlite:///./vmtips.db (local dev). We parse the URL to discover the
# actual directory and mkdir -p it. This works for absolute paths,
# relative paths, and the /data bind-mount used by docker-compose.prod.yml.
#
# Fix: start.sh used to hardcode `/app/data` which is wrong for the
# production compose file (it uses `/data`). Derive the dir from the URL
# so any of the three layouts "just work".
ensure_data_dir() {
  local db_url="${DATABASE_URL:-sqlite:///./vmtips.db}"
  # Strip the sqlite:/// or sqlite:// prefix
  local db_path="${db_url#sqlite:///}"
  db_path="${db_path#sqlite://}"
  # Drop any ?drivername query string
  db_path="${db_path%%\?*}"
  # Take the dirname
  local db_dir
  db_dir="$(dirname "$db_path")"
  # In the container, sqlite:///app/data/vmtips.db has no leading slash
  # (sqlite:// is scheme+//; path is /app/data/...).  dirname on "/app/data/vmtips.db" → "/app/data".
  # For relative paths like "./vmtips.db" dirname is "." which mkdir handles fine.
  if [ -z "$db_dir" ] || [ "$db_dir" = "/" ]; then
    return 0
  fi
  mkdir -p "$db_dir"
  echo "[startup] Ensured data directory: $db_dir"
}

ensure_data_dir

if [ "${ENVIRONMENT:-${APP_ENV:-development}}" = "production" ]; then
  if [ -z "${ADMIN_EMAIL:-}" ] || [ -z "${ADMIN_PASSWORD:-}" ]; then
    echo "[startup] ERROR: ADMIN_EMAIL and ADMIN_PASSWORD must be set in production." >&2
    echo "[startup] Rotate admin credentials by changing these secrets and restarting, then update the admin user's password in the database or through the admin account flow." >&2
    exit 1
  fi
  if [ "${ADMIN_EMAIL}" = "admin@example.com" ] || [ "${ADMIN_PASSWORD}" = "admin" ] || [ "${ADMIN_PASSWORD}" = "change-me-in-production" ]; then
    echo "[startup] ERROR: Refusing insecure production admin credentials." >&2
    echo "[startup] Set unique ADMIN_EMAIL and ADMIN_PASSWORD secrets. Rotate by replacing the secrets, restarting, and updating/removing old admin credentials." >&2
    exit 1
  fi
fi

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

# Create default admin user if it doesn't exist
python -c "
from database import SessionLocal
from models import User
from config import settings
from security import get_password_hash

db = SessionLocal()
try:
    existing = db.query(User).filter(User.email == settings.admin_email).first()
    if not existing:
        print('[startup] Creating admin user...')
        admin = User(
            email=settings.admin_email,
            password_hash=get_password_hash(settings.admin_password),
            display_name='Admin',
            is_admin=True,
        )
        db.add(admin)
        db.commit()
        print('[startup] Admin created.')
    else:
        if not existing.is_admin:
            print('[startup] Updating existing user to admin...')
            existing.is_admin = True
            db.commit()
        print('[startup] Admin user already exists.')
finally:
    db.close()
"

# Start the application
exec uvicorn main:app --host 0.0.0.0 --port 8000
