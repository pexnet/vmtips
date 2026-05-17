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

GROUP_MATCHES = [
    (1, "A", "Mexico", "South Africa", datetime.datetime(2026, 6, 11, 19, 0)),
    (2, "A", "South Korea", "Czech Republic", datetime.datetime(2026, 6, 12, 2, 0)),
    (3, "A", "Czech Republic", "South Africa", datetime.datetime(2026, 6, 18, 16, 0)),
    (4, "A", "Mexico", "South Korea", datetime.datetime(2026, 6, 19, 1, 0)),
    (5, "A", "Czech Republic", "Mexico", datetime.datetime(2026, 6, 25, 1, 0)),
    (6, "A", "South Africa", "South Korea", datetime.datetime(2026, 6, 25, 1, 0)),
    (7, "B", "Canada", "Bosnia & Herzegovina", datetime.datetime(2026, 6, 12, 19, 0)),
    (8, "B", "Qatar", "Switzerland", datetime.datetime(2026, 6, 13, 19, 0)),
    (9, "B", "Switzerland", "Bosnia & Herzegovina", datetime.datetime(2026, 6, 18, 19, 0)),
    (10, "B", "Canada", "Qatar", datetime.datetime(2026, 6, 18, 22, 0)),
    (11, "B", "Switzerland", "Canada", datetime.datetime(2026, 6, 24, 19, 0)),
    (12, "B", "Bosnia & Herzegovina", "Qatar", datetime.datetime(2026, 6, 24, 19, 0)),
    (13, "C", "Brazil", "Morocco", datetime.datetime(2026, 6, 13, 22, 0)),
    (14, "C", "Haiti", "Scotland", datetime.datetime(2026, 6, 14, 1, 0)),
    (15, "C", "Scotland", "Morocco", datetime.datetime(2026, 6, 19, 22, 0)),
    (16, "C", "Brazil", "Haiti", datetime.datetime(2026, 6, 20, 0, 30)),
    (17, "C", "Scotland", "Brazil", datetime.datetime(2026, 6, 24, 22, 0)),
    (18, "C", "Morocco", "Haiti", datetime.datetime(2026, 6, 24, 22, 0)),
    (19, "D", "USA", "Paraguay", datetime.datetime(2026, 6, 13, 1, 0)),
    (20, "D", "Australia", "Turkey", datetime.datetime(2026, 6, 14, 4, 0)),
    (21, "D", "USA", "Australia", datetime.datetime(2026, 6, 19, 19, 0)),
    (22, "D", "Turkey", "Paraguay", datetime.datetime(2026, 6, 20, 3, 0)),
    (23, "D", "Turkey", "USA", datetime.datetime(2026, 6, 26, 2, 0)),
    (24, "D", "Paraguay", "Australia", datetime.datetime(2026, 6, 26, 2, 0)),
    (25, "E", "Germany", "Curaçao", datetime.datetime(2026, 6, 14, 17, 0)),
    (26, "E", "Ivory Coast", "Ecuador", datetime.datetime(2026, 6, 14, 23, 0)),
    (27, "E", "Germany", "Ivory Coast", datetime.datetime(2026, 6, 20, 20, 0)),
    (28, "E", "Ecuador", "Curaçao", datetime.datetime(2026, 6, 21, 0, 0)),
    (29, "E", "Curaçao", "Ivory Coast", datetime.datetime(2026, 6, 25, 20, 0)),
    (30, "E", "Ecuador", "Germany", datetime.datetime(2026, 6, 25, 20, 0)),
    (31, "F", "Netherlands", "Japan", datetime.datetime(2026, 6, 14, 20, 0)),
    (32, "F", "Sweden", "Tunisia", datetime.datetime(2026, 6, 15, 2, 0)),
    (33, "F", "Netherlands", "Sweden", datetime.datetime(2026, 6, 20, 17, 0)),
    (34, "F", "Tunisia", "Japan", datetime.datetime(2026, 6, 21, 4, 0)),
    (35, "F", "Japan", "Sweden", datetime.datetime(2026, 6, 25, 23, 0)),
    (36, "F", "Tunisia", "Netherlands", datetime.datetime(2026, 6, 25, 23, 0)),
    (37, "G", "Belgium", "Egypt", datetime.datetime(2026, 6, 15, 19, 0)),
    (38, "G", "Iran", "New Zealand", datetime.datetime(2026, 6, 16, 1, 0)),
    (39, "G", "Belgium", "Iran", datetime.datetime(2026, 6, 21, 19, 0)),
    (40, "G", "New Zealand", "Egypt", datetime.datetime(2026, 6, 22, 1, 0)),
    (41, "G", "Egypt", "Iran", datetime.datetime(2026, 6, 27, 3, 0)),
    (42, "G", "New Zealand", "Belgium", datetime.datetime(2026, 6, 27, 3, 0)),
    (43, "H", "Spain", "Cape Verde", datetime.datetime(2026, 6, 15, 16, 0)),
    (44, "H", "Saudi Arabia", "Uruguay", datetime.datetime(2026, 6, 15, 22, 0)),
    (45, "H", "Spain", "Saudi Arabia", datetime.datetime(2026, 6, 21, 16, 0)),
    (46, "H", "Uruguay", "Cape Verde", datetime.datetime(2026, 6, 21, 22, 0)),
    (47, "H", "Cape Verde", "Saudi Arabia", datetime.datetime(2026, 6, 27, 0, 0)),
    (48, "H", "Uruguay", "Spain", datetime.datetime(2026, 6, 27, 0, 0)),
    (49, "I", "France", "Senegal", datetime.datetime(2026, 6, 16, 19, 0)),
    (50, "I", "Iraq", "Norway", datetime.datetime(2026, 6, 16, 22, 0)),
    (51, "I", "France", "Iraq", datetime.datetime(2026, 6, 22, 21, 0)),
    (52, "I", "Norway", "Senegal", datetime.datetime(2026, 6, 23, 0, 0)),
    (53, "I", "Norway", "France", datetime.datetime(2026, 6, 26, 19, 0)),
    (54, "I", "Senegal", "Iraq", datetime.datetime(2026, 6, 26, 19, 0)),
    (55, "J", "Argentina", "Algeria", datetime.datetime(2026, 6, 17, 1, 0)),
    (56, "J", "Austria", "Jordan", datetime.datetime(2026, 6, 17, 4, 0)),
    (57, "J", "Argentina", "Austria", datetime.datetime(2026, 6, 22, 17, 0)),
    (58, "J", "Jordan", "Algeria", datetime.datetime(2026, 6, 23, 3, 0)),
    (59, "J", "Algeria", "Austria", datetime.datetime(2026, 6, 28, 2, 0)),
    (60, "J", "Jordan", "Argentina", datetime.datetime(2026, 6, 28, 2, 0)),
    (61, "K", "Portugal", "DR Congo", datetime.datetime(2026, 6, 17, 17, 0)),
    (62, "K", "Uzbekistan", "Colombia", datetime.datetime(2026, 6, 18, 2, 0)),
    (63, "K", "Portugal", "Uzbekistan", datetime.datetime(2026, 6, 23, 17, 0)),
    (64, "K", "Colombia", "DR Congo", datetime.datetime(2026, 6, 24, 2, 0)),
    (65, "K", "Colombia", "Portugal", datetime.datetime(2026, 6, 27, 23, 30)),
    (66, "K", "DR Congo", "Uzbekistan", datetime.datetime(2026, 6, 27, 23, 30)),
    (67, "L", "England", "Croatia", datetime.datetime(2026, 6, 17, 20, 0)),
    (68, "L", "Ghana", "Panama", datetime.datetime(2026, 6, 17, 23, 0)),
    (69, "L", "England", "Ghana", datetime.datetime(2026, 6, 23, 20, 0)),
    (70, "L", "Panama", "Croatia", datetime.datetime(2026, 6, 23, 23, 0)),
    (71, "L", "Panama", "England", datetime.datetime(2026, 6, 27, 21, 0)),
    (72, "L", "Croatia", "Ghana", datetime.datetime(2026, 6, 27, 21, 0)),
]

