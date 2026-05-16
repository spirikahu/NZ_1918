# School County/Borough Assignment — Review Instructions

## Overview

Two phases:
1. **Audit** — adjudicate 149 MISMATCHes flagged by `small_cities.csv`
2. **Expand** — verify/assign the 871 schools with no `small_cities` match

The canonical data store is `Name_Matching_Results/*.csv`. Never edit the Matariki CSVs in `Databank/Schools/`.

---

## Phase 1 — Audit MISMATCHes

### Step 1: Generate the enriched review CSV

```bash
python check_assignments.py --enrich
```

Output: `check_results/mismatches_enriched.csv` (149 rows)

### Step 2: Open in a spreadsheet and sort

Open `mismatches_enriched.csv`. Key columns:

| Column | Meaning |
|---|---|
| `school_cleaned` | Core locality name extracted from the school name |
| `my_county` | Current assignment |
| `matched_sc_name` | What `small_cities` matched — may be a different place |
| `sc_counties` | County `small_cities` says the matched locality is in |
| `match_ratio` | 0–1 similarity between `school_cleaned` and `matched_sc_name` |
| `polling_locality` / `polling_eds` | Nearest polling lookup match and its electoral district(s) |
| `county_lat` / `county_lon` | Centroid of the currently assigned county |
| `verdict` | **You fill this in** |
| `corrected_county` | **You fill this in** if verdict = CORRECT |

### Step 3: Triage by match_ratio

Sort descending by `match_ratio`:

- **ratio < 0.85** — `small_cities` almost certainly found the wrong locality (a different place with a similar name). The original assignment is likely correct. Verdict: `DISMISS`.
- **ratio 0.85–0.95** — borderline. Check `matched_sc_name` carefully. Is it the same place or a different one? Cross-reference `polling_eds` and the original evidence column in the source CSV.
- **ratio ≥ 0.95 or exact match** — `small_cities` found the right locality. This is a genuine dispute. Research which county is correct.

### Step 4: Fill in verdict and corrected_county

Four valid verdicts:

| Verdict | When to use |
|---|---|
| `CONFIRM` | Original assignment is correct; `small_cities` is wrong or matched a different place |
| `CORRECT` | `small_cities` is right; fill `corrected_county` with the correct county/borough |
| `DISMISS` | Bad fuzzy hit — `matched_sc_name` is a different place; no action needed |
| `INVESTIGATE` | Insufficient evidence to decide; leave for further research |

**For `CORRECT` rows:** write the full county/borough name in `corrected_county`, matching the format used in the source CSVs (e.g. `Franklin County`, `Invercargill Borough`).

### Step 5: Apply corrections

```bash
python apply_corrections.py --from-csv check_results/mismatches_enriched.csv
```

This writes every `CORRECT` row back to the relevant `Name_Matching_Results/*.csv`. Run `check_assignments.py` again afterwards to confirm the MISMATCH count drops.

### Additional evidence sources

When `match_ratio` is high and you need to decide between two counties, consult:

- `Databank/Admin/polling_lookup.csv` — electoral district → locality. Electoral districts often follow county boundaries closely.
- `Databank/Places/coordinates_county.csv` — county centroids. Compare `county_lat`/`county_lon` against the known location of the school locality.
- `Databank/Places/placenames_gazateer_csv.csv` — NZ place names with land district. Note: land districts ≠ counties, but can narrow down the region.
- `Databank/Places/Post_offices.txt` — post office routes; useful for remote rural schools.
- `Databank/Articles/` — local newspaper articles may mention specific school locations.

---

## Phase 2 — Expand Unverified Schools

871 schools have no `small_cities` match (not in `check_results/unverified.csv` by default — regenerate with):

```bash
python check_assignments.py --include-unverified
```

Two sub-tasks:

### 2a — Verify already-assigned schools

These have a county/borough in `Name_Matching_Results` but no `small_cities` confirmation. Use polling, coordinates, and the gazetteer to corroborate or correct the existing assignment. Apply corrections via the hardcoded `CORRECTIONS` table in `apply_corrections.py` or a separate enriched CSV workflow.

### 2b — Fill Unresolved schools

These have `county_borough = Unresolved` in `Name_Matching_Results`. They need a county/borough assigned from scratch. For each:

1. Try exact/fuzzy match in `Databank/Places/placenames_gazateer_csv.csv` (column `name`).
2. Try `polling_lookup.csv` — match the school name against `locality`; the `electoral_district` narrows the county.
3. Try `Post_offices.txt` for mail routes that place the school in a known district.
4. Check school grade and average attendance in the Matariki source CSV — very small schools (grade 1, <20 pupils) are almost always rural, confirming a county rather than a borough.

Record the assignment with evidence and confidence in the relevant `Name_Matching_Results/*.csv`.

---

## Quick reference — confidence levels

| Level | Meaning |
|---|---|
| `High` | Direct locality match in a primary source |
| `Medium` | Indirect match (nearby locality, railway line, mail route) |
| `Low` | Fallback reasoning (nearest borough, general district) |
| `Unresolved` | No evidence found |
