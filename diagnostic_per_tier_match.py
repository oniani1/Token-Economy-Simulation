"""
Diagnostic — does per-customer-tier matching reduce active-op decline post-m24?
================================================================================
iter4 observation: active operators decline from 3K (m24) → 1.8K (m60) under
aggregate matching. Hypothesis: customers see global avg quality which doesn't
reflect their actual served quality, so churn is mis-targeted.

This script runs a single seed with matching ON and OFF, captures monthly
active_operators trajectory, plots it side-by-side, and outputs JSON for the
report.

Usage:
  python diagnostic_per_tier_match.py
"""

import copy
import json
import os

import prepare_v5
from prepare_v5 import run_simulation_v5
from train_v5_realistic import PARAMS_V5_REALISTIC

OUT_DIR = "v5_results"
os.makedirs(OUT_DIR, exist_ok=True)


def winner_base():
    p = copy.deepcopy(PARAMS_V5_REALISTIC)
    p["tier_unlock"]["rules"] = {
        3: {"op_count_at_prev_tier": 10},
        4: {"op_count_at_prev_tier": 5},
        6: {"op_count_at_prev_tier": 2},
    }
    p["hardware"]["stake_required_t3_usd"] = 25       # iter5 winner
    return p


def run_with_matching(matching_on: bool, seed: int = 42):
    p = winner_base()
    if matching_on:
        p.setdefault("customers", {}).setdefault("matching", {})["per_customer_tier_pool"] = True
        p["customers"]["matching"]["pool_size_per_tier"] = 25
    prepare_v5.SIMULATION_MONTHS = 60
    history, customers = run_simulation_v5(p, seed=seed)
    return [
        {
            "month": h["month"],
            "active_operators": h.get("active_operators", 0),
            "operators_t4_plus": h.get("operators_t4_plus", 0),
            "monthly_revenue": h.get("monthly_revenue", 0),
            "customer_count_active": h.get("customer_count_active", 0),
            "customer_avg_satisfaction": h.get("customer_avg_satisfaction", 0),
        }
        for h in history
    ]


def main():
    print("Running winner config WITHOUT per-tier matching (seed=42)...")
    off = run_with_matching(matching_on=False, seed=42)

    print("Running winner config WITH per-tier matching (seed=42)...")
    on = run_with_matching(matching_on=True, seed=42)

    print("\nMonthly comparison — active operators:")
    print(f"  {'Month':>5} {'OFF active':>12} {'ON active':>12} {'OFF T4+':>10} {'ON T4+':>10} {'OFF rev':>14} {'ON rev':>14}")
    for off_h, on_h in zip(off, on):
        if off_h["month"] in (1, 6, 12, 18, 24, 30, 36, 42, 48, 54, 60):
            print(f"  M{off_h['month']:>3d} {off_h['active_operators']:>12d} {on_h['active_operators']:>12d} "
                  f"{off_h['operators_t4_plus']:>10d} {on_h['operators_t4_plus']:>10d} "
                  f"${off_h['monthly_revenue']:>11,.0f} ${on_h['monthly_revenue']:>11,.0f}")

    out = {
        "matching_off": off,
        "matching_on": on,
        "summary": {
            "off_peak_active_ops": max(h["active_operators"] for h in off),
            "off_final_active_ops": off[-1]["active_operators"],
            "on_peak_active_ops": max(h["active_operators"] for h in on),
            "on_final_active_ops": on[-1]["active_operators"],
            "off_peak_to_final_decline_pct":
                (max(h["active_operators"] for h in off) - off[-1]["active_operators"])
                / max(1, max(h["active_operators"] for h in off)) * 100,
            "on_peak_to_final_decline_pct":
                (max(h["active_operators"] for h in on) - on[-1]["active_operators"])
                / max(1, max(h["active_operators"] for h in on)) * 100,
        }
    }
    with open(os.path.join(OUT_DIR, "iter5_per_tier_match_diagnostic.json"), "w") as f:
        json.dump(out, f, indent=2)

    print(f"\nWrote {OUT_DIR}/iter5_per_tier_match_diagnostic.json")
    print(f"\nSummary:")
    s = out["summary"]
    print(f"  Matching OFF — peak active ops: {s['off_peak_active_ops']}, final: {s['off_final_active_ops']}, "
          f"peak-to-final decline: {s['off_peak_to_final_decline_pct']:.1f}%")
    print(f"  Matching ON  — peak active ops: {s['on_peak_active_ops']}, final: {s['on_final_active_ops']}, "
          f"peak-to-final decline: {s['on_peak_to_final_decline_pct']:.1f}%")
    if s["on_peak_to_final_decline_pct"] < s["off_peak_to_final_decline_pct"]:
        print(f"  -> Per-tier matching REDUCES decline by "
              f"{s['off_peak_to_final_decline_pct'] - s['on_peak_to_final_decline_pct']:.1f} percentage points.")
    else:
        print(f"  -> Per-tier matching does NOT reduce decline.")

    # Plot if matplotlib available
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        months = [h["month"] for h in off]
        fig, ax = plt.subplots(1, 1, figsize=(10, 5))
        ax.plot(months, [h["active_operators"] for h in off], "b-",
                linewidth=2, label="Aggregate matching (current)")
        ax.plot(months, [h["active_operators"] for h in on], "r-",
                linewidth=2, label="Per-customer-tier matching (iter5)")
        ax.set_xlabel("Month")
        ax.set_ylabel("Active operators")
        ax.set_title("Active operators — aggregate vs per-tier matching (seed 42, winner config)")
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig("v5_iter5_matching_comparison.png", dpi=120, bbox_inches="tight")
        plt.close()
        print(f"\n  Wrote v5_iter5_matching_comparison.png")
    except ImportError:
        pass


if __name__ == "__main__":
    main()
