"""
Re-run just the missing cells from experiments_v4 after the no_macro bug fix.
Combines with existing results in v4_experiment_results.json (if exists).
"""

import copy
import json
import os
import sys
import time
from typing import Dict, List

import prepare
import prepare_v4
from train_v4 import PARAMS_V4
from experiments_v4 import run_v4_cell, aggregate_results

prepare_v4.SIMULATION_MONTHS = 36
prepare.SIMULATION_MONTHS = 36


def main():
    n_runs = int(sys.argv[1]) if len(sys.argv) > 1 else 2

    # Load existing results if any
    existing_results: Dict[str, Dict] = {}
    if os.path.exists("v4_experiment_results.json"):
        try:
            with open("v4_experiment_results.json") as f:
                existing_results = json.load(f)
            print(f"Loaded existing results: {list(existing_results.keys())}")
        except Exception:
            pass

    # We want these from the previous run + new runs:
    # v3_winner, v4_baseline, v4_no_personas, v4_no_customers, v4_no_macro,
    # stress_biggest_customer_churn, stress_segment_collapse,
    # stress_new_customer_drought, stress_composite_shock
    desired = [
        "v3_winner", "v4_baseline", "v4_no_personas", "v4_no_customers", "v4_no_macro",
        "stress_biggest_customer_churn", "stress_segment_collapse",
        "stress_new_customer_drought", "stress_composite_shock",
    ]
    to_run = [k for k in desired if k not in existing_results]
    print(f"Cells to run: {to_run}")

    if not to_run:
        print("Nothing to run — all cells already in results JSON.")
        return

    # Now build params for each missing cell
    print(f"\nRunning {len(to_run)} cells × MC={n_runs}...\n")
    all_results = dict(existing_results)

    if "v4_no_macro" in to_run:
        p = copy.deepcopy(PARAMS_V4)
        del p["macro"]
        all_results["v4_no_macro"] = run_v4_cell("v4_no_macro", p, n_runs=n_runs)

    if "stress_biggest_customer_churn" in to_run:
        p_drop = copy.deepcopy(PARAMS_V4)
        p_drop["macro"]["events"] = list(p_drop["macro"]["events"]) + [
            {"event_type": "key_customer_loss", "fire_month": 18, "duration_months": 0, "severity": 1.0}
        ]
        all_results["stress_biggest_customer_churn"] = run_v4_cell(
            "stress_biggest_customer_churn", p_drop, n_runs=n_runs,
        )

    if "stress_segment_collapse" in to_run:
        p_seg = copy.deepcopy(PARAMS_V4)
        p_seg["customers"]["segments"]["manufacturing"]["churn_baseline_yr"] = 0.80
        all_results["stress_segment_collapse"] = run_v4_cell(
            "stress_segment_collapse", p_seg, n_runs=n_runs,
        )

    if "stress_new_customer_drought" in to_run:
        p_drought = copy.deepcopy(PARAMS_V4)
        p_drought["macro"]["events"] = list(p_drought["macro"]["events"]) + [
            {"event_type": "competitor", "fire_month": 12, "duration_months": 6, "severity": 0.1}
        ]
        all_results["stress_new_customer_drought"] = run_v4_cell(
            "stress_new_customer_drought", p_drought, n_runs=n_runs,
        )

    if "stress_composite_shock" in to_run:
        p_shock = copy.deepcopy(PARAMS_V4)
        p_shock["macro"]["sentiment"]["p_bull_to_bear"] = 1.0 / 12
        p_shock["macro"]["sentiment"]["initial"] = "bear"
        all_results["stress_composite_shock"] = run_v4_cell(
            "stress_composite_shock", p_shock, n_runs=n_runs,
        )

    # Save updated combined results
    out_path = "v4_experiment_results.json"
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\nSaved -> {out_path}")

    # Print summary table
    def get(d, k, default=0):
        return d.get(k + "_mean", d.get(k, default))

    print()
    print("=" * 95)
    print("EXPERIMENT SUMMARY (combined)")
    print("=" * 95)
    print(f"{'Cell':35s} {'Score':>8s}  {'CumRev':>10s}  {'T4+':>7s}  {'Active':>8s}  {'Top3%':>6s}  {'NRR':>5s}")
    print("-" * 95)
    for name in desired:
        m = all_results.get(name, {})
        if not m:
            continue
        score = get(m, "score")
        cum_rev = get(m, "cumulative_revenue")
        t4 = get(m, "t4_plus_operators")
        active = get(m, "active_operators_final")
        top3 = get(m, "top_3_concentration_pct")
        nrr = get(m, "nrr_blended")
        print(f"{name:35s} {score:>8.4f}  ${cum_rev:>9,.0f}  {t4:>7.0f}  {active:>8.0f}  {top3:>6.1f}  {nrr:>5.2f}")
    print()


if __name__ == "__main__":
    main()
