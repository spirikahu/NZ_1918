#!/usr/bin/env python3
"""
check_assignments.py

Cross-references county/borough assignments in Name_Matching_Results/*.csv
against small_cities.csv, which has ground-truth county data for ~1300 NZ
localities extracted from a 1918-era census publication.

For each school assigned to a county (not a borough/town district), the script:
  1. Cleans the school name down to its core locality
  2. Looks it up in small_cities (exact, then fuzzy)
  3. Compares the assigned county against the small_cities county
  4. Flags MISMATCH (different county found) or MULTI_MATCH (name appears in
     multiple counties and mine is one of them — worth reviewing)

Usage:
    python check_assignments.py [--include-unverified]

Output:
    check_results/mismatches.csv   — MISMATCHes and MULTI_MATCHes
    check_results/unverified.csv   — schools with no small_cities match (if flag set)
"""

import csv
import re
import sys
from pathlib import Path
from difflib import get_close_matches

BASE        = Path(__file__).parent
RESULTS_DIR = BASE / "Name_Matching_Results"
SMALL_CITIES = BASE / "Databank" / "Places" / "small_cities.csv"
OUT_DIR     = BASE / "check_results"

RESULT_FILES = sorted(RESULTS_DIR.glob("*_county_borough.csv")) + \
               [RESULTS_DIR / "county_borough_assignments.csv"]

FUZZY_CUTOFF = 0.85   # difflib ratio; lower = more matches, more false positives

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def strip_bom(s: str) -> str:
    return s.lstrip('﻿')


def normalise_county(raw: str) -> str:
    """'Patea County' → 'patea', 'Wairarapa South County' → 'wairarapa south'"""
    s = raw.strip()
    for suffix in (' County', ' Borough', ' Town District', ' Town Board'):
        if s.lower().endswith(suffix.lower()):
            s = s[: -len(suffix)]
    return s.strip().lower()


# Patterns to strip from school names to get the core locality
_STRIP = [
    r'\s+District High School.*',
    r'\s+High School.*',
    r'\s+Primary.*',
    r'\s*\([\d]+\)\s*and side school.*',
    r'\s*\([\d]+\)',              # trailing attendance numbers
    r'\s+[Ss]ee under\s+.*',
    r'\s*\(half-time\).*',
    r'\s+side school\b.*',
    r'\s+Infants?\'?s?\b.*',
    r'\s+Boys\'?\b.*',
    r'\s+Girls\'?\b.*',
    r'\s+Central\b.*',
    r',.*',                       # everything after first comma
]
_STRIP_RE = [re.compile(p, re.IGNORECASE) for p in _STRIP]


def clean_school_name(raw: str) -> str:
    s = raw.strip().strip('"')
    for pattern in _STRIP_RE:
        s = pattern.sub('', s)
    # Remove possessive apostrophes: Bull's → Bulls
    s = s.replace("'s", 's').replace("'", '')
    # Collapse whitespace
    s = re.sub(r'\s+', ' ', s).strip(' .,;-()')
    return s


def is_county_assignment(county_borough: str) -> bool:
    return 'county' in county_borough.lower()


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

