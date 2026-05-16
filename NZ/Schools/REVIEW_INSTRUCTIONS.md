# School County/Borough Assignment — Review Instructions

## Overview

The canonical data store is `Name_Matching_Results/*.csv`. Never edit the Matariki CSVs in `Databank/Schools/`.

Two phases have been completed. What remains is **25 INVESTIGATE cases** across both phases.

---

## Status

### Phase 1 — Audit MISMATCHes ✓ COMPLETE

`check_results/mismatches_enriched.csv` — 149 rows, all verdicted.

| Verdict | Count | Meaning |
|---|---|---|
| CONFIRM | 63 | Original assignment correct; `small_cities` wrong or matched different locality |
| DISMISS | 81 | Bad fuzzy hit; `matched_sc_name` is a different place entirely |
| CORRECT | 1 | Hillend/Otago: Tuapeka → Bruce County (applied) |
| INVESTIGATE | 4 | Insufficient evidence — see below |

### Phase 2 — Verify Unverified Schools ✓ COMPLETE

`check_results/unverified_enriched.csv` — 871 rows, all verdicted.

| Verdict | Count | Meaning |
|---|---|---|
| CONFIRM | 850 | Assignment supported by polling ED, gazetteer, or clear KG evidence |
| INVESTIGATE | 21 | No direct source, or explicitly uncertain/probable assignment |

---

## Remaining work — 25 INVESTIGATE cases

### From Phase 1 (mismatches_enriched.csv, verdict = INVESTIGATE)

| District | School | Assigned county | Issue |
|---|---|---|---|
| ~~Nelson~~ | ~~Woodstock~~ | ~~Inangahua County~~ | ~~Resolved CORRECT → Westland County — small_cities + polling both definitive~~ |
| Otago | Fair View | Clutha County | sc=Levels; avg attendance 2; no direct source |
| Wanganui | Matarawa | Rangitikei County | exact sc match; original evidence tentative |
| Wellington | Spring Grove | Sounds County | sc=Waimea; grade 0; no Sounds County source found |

### From Phase 2 (unverified_enriched.csv, verdict = INVESTIGATE)

| District | School | Assigned county | Issue |
|---|---|---|---|
| Auckland | Hora Hora Rapids | Waikato County | grade 0, 8 pupils; no source |
| ~~Nelson~~ | ~~Hamama~~ | ~~Waimea County~~ | ~~Resolved CONFIRM — gazetteer confirms official locality in Nelson LD~~ |
| Nelson | Hinekaka | Collingwood County | no source; neighbours are Nelson/Waimea/Inangahua schools — Collingwood has no alphabetical support |
| Nelson | Koreke | Collingwood County | no source; neighbours Kikiwa/Kiwi (Waimea) + Little Grey (Inangahua) suggest Buller/Inangahua more plausible |
| ~~Nelson~~ | ~~Long Plain~~ | ~~Collingwood County~~ | ~~Resolved CORRECT → Takaka County — Kotinga=Long Plain per gazetteer; coordinates at Takaka centroid~~ |
| ~~Nelson~~ | ~~Norriss Gully~~ | ~~Nelson County~~ | ~~Resolved CONFIRM — alphabetical neighbours support Nelson County~~ |
| ~~Nelson~~ | ~~Te Arowhenua~~ | ~~Nelson County~~ | ~~Resolved CONFIRM — Tophouse neighbour confirms Nelson County~~ |
| Nelson | Wairangi | Nelson County | grade 0/3 pupils; alphabetical position suggests Waimea or Inangahua rather than Nelson County |
| ~~Nelson~~ | ~~Wills Road~~ | ~~Buller County~~ | ~~Resolved CONFIRM — alphabetically between Nelson and Westland schools; Buller is intermediate~~ |
| Otago | Berwen | Clutha County | grade 0/4 pupils; neighbours Benhar+Blacks = Bruce County — Bruce more plausible |
| Otago | Hill Springs | Waitaki County | grade 0/5 pupils; between Hillend (Bruce) and Hinahina (Clutha) alphabetically |
| Otago | Killermont | Tuapeka County | grade 0/1 pupil — essentially no school; unresolvable |
| ~~Otago~~ | ~~Kokoano~~ | ~~Clutha County~~ | ~~Resolved CONFIRM — neighbours Kia Ora + Kuriwao both Clutha County~~ |
| ~~Otago~~ | ~~Reomoana~~ | ~~Clutha County~~ | ~~Resolved CONFIRM — neighbours Ratanui + Romahapa both Clutha County (Catlins)~~ |
| ~~Otago~~ | ~~Southbridge~~ | ~~Clutha County~~ | ~~Resolved: marked Unresolved — AJHR transcription error; no Otago Southbridge exists~~ |
| Otago | Table Hill | Taieri County | alphabetical boundary between Sutton (Taieri) and Tahakapa (Clutha); multiple Table Hills in Otago |
| ~~Otago~~ | ~~Waronui~~ | ~~Clutha County~~ | ~~Resolved CONFIRM — neighbours Wangaloa + Warepa + Wetherstones all Clutha County~~ |
| Wanganui | Aratika | Wanganui County | no direct match |
| Wanganui | Bluff Road | Wanganui County | no direct match |
| Southland | Daere | Southland County | no direct source |
| Southland | Glen Dhu | Southland County | grade 0, 3 pupils; no source |

**Remaining open:** Berwen (Bruce County more likely than Clutha), Hill Springs, Killermont (grade 0/1 pupil — probably unresolvable), Table Hill.

---

## How to apply corrections

For any INVESTIGATE case you resolve as a correction:

```bash
# 1. Fill corrected_county in the relevant enriched CSV
# 2. Run:
python apply_corrections.py --from-csv check_results/mismatches_enriched.csv
# or add to the CORRECTIONS table in apply_corrections.py for unverified cases
```

For unverified school corrections, add an entry to the `CORRECTIONS` table in `apply_corrections.py`:

```python
("District", "School name fragment", "Correct County", "High",
 "Evidence note explaining the correction"),
```

---

## Regenerating check outputs

```bash
# Re-run mismatch check (picks up any new corrections):
python check_assignments.py --enrich --include-unverified
```

---

## Quick reference — confidence levels

| Level | Meaning |
|---|---|
| `High` | Direct locality match in a primary source |
| `Medium` | Indirect match (nearby locality, railway line, mail route) |
| `Low` | Fallback reasoning (nearest borough, general district) |
| `Unresolved` | No evidence found |

## Quick reference — verdict values

| Verdict | Meaning |
|---|---|
| `CONFIRM` | Assignment is correct |
| `DISMISS` | Bad fuzzy hit; `small_cities` matched a different place; no action |
| `CORRECT` | Assignment wrong; fill `corrected_county` and apply via `--from-csv` |
| `INVESTIGATE` | Insufficient evidence; needs further research |
