"""
Build synthetic household distribution by size and number of children.

Combines:
  - data/Household_distribution.txt  (household counts by size, per area)
  - data/childless_households.txt    (childless household counts, per area)
  - data/number_of_children.txt      (children distribution by mother's age, national)
  - clean_data/demography_male.csv   (male population by age, per location)
  - clean_data/demography_female.csv (female population by age, per location)

Outputs:
  - clean_data/household_distribution.csv
  - clean_data/childless_households.csv
  - clean_data/number_of_children.csv
  - clean_data/synthetic_households.csv
"""

import re
import numpy as np
import pandas as pd

DATA = 'data'
CLEAN = 'clean_data'

# ---------------------------------------------------------------------------
# Step 1: Parse txt files
# ---------------------------------------------------------------------------

def parse_household_distribution():
    """Parse data/Household_distribution.txt into a clean DataFrame."""
    rows = []
    with open(f'{DATA}/Household_distribution.txt') as f:
        for line in f:
            line = line.rstrip('\n')
            # Skip comment lines and blank lines
            if line.startswith('#') or not line.strip():
                continue
            # Skip header lines (contain 'Metropolitan' or just numbers like '1.\t2.\t...')
            if 'Metropolitan' in line or line.strip().startswith('1.'):
                continue
            parts = line.split('\t')
            if len(parts) < 13:
                continue
            area = parts[0].strip()
            if not area or area in ('Metropolitan areas—', 'Suburban areas—'):
                continue
            try:
                counts = [int(p.strip().replace(',', '')) for p in parts[1:13]]
            except ValueError:
                continue
            rows.append([area] + counts)

    cols = ['Area', 'size_1', 'size_2', 'size_3', 'size_4', 'size_5',
            'size_6', 'size_7', 'size_8', 'size_9', 'size_10', 'size_11plus', 'total']
    df = pd.DataFrame(rows, columns=cols)
    # Normalise area names
    df['Area'] = df['Area'].str.strip()
    return df


def parse_childless_households():
    """
    Parse data/childless_households.txt.
    Metro city counts come from prose; suburban areas from a table at the end.
    """
    rows = []

    # Metro cities mentioned in prose
    metro = {
        'Auckland': 11772,
        'Wellington': 8095,
        'Christchurch': 8980,
        'Dunedin': 6872,   # "0,872" in source is a clear OCR/typo for 6,872
    }
    for area, count in metro.items():
        rows.append({'Area': area, 'childless_count': count})

    # Suburban areas from the tab-delimited table at the end of the file
    known_metro = set(metro.keys())
    with open(f'{DATA}/childless_households.txt') as f:
        for line in f:
            line = line.rstrip('\n')
            parts = line.split('\t')
            if len(parts) >= 2:
                area = parts[0].strip()
                val_str = parts[1].strip().replace(',', '')
                if area and val_str.isdigit() and area not in known_metro:
                    if 'Total' not in area and 'Rest' not in area and 'Whole' not in area:
                        rows.append({'Area': area, 'childless_count': int(val_str)})

    # Aggregate rows (hardcoded from source)
    rows.append({'Area': 'Total metropolitan and suburban areas', 'childless_count': 45558})
    rows.append({'Area': 'Rest of Dominion', 'childless_count': 54945})
    rows.append({'Area': 'Whole Dominion', 'childless_count': 100503})

    df = pd.DataFrame(rows).drop_duplicates('Area').reset_index(drop=True)
    return df


