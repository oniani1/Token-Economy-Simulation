"""
v4 experiments — pillar ablation + stress tests + v3 comparison.

Run plan (8 cells, MC=2-3 each, ~30 min total):
  1. v4_baseline             — all 3 pillars on
  2. v4_no_personas          — drop params['operators']
  3. v4_no_customers         — drop params['customers']
  4. v4_no_macro             — drop params['macro']
  5. stress: biggest_customer_churn — drop top customer at month 18
  6. stress: segment_collapse       — entire manufacturing segment churns over 3mo
  7. stress: new_customer_drought   — arrival rate × 0.1 for 6mo starting m12
  8. stress: composite_shock        — all 3 default events + bear-bias

Plus reference: v3 winner config through original prepare.py.
"""

import copy
import json
import sys
import time
from typing import Dict, List

import prepare       # v3 engine
import prepare_v4    # v4 engine
from train_v4 import PARAMS_V4

# Reduce MC default for sweeps; bump for final report
prepare_v4.NUM_MONTE_CARLO_RUNS = 3
prepare.NUM_MONTE_CARLO_RUNS = 3
prepare.SIMULATION_MONTHS = 36
prepare_v4.SIMULATION_MONTHS = 36


def run_v4_cell(name: str, params: Dict, n_runs: int = 3, customer_drop_at: int = None,
                segment_to_collapse: str = None, drought_start_month: int = None,
                drought_duration: int = None, drought_multiplier: float = None,
                composite_shock: bool = False) -> Dict:
    """
    Run a v4 cell. Stress-test parameters allow injecting external shocks.
    Returns aggregated metrics dict.
    """
    print(f"  Running {name}...", flush=True)
    t0 = time.time()

    # Clone params and apply stress overrides
    p = copy.deepcopy(params)
    if drought_start_month is not None:
        # Reduce λ_max during drought window via temporary override (handled at sim level via events)
        # Simpler: just lower lambda_max for the entire sim and let competitive event handle the dip
        # For MVP: set the lambda_max for the customers section globally during drought
        # We'll use a custom event mechanism: insert a competitor event spanning the drought window
        events = list(p["macro"]["events"])
        events.append({
            "event_type": "competitor",
            "fire_month": drought_start_month,
            "duration_months": drought_duration,
            "severity": drought_multiplier,
        })
        p["macro"]["events"] = events
    if segment_to_collapse is not None:
        # Will be handled at end-of-sim via direct customer manipulation in run_with_drop
        pass

    if composite_shock:
        # Force a bear-heavy run by raising p_bull_to_bear
        p["macro"]["sentiment"]["p_bull_to_bear"] = 1.0 / 12   # faster bear transitions
        p["macro"]["sentiment"]["initial"] = "bear"

    # Stress: biggest_customer_drop happens at customer_drop_at
    # Implementation: run the sim, find the largest customer, drop them at the specified month
    # We need a custom run loop for this. Use multiple seeds.
    if customer_drop_at is not None or segment_to_collapse is not None:
        # Custom run with mid-sim customer manipulation
        all_results = []
        for i in range(n_runs):
            history, customers = prepare_v4.run_simulation_v4(p, seed=42 + i)
            # Apply post-hoc shock: instead of mid-sim, look at TOP customer at the drop month
            # (since we can't easily inject mid-sim, simulate the impact by recalculating
            # what would have happened if top customer had churned at month drop_at)
            # For MVP shortcut: just report what happened with the standard sim;
            # add an observation about top-3 concentration as proxy for vulnerability
            result = prepare_v4.evaluate_v4(history, customers)
            all_results.append(result)
        agg = aggregate_results(all_results)
    else:
        agg = prepare_v4.run_monte_carlo_v4(p, n_runs=n_runs)

    elapsed = time.time() - t0
    print(f"    {name}: score={agg.get('score_mean', 0):.4f}±{agg.get('score_std', 0):.3f}  ({elapsed:.0f}s)", flush=True)
    return agg


def aggregate_results(results: List[Dict]) -> Dict:
    if not results:
        return {"score_mean": 0.0}
    keys = results[0].keys()
    agg = {"n_runs": len(results)}
    for k in keys:
        vals = [r.get(k, 0) for r in results if isinstance(r.get(k), (int, float))]
        if vals:
            mean_v = sum(vals) / len(vals)
            std_v = (sum((v - mean_v) ** 2 for v in vals) / len(vals)) ** 0.5
            agg[k + "_mean"] = round(mean_v, 4)
            agg[k + "_std"] = round(std_v, 4)
    return agg


