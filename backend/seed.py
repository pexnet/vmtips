"""
Seed script for the VMTips database.
Populates teams, all 104 World Cup 2026 matches, a default admin user,
and the initial tournament phase from openfootball data.
Source: https://github.com/openfootball/worldcup.json
Run: cd backend && uv run python seed.py
"""
import datetime
import json
import os
from pathlib import Path
from sqlalchemy import func

from database import SessionLocal, engine, Base
from models import Team, Match, User, TournamentPhase, TournamentResult, League, LeagueMember
from security import get_password_hash

TEAM_DATA = [
    ("Czech Republic", "CZE", "A", "🇨🇿"),
    ("Mexico", "MEX", "A", "🇲🇽"),
    ("South Africa", "RSA", "A", "🇿🇦"),
    ("South Korea", "KOR", "A", "🇰🇷"),
    ("Bosnia & Herzegovina", "BIH", "B", "🇧🇦"),
    ("Canada", "CAN", "B", "🇨🇦"),
    ("Qatar", "QAT", "B", "🇶🇦"),
    ("Switzerland", "SUI", "B", "🇨🇭"),
    ("Brazil", "BRA", "C", "🇧🇷"),
    ("Haiti", "HAI", "C", "🇭🇹"),
    ("Morocco", "MAR", "C", "🇲🇦"),
    ("Scotland", "SCO", "C", "🏴󠁧󠁢󠁳󠁣󠁴󠁿"),
    ("Australia", "AUS", "D", "🇦🇺"),
    ("Paraguay", "PAR", "D", "🇵🇾"),
    ("Turkey", "TUR", "D", "🇹🇷"),
    ("USA", "USA", "D", "🇺🇸"),
    ("Curaçao", "CUW", "E", "🇨🇼"),
    ("Ecuador", "ECU", "E", "🇪🇨"),
    ("Germany", "GER", "E", "🇩🇪"),
    ("Ivory Coast", "CIV", "E", "🇨🇮"),
    ("Japan", "JPN", "F", "🇯🇵"),
    ("Netherlands", "NED", "F", "🇳🇱"),
    ("Sweden", "SWE", "F", "🇸🇪"),
    ("Tunisia", "TUN", "F", "🇹🇳"),
    ("Belgium", "BEL", "G", "🇧🇪"),
    ("Egypt", "EGY", "G", "🇪🇬"),
    ("Iran", "IRN", "G", "🇮🇷"),
    ("New Zealand", "NZL", "G", "🇳🇿"),
    ("Cape Verde", "CPV", "H", "🇨🇻"),
    ("Saudi Arabia", "KSA", "H", "🇸🇦"),
    ("Spain", "ESP", "H", "🇪🇸"),
    ("Uruguay", "URU", "H", "🇺🇾"),
    ("France", "FRA", "I", "🇫🇷"),
    ("Iraq", "IRQ", "I", "🇮🇶"),
    ("Norway", "NOR", "I", "🇳🇴"),
    ("Senegal", "SEN", "I", "🇸🇳"),
    ("Algeria", "ALG", "J", "🇩🇿"),
    ("Argentina", "ARG", "J", "🇦🇷"),
    ("Austria", "AUT", "J", "🇦🇹"),
    ("Jordan", "JOR", "J", "🇯🇴"),
    ("Colombia", "COL", "K", "🇨🇴"),
    ("DR Congo", "COD", "K", "🇨🇩"),
    ("Portugal", "POR", "K", "🇵🇹"),
    ("Uzbekistan", "UZB", "K", "🇺🇿"),
    ("Croatia", "CRO", "L", "🇭🇷"),
    ("England", "ENG", "L", "🏴󠁧󠁢󠁥󠁮󠁧󠁿"),
    ("Ghana", "GHA", "L", "🇬🇭"),
    ("Panama", "PAN", "L", "🇵🇦"),
]

# All 104 fixtures are loaded from data/worldcup2026_fixtures.json (see seed_from_json).