def load_small_cities() -> dict[str, list[str]]:
    """Returns {lowercase_name: [county1, county2, ...]}."""
    lookup: dict[str, list[str]] = {}
    with open(SMALL_CITIES, newline='', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        next(reader)  # header
        for row in reader:
            if len(row) < 2:
                continue
            name  = row[0].strip()
            county = row[1].strip()
            if not name or not county:
                continue
            key = name.lower()
            lookup.setdefault(key, [])
            if county not in lookup[key]:
                lookup[key].append(county)
    return lookup


def load_results() -> list[dict]:
    records = []
    for path in RESULT_FILES:
        if not path.exists():
            continue
        # Derive a friendly district label from the filename
        stem = path.stem
        if stem == 'county_borough_assignments':
            district = 'Southland'
        else:
            district = stem.replace('_county_borough', '')
        with open(path, newline='', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                row['source_district'] = district
                records.append(row)
    return records


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    include_unverified = '--include-unverified' in sys.argv

    print(f"Loading small_cities …")
    sc = load_small_cities()
    sc_names = list(sc.keys())
    print(f"  {len(sc):,} locality names loaded")

    print(f"Loading assignment results …")
    records = load_results()
    county_records = [r for r in records if is_county_assignment(r.get('county_borough', ''))]
    print(f"  {len(records):,} total records; {len(county_records):,} county assignments to check")

    mismatches   = []
    unverified   = []
    match_count  = 0

    for rec in county_records:
        school_raw    = rec.get('school', '').strip()
        county_borough = rec.get('county_borough', '').strip()
        confidence    = rec.get('confidence', '').strip()
        district      = rec.get('source_district', '')

        if county_borough.lower() in ('unresolved', ''):
            continue

        my_county = normalise_county(county_borough)
        cleaned   = clean_school_name(school_raw)
        key       = cleaned.lower()

        # --- Lookup ---
        sc_counties  = None
        matched_name = None

        if key in sc:
            sc_counties  = sc[key]
            matched_name = cleaned
        else:
            close = get_close_matches(key, sc_names, n=1, cutoff=FUZZY_CUTOFF)
            if close:
                matched_name = close[0]
                sc_counties  = sc[matched_name]

        # --- Compare ---
        if sc_counties is None:
            unverified.append({
                'source_district': district,
                'school':          school_raw,
                'school_cleaned':  cleaned,
                'my_county':       county_borough,
                'confidence':      confidence,
            })
            continue

        sc_counties_norm = [normalise_county(c) for c in sc_counties]
        unique_sc = list(dict.fromkeys(sc_counties_norm))  # deduplicated, order kept

        if my_county in unique_sc and len(unique_sc) == 1:
            match_count += 1          # exact match — all good
        elif my_county in unique_sc:
            mismatches.append({       # my county is one valid option, but others exist
                'flag':            'MULTI_MATCH',
                'source_district': district,
                'school':          school_raw,
                'school_cleaned':  cleaned,
                'my_county':       county_borough,
                'confidence':      confidence,
                'matched_sc_name': matched_name,
                'sc_counties':     ' | '.join(sc_counties),
            })
        else:
            mismatches.append({
                'flag':            'MISMATCH',
                'source_district': district,
                'school':          school_raw,
                'school_cleaned':  cleaned,
                'my_county':       county_borough,
                'confidence':      confidence,
                'matched_sc_name': matched_name,
                'sc_counties':     ' | '.join(sc_counties),
            })

    # --- Sort: MISMATCH before MULTI_MATCH, then High-confidence mismatches first ---
    conf_rank = {'High': 0, 'Medium': 1, 'Low': 2}
    mismatches.sort(key=lambda r: (
        0 if r['flag'] == 'MISMATCH' else 1,
        conf_rank.get(r['confidence'], 9),
        r['source_district'],
    ))

    # --- Print summary ---
    n_mismatch = sum(1 for r in mismatches if r['flag'] == 'MISMATCH')
    n_multi    = sum(1 for r in mismatches if r['flag'] == 'MULTI_MATCH')
    print(f"\n{'='*60}")
    print(f"  Confirmed matches : {match_count:>4}")
    print(f"  MISMATCHes        : {n_mismatch:>4}  ← different county in small_cities")
    print(f"  MULTI_MATCHes     : {n_multi:>4}  ← name exists in multiple counties")
    print(f"  Unverified        : {len(unverified):>4}  ← not in small_cities")
    print(f"{'='*60}\n")

    for r in mismatches:
        if r['flag'] == 'MISMATCH':
            print(f"[MISMATCH] {r['source_district']} | {r['school_cleaned']!r}  ({r['confidence']})")
            print(f"  Assigned : {r['my_county']}")
            print(f"  SC says  : {r['sc_counties']}  (matched name: '{r['matched_sc_name']}')")
            print()

    # --- Write outputs ---
    OUT_DIR.mkdir(exist_ok=True)

    mismatch_fields = ['flag', 'source_district', 'school', 'school_cleaned',
                       'my_county', 'confidence', 'matched_sc_name', 'sc_counties']
    mismatch_path = OUT_DIR / 'mismatches.csv'
    with open(mismatch_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=mismatch_fields)
        w.writeheader()
        w.writerows(mismatches)
    print(f"Mismatches written to {mismatch_path}  ({len(mismatches)} rows)")

    if include_unverified:
        unverified_path = OUT_DIR / 'unverified.csv'
        uv_fields = ['source_district', 'school', 'school_cleaned', 'my_county', 'confidence']
        with open(unverified_path, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=uv_fields)
            w.writeheader()
            w.writerows(unverified)
        print(f"Unverified written to {unverified_path}  ({len(unverified)} rows)")


if __name__ == '__main__':
    main()