KNOCKOUT_MATCHES = [
    (73, "round_of_32", "2A", "2B", datetime.datetime(2026, 6, 28, 19, 0)),
    (74, "round_of_32", "1E", "3A/B/C/D/F", datetime.datetime(2026, 6, 29, 20, 30)),
    (75, "round_of_32", "1F", "2C", datetime.datetime(2026, 6, 30, 1, 0)),
    (76, "round_of_32", "1C", "2F", datetime.datetime(2026, 6, 29, 17, 0)),
    (77, "round_of_32", "1I", "3C/D/F/G/H", datetime.datetime(2026, 6, 30, 21, 0)),
    (78, "round_of_32", "2E", "2I", datetime.datetime(2026, 6, 30, 17, 0)),
    (79, "round_of_32", "1A", "3C/E/F/H/I", datetime.datetime(2026, 7, 1, 1, 0)),
    (80, "round_of_32", "1L", "3E/H/I/J/K", datetime.datetime(2026, 7, 1, 16, 0)),
    (81, "round_of_32", "1D", "3B/E/F/I/J", datetime.datetime(2026, 7, 2, 0, 0)),
    (82, "round_of_32", "1G", "3A/E/H/I/J", datetime.datetime(2026, 7, 1, 20, 0)),
    (83, "round_of_32", "2K", "2L", datetime.datetime(2026, 7, 2, 23, 0)),
    (84, "round_of_32", "1H", "2J", datetime.datetime(2026, 7, 2, 19, 0)),
    (85, "round_of_32", "1B", "3E/F/G/I/J", datetime.datetime(2026, 7, 3, 3, 0)),
    (86, "round_of_32", "1J", "2H", datetime.datetime(2026, 7, 3, 22, 0)),
    (87, "round_of_32", "1K", "3D/E/I/J/L", datetime.datetime(2026, 7, 4, 1, 30)),
    (88, "round_of_32", "2D", "2G", datetime.datetime(2026, 7, 3, 18, 0)),
    (89, "round_of_16", "W74", "W77", datetime.datetime(2026, 7, 4, 21, 0)),
    (90, "round_of_16", "W73", "W75", datetime.datetime(2026, 7, 4, 17, 0)),
    (91, "round_of_16", "W76", "W78", datetime.datetime(2026, 7, 5, 20, 0)),
    (92, "round_of_16", "W79", "W80", datetime.datetime(2026, 7, 6, 0, 0)),
    (93, "round_of_16", "W83", "W84", datetime.datetime(2026, 7, 6, 19, 0)),
    (94, "round_of_16", "W81", "W82", datetime.datetime(2026, 7, 7, 0, 0)),
    (95, "round_of_16", "W86", "W88", datetime.datetime(2026, 7, 7, 16, 0)),
    (96, "round_of_16", "W85", "W87", datetime.datetime(2026, 7, 7, 20, 0)),
    (97, "quarter_final", "W89", "W90", datetime.datetime(2026, 7, 9, 20, 0)),
    (98, "quarter_final", "W93", "W94", datetime.datetime(2026, 7, 10, 19, 0)),
    (99, "quarter_final", "W91", "W92", datetime.datetime(2026, 7, 11, 21, 0)),
    (100, "quarter_final", "W95", "W96", datetime.datetime(2026, 7, 12, 1, 0)),
    (101, "semi_final", "W97", "W98", datetime.datetime(2026, 7, 14, 19, 0)),
    (102, "semi_final", "W99", "W100", datetime.datetime(2026, 7, 15, 19, 0)),
    (103, "match_for_third_place", "L101", "L102", datetime.datetime(2026, 7, 18, 21, 0)),
    (104, "final", "W101", "W102", datetime.datetime(2026, 7, 19, 19, 0)),
]

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