def parse_number_of_children():
    """Parse data/number_of_children.txt into a clean DataFrame."""
    rows = []
    def to_int(s):
        s = s.strip().replace(',', '')
        return 0 if s in ('..', '', '.') else int(s)

    with open(f'{DATA}/number_of_children.txt') as f:
        for line in f:
            line = line.rstrip('\n')
            if not line.strip():
                continue
            parts = line.split('\t')
            # Data rows have 20 fields: age + total_women + n_0..n_16 + total_children
            if len(parts) < 20:
                continue
            age = parts[0].strip()
            # Skip header rows
            if not age or age.startswith('Age') or age.startswith('0.'):
                continue
            # Skip the totals/unspecified rows
            if 'Total' in age or 'Unspecified' in age:
                continue
            try:
                values = [to_int(p) for p in parts[1:20]]
            except ValueError:
                continue
            rows.append([age] + values)

    # Columns: age_group, total_women, n_0, n_1, ..., n_16, total_children (20 total)
    cols = (['age_group', 'total_women'] +
            [f'n_{i}' for i in range(17)] +
            ['total_children'])
    df = pd.DataFrame(rows, columns=cols)
    return df


# ---------------------------------------------------------------------------
# Step 2: Compute joint distribution P(size=k, n_children=j)
# ---------------------------------------------------------------------------

def compute_joint_distribution(df_hh, df_childless, df_noc):
    """
    Returns a 2D numpy array joint[k, j] = P(size=k+1, n_children=j)
    where k in 0..10 (sizes 1..11+) and j in 0..10 (0..10 children).
    """
    # --- Size distribution (Remainder of Dominion) ---
    remainder = df_hh[df_hh['Area'].str.strip() == 'Remainder of Dominion'].iloc[0]
    size_counts = np.array([
        remainder[f'size_{s}'] if s <= 10 else remainder['size_11plus']
        for s in range(1, 12)
    ], dtype=float)
    total_hh = size_counts.sum()
    p_size = size_counts / total_hh

    # Mean household size (treat 11+ as 11)
    sizes = np.arange(1, 12, dtype=float)
    mean_size = (sizes * p_size).sum()

    # --- Childless fraction (Remainder of Dominion) ---
    rest_row = df_childless[df_childless['Area'].str.strip() == 'Rest of Dominion']
    childless_rest = int(rest_row['childless_count'].iloc[0])
    # Total households in Remainder of Dominion from household_distribution
    total_remainder = int(remainder['total'])
    p_childless = childless_rest / total_remainder

    # --- Children distribution given at least 1 child ---
    child_cols = [f'n_{i}' for i in range(1, 17)]  # n_1 .. n_16 (exclude n_0)
    child_totals = df_noc[child_cols].sum()
    child_totals_arr = child_totals.values.astype(float)
    # Cap at 10 children (merge 11+ into 10 bucket for simplicity)
    child_totals_capped = np.zeros(10)
    child_totals_capped[:9] = child_totals_arr[:9]   # n_1 .. n_9
    child_totals_capped[9] = child_totals_arr[9:].sum()  # n_10 .. n_16 → bucket 10
    p_nchildren_given_positive = child_totals_capped / child_totals_capped.sum()

    # --- Joint distribution ---
    # Rows: size k in {1..11}, indexed 0..10
    # Cols: n_children j in {0..10}, indexed 0..10
    n_sizes = 11
    n_children_max = 11  # 0..10
    joint = np.zeros((n_sizes, n_children_max))

    for k_idx in range(n_sizes):
        size = k_idx + 1  # actual household size (1..11)
        # Childless component
        joint[k_idx, 0] = p_size[k_idx] * p_childless
        # Children components: j must be in [1, size-1] (need at least 1 adult)
        max_children = min(size - 1, 10)
        if max_children >= 1:
            for j in range(1, max_children + 1):
                joint[k_idx, j] = (p_size[k_idx]
                                   * (1 - p_childless)
                                   * p_nchildren_given_positive[j - 1])

    # Renormalise
    joint /= joint.sum()

    return joint, mean_size


# ---------------------------------------------------------------------------
# Step 3: Build synthetic_households.csv
# ---------------------------------------------------------------------------

