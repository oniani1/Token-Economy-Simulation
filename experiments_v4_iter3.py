"""
Iteration 3: Long-horizon (60-month) simulation of the winning v4 config.

Goal: see what happens when we let the sim breathe past the 36mo cliff:
  - Multiple sentiment cycles (~21mo bull + 9mo bear average → 60mo sees ~2 cycles)
  - Maturity era fully engaged (era_multipliers cut emission to 0.5x)
  - Node ROI score gets meaningful (most nodes 36mo+ old)
  - NRR cohort comparison can use month 12 → month 60 (48mo gap)

Runs the v4_no_personas config (best from main sweep) + v4_baseline + v3_winner at 60mo.
"""

import copy
import json
import sys
import time
from typing import Dict

import prepare
import prepare_v4
from train_v4 import PARAMS_V4
from experiments_v4 import run_v4_cell, run_v3_winner_reference

prepare.SIMULATION_MONTHS = 60
prepare_v4.SIMULATION_MONTHS = 60


def main():
    n_runs = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    OUT_PATH = "v4_iter3_results.json"
    print(f"Iteration 3: long-horizon (60mo) sweep — MC={n_runs} per cell")
    print()

    all_results: Dict[str, Dict] = {}

    def save_after(name: str, metrics: Dict):
        all_results[name] = metrics
        with open(OUT_PATH, "w") as f:
            json.dump(all_results, f, indent=2, default=str)
        print(f"  Saved {name} -> {OUT_PATH}", flush=True)

    print("=== Iteration 3: 60-month Long Horizon ===")

    save_after("v3_winner_60mo", run_v3_winner_reference(n_runs=n_runs))

    save_after("v4_baseline_60mo", run_v4_cell("v4_baseline_60mo", PARAMS_V4, n_runs=n_runs))

    p_no_personas = copy.deepcopy(PARAMS_V4)
    del p_no_personas["operators"]
    save_after("v4_no_personas_60mo", run_v4_cell("v4_no_personas_60mo", p_no_personas, n_runs=n_runs))

    print()
    print("=" * 95)
    print("ITERATION 3 SUMMARY (60mo)")
    print("=" * 95)

    def get(d, k, default=0):
        return d.get(k + "_mean", d.get(k, default))

    print(f"{'Cell':35s} {'Score':>8s}  {'CumRev':>10s}  {'T4+':>7s}  {'Active':>8s}  {'NRR':>5s}")
    print("-" * 95)
    for name, m in all_results.items():
        score = get(m, "score")
        cum_rev = get(m, "cumulative_revenue")
        t4 = get(m, "t4_plus_operators")
        active = get(m, "active_operators_final")
        nrr = get(m, "nrr_blended")
        print(f"{name:35s} {score:>8.4f}  ${cum_rev:>9,.0f}  {t4:>7.0f}  {active:>8.0f}  {nrr:>5.2f}")
    print()


if __name__ == "__main__":
    main()
