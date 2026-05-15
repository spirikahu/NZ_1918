"""
Build synthetic workplace distributions by industry class.

Sources:
  data/num_workers.txt        — national male/female worker counts per class (ground truth)
  data/percentage_workers.txt — participation rates via "Dependent" row
  data/employment_males.txt   — class proportions among male workers
  data/employment_females.txt — class proportions among female workers
  data/breadwinners.txt       — context only, not used for worker estimation
  clean_data/demography_male.csv
  clean_data/demography_female.csv

Outputs (one per class):
  clean_data/workplaces_Professional.csv
  clean_data/workplaces_Domestic.csv
  clean_data/workplaces_Commercial.csv
  clean_data/workplaces_Transport.csv
  clean_data/workplaces_Industrial.csv
  clean_data/workplaces_Agricultural.csv
  clean_data/workplaces_Indefinite.csv

Each row = one synthetic workplace.
Columns: geo_id, n_male, n_female, industry_code
"""

import numpy as np
import pandas as pd

DATA  = 'data'
CLEAN = 'clean_data'

# Roman-numeral → short label (matches source files)
CLASS_LABELS = {
    'I':   'Professional',
    'II':  'Domestic',
    'III': 'Commercial',
    'IV':  'Transport',
    'V':   'Industrial',
    'VI':  'Agricultural',
    'VII': 'Indefinite',
}

# Poisson mean workplace size per class
MEAN_WORKPLACE_SIZE = {
    'I':   3,
    'II':  1,
    'III': 4,
    'IV':  5,
    'V':   8,
    'VI':  3,
    'VII': 2,
}


# ── Parsing ───────────────────────────────────────────────────────────────────

def parse_num_workers():
    """
    Parse data/num_workers.txt.
    Returns two dicts keyed by Roman numeral: male_counts, female_counts.
    """
    roman_map = {
        'I. Professional':    'I',
        'II. Domestic':       'II',
        'III. Commercial':    'III',
        'IV. Transport':      'IV',
        'V. Industrial':      'V',
        'VI. Primary producers': 'VI',
        'VII. Indefinite':    'VII',
    }
    male_counts   = {}
    female_counts = {}
    with open(f'{DATA}/num_workers.txt') as f:
        next(f)  # header
        for line in f:
            line = line.strip()
            if not line or line.startswith('Total'):
                continue
            parts = line.split('\t')
            if len(parts) < 3:
                continue
            label = parts[0].strip()
            code  = roman_map.get(label)
            if code is None:
                continue
            male_counts[code]   = int(parts[1].replace(',', ''))
            female_counts[code] = int(parts[2].replace(',', ''))
    return male_counts, female_counts


def parse_participation_rates():
    """
    Parse data/percentage_workers.txt.
    Returns (male_rate, female_rate) as fractions of total population.
    Derived from 1 − "Dependent" percentage.
    """
    with open(f'{DATA}/percentage_workers.txt') as f:
        next(f)  # header
        for line in f:
            line = line.strip()
            if line.lower().startswith('dependent'):
                parts = line.split('\t')
                male_dep   = float(parts[1]) / 100.0
                female_dep = float(parts[2]) / 100.0
                return 1.0 - male_dep, 1.0 - female_dep
    raise ValueError('Dependent row not found in percentage_workers.txt')


def parse_class_proportions(filepath):
    """
    Parse employment_males.txt or employment_females.txt.
    Returns dict: Roman numeral → proportion (0–1).
    """
    props = {}
    with open(filepath) as f:
        next(f)  # header
        for line in f:
            line = line.strip()
            if not line or line.lower().startswith('total'):
                continue
            parts = line.split('\t')
            if len(parts) < 2:
                continue
            code = parts[0].split('.')[0].strip()   # "I. Professional" → "I"
            if code in CLASS_LABELS:
                props[code] = float(parts[1]) / 100.0
    return props


# ── Workplace generation ──────────────────────────────────────────────────────