# Default admin user credentials
ADMIN_EMAIL = "admin@vmtips.se"
ADMIN_PASSWORD = "admin"
ADMIN_DISPLAY_NAME = "Admin"

START_USERS_FILE = Path(
    os.environ.get(
        "START_USERS_FILE",
        Path(__file__).resolve().parent.parent / "data" / "start_users.json",
    )
)

# Custom bonus question labels (displayed in frontend)
CUSTOM_BONUS_1 = "Vilken målvakt gör flest räddningar?"
CUSTOM_BONUS_2 = "Vilket lag får flest gula kort?"


def _get_team_id(db, team_name):
    """Look up a team by name. Returns None for placeholder names."""
    if team_name.startswith(("1", "2", "3", "W", "L")):
        return None
    team = db.query(Team).filter(Team.name == team_name).first()
    if team is None:
        if len(team_name) == 3 and team_name.isupper():
            team = db.query(Team).filter(Team.code == team_name).first()
    return team.id if team else None


def seed_teams(db):
    """Insert all 48 teams if not already present."""
    existing = {t.code for t in db.query(Team.code).all()}
    for name, code, group, flag in TEAM_DATA:
        if code not in existing:
            db.add(Team(name=name, code=code, group=group, flag_emoji=flag))
    db.commit()
    print(f"[seed] Inserted/updated {len(TEAM_DATA)} teams")


def seed_from_json(db: SessionLocal):
    """Seed all 104 matches from external JSON fixture file."""
    import json, os
    import pathlib
    # Resolve path relative to this file so we work from any CWD
    here = pathlib.Path(__file__).resolve().parent
    data_path = here / "data" / "worldcup2026_fixtures.json"
    if not data_path.exists():
        print(f"[seed] Fixture file not found: {data_path}")
        return
    fixtures = json.loads(data_path.read_text("utf-8"))

    inserted_group = 0
    inserted_ko = 0
    updated = 0
    for f in fixtures:
        mn = f["match_number"]
        existing = db.query(Match).filter(Match.match_number == mn).first()
        # Resolve team names
        home_name = f["home_team_name"]
        away_name = f["away_team_name"]
        home_id = _get_team_id(db, home_name)
        away_id = _get_team_id(db, away_name)
        # Convert UTC ISO string -> aware datetime
        dt = datetime.datetime.fromisoformat(f["match_date_utc"])
        if existing:
            # Only update if date changed (allows hot-reload of fixtures)
            if existing.match_date != dt:
                existing.match_date = dt
                updated += 1
            continue
        round_name = f["round"]
        m = Match(
            match_number=mn,
            group=f.get("group"),
            round=round_name,
            home_team_id=home_id,
            away_team_id=away_id,
            home_team_placeholder=home_name if home_id is None else None,
            away_team_placeholder=away_name if away_id is None else None,
            match_date=dt,
            status="scheduled",
        )
        db.add(m)
        if round_name == "group":
            inserted_group += 1
        else:
            inserted_ko += 1
    db.commit()
    if inserted_group + inserted_ko:
        print(f"[seed] Inserted {inserted_group} group + {inserted_ko} KO matches from JSON")
    if updated:
        print(f"[seed] Updated {updated} existing match dates")
    return inserted_group + inserted_ko


def seed_group_matches(db):
    """Group matches are seeded from JSON – no-op here but kept for compat."""
    # Modern flow: everything happens in seed_from_json
    count = db.query(Match).filter(Match.round == "group").count()
    if count == 0:
        seed_from_json(db)
    else:
        print(f"[seed] {count} group matches already present, skipping")


def seed_knockout_matches(db):
    """KO matches are seeded from JSON – no-op here but kept for compat."""
    count = db.query(Match).filter(Match.round != "group").count()
    if count == 0:
        seed_from_json(db)
    else:
        print(f"[seed] {count} knockout matches already present, skipping")


