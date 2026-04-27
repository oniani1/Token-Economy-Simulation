"""
Iteration 2: Tuned persona mix to claw back composite while keeping behavioral richness.

Hypothesis: the v4 baseline lost ~0.17 of composite vs v3 because 60% Casual personas
don't grind to T4+ (low stake_aggro, slow tier_speed). Try:

  - Reduce Casual share: 60% → 40%
  - Boost Pro Earner share: 25% → 40%
  - Boost Casual stake_aggro: 0.05 → 0.15
  - Boost Pro Earner stake_aggro: 0.40 → 0.55
  - Tighten Casual tier_speed: 1.30 → 1.15

Run 4 cells: tuned_v4_baseline (all 3 pillars), tuned_no_macro,
            tuned_no_customers, tuned_no_personas-as-control (same as before).

Saves to v4_iter2_results.json.
"""

import copy
import json
import sys
import time
from typing import Dict

import prepare
import prepare_v4
from train_v4 import PARAMS_V4
from experiments_v4 import run_v4_cell

prepare_v4.SIMULATION_MONTHS = 36


# ─── TUNED PARAMS ─────────────────────────────────────────────────────────
TUNED_PARAMS_V4 = copy.deepcopy(PARAMS_V4)
TUNED_PARAMS_V4["operators"]["personas"] = {
    "casual": {
        "share":              0.40,    # was 0.60
        "time_per_month":     40,
        "base_sell":          0.55,
        "stake_aggro":        0.15,    # was 0.05 (more willing to convert tokens to stake)
        "tier_speed":         1.15,    # was 1.30 (faster advancement)
        "quality_focus":      0.80,
        "validator_share":    0.0,
        "front_load_stake":   0.0,
    },
    "pro_earner": {
        "share":              0.40,    # was 0.25
        "time_per_month":     160,
        "base_sell":          0.30,
        "stake_aggro":        0.55,    # was 0.40
        "tier_speed":         0.65,    # was 0.70
        "quality_focus":      1.10,
        "validator_share":    0.0,
        "front_load_stake":   0.0,
    },
    "validator": {
        "share":              0.15,    # was 0.10
        "time_per_month":     120,
        "base_sell":          0.20,
        "stake_aggro":        0.40,
        "tier_speed":         1.00,
        "quality_focus":      1.20,
        "validator_share":    0.50,
        "front_load_stake":   0.0,
    },
    "hw_investor": {
        "share":              0.05,
        "time_per_month":     80,
        "base_sell":          0.15,
        "stake_aggro":        0.80,
        "tier_speed":         1.00,
        "quality_focus":      1.00,
        "validator_share":    0.0,
        "front_load_stake":   0.30,
    },
}


def main():
    n_runs = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    OUT_PATH = "v4_iter2_results.json"
    print(f"Iteration 2: tuned-persona sweep — MC={n_runs} per cell")
    print(f"Persona mix: 40% Casual / 40% Pro Earner / 15% Validator / 5% HW Investor")
    print()

    all_results: Dict[str, Dict] = {}

    def save_after(name: str, metrics: Dict):
        all_results[name] = metrics
        with open(OUT_PATH, "w") as f:
            json.dump(all_results, f, indent=2, default=str)
        print(f"  Saved {name} -> {OUT_PATH}", flush=True)

    print("=== Iteration 2: Tuned Personas ===")
    save_after("tuned_baseline", run_v4_cell("tuned_baseline", TUNED_PARAMS_V4, n_runs=n_runs))

    p_no_personas = copy.deepcopy(TUNED_PARAMS_V4)
    del p_no_personas["operators"]
    save_after("tuned_no_personas_control", run_v4_cell("tuned_no_personas_control", p_no_personas, n_runs=n_runs))

    p_no_customers = copy.deepcopy(TUNED_PARAMS_V4)
    del p_no_customers["customers"]
    save_after("tuned_no_customers", run_v4_cell("tuned_no_customers", p_no_customers, n_runs=n_runs))

    p_no_macro = copy.deepcopy(TUNED_PARAMS_V4)
    del p_no_macro["macro"]
    save_after("tuned_no_macro", run_v4_cell("tuned_no_macro", p_no_macro, n_runs=n_runs))

    print()
    print("=" * 95)
    print("ITERATION 2 SUMMARY")
    print("=" * 95)

    def get(d, k, default=0):
        return d.get(k + "_mean", d.get(k, default))

    print(f"{'Cell':35s} {'Score':>8s}  {'CumRev':>10s}  {'T4+':>7s}  {'Active':>8s}  {'Top3%':>6s}  {'NRR':>5s}")
    print("-" * 95)
    for name, m in all_results.items():
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
