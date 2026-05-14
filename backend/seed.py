"""
Seed script for the VMTips database.
Populates teams, groups, and all 104 World Cup 2026 matches.
Run: cd backend && uv run python seed.py
"""
import datetime
from database import SessionLocal, engine, Base
from models import Team, Match

# ─────────────────────────────────────────────────────────────
# 48 teams across 12 groups (A–L).
# Update this list when qualification is fully known.
# Each entry: (name, fifa_code, group, flag_emoji)
# ─────────────────────────────────────────────────────────────
TEAM_DATA = [
    # Group A
    ("Qatar", "QAT", "A", "🇶🇦"),
    ("Ecuador", "ECU", "A", "🇪🇨"),
    ("Senegal", "SEN", "A", "🇸🇳"),
    ("Netherlands", "NED", "A", "🇳🇱"),
    # Group B
    ("England", "ENG", "B", "🏴󠁧󠁢󠁥󠁮󠁧󠁿"),
    ("Iran", "IRN", "B", "🇮🇷"),
    ("USA", "USA", "B", "🇺🇸"),
    ("Wales", "WAL", "B", "🏴󠁧󠁢󠁷󠁬󠁳󠁿"),
    # Group C
    ("Argentina", "ARG", "C", "🇦🇷"),
    ("Saudi Arabia", "KSA", "C", "🇸🇦"),
    ("Mexico", "MEX", "C", "🇲🇽"),
    ("Poland", "POL", "C", "🇵🇱"),
    # Group D
    ("France", "FRA", "D", "🇫🇷"),
    ("Australia", "AUS", "D", "🇦🇺"),
    ("Denmark", "DEN", "D", "🇩🇰"),
    ("Tunisia", "TUN", "D", "🇹🇳"),
    # Group E
    ("Spain", "ESP", "E", "🇪🇸"),
    ("Costa Rica", "CRC", "E", "🇨🇷"),
    ("Germany", "GER", "E", "🇩🇪"),
    ("Japan", "JPN", "E", "🇯🇵"),
    # Group F
    ("Belgium", "BEL", "F", "🇧🇪"),
    ("Canada", "CAN", "F", "🇨🇦"),
    ("Morocco", "MAR", "F", "🇲🇦"),
    ("Croatia", "CRO", "F", "🇭🇷"),
    # Group G
    ("Brazil", "BRA", "G", "🇧🇷"),
    ("Serbia", "SRB", "G", "🇷🇸"),
    ("Switzerland", "SUI", "G", "🇨🇭"),
    ("Cameroon", "CMR", "G", "🇨🇲"),
    # Group H
    ("Portugal", "POR", "H", "🇵🇹"),
    ("Ghana", "GHA", "H", "🇬🇭"),
    ("Uruguay", "URU", "H", "🇺🇾"),
    ("South Korea", "KOR", "H", "🇰🇷"),
    # Group I
    ("Italy", "ITA", "I", "🇮🇹"),
    ("Ukraine", "UKR", "I", "🇺🇦"),
    ("Scotland", "SCO", "I", "🏴󠁧󠁢󠁳󠁣󠁴󠁿"),
    ("Turkey", "TUR", "I", "🇹🇷"),
    # Group J
    ("Sweden", "SWE", "J", "🇸🇪"),
    ("Norway", "NOR", "J", "🇳🇴"),
    ("Czech Republic", "CZE", "J", "🇨🇿"),
    ("Hungary", "HUN", "J", "🇭🇺"),
    # Group K
    ("Colombia", "COL", "K", "🇨🇴"),
    ("Peru", "PER", "K", "🇵🇪"),
    ("Chile", "CHI", "K", "🇨🇱"),
    ("Paraguay", "PAR", "K", "🇵🇾"),
    # Group L
    ("Nigeria", "NGA", "L", "🇳🇬"),
    ("Egypt", "EGY", "L", "🇪🇬"),
    ("Algeria", "ALG", "L", "🇩🇿"),
    ("Ivory Coast", "CIV", "L", "🇨🇮"),
]


def seed_teams(db):
    """Insert all 48 teams if not already present."""
    existing = {t.code for t in db.query(Team.code).all()}
    for name, code, group, flag in TEAM_DATA:
        if code not in existing:
            db.add(Team(name=name, code=code, group=group, flag_emoji=flag))
    db.commit()
    print(f"[seed] Inserted/updated {len(TEAM_DATA)} teams")