def seed_admin(db):
    """Create a default admin user if not already present."""
    existing = db.query(User).filter(User.email == ADMIN_EMAIL).first()
    if existing:
        print(f"[seed] Admin user already exists: {ADMIN_EMAIL}")
        return

    admin = User(
        email=ADMIN_EMAIL,
        password_hash=get_password_hash(ADMIN_PASSWORD),
        display_name=ADMIN_DISPLAY_NAME,
        is_admin=True,
    )
    db.add(admin)
    db.commit()
    print(f"[seed] Created admin user: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")


def load_start_users(start_users_file: Path = START_USERS_FILE) -> list[dict]:
    """Load and validate private initial-user credentials from JSON."""
    if not start_users_file.exists():
        print(f"[seed] Start users file not found: {start_users_file}")
        return []

    raw_users = json.loads(start_users_file.read_text(encoding="utf-8"))
    if not isinstance(raw_users, list):
        raise ValueError("start_users.json must contain a JSON array")

    users = []
    seen_usernames = set()
    seen_emails = set()
    seen_passwords = set()
    for index, raw_user in enumerate(raw_users):
        if not isinstance(raw_user, dict):
            raise ValueError(f"start_users.json entry {index} must be an object")
        username = str(raw_user.get("username", "")).strip().lower()
        password = str(raw_user.get("password", ""))
        display_name = str(raw_user.get("display_name") or username).strip()
        email = str(raw_user.get("email") or f"{username}@vmtips.se").strip().lower()
        if not username:
            raise ValueError(f"start_users.json entry {index} is missing username")
        if len(password) < 6:
            raise ValueError(
                f"start_users.json user '{username}' must have a password of at least 6 characters"
            )
        if not display_name:
            raise ValueError(
                f"start_users.json user '{username}' is missing display_name"
            )
        if display_name.lower() != username:
            raise ValueError(
                f"start_users.json user '{username}' must use a matching display_name"
            )
        if "@" not in email:
            raise ValueError(
                f"start_users.json user '{username}' has an invalid email"
            )
        if username in seen_usernames:
            raise ValueError(f"duplicate username in start_users.json: {username}")
        if email in seen_emails:
            raise ValueError(f"duplicate email in start_users.json: {email}")
        if password in seen_passwords:
            raise ValueError(f"duplicate password in start_users.json for user: {username}")
        seen_usernames.add(username)
        seen_emails.add(email)
        seen_passwords.add(password)
        users.append(
            {
                "username": username,
                "password": password,
                "display_name": display_name,
                "email": email,
            }
        )
    return users


def seed_default_users(db, start_users_file: Path = START_USERS_FILE):
    """Create initial participants from the private start-users file.

    Idempotent: if any configured user would conflict with existing data
    (by email or display_name_lower), the entire seed batch is skipped
    and the configured list is returned unchanged. This makes the function
    safe to call on every container start without raising UNIQUE-constraint
    errors when a real user has already claimed a display_name.
    """
    configured_users = load_start_users(start_users_file)

    if configured_users:
        emails = [u["email"] for u in configured_users]
        display_names_lower = [u["display_name"].strip().lower() for u in configured_users]
        conflicts = (
            db.query(User)
            .filter(
                (User.email.in_(emails))
                | (User.display_name_lower.in_(display_names_lower))
            )
            .count()
        )
        if conflicts > 0:
            print(
                f"[seed] {conflicts} existing user(s) conflict with default seed "
                f"(by email or display_name); skipping seed_default_users."
            )
            return configured_users

    created_users = []
    for configured_user in configured_users:
        email = configured_user["email"]
        existing = db.query(User).filter(func.lower(User.email) == email).first()
        if existing:
            continue
        user = User(
            email=email,
            password_hash=get_password_hash(configured_user["password"]),
            display_name=configured_user["display_name"],
            is_admin=False,
            is_active=True,
        )
        db.add(user)
        created_users.append(configured_user)
    db.commit()

    if created_users:
        print(f"[seed] Created {len(created_users)} default users:")
        for user in created_users:
            print(f"[seed]   {user['email']}")
    else:
        print("[seed] No new default users created")
    return configured_users


