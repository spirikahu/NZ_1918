import pandas as pd
import re
from pathlib import Path

# ============================================================
# CONFIG
# ============================================================

INPUT_CSV = "Schools/School 1918 Data(Southland).csv"          # input file
OUTPUT_CSV = "Schools/place_aliases_southland.csv"  # output file
SCHOOL_COLUMN = "Name"     # column containing school names

# ============================================================
# NORMALIZATION RULES
# ============================================================

SCHOOL_SUFFIXES = [
    r"\bpublic school\b",
    r"\bdistrict high school\b",
    r"\bhigh school\b",
    r"\bnative school\b",
    r"\bside school\b",
    r"\bconvent school\b",
    r"\bschool\b",
]

RAILWAY_TERMS = [
    r"\bsiding\b",
    r"\brailway station\b",
    r"\bstation\b",
    r"\bjunction\b",
]

DIRECTIONALS = [
    r"\bnorth\b",
    r"\bsouth\b",
    r"\beast\b",
    r"\bwest\b",
    r"\bupper\b",
    r"\blower\b",
]

SAINT_PATTERNS = [
    (r"\bst\.\b", "saint"),
    (r"\bst\b", "saint"),
]

# ============================================================
# CLEANING FUNCTIONS
# ============================================================

def basic_normalize(text):
    """
    Lowercase + normalize punctuation/spaces.
    """
    text = str(text).strip().lower()

    # replace punctuation with spaces
    text = re.sub(r"[-_/]", " ", text)
    text = re.sub(r"[']", "", text)
    text = re.sub(r"[.,()]", " ", text)

    # normalize saint
    for pattern, repl in SAINT_PATTERNS:
        text = re.sub(pattern, repl, text)

    # collapse whitespace
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def title_case(text):
    """
    Convert normalized text back to readable title case.
    """
    return " ".join(word.capitalize() for word in text.split())


# ============================================================
# ALIAS GENERATION
# ============================================================

def generate_aliases(original_name):
    """
    Generate alias rows for one school/locality name.
    """

    aliases = []

    normalized = basic_normalize(original_name)

    canonical = normalized

    # --------------------------------------------------------
    # Alias 1: exact normalized form
    # --------------------------------------------------------

    aliases.append({
        "alias": title_case(original_name),
        "canonical_name": title_case(canonical),
        "confidence": "high",
        "alias_type": "exact_normalized",
        "notes": ""
    })

    # --------------------------------------------------------
    # Remove school suffixes
    # --------------------------------------------------------

    stripped = canonical

    for pattern in SCHOOL_SUFFIXES:
        stripped = re.sub(pattern, "", stripped)

    stripped = re.sub(r"\s+", " ", stripped).strip()

    if stripped and stripped != canonical:
        aliases.append({
            "alias": title_case(original_name),
            "canonical_name": title_case(stripped),
            "confidence": "high",
            "alias_type": "school_suffix_removed",
            "notes": ""
        })

    # --------------------------------------------------------
    # Remove railway terms
    # --------------------------------------------------------

    railway = canonical

    for pattern in RAILWAY_TERMS:
        railway = re.sub(pattern, "", railway)

    railway = re.sub(r"\s+", " ", railway).strip()

    if railway and railway != canonical:
        aliases.append({
            "alias": title_case(original_name),
            "canonical_name": title_case(railway),
            "confidence": "high",
            "alias_type": "railway_variant",
            "notes": ""
        })

    # --------------------------------------------------------
    # Directional variants
    # --------------------------------------------------------

    directional = canonical

    for pattern in DIRECTIONALS:
        directional = re.sub(pattern, "", directional)

    directional = re.sub(r"\s+", " ", directional).strip()

    if directional and directional != canonical:
        aliases.append({
            "alias": title_case(original_name),
            "canonical_name": title_case(directional),
            "confidence": "medium",
            "alias_type": "directional_variant",
            "notes": "direction removed"
        })

    # --------------------------------------------------------
    # Combined stripping
    # --------------------------------------------------------

    combined = canonical

    for pattern in SCHOOL_SUFFIXES:
        combined = re.sub(pattern, "", combined)

    for pattern in RAILWAY_TERMS:
        combined = re.sub(pattern, "", combined)

    combined = re.sub(r"\s+", " ", combined).strip()

    if combined and combined != canonical:
        aliases.append({
            "alias": title_case(original_name),
            "canonical_name": title_case(combined),
            "confidence": "high",
            "alias_type": "combined_variant",
            "notes": ""
        })

    return aliases


# ============================================================
# MAIN
# ============================================================

def build_alias_table(input_csv, output_csv):

    df = pd.read_csv(input_csv)

    if SCHOOL_COLUMN not in df.columns:
        raise ValueError(f"Column '{SCHOOL_COLUMN}' not found.")

    all_aliases = []

    for school_name in df[SCHOOL_COLUMN].dropna():

        generated = generate_aliases(school_name)

        all_aliases.extend(generated)

    alias_df = pd.DataFrame(all_aliases)

    # remove duplicates
    alias_df = alias_df.drop_duplicates()

    # sort for readability
    alias_df = alias_df.sort_values(
        by=["canonical_name", "alias"]
    )

    alias_df.to_csv(output_csv, index=False)

    print(f"Alias table written to: {output_csv}")
    print(f"Total aliases: {len(alias_df)}")


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    build_alias_table(INPUT_CSV, OUTPUT_CSV)
