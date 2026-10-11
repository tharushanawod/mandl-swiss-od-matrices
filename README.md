# Mandl synthetic 24-hour OD dataset

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
