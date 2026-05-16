#!/usr/bin/env python3
"""
apply_corrections.py

Applies confirmed county corrections to *_county_borough.csv files.
Each correction is a tuple:
    (file_stem, school_name_fragment, new_county, new_evidence_note)

school_name_fragment is matched against the start of the 'school' column
(case-insensitive, stripped). The first match wins.
"""

import csv
import re
from pathlib import Path

BASE        = Path(__file__).parent
RESULTS_DIR = BASE / "Name_Matching_Results"

# ---------------------------------------------------------------------------
# Corrections table
# Format: (file_stem, school_fragment, new_county_borough, confidence, note)
# note is appended to the existing evidence field.
# ---------------------------------------------------------------------------
CORRECTIONS = [
    # ── TARANAKI ────────────────────────────────────────────────────────────
    # Inglewood County → Taranaki County (small_cities confirmed)
    ("Taranaki", "Egmont Villiage",   "Taranaki County", "High",
     "small_cities: Egmont Village → Taranaki County (211); corrected from Inglewood County"),
    ("Taranaki", "Kaimata",           "Taranaki County", "High",
     "small_cities: Kaimata → Taranaki County (360); corrected from Inglewood County"),
    ("Taranaki", "Kaimiro",           "Taranaki County", "High",
     "small_cities: Kaimiro implicit in Taranaki County area; corrected from Inglewood County"),
    ("Taranaki", "Lepperton",         "Taranaki County", "High",
     "small_cities: Lepperton → Taranaki County (291); corrected from Inglewood County"),
    ("Taranaki", "Ratapiko",          "Taranaki County", "High",
     "small_cities: Ratapiko → Taranaki County (133); corrected from Inglewood County"),
    ("Taranaki", "Tariki",            "Taranaki County", "High",
     "small_cities: Tariki → Taranaki County (505); corrected from Inglewood County"),
    ("Taranaki", "Tarurutangi",       "Taranaki County", "High",
     "small_cities: Tarurutangi → Taranaki County (198); corrected from Inglewood County"),
    ("Taranaki", "Waiongona",         "Taranaki County", "High",
     "small_cities: Waiongona → Taranaki County (213); corrected from Inglewood County"),
    # Inglewood County → Stratford County
    ("Taranaki", "Midhurst",          "Stratford County", "High",
     "small_cities: Midhirst → Stratford County (711); corrected from Inglewood County"),
    ("Taranaki", "Pukengahu",         "Stratford County", "High",
     "small_cities: Pukengahu → Stratford County (127); corrected from Inglewood County"),
    # Inglewood County → Clifton County
    ("Taranaki", "Tarata",            "Clifton County", "High",
     "small_cities: Tarata → Clifton County (190); corrected from Inglewood County"),
    # Inglewood County → Hawera County
    ("Taranaki", "Tokaora",           "Hawera County", "High",
     "small_cities: Tokaora → Hawera County (110); corrected from Inglewood County"),
    # Eltham County → Egmont County
    ("Taranaki", "Awatuna",           "Egmont County", "High",
     "small_cities: Awatuna → Egmont County (228); corrected from Eltham County"),
    ("Taranaki", "Te Kiri",           "Egmont County", "High",
     "small_cities: Te Kiri → Egmont County (292); corrected from Eltham County"),
    # Eltham County → Hawera County
    ("Taranaki", "Ararata",           "Hawera County", "High",
     "small_cities: Ararata → Hawera County (155); corrected from Eltham County"),
    # Hawera County → Eltham County
    ("Taranaki", "Matapu",            "Eltham County", "High",
     "small_cities: Matapu → Eltham County (375); corrected from Hawera County"),
    ("Taranaki", "Te Roti",           "Eltham County", "High",
     "small_cities: Te Roti → Eltham County (273); corrected from Hawera County"),
    # Hawera County → Waimate West County
    ("Taranaki", "Auroa",             "Waimate West County", "High",
     "small_cities: Auroa → Waimate West County (371); corrected from Hawera County"),
    ("Taranaki", "Kapuni",            "Waimate West County", "High",
     "small_cities: Kapuni → Waimate West County (460); corrected from Hawera County"),
    ("Taranaki", "Otakeho",           "Waimate West County", "High",
     "small_cities: Otakeho → Waimate West County (324); corrected from Hawera County"),
    # Patea County → Eltham County
    ("Taranaki", "Mata,",             "Eltham County", "High",
     "small_cities: Mata → Eltham County (124); corrected from Patea County"),
    # Egmont County → Hawera County
    ("Taranaki", "Meremere",          "Hawera County", "High",
     "small_cities: Meremere → Hawera County (330); corrected from Egmont County"),
    # Clifton County → Taranaki County
    ("Taranaki", "Bell Block",        "Taranaki County", "High",
     "small_cities: Bell Block → Taranaki County (263); corrected from Clifton County"),
    # Clifton County → Whangamomona County
    ("Taranaki", "Hurimoana",         "Whangamomona County", "High",
     "small_cities: Hurimoana → Whangamomona County (113); corrected from Clifton County"),
    # Stratford County → Whangamomona County
    ("Taranaki", "Pohokura",          "Whangamomona County", "High",
     "small_cities: Pohokura → Whangamomona County (145); corrected from Stratford County"),
    # Ohura County → Awakino County (Auckland Province)
    ("Taranaki", "Mahoenui",          "Awakino County (Auckland Province)", "High",
     "small_cities: Mahoenui → Awakino County (112); corrected from Ohura County"),
    # Clifton County → Awakino County
    ("Taranaki", "Mokau,",            "Awakino County (Auckland Province)", "High",
     "small_cities: Mokau → Awakino County (171); corrected from Clifton County"),
    # Waitomo County → Awakino County
    ("Taranaki", "Marakopa",          "Awakino County (Auckland Province)", "High",
     "small_cities: Marakopa → Awakino County (105); corrected from Waitomo County"),

    # ── OTAGO ───────────────────────────────────────────────────────────────
    # Vincent County → Tuapeka County
    ("Otago", "Ettrick",              "Tuapeka County", "High",
     "small_cities: Ettrick → Tuapeka County (153); corrected from Vincent County"),
    ("Otago", "Millers Flat",         "Tuapeka County", "High",
     "small_cities: Miller's Flat → Tuapeka County (365); corrected from Vincent County"),
    ("Otago", "Moa Flat",             "Tuapeka County", "High",
     "small_cities: Moa Flat → Tuapeka County (160); corrected from Vincent County"),
    ("Otago", "Coal Creek",           "Tuapeka County", "High",
     "small_cities: Coal Creek → Tuapeka County (179); corrected from Vincent County"),
    # Maniototo County → Vincent County
    ("Otago", "Lauder",               "Vincent County", "High",
     "small_cities: Lauder → Vincent County (176); corrected from Maniototo County"),
    ("Otago", "Moa Creek",            "Vincent County", "High",
     "small_cities: Moa Creek → Vincent County (189); corrected from Maniototo County"),
    ("Otago", "Poolburn",             "Vincent County", "High",
     "small_cities: Poolburn → Vincent County (103); corrected from Maniototo County"),
    # Maniototo County → Taieri County
    ("Otago", "Berwick",              "Taieri County", "High",
     "small_cities: Berwick → Taieri County (192); corrected from Maniototo County"),
    ("Otago", "Sutton",               "Taieri County", "High",
     "small_cities: Sutton → Taieri County (114); corrected from Maniototo County"),
    # Lake County → Vincent County
    ("Otago", "Nevis",                "Vincent County", "High",
     "small_cities: Nevis → Vincent County (132); corrected from Lake County"),
    ("Otago", "Tarras",               "Vincent County", "High",
     "small_cities: Tarras → Vincent County (127); corrected from Lake County"),
    # Tuapeka County → Clutha County
    ("Otago", "Glenkenich",           "Clutha County", "High",
     "small_cities: Glenkenich → Clutha County (216); corrected from Tuapeka County"),
    ("Otago", "Waikoikoi",            "Clutha County", "High",
     "small_cities: Waikoikoi → Clutha County (220); corrected from Tuapeka County"),
    ("Otago", "Conicall Hill",        "Clutha County", "High",
     "small_cities: Conical Hill → Clutha County (105); corrected from Tuapeka County"),
    # Taieri County → Clutha County
    ("Otago", "Purekireki",           "Clutha County", "High",
     "small_cities: Purekireki → Clutha County (104); corrected from Taieri County"),
    # Taieri County → Bruce County
    ("Otago", "Waihola",              "Bruce County", "High",
     "small_cities: Waihola → Bruce County (222); corrected from Taieri County"),
    # Waikouaiti County → Waihemo County
    ("Otago", "Dunback",              "Waihemo County", "High",
     "small_cities: Dunback → Waihemo County (345); corrected from Waikouaiti County"),
    # Maniototo County → Waihemo County
    ("Otago", "Macraes",              "Waihemo County", "High",
     "small_cities: Macrae's → Waihemo County (125); corrected from Maniototo County"),
    # Peninsula County → Waikouaiti County
    ("Otago", "Purakanui",            "Waikouaiti County", "High",
     "small_cities: Purakanui → Waikouaiti County (134); corrected from Peninsula County"),
    ("Otago", "Sawyers Bay",          "Waikouaiti County", "High",
     "small_cities: Sawyer's Bay → Waikouaiti County (536); corrected from Peninsula County"),
    # Waitaki County → Waikouaiti County
    ("Otago", "Merton",               "Waikouaiti County", "High",
     "small_cities: Merton → Waikouaiti County (152); corrected from Waitaki County"),
    # Waitaki County → Bruce County
    ("Otago", "Awamangu",             "Bruce County", "High",
     "small_cities: Awamangu → Bruce County (117); corrected from Waitaki County"),

    # ── NELSON ──────────────────────────────────────────────────────────────
    # Buller County → Inangahua County
    ("Nelson", "Cronadun",            "Inangahua County", "High",
     "small_cities: Cronadun → Inangahua County (154); corrected from Buller County"),
    # Buller County → Murchison County
    ("Nelson", "Murchison",           "Murchison County", "High",
     "small_cities: Murchison → Murchison County (318); corrected from Buller County"),
    # Collingwood County → Takaka County
    ("Nelson", "Motupipi",            "Takaka County", "High",
     "small_cities: Motupipi → Takaka County (210); corrected from Collingwood County"),
    ("Nelson", "Takaka East",         "Takaka County", "High",
     "small_cities: Takaka East → Takaka County (130); corrected from Collingwood County"),
    ("Nelson", "Tarakohe",            "Takaka County", "High",
     "small_cities: Terakohe → Takaka County (127); corrected from Collingwood County"),

    # ── WELLINGTON ──────────────────────────────────────────────────────────
    # Pahiatua County → Akitio County
    ("Wellington", "Pongaroa",        "Akitio County", "High",
     "small_cities: Pongara → Akitio County (487); corrected from Pahiatua County"),
    ("Wellington", "Pukehinau",       "Akitio County", "High",
     "small_cities: Pukehinau → Akitio County (111); corrected from Pahiatua County"),

    # ── WANGANUI ────────────────────────────────────────────────────────────
    # Rangitikei County → Kairanga County
    ("Wanganui", "Newbury",           "Kairanga County", "High",
     "small_cities: Newbury → Kairanga County (261); corrected from Rangitikei County"),
]