def seed_group_matches(db):
    """Create all 72 group-stage matches."""
    existing = db.query(Match.match_number).filter(Match.round == "group").count()
    if existing == 72:
        print("[seed] Group matches already present, skipping")
        return

    matches = []
    for match_num, group, home_name, away_name, match_date in GROUP_MATCHES:
        home_id = _get_team_id(db, home_name)
        away_id = _get_team_id(db, away_name)
        matches.append(
            Match(
                match_number=match_num,
                group=group,
                round="group",
                home_team_id=home_id,
                away_team_id=away_id,
                match_date=match_date,
                status="scheduled",
            )
        )

    db.add_all(matches)
    db.commit()
    print(f"[seed] Inserted {len(matches)} group-stage matches")


def seed_knockout_matches(db):
    """Create all 32 knockout matches with placeholders."""
    existing = db.query(Match.match_number).filter(Match.round != "group").count()
    if existing == 32:
        print("[seed] Knockout matches already present, skipping")
        return

    matches = []
    for match_num, round_name, home_name, away_name, match_date in KNOCKOUT_MATCHES:
        home_id = _get_team_id(db, home_name)
        away_id = _get_team_id(db, away_name)
        matches.append(
            Match(
                match_number=match_num,
                group=None,
                round=round_name,
                home_team_id=home_id,
                away_team_id=away_id,
                home_team_placeholder=home_name if home_id is None else None,
                away_team_placeholder=away_name if away_id is None else None,
                match_date=match_date,
                status="scheduled",
            )
        )

    db.add_all(matches)
    db.commit()
    print(f"[seed] Inserted {len(matches)} knockout matches")


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