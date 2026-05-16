#!/usr/bin/env python3
"""
parse_polling_stations.py

Parses Databank/Admin/Polling_station_appointments.txt into a structured CSV.

Input:  OCR scan of the 1918 NZ Gazette polling-places schedule.
        Pages 1-2 are single-column; pages 3+ are two-column (interleaved OCR).

Output: Databank/Admin/polling_lookup.csv
        Columns: page, electoral_district, locality, venue_type, entry_raw

Strategy
--------
On two-column pages the OCR interleaves left and right columns on the same
text line, separated by ". " (period + space).  District headers may appear
anywhere within a line.

We therefore:
  1. Split each raw line on the hard delimiters ". "  "| "  "; "
     to produce short sub-fragments.
  2. Check whether each sub-fragment STARTS with a district header.
     If so, update current district and strip the header.
  3. Try to parse any remaining content as a polling-place entry.

This prevents the regex greedily absorbing preceding entry text into the
district name (e.g. "Eastern Boundary. Pahiatua Electoral District—" splits
into ["Eastern Boundary", "Pahiatua Electoral District—"] and the district
name "Pahiatua" is cleanly captured).
"""

import csv
import re
from pathlib import Path

INPUT  = Path(__file__).parent / "Databank" / "Admin" / "Polling_station_appointments.txt"
OUTPUT = Path(__file__).parent / "Databank" / "Admin" / "polling_lookup.csv"

# ---------------------------------------------------------------------------
# Known / canonical electoral district names for fuzzy normalisation
# ---------------------------------------------------------------------------
KNOWN_DISTRICTS = {
    "bay of islands", "marsden", "kaipara", "waitemata", "parnell",
    "auckland east", "auckland central", "auckland west",
    "manukau", "franklin", "raglan", "thames",
    "tauranga", "waikato", "bay of plenty",
    "taumarunui", "gisborne", "hawke's bay", "napier",
    "waipawa", "pahiatua", "wairarapa", "hutt", "otaki",
    "wellington north", "wellington central", "wellington east",
    "nelson", "motueka", "buller", "grey", "westland",
    "wairau", "hurunui", "kaiapoi",
    "christchurch north", "christchurch east", "christchurch south",
    "riccarton", "avon", "lyttelton", "ellesmere", "selwyn",
    "timaru", "temuka", "waitaki",
    "otago central", "dunedin north", "dunedin west",
    "dunedin central", "dunedin south", "chalmers",
    "wakatipu", "wallace", "awarua",
    "stratford", "taranaki", "egmont", "patea",
    "wanganui", "waimarino", "oroua", "rangitikei", "palmerston",
}

def normalise_district(name: str) -> str:
    """
    Return a cleaned district name.
    If the cleaned name is in KNOWN_DISTRICTS (or close enough), use it.
    Otherwise return the cleaned original.
    """
    # Strip OCR noise characters from boundaries
    name = name.strip(" .,'|;`'\"-–—")
    # Collapse whitespace
    name = re.sub(r'\s+', ' ', name).strip()
    # Capitalise each word
    name = name.title()
    return name

# ---------------------------------------------------------------------------
# District header — must appear at/near the START of a fragment.
# Allows lowercase connectives (of, the, and) so "Bay of Islands" works.
# Anchored version used for start-of-fragment; mid version for mid-fragment.
# ---------------------------------------------------------------------------
_DIST_NAME = (
    r'('
    r'[A-Z][A-Za-z\'\.]*'                       # first capitalised word
    r'(?:\s+(?:of|the|de|and|[A-Z][A-Za-z\'\.]+)){0,4}'  # optional more words
    r'\s+'
    r')'
)
DISTRICT_RE     = re.compile(r'^'  + _DIST_NAME + r'[EH][a-zA-Z]*oral\s+District\s*[—\-–]')
DISTRICT_RE_MID = re.compile(_DIST_NAME + r'[EH][a-zA-Z]*oral\s+District\s*[—\-–]')