def create_workplaces(geo_id, total_male, total_female, lam, label, rng):
    """
    Partition total_male + total_female workers into Poisson-sized workplaces.
    Male/female split within each workplace drawn from Binomial(size, male_frac).
    Returns list of row dicts.
    """
    rem_m = int(round(total_male))
    rem_f = int(round(total_female))
    if rem_m + rem_f == 0:
        return []

    male_frac = rem_m / (rem_m + rem_f)
    rows = []

    while rem_m + rem_f > 0:
        remaining = rem_m + rem_f
        size = min(max(1, int(rng.poisson(lam))), remaining)

        n_m = min(int(rng.binomial(size, male_frac)), rem_m)
        n_f = min(size - n_m, rem_f)

        # Ensure progress when rounding leaves nothing allocated
        if n_m + n_f == 0:
            if rem_m > 0:
                n_m = 1
            else:
                n_f = 1

        rows.append({
            'geo_id':        geo_id,
            'n_male':        n_m,
            'n_female':      n_f,
            'industry_code': label,
        })
        rem_m -= n_m
        rem_f -= n_f

    return rows


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    rng = np.random.default_rng(seed=42)

    # Parse data
    male_national, female_national = parse_num_workers()
    male_rate, female_rate         = parse_participation_rates()
    male_props   = parse_class_proportions(f'{DATA}/employment_males.txt')
    female_props = parse_class_proportions(f'{DATA}/employment_females.txt')

    print(f'Participation rates — male: {male_rate:.4f}  female: {female_rate:.4f}')
    print(f'National totals    — male: {sum(male_national.values()):,}  '
          f'female: {sum(female_national.values()):,}')

    # Load demography
    df_m = pd.read_csv(f'{CLEAN}/demography_male.csv',   index_col=0)
    df_f = pd.read_csv(f'{CLEAN}/demography_female.csv', index_col=0)

    age_cols = [str(a) for a in range(106)]
    geo_ids  = df_m['ID'].values

    total_male_pop   = df_m[age_cols].sum(axis=1).values.astype(float)
    total_female_pop = df_f[age_cols].sum(axis=1).values.astype(float)

    # Raw worker estimates per location
    male_workers_raw   = total_male_pop   * male_rate
    female_workers_raw = total_female_pop * female_rate

    # Scale so national sums match num_workers.txt exactly
    national_m = sum(male_national.values())
    national_f = sum(female_national.values())
    scale_m = national_m / male_workers_raw.sum()
    scale_f = national_f / female_workers_raw.sum()
    male_workers   = male_workers_raw   * scale_m
    female_workers = female_workers_raw * scale_f

    print(f'Scale factors      — male: {scale_m:.4f}  female: {scale_f:.4f}')
    print(f'Scaled totals      — male: {male_workers.sum():,.0f}  '
          f'female: {female_workers.sum():,.0f}')
    print()

    classes = list(CLASS_LABELS.keys())
    grand_m = grand_f = grand_wp = 0

    for cls in classes:
        label  = CLASS_LABELS[cls]
        lam    = MEAN_WORKPLACE_SIZE[cls]
        m_prop = male_props[cls]
        f_prop = female_props[cls]

        all_rows = []
        for i, geo_id in enumerate(geo_ids):
            rows = create_workplaces(
                geo_id,
                male_workers[i]   * m_prop,
                female_workers[i] * f_prop,
                lam,
                label,
                rng,
            )
            all_rows.extend(rows)

        df_out = pd.DataFrame(
            all_rows,
            columns=['geo_id', 'n_male', 'n_female', 'industry_code'],
        )
        outpath = f'{CLEAN}/workplaces_{label}.csv'
        df_out.to_csv(outpath, index=False)

        tot_m  = int(df_out['n_male'].sum())
        tot_f  = int(df_out['n_female'].sum())
        n_wp   = len(df_out)
        exp_m  = male_national[cls]
        exp_f  = female_national[cls]

        grand_m  += tot_m
        grand_f  += tot_f
        grand_wp += n_wp

        print(f'  {label:<14}  {n_wp:>7,} workplaces  '
              f'male {tot_m:>7,} (expected {exp_m:>7,})  '
              f'female {tot_f:>6,} (expected {exp_f:>6,})')

    print()
    print(f'  {"TOTAL":<14}  {grand_wp:>7,} workplaces  '
          f'workers {grand_m + grand_f:,} (expected {national_m + national_f:,})')


if __name__ == '__main__':
    main()