def file_for(stem: str) -> Path:
    """Find the CSV for a given district stem."""
    # Handle Southland special case
    if stem == "Southland":
        return RESULTS_DIR / "county_borough_assignments.csv"
    return RESULTS_DIR / f"{stem}_county_borough.csv"


def apply_corrections():
    # Group corrections by file stem
    by_file: dict[str, list] = {}
    for (stem, frag, new_county, conf, note) in CORRECTIONS:
        by_file.setdefault(stem, []).append((frag, new_county, conf, note))

    total_applied = 0
    total_missed  = 0

    for stem, corrs in by_file.items():
        path = file_for(stem)
        if not path.exists():
            print(f"  [SKIP] {path.name} not found")
            continue

        rows = []
        with open(path, newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            rows = list(reader)

        applied_here = 0
        for (frag, new_county, conf, note) in corrs:
            frag_lower = frag.lower().rstrip(',')
            matched = False
            for row in rows:
                school = row['school'].strip().strip('"')
                if school.lower().startswith(frag_lower):
                    old = row['county_borough']
                    row['county_borough'] = new_county
                    row['confidence']     = conf
                    row['evidence']       = note
                    matched = True
                    applied_here += 1
                    print(f"  [{stem}] {school[:50]!r}")
                    print(f"         {old!r} → {new_county!r}")
                    break
            if not matched:
                print(f"  [MISS] {stem} | fragment {frag!r} not found")
                total_missed += 1

        # Write back
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        print(f"  → {path.name}: {applied_here} correction(s) applied\n")
        total_applied += applied_here

    print(f"Done. {total_applied} corrections applied, {total_missed} fragments not matched.")


if __name__ == '__main__':
    apply_corrections()