# Lines that are pure OCR noise / page headers
NOISE_RE = re.compile(
    r'^(?:'
    r'=====|'
    r'[0-9\s]+$|'
    r'THE NEW ZEALAND GAZETTE|'
    r'Polling-places appointed|'
    r'SUPPLEMENT|WELLINGTON|Published by Authority|'
    r'LIVERPOOL|Governor-General|'
    r'Legislature Act|electoral districts|'
    r'herein specified|schedule hereto|'
    r'by appoint|do hereby|Dominion|'
    r'Humb,|GAZEP|'
    r'[A-Z\s,\.]{30,}$'
    r')',
    re.IGNORECASE,
)

# Entry must contain a comma and start with a recognisable venue prefix
ENTRY_START_RE = re.compile(
    r'^(?:The\s+|No\.\s*\d+\s+|Mr[s]?\.\s+|[A-Z][a-z]+(?:\'s)?\s+\w)',
    re.IGNORECASE,
)

# Venue type prefix → clean label
VENUE_TYPES = [
    (r'No\.\s*\d+\s+Public School',    'Public School'),
    (r'The Public School',              'Public School'),
    (r'The Native School',              'Native School'),
    (r'The Catholic School',            'Catholic School'),
    (r'The [\w\s\-]+ School\b',         'School'),
    (r'The Court.?house',               'Courthouse'),
    (r'The Town Hall',                  'Town Hall'),
    (r'Town Hall',                      'Town Hall'),
    (r'The Council Chambers',           'Council Chambers'),
    (r'The County Council Chambers',    'Council Chambers'),
    (r'The Borough Council Chambers',   'Council Chambers'),
    (r'The Road Board Office',          'Board Office'),
    (r'The Town Board Office',          'Board Office'),
    (r'The Board Office',               'Board Office'),
    (r'The Public Hall',                'Public Hall'),
    (r'The Public Library',             'Library'),
    (r'The Library',                    'Library'),
    (r'The Post.?[Oo]ffice',            'Post Office'),
    (r'Post.?[Oo]ffice',               'Post Office'),
    (r'The Railway.?[Ss]tation',        'Railway Station'),
    (r'Railway.?[Ss]tation',           'Railway Station'),
    (r'The Drill.?(?:Hall|shed)',        'Drill Hall'),
    (r'The Garrison Hall',              'Hall'),
    (r'The [\w\'\-\s]+ Hall',           'Hall'),
    (r'[\w\'\-]+\'s?\s+Hall',          'Hall'),
    (r'The Theatre',                    'Theatre'),
    (r'The Atheneum',                   'Hall'),
    (r'The Schoolroom',                 'Schoolroom'),
    (r'The [\w\s\-]+ Institute',        'Institute'),
    (r'The [\w\s\-]+ Club',             'Club Rooms'),
    (r'Goods.?shed',                    'Goods Shed'),
    (r'The Homestead',                  'Private dwelling'),
    (r'Mr[s]?\.',                       'Private dwelling'),
]
VENUE_TYPE_RES = [(re.compile('^' + p, re.IGNORECASE), label)
                  for p, label in VENUE_TYPES]


def classify_venue(entry: str) -> str:
    s = entry.strip()
    for pat, label in VENUE_TYPE_RES:
        if pat.match(s):
            return label
    return 'Other'


def extract_locality(entry: str) -> str:
    s = re.sub(r'\s*\(principal\)', '', entry, flags=re.IGNORECASE)
    s = re.sub(r'\s*\([^\)]{1,50}\)', '', s)
    s = s.strip(' .,;|\'`')
    parts = [p.strip(' .,;\'`') for p in s.split(',')]
    candidates = [p for p in parts[1:] if p and len(p) > 1]
    if not candidates:
        return ''
    loc = candidates[-1].strip()
    # Drop trailing single OCR characters
    loc = re.sub(r'\s+[A-Za-z]$', '', loc).strip()
    return loc


