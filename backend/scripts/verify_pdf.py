#!/usr/bin/env python3
"""Verify seeded matches against FIFA PDF by converting PDF times to UTC."""
import sys, datetime, re
sys.path.insert(0, '/home/pex/vmtips/backend')

from database import SessionLocal
from models import Match, Team

db = SessionLocal()

# Our group matches
our_matches = {}
for m in db.query(Match).filter(Match.round == 'group').all():
    home = db.query(Team).filter(Team.id == m.home_team_id).first()
    away = db.query(Team).filter(Team.id == m.away_team_id).first()
    pair = frozenset({home.code if home else '?', away.code if away else '?'})
    # Store as UTC datetime
    our_matches[pair] = {
        'match_number': m.match_number,
        'datetime': m.match_date,
    }
db.close()

# PDF matches — parse with times and convert to UTC
import pymupdf
doc = pymupdf.open("/home/pex/vmtips/docs/Scores & Fixtures _ FIFA World Cup 2026™.pdf")
pdf_matches = {}
current_date = None

for page in doc:
    text = page.get_text()
    lines = text.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        date_match = re.match(r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+(\d+)\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(2026)', line)
        if date_match:
            _, day, month, year = date_match.groups()
            month_num = {'January':1,'February':2,'March':3,'April':4,'May':5,'June':6,
                        'July':7,'August':8,'September':9,'October':10,'November':11,'December':12}[month]
            current_date = datetime.date(int(year), month_num, int(day))
            i += 1
            continue
        if i + 2 < len(lines):
            t1 = line
            time_line = lines[i+1].strip()
            t2 = lines[i+2].strip()
            if re.match(r'^[A-Z]{3}$', t1) and re.match(r'^\d{2}:\d{2}$', time_line) and re.match(r'^[A-Z]{3}$', t2):
                if current_date:
                    hh, mm = map(int, time_line.split(':'))
                    # PDF shows times in user's local timezone (CET/CEST, UTC+1 or UTC+2)
                    # For June 2026, CEST is UTC+2
                    # Convert PDF local time to UTC by subtracting 2 hours
                    utc_hh = hh - 2
                    pdf_date = current_date
                    if utc_hh < 0:
                        utc_hh += 24
                        pdf_date = pdf_date - datetime.timedelta(days=1)
                    pdf_dt = datetime.datetime(pdf_date.year, pdf_date.month, pdf_date.day, utc_hh, mm)
                    pair = frozenset({t1, t2})
                    pdf_matches[pair] = {
                        'datetime': pdf_dt,
                    }
                i += 3
                continue
        i += 1

doc.close()

print(f"Our group matches:   {len(our_matches)}")
print(f"PDF group matches:   {len(pdf_matches)}")
print()

# Compare by UTC datetime
mismatches = []
only_in_ours = []
only_in_pdf = []

for pair, om in our_matches.items():
    if pair not in pdf_matches:
        only_in_ours.append(f"Match {om['match_number']}: {om['datetime']} {list(pair)[0]} vs {list(pair)[1]}")
    else:
        pm = pdf_matches[pair]
        # Allow 1 hour tolerance for timezone uncertainty
        diff = abs((om['datetime'] - pm['datetime']).total_seconds())
        if diff > 3600:
            mismatches.append({
                'pair': pair,
                'our': f"{om['datetime']} UTC",
                'pdf': f"{pm['datetime']} UTC (converted from PDF)",
                'diff_hours': diff / 3600,
            })

for pair, pm in pdf_matches.items():
    if pair not in our_matches:
        only_in_pdf.append(f"{pm['datetime']} {list(pair)[0]} vs {list(pair)[1]}")

if only_in_ours:
    print(f"⚠️ {len(only_in_ours)} matches only in our seed:")
    for m in only_in_ours[:10]:
        print(f"  {m}")

if only_in_pdf:
    print(f"⚠️ {len(only_in_pdf)} matches only in PDF:")
    for m in only_in_pdf[:10]:
        print(f"  {m}")

if mismatches:
    print(f"\n❌ {len(mismatches)} time mismatches (>1h difference):")
    for m in mismatches[:20]:
        print(f"  {m['pair']}: OUR={m['our']} | PDF={m['pdf']} [diff={m['diff_hours']:.1f}h]")
else:
    print("\n✅ All team pairs match with correct UTC times!")

if not mismatches and not only_in_ours and not only_in_pdf:
    print("\n✅✅ PERFECT MATCH: All 72 group matches match FIFA PDF!")
    sys.exit(0)
else:
    sys.exit(1)
