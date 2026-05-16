# Schools Project — Domain Glossary

## Assignment
A row in `Name_Matching_Results/*.csv` that records which county or borough a school belonged to in 1918. The canonical working store. Never modify Matariki CSVs.

## County
A rural local government unit in 1918 NZ (e.g. Franklin County, Clutha County). Mutually exclusive with Borough for a given locality.

## Borough
An urban local government unit in 1918 NZ (e.g. Invercargill Borough, Gore Borough). Mutually exclusive with County.

## Education District
The administrative grouping under which schools appear in the 1918 parliamentary appendix (e.g. Auckland, Canterbury, Southland). Does not map 1-to-1 to counties or provinces.

## small_cities
A reference dataset of ~1,302 NZ localities with county assignments, extracted from a 1918-era census publication. One evidence source among several; a disagreement triggers review but does not override other evidence.

## MISMATCH
A school where `small_cities` identifies the locality but places it in a different county from the current assignment. Requires a CONFIRM / CORRECT / DISMISS / INVESTIGATE verdict.

## MULTI_MATCH (deprecated flag)
Previously flagged when `small_cities` listed multiple counties and the assignment was one of them. Now treated as auto-confirmed: if small_cities is compatible with the assignment, the assignment stands.

## Unverified
A school with no match in `small_cities`. The assignment may still be correct; other Databank sources (polling_lookup, coordinates, gazetteer) are used to verify or fill it.

## Verdict
A four-way decision applied during mismatch review:
- `CONFIRM` — assignment is positively verified; small_cities wrong or bad fuzzy hit
- `CORRECT` — assignment is wrong; `corrected_county` column holds the fix
- `DISMISS` — fuzzy hit was a different locality entirely; no action
- `INVESTIGATE` — insufficient evidence to decide; needs further research

## match_ratio
A 0–1 score (SequenceMatcher) between `school_cleaned` and the name `small_cities` matched. Low score (< ~0.7) indicates a likely false-positive fuzzy hit (DISMISS candidate). High score (≥ 0.9) indicates the right locality was found (genuine dispute).
