"""
CrowdBrain v5 — Realism backtest against published DePIN / data-labeling peers
==============================================================================
Compares the winner timeseries against approximate published trajectories of
Scale AI (data-labeling, the closest analog) and Helium (DePIN, different
shape — fast token growth, slow revenue).

The "realism distance" is the L2 distance between the winner ARR trajectory
(at year-anchor checkpoints) and the reference. Lower = closer match.

Reference data is approximate (Scale AI was private through 2021; numbers
are based on Forbes / The Information / Crunchbase coverage). This is a
sanity-check, not a precise calibration.

Usage:
  python backtest_v5.py                            # uses winner_timeseries_v5_realistic.csv
  python backtest_v5.py path/to/timeseries.csv     # custom timeseries
"""

import sys
import csv
import json
import os
from typing import Dict, List, Tuple

OUT_DIR = "v5_results"
os.makedirs(OUT_DIR, exist_ok=True)


# ─── REFERENCE TRAJECTORIES (approximate, published data) ──────────────────
# Year-anchor → ARR at end of year (USD)
# Sources: Forbes ($870M 2024), The Information (Series E filings),
#          Crunchbase. Years 1-2 are estimates from seed-round sizing.
SCALE_AI_ARR = {
    1: 1_000_000,        # 2017 — seed funding, first paying contracts
    2: 5_000_000,        # 2018 — Series A
    3: 10_000_000,       # 2019 — published in coverage
    4: 60_000_000,       # 2020 — pandemic data-labeling boom
    5: 250_000_000,      # 2021 — Series E at $7.3B valuation
}

# Helium grew tokens faster than revenue (DePIN tokenomics-led).
# Source: Helium foundation transparency reports + on-chain data.
HELIUM_ARR = {
    1: 100_000,          # 2019 — launch year
    2: 500_000,          # 2020
    3: 2_000_000,        # 2021 — peak token market cap moment
    4: 14_000_000,       # 2022
    5: 12_000_000,       # 2023 — modest decline
}

# Hivemapper — DePIN mapping; quick early growth, recent slowdown
HIVEMAPPER_ARR = {
    1: 200_000,          # 2023
    2: 3_000_000,        # 2024
}


def load_timeseries(path: str) -> List[Dict]:
    rows = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                row["month"] = int(row.get("month", 0))
                for k in ("monthly_revenue", "annualized_arr", "active_customers",
                          "t4_plus_operators", "active_operators", "token_price",
                          "cumulative_revenue"):
                    if k in row and row[k]:
                        row[k] = float(row[k])
            except (ValueError, KeyError):
                pass
            rows.append(row)
    return rows


def arr_at_year_end(rows: List[Dict], year: int) -> float:
    """Find ARR at end of given year (months 12*year - 1)."""
    target_month = 12 * year
    for row in rows:
        if row.get("month") == target_month:
            return float(row.get("annualized_arr", row.get("monthly_revenue", 0) * 12))
    return 0.0


def realism_distance(winner_arr: Dict[int, float], ref_arr: Dict[int, float]) -> float:
    """
    Log-L2 distance between two ARR trajectories — log-space because revenue
    spans many orders of magnitude, so L2 in raw $ would over-weight late years.
    """
    import math
    n = 0
    s = 0.0
    for year in sorted(ref_arr.keys()):
        if year in winner_arr and winner_arr[year] > 0 and ref_arr[year] > 0:
            log_diff = math.log10(winner_arr[year]) - math.log10(ref_arr[year])
            s += log_diff ** 2
            n += 1
    return math.sqrt(s / n) if n > 0 else float("inf")


def print_comparison(winner_arr: Dict[int, float], references: Dict[str, Dict[int, float]]):
    print(f"\n{'='*78}")
    print("REALISM BACKTEST — winner vs DePIN / data-labeling peers")
    print(f"{'='*78}\n")

    print(f"{'Year':>4} {'Winner ARR':>15}", end="")
    for name in references:
        print(f" {name+' ARR':>20}", end="")
    print()
    print("-" * 78)

    for year in sorted(set().union(*(set(r.keys()) for r in references.values())) | set(winner_arr.keys())):
        win_str = f"${winner_arr.get(year, 0)/1e6:>12.2f}M"
        print(f"  {year:>2}   {win_str:>15}", end="")
        for name, ref in references.items():
            ref_str = f"${ref.get(year, 0)/1e6:>17.2f}M" if year in ref else " " * 19 + "—"
            print(f" {ref_str:>20}", end="")
        print()

    print()
    print("Realism distance (log-L2, lower = closer match):")
    distances = {}
    for name, ref in references.items():
        d = realism_distance(winner_arr, ref)
        distances[name] = d
        print(f"  {name:>20}: {d:.3f}")

    closest = min(distances, key=distances.get)
    print(f"\nClosest peer trajectory: {closest} (distance {distances[closest]:.3f})")
    return distances


def main():
    timeseries_path = sys.argv[1] if len(sys.argv) > 1 else "winner_timeseries_v5_realistic.csv"
    if not os.path.exists(timeseries_path):
        print(f"ERROR: timeseries not found: {timeseries_path}")
        print("Run deck_artifacts_v5.py first to generate winner_timeseries_v5_realistic.csv")
        sys.exit(1)

    rows = load_timeseries(timeseries_path)

    winner_arr = {}
    for year in range(1, 6):
        arr = arr_at_year_end(rows, year)
        if arr > 0:
            winner_arr[year] = arr

    if not winner_arr:
        print("ERROR: no ARR data found in timeseries")
        sys.exit(1)

    references = {
        "Scale AI":   SCALE_AI_ARR,
        "Helium":     HELIUM_ARR,
        "Hivemapper": HIVEMAPPER_ARR,
    }

    distances = print_comparison(winner_arr, references)

    out = {
        "winner_arr_by_year": winner_arr,
        "reference_arr": {k: v for k, v in references.items()},
        "realism_distance": distances,
        "closest_peer": min(distances, key=distances.get),
        "interpretation": (
            "Distance < 0.5 = within order-of-magnitude of peer; "
            "0.5-1.0 = same shape, different scale; "
            ">1.0 = qualitatively different trajectory."
        ),
    }
    with open(os.path.join(OUT_DIR, "iter5_backtest_results.json"), "w") as f:
        json.dump(out, f, indent=2)

    print(f"\nResults: {OUT_DIR}/iter5_backtest_results.json")


if __name__ == "__main__":
    main()