def _group_matches(db, group: str, match_num_start: int, day_offset: int):
    """Create the 6 round-robin matches for a single group."""
    teams = (
        db.query(Team)
        .filter(Team.group == group)
        .order_by(Team.id)
        .all()
    )
    if len(teams) != 4:
        raise ValueError(f"Group {group} must contain 4 teams")

    t1, t2, t3, t4 = teams
    base_date = datetime.datetime(2026, 6, 12) + datetime.timedelta(days=day_offset)

    fixtures = [
        (t1, t2), (t3, t4),
        (t1, t3), (t2, t4),
        (t1, t4), (t2, t3),
    ]
    matches = []
    for idx, (home, away) in enumerate(fixtures, start=match_num_start):
        matches.append(
            Match(
                match_number=idx,
                group=group,
                round="group",
                home_team_id=home.id,
                away_team_id=away.id,
                match_date=base_date + datetime.timedelta(hours=idx % 3 * 4),
                status="scheduled",
            )
        )
    return matches, match_num_start + len(fixtures)


def seed_group_matches(db):
    """Create all 72 group-stage matches."""
    existing = db.query(Match.match_number).filter(Match.round == "group").count()
    if existing == 72:
        print("[seed] Group matches already present, skipping")
        return

    match_num = 1
    matches = []
    day_offsets = {
        "A": 0, "B": 0, "C": 1, "D": 1,
        "E": 2, "F": 2, "G": 3, "H": 3,
        "I": 4, "J": 4, "K": 5, "L": 5,
    }
    for group in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"]:
        group_matches, match_num = _group_matches(db, group, match_num, day_offsets[group])
        matches.extend(group_matches)

    db.add_all(matches)
    db.commit()
    print(f"[seed] Inserted {len(matches)} group-stage matches")


def seed_knockout_matches(db):
    """Create all 32 knockout matches with placeholders."""
    existing = db.query(Match.match_number).filter(Match.round != "group").count()
    if existing == 32:
        print("[seed] Knockout matches already present, skipping")
        return

    base_date = datetime.datetime(2026, 6, 28, 16, 0, 0)
    round_schedule = [
        # (round_name, match_count, hours_between)
        ("ro32", 16, 4),
        ("ro16", 8, 8),
        ("qf", 4, 24),
        ("sf", 2, 48),
        ("3rd", 1, 24),
        ("final", 1, 48),
    ]

    match_num = 73
    matches = []
    current_date = base_date

    # Round of 32 — placeholders follow FIFA bracket format
    ro32_fixtures = [
        ("1A", "2B"), ("1C", "2D"), ("1E", "2F"), ("1G", "2H"),
        ("1I", "2J"), ("1K", "2L"), ("1B", "2A"), ("1D", "2C"),
        ("1F", "2E"), ("1H", "2G"), ("1J", "2I"), ("1L", "2K"),
        ("1A", "3C"), ("1B", "3D"), ("1E", "3G"), ("1F", "3H"),
    ]
    for home_ph, away_ph in ro32_fixtures:
        matches.append(
            Match(
                match_number=match_num,
                round="ro32",
                home_team_placeholder=home_ph,
                away_team_placeholder=away_ph,
                match_date=current_date,
                status="scheduled",
            )
        )
        match_num += 1
        current_date += datetime.timedelta(hours=4)

    # Round of 16
    current_date += datetime.timedelta(hours=8)
    for i in range(8):
        matches.append(
            Match(
                match_number=match_num,
                round="ro16",
                home_team_placeholder=f"W{i*2+89}",
                away_team_placeholder=f"W{i*2+90}",
                match_date=current_date,
                status="scheduled",
            )
        )
        match_num += 1
        current_date += datetime.timedelta(hours=8)

    # Quarterfinals
    current_date += datetime.timedelta(hours=24)
    for i in range(4):
        matches.append(
            Match(
                match_number=match_num,
                round="qf",
                home_team_placeholder=f"W{i*2+105}",
                away_team_placeholder=f"W{i*2+106}",
                match_date=current_date,
                status="scheduled",
            )
        )
        match_num += 1
        current_date += datetime.timedelta(hours=24)

    # Semifinals
    current_date += datetime.timedelta(hours=48)
    for i in range(2):
        matches.append(
            Match(
                match_number=match_num,
                round="sf",
                home_team_placeholder=f"W{i*2+113}",
                away_team_placeholder=f"W{i*2+114}",
                match_date=current_date,
                status="scheduled",
            )
        )
        match_num += 1
        current_date += datetime.timedelta(hours=48)

    # 3rd place
    matches.append(
        Match(
            match_number=match_num,
            round="3rd",
            home_team_placeholder="L117",
            away_team_placeholder="L118",
            match_date=current_date,
            status="scheduled",
        )
    )
    match_num += 1
    current_date += datetime.timedelta(hours=24)

    # Final
    matches.append(
        Match(
            match_number=match_num,
            round="final",
            home_team_placeholder="W117",
            away_team_placeholder="W118",
            match_date=current_date,
            status="scheduled",
        )
    )

    db.add_all(matches)
    db.commit()
    print(f"[seed] Inserted {len(matches)} knockout matches")


def main():
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        seed_teams(db)
        seed_group_matches(db)
        seed_knockout_matches(db)
        print("[seed] Done")
    finally:
        db.close()


if __name__ == "__main__":
    main()