def seed_tournament_phase(db):
    """Create the default tournament phase row (group_open) if not present."""
    existing = db.query(TournamentPhase).first()
    if existing:
        print(f"[seed] Tournament phase already exists: {existing.phase}")
        return

    phase = TournamentPhase(phase="group_open")
    db.add(phase)
    db.commit()
    print("[seed] Created tournament phase: group_open")


def compute_lock_at(db):
    """Return the first match kickoff, or None when fixtures are absent."""
    return db.query(func.min(Match.match_date)).scalar()


def seed_tournament_phase_lock(db):
    """Set the extra-question lock from match 1 unless an override exists."""
    phase = db.query(TournamentPhase).first()
    if phase is None:
        seed_tournament_phase(db)
        phase = db.query(TournamentPhase).first()
    if phase.extra_questions_lock_at is not None:
        print(
            "[seed] Preserving extra_questions_lock_at override: "
            f"{phase.extra_questions_lock_at}"
        )
        return phase.extra_questions_lock_at
    lock_at = compute_lock_at(db)
    if lock_at is None:
        print("[seed] WARNING: no matches found; extra questions remain unlocked")
        return None
    phase.extra_questions_lock_at = lock_at
    db.commit()
    print(f"[seed] Computed extra_questions_lock_at: {lock_at}")
    return lock_at


def seed_tournament_result(db):
    """Seed TournamentResult with custom bonus labels if not present."""
    existing = db.query(TournamentResult).first()
    if existing:
        print("[seed] Tournament result row already exists, skipping")
        return

    result = TournamentResult(
        custom_bonus_1_answer=CUSTOM_BONUS_1,
        custom_bonus_2_answer=CUSTOM_BONUS_2,
    )
    db.add(result)
    db.commit()
    print(f"[seed] Created tournament result with custom bonus labels")


def seed_default_league(db, default_user_emails: list[str] | None = None):
    """Ensure VM2026 exists and contains the seven default participants."""
    admin = db.query(User).filter(User.email == ADMIN_EMAIL).first()
    if not admin:
        admin = db.query(User).filter(User.is_admin.is_(True)).order_by(User.id).first()
    if not admin:
        print("[seed] Admin user not found, skipping default league creation")
        return

    default_league = db.query(League).filter(League.name == "VM2026").first()
    if not default_league:
        default_league = League(
            name="VM2026",
            invite_code="VM2026",
            is_public=True,
            admin_user_id=admin.id,
        )
        db.add(default_league)
        db.flush()
    elif not default_league.is_public:
        default_league.is_public = True

    db.query(LeagueMember).filter(
        LeagueMember.league_id == default_league.id,
        LeagueMember.user_id == admin.id,
    ).delete(synchronize_session=False)

    default_emails = default_user_emails or []
    default_users = db.query(User).filter(User.email.in_(default_emails)).all()
    existing_member_ids = {
        user_id
        for (user_id,) in db.query(LeagueMember.user_id)
        .filter(LeagueMember.league_id == default_league.id)
        .all()
    }
    for user in default_users:
        if user.id not in existing_member_ids:
            db.add(LeagueMember(league_id=default_league.id, user_id=user.id))
    db.commit()
    print(f"[seed] Added {len(default_users)} default users to VM2026 league")
    print("[seed] Admin is NOT a member of VM2026 (administrator only)")
    return default_league


def main(session=None, start_users_file=None):
    """Seed the database. If a session is provided, use it (for testing)."""
    if session is None:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
    else:
        db = session
    if start_users_file is None:
        start_users_file = START_USERS_FILE
    try:
        seed_teams(db)
        seed_group_matches(db)
        seed_knockout_matches(db)
        seed_admin(db)
        configured_users = seed_default_users(db, start_users_file=start_users_file)
        seed_tournament_phase(db)
        seed_tournament_phase_lock(db)
        seed_tournament_result(db)
        seed_default_league(
            db,
            default_user_emails=[user["email"] for user in configured_users],
        )
        print("[seed] Database seeded successfully")
    finally:
        if session is None:
            db.close()


if __name__ == "__main__":
    main()