def run_v3_winner_reference(n_runs: int = 3) -> Dict:
    """Run the v3 winner config through prepare.py (v3 engine) for direct comparison."""
    print(f"  Running v3_winner_reference...", flush=True)
    t0 = time.time()

    # Build winner config (v3 winner from REPORT_v3 + post-stress refinement)
    p = copy.deepcopy(PARAMS_V4)
    # Strip v4 sections so we run pure v3
    for key in ("operators", "customers", "macro"):
        if key in p:
            del p[key]
    # Add the v3 demand model (since v4 doesn't include it as fallback applies if customers absent)
    p["demand"] = {
        "per_customer_hours_per_tier": {0: 0, 1: 500, 2: 300, 3: 200, 4: 200, 5: 100, 6: 30},
        "max_customers_at_24mo": 60,
        "customer_curve_steepness": 0.4,
        "customer_curve_midpoint_month": 13,
        "customer_growth_post_24mo": 5.0,
        "customer_cap": 200,
        "demand_volatility_std": 0.10,
    }

    metrics = prepare.run_monte_carlo(p, n_runs=n_runs)
    elapsed = time.time() - t0
    print(f"    v3_winner: score={metrics.get('score_mean', 0):.4f}±{metrics.get('score_std', 0):.3f}  ({elapsed:.0f}s)", flush=True)
    return metrics


def main():
    n_runs = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    print(f"v4 experimental sweep — MC={n_runs} per cell")
    print()

    OUT_PATH = "v4_experiment_results.json"
    all_results: Dict[str, Dict] = {}

    def save_after_each(name: str, metrics: Dict):
        all_results[name] = metrics
        with open(OUT_PATH, "w") as f:
            json.dump(all_results, f, indent=2, default=str)

    # ── 1. Reference: v3 winner ──────────────────────────────────────────
    print("=== Reference (v3 winner config) ===")
    save_after_each("v3_winner", run_v3_winner_reference(n_runs=n_runs))

    # ── 2-5. v4 baseline + 3 pillar ablations ────────────────────────────
    print()
    print("=== v4 Baseline + Pillar Ablations ===")

    save_after_each("v4_baseline", run_v4_cell("v4_baseline", PARAMS_V4, n_runs=n_runs))

    p_no_personas = copy.deepcopy(PARAMS_V4)
    del p_no_personas["operators"]
    save_after_each("v4_no_personas", run_v4_cell("v4_no_personas", p_no_personas, n_runs=n_runs))

    p_no_customers = copy.deepcopy(PARAMS_V4)
    del p_no_customers["customers"]
    save_after_each("v4_no_customers", run_v4_cell("v4_no_customers", p_no_customers, n_runs=n_runs))

    p_no_macro = copy.deepcopy(PARAMS_V4)
    del p_no_macro["macro"]
    save_after_each("v4_no_macro", run_v4_cell("v4_no_macro", p_no_macro, n_runs=n_runs))

    # ── 6-9. Stress tests ─────────────────────────────────────────────────
    print()
    print("=== Stress Tests ===")

    p_drop = copy.deepcopy(PARAMS_V4)
    p_drop["macro"]["events"] = list(p_drop["macro"]["events"]) + [
        {"event_type": "key_customer_loss", "fire_month": 18, "duration_months": 0, "severity": 1.0}
    ]
    save_after_each("stress_biggest_customer_churn", run_v4_cell(
        "stress_biggest_customer_churn", p_drop, n_runs=n_runs,
    ))

    p_seg_collapse = copy.deepcopy(PARAMS_V4)
    p_seg_collapse["customers"]["segments"]["manufacturing"]["churn_baseline_yr"] = 0.80
    save_after_each("stress_segment_collapse", run_v4_cell(
        "stress_segment_collapse", p_seg_collapse, n_runs=n_runs,
    ))

    save_after_each("stress_new_customer_drought", run_v4_cell(
        "stress_new_customer_drought", PARAMS_V4, n_runs=n_runs,
        drought_start_month=12, drought_duration=6, drought_multiplier=0.1,
    ))

    save_after_each("stress_composite_shock", run_v4_cell(
        "stress_composite_shock", PARAMS_V4, n_runs=n_runs, composite_shock=True,
    ))

    print()
    print(f"Saved -> {OUT_PATH}")

    # ── Print summary table ──────────────────────────────────────────────
    print()
    print("=" * 95)
    print("EXPERIMENT SUMMARY")
    print("=" * 95)
    print(f"{'Cell':35s} {'Score':>8s}  {'CumRev':>10s}  {'T4+':>7s}  {'Active':>8s}  {'Top3%':>6s}  {'NRR':>5s}")
    print("-" * 95)
    for name, m in all_results.items():
        score = m.get("score_mean", 0)
        cum_rev = m.get("cumulative_revenue_mean", 0)
        t4 = m.get("t4_plus_operators_mean", 0)
        active = m.get("active_operators_final_mean", 0)
        top3 = m.get("top_3_concentration_pct_mean", m.get("top_3_concentration_pct", 0))
        nrr = m.get("nrr_blended_mean", m.get("nrr_blended", 0))
        print(f"{name:35s} {score:>8.4f}  ${cum_rev:>9,.0f}  {t4:>7.0f}  {active:>8.0f}  {top3:>6.1f}  {nrr:>5.2f}")
    print()


if __name__ == "__main__":
    main()
