#!/usr/bin/env python3
"""
verify_firecrawl.py
Fetch FIFA World Cup 2026 fixtures via Firecrawl and compare with DB.
Caches raw responses locally to save Firecrawl quota.

Usage from backend directory:
    .venv/bin/python scripts/verify_firecrawl.py
    .venv/bin/python scripts/verify_firecrawl.py --no-cache   # force fresh fetch
    .venv/bin/python scripts/verify_firecrawl.py --dump       # save markdown to file
    .venv/bin/python scripts/verify_firecrawl.py --dry-run    # fetch + parse only, no DB
"""
import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request
from datetime import date, datetime, timedelta
from collections import defaultdict

# ---------------------------------------------------------------------------
# CLI flags
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser(description="Verify seed data against FIFA.com")
parser.add_argument("--no-cache", action="store_true", help="Force fresh Firecrawl fetch")
parser.add_argument("--dump", action="store_true", help="Write raw markdown to .cache/fifa_markdown.txt")
parser.add_argument("--dry-run", action="store_true", help="Only fetch/parse, skip DB comparison")
args = parser.parse_args()

# ---------------------------------------------------------------------------
# 1. Cache directory
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(SCRIPT_DIR, "..")
CACHE_DIR = os.path.join(BACKEND_DIR, ".cache")
os.makedirs(CACHE_DIR, exist_ok=True)

FIFA_URL = (
    "https://www.fifa.com/en/tournaments/mens/worldcup"
    "/canadamexicousa2026/scores-fixtures?country=SE&wtw-filter=ALL"
)

# Cache key based on the URL
CACHE_KEY = hashlib.sha256(FIFA_URL.encode()).hexdigest()[:16]
CACHE_JSON = os.path.join(CACHE_DIR, f"fifa_{CACHE_KEY}.json")
CACHE_MD  = os.path.join(CACHE_DIR, "fifa_markdown.txt")

