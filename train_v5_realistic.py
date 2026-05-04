"""
CrowdBrain v5 — REALISTIC PARAMETER CALIBRATION
================================================
Default v5 params produce $73M cum revenue / $46M ARR end-of-sim, which is
not defensible vs real-world Series-B-stage robotics-data startups
(Scale AI was ~$10M ARR at year 3). This file calibrates the customer model
to produce realistic trajectories that match the memo's own Q4 2026 milestone:
3+ paying customers, $500K+ ARR at month 8 of horizon (Nov 2026 if launch May 2026).

Key changes vs PARAMS_V5:
- Per-customer monthly contracts: $15-50K (was $60-150K)
- Customer arrival lambda_max_per_segment: 0.5 (was 3.0)
- Pareto max_factor: 1.5 (was 3.0)
- Expansion cap: 1.5 (was 3.0)
- Bull-market arrival multiplier: 1.1 (was 1.3)

Expected end-state @ 36mo:
- 40-80 active customers (was ~250)
- $5-15M cumulative revenue (was $26-73M)
- $5-15M ARR by end-of-sim (was $46M+)

Use this for production stakeholder runs. Keep PARAMS_V5 for tail-upside
"what if" scenarios that the deck explicitly footnotes as bull-case.
"""

import sys
import time
import copy

from prepare_v5 import (
    run_simulation_v5, run_monte_carlo_v5, evaluate_v5, print_results_v5,
)
from train_v5 import PARAMS_V5


# ─── BUILD THE REALISTIC CALIBRATION (deep copy + override) ─────────────────
PARAMS_V5_REALISTIC = copy.deepcopy(PARAMS_V5)

# Customer-side recalibration
PARAMS_V5_REALISTIC["customers"]["segments"] = {
    "manufacturing": {
        "demand_profile": {0: 0.0, 1: 0.30, 2: 0.30, 3: 0.15, 4: 0.15, 5: 0.05, 6: 0.05},
        "size_mean_usd": 35_000,           # was 80_000
        "churn_baseline_yr": 0.15,
    },
    "warehouse": {
        "demand_profile": {0: 0.0, 1: 0.20, 2: 0.40, 3: 0.10, 4: 0.15, 5: 0.10, 6: 0.05},
        "size_mean_usd": 22_000,           # was 60_000
        "churn_baseline_yr": 0.25,
    },
    "healthcare": {
        "demand_profile": {0: 0.0, 1: 0.05, 2: 0.15, 3: 0.15, 4: 0.20, 5: 0.25, 6: 0.20},
        "size_mean_usd": 55_000,           # was 120_000 (kept higher due to compliance)
        "churn_baseline_yr": 0.10,
    },
    "robotics_oem": {
        "demand_profile": {0: 0.0, 1: 0.05, 2: 0.10, 3: 0.15, 4: 0.30, 5: 0.25, 6: 0.15},
        "size_mean_usd": 45_000,           # was 150_000 (early-stage robotics startups can't afford $150K/mo)
        "churn_baseline_yr": 0.08,
    },
}

PARAMS_V5_REALISTIC["customers"]["size_distribution"] = {
    "alpha":      1.5,
    "min_factor": 0.10,
    "max_factor": 1.5,                     # was 3.0 — no mega-whales early stage
}

PARAMS_V5_REALISTIC["customers"]["arrival"]["lambda_max_per_segment"] = 1.0    # was 3.0; 0.5/0.7 too conservative for memo Q4 2026 milestone
PARAMS_V5_REALISTIC["customers"]["arrival"]["design_partners"] = [
    ("manufacturing",  30_000),            # was 100_000
    ("warehouse",      20_000),            # was 80_000
    ("healthcare",     50_000),            # was 150_000
]

# Tier-unlock: switch from revenue-gated (which assumes $50M+ revenue) to op-count
# gated, which scales correctly to realistic revenue. Memo's "with scale" framing
# applies to operator-base growth, not just revenue.
PARAMS_V5_REALISTIC["tier_unlock"]["rules"] = {
    3: {"op_count_at_prev_tier": 25},      # T3 unlocks when 25 qualified T2 ops exist
    4: {"op_count_at_prev_tier": 10},      # T4 unlocks when 10 qualified T3 ops exist
    6: {"op_count_at_prev_tier": 5},       # T5 (internal T6) unlocks when 5 qualified T4 ops exist
}

PARAMS_V5_REALISTIC["customers"]["satisfaction"]["expansion_cap"] = 1.5        # was 3.0
PARAMS_V5_REALISTIC["customers"]["satisfaction"]["expand_pct"] = 0.10           # was 0.20 (slower expansion)

# Bull-market customer arrival multiplier — less FOMO-driven
PARAMS_V5_REALISTIC["macro"]["sentiment"]["multipliers"]["bull"]["customer_arrival"] = 1.1   # was 1.3

# Era multipliers — less aggressive in growth phase
PARAMS_V5_REALISTIC["macro"]["era"]["era_multipliers"]["growth"]["customer_arrival"] = 1.2   # was 1.5
PARAMS_V5_REALISTIC["macro"]["era"]["era_multipliers"]["maturity"]["customer_arrival"] = 1.0  # was 1.2

# Lower the customer-facing blended hourly rate (closer to memo $5-12 range)
PARAMS_V5_REALISTIC["customers"]["usd_per_hour_blended"] = 18.0                # was 25.0

