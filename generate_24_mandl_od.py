"""Generate reproducible 24 synthetic Mandl hourly OD matrices.

Inputs (same directory as this script):
  mandl_original_od_matrix.csv  - published 15x15 symmetric reference OD
  geneva_hourly_demand_multipliers_2025.csv - previous peak-normalized Geneva TPG profile

Model: D_ij^(t) = D_ij^base * p_t, with A_ij^(t) = 1.
To obtain integer passengers while retaining symmetry, round the TOTAL
upper-triangle demand by the largest remainder (Hamilton) apportionment:
  - Multiply each unique undirected OD pair by p_t.
  - Round the sum of those scaled pair demands to the nearest integer.
  - Distribute remaining whole passengers to pair cells with largest
    fractional remainders (deterministic row-column tie breaking).
  - Mirror resulting pairs into both directions; diagonal stays zero.
This preserves symmetry and makes total = 2 * round(15570*p_t/2),
which is within one passenger of the unrounded target total.

Note: No random disturbance or directional A_ij^(t) adjustment is included.
These are synthetic/scenario matrices, not observed OD counts.
"""
import csv
import math
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE_FILE = ROOT / 'mandl_original_od_matrix.csv'
PROFILE_FILE = ROOT / 'geneva_hourly_demand_multipliers_2025.csv'
OUT = ROOT / 'mandl_24_hourly_od_matrices'
ZIP = ROOT / 'mandl_24_hourly_od_matrices.zip'

with BASE_FILE.open(newline='', encoding='utf-8') as f:
    base = [[int(cell) for cell in row] for row in csv.reader(f)]
assert len(base) == 15 and all(len(row) == 15 for row in base)
assert all(base[i][i] == 0 for i in range(15))
assert all(base[i][j] == base[j][i] and base[i][j] >= 0
           for i in range(15) for j in range(15))
base_total = sum(sum(row) for row in base)
assert base_total == 15570

with PROFILE_FILE.open(newline='', encoding='utf-8') as f:
    profile = list(csv.DictReader(f))
assert len(profile) == 24 and [int(rec['hour']) for rec in profile] == list(range(24))

OUT.mkdir(exist_ok=True)
summary = []
for rec in profile:
    hour = int(rec['hour'])
    factor = float(rec['demand_multiplier_pt'])
    assert 0 <= factor <= 1
    # Each symmetric OD pair is represented once.
    pair_targets = [(i, j, base[i][j] * factor)
                    for i in range(15) for j in range(i + 1, 15)
                    if base[i][j] > 0]
    floors = [math.floor(v) for _, _, v in pair_targets]
    target_half = round(sum(v for _, _, v in pair_targets))
    increments = target_half - sum(floors)
    assert 0 <= increments <= len(pair_targets)
    # Descending fractional remainder; deterministic ties (row, col).
    order = sorted(range(len(pair_targets)),
                   key=lambda k: (-(pair_targets[k][2] - floors[k]),
                                  pair_targets[k][0], pair_targets[k][1]))
    selected = set(order[:increments])
    od = [[0] * 15 for _ in range(15)]
    for k, (i, j, _) in enumerate(pair_targets):
        value = floors[k] + (1 if k in selected else 0)
        od[i][j] = od[j][i] = value
    total = sum(sum(row) for row in od)
    target = base_total * factor
    assert abs(total - target) <= 1.00001
    assert total == 2 * target_half
    assert all(od[i][j] == od[j][i] for i in range(15) for j in range(15))
    assert all(od[i][i] == 0 for i in range(15))
    assert all(od[i][j] == 0 for i in range(15) for j in range(15) if base[i][j] == 0)
    path = OUT / f'od_{hour:02d}.csv'
    with path.open('w', encoding='utf-8', newline='') as f:
        csv.writer(f).writerows(od)
    summary.append([hour, rec['time_slot'], int(rec['normal_weekdays']),
                    rec['mean_boardings_Bt'], rec['demand_multiplier_pt'],
                    f'{target:.6f}', total, f'{total-target:+.6f}',
                    sum(od[i][j] > 0 for i in range(15) for j in range(15))])

summary_headers = ['hour','time_slot','normal_weekdays','mean_boardings_Bt',
                   'demand_multiplier_pt','theoretical_network_demand',
                   'integer_network_demand','rounding_error_passengers',
                   'nonzero_directional_od_cells']
with (OUT / 'hourly_summary.csv').open('w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(summary_headers)
    w.writerows(summary)

readme = '''# Mandl synthetic 24-hour OD dataset

The 24 files `od_00.csv` through `od_23.csv` contain 15x15 comma-separated
numeric passenger-count matrices, without headers or row labels. Row/column 1
correspond to Mandl stop 1 (Python index 0); row/column 15 to stop 15.

## Source inputs

* Base network OD: `mandl_original_od_matrix.csv`, 15,570 total passengers,
  assumed (for this synthetic study) to represent **peak-hour** demand.
* 2025 Geneva TPG network-wide normal-weekday hourly boarding profile,
  in `geneva_hourly_demand_multipliers_2025.csv`, using 190 normal weekdays.
* A_t = 1 for all OD pairs and hours. **No** 2015 directional disturbance was
  applied in this baseline.

## Calculation

For each hour t:

    p_t = average boardings in hour t / maximum 24-hour average boardings
    continuous_OD_t[i,j] = Mandl_original_OD[i,j] * p_t

For integral passenger OD counts and exact input-matrix symmetry, allocate
integer values to the undirected OD pairs using largest-remainder rounding,
then mirror them across the diagonal. Network totals therefore become:

    2 * round(15570 * p_t / 2)

They differ by at most one passenger from 15570*p_t. The 17:00--18:00
reference hour reproduces the original Mandl matrix exactly.

## Interpretation and caveats

* These are **synthetic** hourly OD matrices, not measured OD flows in
  Geneva, and not evidence of observed travel between Mandl stops.
* Reusing a network-wide multiplier maintains the OD spatial distribution
  and symmetric directional pattern across the day. It changes demand
  intensity only. The 2015 Arbex & da Cunha asymmetric/reduced demand
  method would be a separate extension.
* The earlier hourly boarding analysis treated absent 02:00 and 03:00
  records as zero for selected weekdays; verify that data treatment
  before interpreting the very low overnight demand levels.
* This baseline assumes the entire original 15,570-passenger OD matrix is
  peak-hour demand, which is a **modelling choice** rather than a property
  proven by the boarding data.

`hourly_summary.csv` gives the actual integral matrix totals, rounded demand
and the per-hour multiplier. Repeat the generation using the provided
`generate_24_mandl_od.py` script together with the two original inputs.
'''
(OUT / 'README.md').write_text(readme, encoding='utf-8')

with zipfile.ZipFile(ZIP, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
    for file in sorted(OUT.iterdir()):
        archive.write(file, arcname=file.name)
    archive.write(ROOT / 'generate_24_mandl_od.py', arcname='generate_24_mandl_od.py')
    archive.write(BASE_FILE, arcname='mandl_original_od_matrix.csv')
    archive.write(PROFILE_FILE, arcname='geneva_hourly_demand_multipliers_2025.csv')

print('Output:', ZIP)
print('Hour | p_t       | theoretical | integer | nonzero directional OD cells')
for row in summary:
    print(f'{row[0]:02d}   | {row[4]:>9s} | {float(row[5]):>11.3f} | {row[6]:>7} | {row[8]:>3}')
print('Files in ZIP:', len(zipfile.ZipFile(ZIP).namelist()))
print('Peak file identical to original:',
      (OUT / 'od_17.csv').read_text() == BASE_FILE.read_text())