# ---------------------------------------------------------------------------
# 2. Load Firecrawl API key from ~/.hermes/.env
# ---------------------------------------------------------------------------
FIRECRAWL_KEY = None
env_path = os.path.expanduser("~/.hermes/.env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            if line.startswith("FIRECRAWL_API_KEY="):
                FIRECRAWL_KEY = line.strip().split("=", 1)[1]
                break

if not FIRECRAWL_KEY:
    print("Error: FIRECRAWL_API_KEY not found in ~/.hermes/.env")
    sys.exit(1)

# ---------------------------------------------------------------------------
# 3. Fetch from cache or Firecrawl
# ---------------------------------------------------------------------------
markdown = None

if not args.no_cache and os.path.exists(CACHE_JSON):
    print(f"Using cached response: {CACHE_JSON}")
    with open(CACHE_JSON) as f:
        data = json.load(f)
    if data.get("success") and data.get("data", {}).get("markdown"):
        markdown = data["data"]["markdown"]
    else:
        print("  Cache invalid, will refetch.")

if markdown is None:
    print("Fetching FIFA fixtures via Firecrawl ...")
    req = urllib.request.Request(
        "https://api.firecrawl.dev/v1/scrape",
        data=json.dumps({"url": FIFA_URL, "formats": ["markdown"]}).encode(),
        headers={"Authorization": f"Bearer {FIRECRAWL_KEY}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req, timeout=60)
        data = json.loads(resp.read())
    except Exception as e:
        print("Request failed:", e)
        sys.exit(1)

    if not data.get("success"):
        print("Firecrawl error:", data.get("error"))
        sys.exit(1)

    # Save to cache
    with open(CACHE_JSON, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  -> Cached response to {CACHE_JSON}")

    markdown = data["data"]["markdown"]

print(f"  -> Markdown length: {len(markdown)} chars\n")

# Optional dump for manual inspection
if args.dump:
    with open(CACHE_MD, "w") as f:
        f.write(markdown)
    print(f"  -> Dumped markdown to {CACHE_MD}\n")

# ---------------------------------------------------------------------------
# 4. Parse matches from raw markdown string
# ---------------------------------------------------------------------------
# FIFA markdown uses \\n\\n as separator between elements.
SEP = bytes([92, 92, 10, 92, 92, 10]).decode()

MONTH_MAP = {
    "January": 1, "February": 2, "March": 3, "April": 4,
    "May": 5, "June": 6, "July": 7, "August": 8,
    "September": 9, "October": 10, "November": 11, "December": 12,
}

# 4a. Find all date markers with their positions
day_re = re.compile(
    r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+"
    r"(\d+)\s+(June|July)\s+2026$",
    re.MULTILINE,
)

dates = []
for m in day_re.finditer(markdown):
    d = date(2026, MONTH_MAP[m.group(3)], int(m.group(2)))
    dates.append((m.start(), d))
dates.sort()
print(f"Found {len(dates)} date markers")

# 4b. Find all match blocks
# Pattern: [HOME_CODE SEP HOME_NAME SEP TIME SEP AWAY_CODE SEP AWAY_NAME SEP "First Stage·" SEP "Group X·" SEP VENUE](URL)
# We capture: home_code, time, away_code, group
match_re = re.compile(
    r"\[([A-Z]{3})" + re.escape(SEP) + r"[^" + re.escape(chr(92)) + r"]+" + re.escape(SEP) +
    r"(\d{2}:\d{2})" + re.escape(SEP) +
    r"([A-Z]{3})" + re.escape(SEP) + r"[^" + re.escape(chr(92)) + r"]+" + re.escape(SEP) +
    r"First Stage\xb7" + re.escape(SEP) + r"Group\s+([A-L])\xb7"
)

matches = []
for m in match_re.finditer(markdown):
    pos = m.start()
    # Find the most recent date before this match
    current_date = None
    for date_pos, d in dates:
        if date_pos > pos:
            break
        current_date = d

    matches.append({
        "date": current_date,
        "time": m.group(2),
        "home_code": m.group(1),
        "away_code": m.group(3),
        "group": m.group(4),
    })

print(f"Parsed {len(matches)} group-stage matches from Firecrawl\n")
for m in matches[:10]:
    print(f"  {m['date']} {m['time']:5s}  {m['home_code']:3s} vs {m['away_code']:3s}   Group {m['group']}")
print()

# ---------------------------------------------------------------------------
# 5. Build FIFA lookup by team-pair + UTC
#    The FIFA page currently returns all times in EDT (UTC-4).
# ---------------------------------------------------------------------------
fifa_lookup = defaultdict(list)
for m in matches:
    hh, mm = int(m["time"][:2]), int(m["time"][3:])
    # FIFA page shows EDT (UTC-4); add 4h to get UTC
    utc_hh = hh + 4
    m_date = m["date"]
    if utc_hh >= 24:
        m_date = m["date"] + timedelta(days=1)
        utc_hh -= 24
    dt = datetime(m_date.year, m_date.month, m_date.day, utc_hh, mm)
    fifa_lookup[frozenset({m["home_code"], m["away_code"]})].append(dt)

# ---------------------------------------------------------------------------
# 6. Compare against DB (unless --dry-run)
# ---------------------------------------------------------------------------
if args.dry_run:
    print("--dry-run: skipping DB comparison")
    sys.exit(0)

sys.path.insert(0, BACKEND_DIR)

from database import engine
from sqlalchemy import text
from sqlalchemy.orm import Session

session = Session(engine)

db_matches = session.execute(
    text(
        'SELECT m.match_number, m."group" AS group_code, '
        "ht.code AS home_code, at.code AS away_code, m.match_date "
        "FROM matches m "
        "JOIN teams ht ON m.home_team_id = ht.id "
        "JOIN teams at ON m.away_team_id = at.id "
        "WHERE m.round = 'group' ORDER BY m.match_number"
    )
).mappings().all()

mismatches = not_found = matches_found = 0

for dbm in db_matches:
    pair = frozenset({dbm["home_code"], dbm["away_code"]})
    db_dt = dbm["match_date"]
    # DB may return match_date as string — parse if needed
    if isinstance(db_dt, str):
        db_dt = datetime.fromisoformat(db_dt.replace(" ", "T").replace("Z", "+00:00"))
    fifa_dts = fifa_lookup.get(pair)

    if not fifa_dts:
        print(
            f"  ❌ NOT FOUND: Match {dbm['match_number']:2d} "
            f"Group {dbm['group_code']}  {dbm['home_code']} vs {dbm['away_code']}"
        )
        not_found += 1
        continue

    best = min(fifa_dts, key=lambda f: abs((f - db_dt).total_seconds()))
    diff = abs((best - db_dt).total_seconds())

    if diff <= 3600:
        matches_found += 1
    else:
        print(
            f"  ⚠️ TIME DIFF: Match {dbm['match_number']:2d} "
            f"Group {dbm['group_code']}  {dbm['home_code']} vs {dbm['away_code']}"
        )
        print(f"       DB:   {dbm['match_date']} UTC")
        print(f"       FIFA: {best} UTC")
        mismatches += 1

session.close()

# ---------------------------------------------------------------------------
# 7. Summary
# ---------------------------------------------------------------------------
print()
print("=" * 60)
print("  FIFA Firecrawl vs VMTips Database")
print("  -----------------------------------")
print(f"  Total DB group matches:  {len(db_matches)}")
print(f"  Parsed from FIFA:        {len(matches)}")
print(f"  ✅ Perfect:              {matches_found}")
print(f"  ⚠️  Time diff:          {mismatches}")
print(f"  ❌ Missing in FIFA:     {not_found}")
if mismatches == 0 and not_found == 0:
    print("  🎉 ALL CLEAR!")
print("=" * 60)