# Operator onboarding multiplier — scales to memo's "1K trained operators @ Q3 2026"
# target. Default v3/v4 onboarding builds ~120K total operators; for realistic
# customer demand (~80 customers, ~30K hrs/mo total) we need ~3-5K active ops.
PARAMS_V5_REALISTIC["task_model"]["onboarding_multiplier"] = 0.35              # was 1.0; 0.20 was too low

# Token emission: scale down to match realistic revenue / burn ratio.
# v4 winner emits 3M/mo with $73M cum revenue. Realistic revenue is ~$10-20M cum,
# so emission should scale ~5-10x down to keep burn/emission balanced.
PARAMS_V5_REALISTIC["supply"]["monthly_emission_rate"] = 500_000               # was 3_000_000
PARAMS_V5_REALISTIC["supply"]["initial_supply"] = 5_000_000                    # was 10_000_000
PARAMS_V5_REALISTIC["supply"]["max_supply"] = 100_000_000                      # was 500_000_000

# AMM depth: smaller economy needs proportionally smaller pools to keep depth
# meaningful for typical sell volumes
PARAMS_V5_REALISTIC["macro"]["amm"]["initial_token_pool"] = 200_000            # was 1_000_000
PARAMS_V5_REALISTIC["macro"]["amm"]["initial_usd_pool"] = 200_000              # was 1_000_000

# Base emission per active op: scale down with the smaller economy
PARAMS_V5_REALISTIC["task_model"]["base_emission_per_active_op_per_month"] = 25.0   # was 45.0; 15 was too low (T4+ stuck at 0)

# Hardware stakes: smaller token economy means stakes must scale down too,
# otherwise USD-denominated stakes consume too many tokens
PARAMS_V5_REALISTIC["hardware"]["stake_required_t3_usd"] = 200                  # was 400
PARAMS_V5_REALISTIC["hardware"]["stake_required_t4_usd"] = 100                  # was 150
PARAMS_V5_REALISTIC["hardware"]["stake_required_t6_usd"] = 400                  # was 800


def evaluate_realism(history, customers):
    """
    Augment evaluate_v5 with explicit realism checks against memo milestones.
    Returns the v5 evaluation plus realism flags.
    """
    base = evaluate_v5(history, customers)

    # Memo Q4 2026 milestone (month 8 if launch month 0 = May 2026): 3+ paying, $500K+ ARR
    m8 = next((h for h in history if h["month"] == 8), None)
    if m8:
        m8_customers = m8.get("customer_count_active", 0)
        m8_monthly_rev = m8.get("monthly_revenue", 0)
        m8_arr = m8_monthly_rev * 12
        base["realism_q4_2026_customers"] = m8_customers
        base["realism_q4_2026_arr_usd"] = m8_arr
        base["realism_q4_2026_milestone_hit"] = bool(m8_customers >= 3 and m8_arr >= 500_000)
    else:
        base["realism_q4_2026_milestone_hit"] = False

    # Final-month ARR (annualized monthly_revenue × 12)
    final = history[-1] if history else {}
    final_arr = final.get("monthly_revenue", 0) * 12
    base["realism_final_arr_usd"] = final_arr
    base["realism_final_customer_count"] = final.get("customer_count_active", 0)

    # Realism flag: end-of-sim ARR <$60M and >$1M (Series-B-trajectory band)
    base["realism_arr_in_band"] = bool(1_000_000 <= final_arr <= 60_000_000)
    base["realism_customer_count_in_band"] = bool(20 <= final.get("customer_count_active", 0) <= 100)

    return base


if __name__ == "__main__":
    start = time.time()
    print("Running CrowdBrain v5 REALISTIC calibration (36 months)...")
    print()

    history, customers = run_simulation_v5(PARAMS_V5_REALISTIC, seed=42)

    # Show a focused trajectory: m1, m4, m8, m12, m18, m24, m30, m36
    print("Trajectory checkpoints:")
    print(f"  {'month':>5} {'price':>10} {'cust':>5} {'mo_rev':>12} {'ARR':>14} {'T4+':>6} {'active':>7}")
    for tgt in (1, 4, 8, 12, 18, 24, 30, 36):
        h = next((x for x in history if x["month"] == tgt), None)
        if not h:
            continue
        arr = h["monthly_revenue"] * 12
        print(
            f"  M{h['month']:>3d} ${h['token_price']:>8.4f} {h.get('customer_count_active', 0):>5d} "
            f"${h['monthly_revenue']:>10,.0f} ${arr:>12,.0f} "
            f"{h['operators_t4_plus']:>6d} {h['active_operators']:>7d}"
        )

    result = evaluate_realism(history, customers)
    print()
    print(f"Composite score: {result['score']}")
    print(f"  Cumulative revenue:     ${result['cumulative_revenue']:,}")
    print(f"  T4+ operators:          {result['t4_plus_operators']:,}")
    print()
    print("REALISM CHECKS:")
    print(f"  Q4 2026 (month 8) hit?  {result.get('realism_q4_2026_milestone_hit')}")
    print(f"    customers @ m8:       {result.get('realism_q4_2026_customers', 0)}  (target >=3)")
    print(f"    ARR @ m8:             ${result.get('realism_q4_2026_arr_usd', 0):,.0f}  (target >=$500K)")
    print(f"  Final ARR:              ${result.get('realism_final_arr_usd', 0):,.0f}  (band $1M-$60M)")
    print(f"  Final customers:        {result.get('realism_final_customer_count', 0)}  (band 20-100)")
    print(f"  ARR in realism band:    {result.get('realism_arr_in_band')}")
    print(f"  Customers in band:      {result.get('realism_customer_count_in_band')}")

    elapsed = time.time() - start
    print()
    print(f"Single-run completed in {elapsed:.1f}s")