def fragment_district_and_text(fragment: str) -> tuple[str | None, str]:
    """
    If the fragment starts (after stripping noise chars) with a district header,
    return (district_name, remaining_text).
    Otherwise return (None, fragment).
    """
    s = fragment.strip(" .,'|;`'\"-–—")
    m = DISTRICT_RE.match(s)
    if m:
        dist = normalise_district(m.group(1))
        rest = s[m.end():].strip(" .,'|;`'\"-–—")
        return dist, rest
    return None, fragment


def is_valid_entry(s: str) -> bool:
    s = s.strip()
    return (
        len(s) > 10
        and ',' in s
        and bool(ENTRY_START_RE.match(s))
    )


def parse_file(path: Path) -> list[dict]:
    records = []
    current_page     = 0
    current_district = 'Unknown'

    with open(path, encoding='utf-8', errors='replace') as f:
        lines = f.readlines()

    for raw_line in lines:
        line = raw_line.rstrip('\n')
        stripped = line.strip()

        # Page marker
        pm = re.match(r'=====\s*PAGE\s+(\d+)\s*=====', stripped)
        if pm:
            current_page = int(pm.group(1))
            continue

        if not stripped or NOISE_RE.match(stripped) or len(stripped) < 8:
            continue

        # ---------------------------------------------------------------
        # Step 1: split raw line into sub-fragments on hard delimiters.
        # ". " splits entries on two-column pages; "| " and "; " are OCR
        # column separators.
        # We split on ". " only when followed by a capital letter.
        # ---------------------------------------------------------------
        sub_fragments = re.split(r'\.\s+(?=[A-Z])|[|;]\s+', line)

        # ---------------------------------------------------------------
        # Step 2: for each sub-fragment, detect district headers then entries
        # ---------------------------------------------------------------
        for frag in sub_fragments:
            frag = frag.strip()
            if not frag:
                continue

            # Check for district header at start of fragment
            dist_name, text = fragment_district_and_text(frag)
            if dist_name:
                current_district = dist_name

            # Also check for district header mid-fragment (e.g. if ". " split
            # didn't isolate it cleanly)
            else:
                mm = DISTRICT_RE_MID.search(frag)
                if mm:
                    # Text before the header
                    before = frag[:mm.start()].strip()
                    if is_valid_entry(before):
                        text = before
                    else:
                        text = ''
                    current_district = normalise_district(mm.group(1))
                    after = frag[mm.end():].strip()
                    if after:
                        text = (text + ' ' + after).strip() if text else after
                else:
                    text = frag

            # Try to parse text as an entry
            text = text.strip(" .,'|;`'\"-–—")
            if is_valid_entry(text):
                locality   = extract_locality(text)
                venue_type = classify_venue(text)
                if locality and len(locality) > 1:
                    records.append({
                        'page':               current_page,
                        'electoral_district': current_district,
                        'locality':           locality,
                        'venue_type':         venue_type,
                        'entry_raw':          text,
                    })

    return records


def main():
    print(f"Parsing {INPUT.name} …")
    records = parse_file(INPUT)
    print(f"  {len(records):,} entries found (before dedup)")

    seen: set[tuple] = set()
    unique = []
    for r in records:
        key = (r['electoral_district'].lower(), r['locality'].lower())
        if key not in seen:
            seen.add(key)
            unique.append(r)

    print(f"  {len(unique):,} unique (district, locality) pairs")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(
            f,
            fieldnames=['page', 'electoral_district', 'locality', 'venue_type', 'entry_raw'],
        )
        writer.writeheader()
        writer.writerows(unique)

    print(f"Written → {OUTPUT}")

    # Summary by district
    by_dist: dict[str, int] = {}
    for r in unique:
        d = r['electoral_district']
        by_dist[d] = by_dist.get(d, 0) + 1

    print(f"\n{'Electoral District':<40} {'Localities':>10}")
    print('-' * 52)
    for d, n in sorted(by_dist.items(), key=lambda x: x[0]):
        print(f"  {d:<38} {n:>10}")


if __name__ == '__main__':
    main()
