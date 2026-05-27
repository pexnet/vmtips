"""
Seed script for the VMTips database.
Populates teams, all 104 World Cup 2026 matches, a default admin user,
and the initial tournament phase from openfootball data.
Source: https://github.com/openfootball/worldcup.json
Run: cd backend && uv run python seed.py
"""
import datetime
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


def seed_default_league(db):
    """Ensure a private VM2026 default league exists and admin is member."""
    existing = db.query(League).filter(League.name == "VM2026").first()
    if existing:
        print("[seed] Default VM2026 league already exists")
        return

    # Clean up any stray leagues created before this fix
    db.query(League).filter(League.name != "VM2026").delete(synchronize_session=False)
    db.commit()

    admin = db.query(User).filter(User.email == ADMIN_EMAIL).first()
    if not admin:
        print("[seed] Admin user not found, skipping default league creation")
        return

    default_league = League(
        name="VM2026",
        invite_code="VM2026",
        is_public=False,
        admin_user_id=admin.id,
    )
    db.add(default_league)
    db.commit()
    db.refresh(default_league)

    member = LeagueMember(league_id=default_league.id, user_id=admin.id)
    db.add(member)
    db.commit()
    print(f"[seed] Created default VM2026 league (private) and joined admin")


def main(session=None):
    """Seed the database. If a session is provided, use it (for testing)."""
    if session is None:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
    else:
        db = session
    try:
        seed_teams(db)
        seed_group_matches(db)
        seed_knockout_matches(db)
        seed_admin(db)
        seed_tournament_phase(db)
        seed_tournament_result(db)
        seed_default_league(db)
        print("[seed] Database seeded successfully")
    finally:
        if session is None:
            db.close()


if __name__ == "__main__":
    main()