def build_synthetic_households(joint, mean_size):
    df_male = pd.read_csv(f'{CLEAN}/demography_male.csv', index_col=0)
    df_female = pd.read_csv(f'{CLEAN}/demography_female.csv', index_col=0)

    # Metadata columns
    meta_cols = ['ID', 'Name', 'Latitude', 'Longitude']
    age_cols = [str(i) for i in range(106)]

    meta = df_male[meta_cols].copy()
    total_pop = (df_male[age_cols].sum(axis=1) +
                 df_female[age_cols].sum(axis=1))

    # Estimated total households per location
    total_hh_per_loc = total_pop / mean_size

    # Build column names
    hh_cols = []
    for k_idx in range(11):
        size = k_idx + 1
        size_label = f's{size}' if size < 11 else 's11p'
        max_children = min(size - 1, 10)
        for j in range(max_children + 1):
            hh_cols.append(f'{size_label}_c{j}')

    # Build joint probability lookup: col_name → (k_idx, j)
    col_map = {}
    for k_idx in range(11):
        size = k_idx + 1
        size_label = f's{size}' if size < 11 else 's11p'
        max_children = min(size - 1, 10)
        for j in range(max_children + 1):
            col_map[f'{size_label}_c{j}'] = (k_idx, j)

    # Build household count matrix
    hh_matrix = np.zeros((len(meta), len(hh_cols)), dtype=int)
    for col_i, col_name in enumerate(hh_cols):
        k_idx, j = col_map[col_name]
        prob = joint[k_idx, j]
        hh_matrix[:, col_i] = np.round(total_hh_per_loc.values * prob).astype(int)

    df_out = meta.copy().reset_index(drop=True)
    df_hh = pd.DataFrame(hh_matrix, columns=hh_cols)
    df_out = pd.concat([df_out, df_hh], axis=1)

    return df_out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    print('Parsing Household_distribution.txt...')
    df_hh = parse_household_distribution()
    df_hh.to_csv(f'{CLEAN}/household_distribution.csv', index=False)
    print(f'  → {CLEAN}/household_distribution.csv  ({len(df_hh)} rows)')

    print('Parsing childless_households.txt...')
    df_childless = parse_childless_households()
    df_childless.to_csv(f'{CLEAN}/childless_households.csv', index=False)
    print(f'  → {CLEAN}/childless_households.csv  ({len(df_childless)} rows)')

    print('Parsing number_of_children.txt...')
    df_noc = parse_number_of_children()
    df_noc.to_csv(f'{CLEAN}/number_of_children.csv', index=False)
    print(f'  → {CLEAN}/number_of_children.csv  ({len(df_noc)} rows)')

    print('Computing joint distribution...')
    joint, mean_size = compute_joint_distribution(df_hh, df_childless, df_noc)
    print(f'  Mean household size (Remainder of Dominion): {mean_size:.2f}')
    print(f'  Joint distribution sums to: {joint.sum():.4f}')

    print('Building synthetic_households.csv...')
    df_out = build_synthetic_households(joint, mean_size)
    df_out.to_csv(f'{CLEAN}/synthetic_households.csv', index=False)
    print(f'  → {CLEAN}/synthetic_households.csv  ({len(df_out)} rows, {len(df_out.columns)} columns)')

    # --- Verification ---
    print('\nVerification:')
    hh_cols = [c for c in df_out.columns if c.startswith('s')]
    row_sums = df_out[hh_cols].sum(axis=1)
    df_male = pd.read_csv(f'{CLEAN}/demography_male.csv', index_col=0)
    df_female = pd.read_csv(f'{CLEAN}/demography_female.csv', index_col=0)
    age_cols = [str(i) for i in range(106)]
    total_pop = (df_male[age_cols].sum(axis=1) + df_female[age_cols].sum(axis=1))
    nonzero = row_sums.values > 0
    implied_mean_size = total_pop.values[nonzero] / row_sums.values[nonzero]
    print(f'  Implied mean household size: mean={implied_mean_size.mean():.2f}, '
          f'std={implied_mean_size.std():.2f} (excluding {(~nonzero).sum()} zero-pop locations)')

    childless_cols = [c for c in hh_cols if c.endswith('_c0')]
    childless_frac = df_out[childless_cols].sum(axis=1) / row_sums
    print(f'  Childless fraction: mean={childless_frac.mean():.3f} '
          f'(expected ≈ {54945/129937:.3f})')
