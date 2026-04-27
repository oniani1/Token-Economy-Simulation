"""
CrowdTrain v3 Token Economy Parameters
=======================================
Edit these to experiment. prepare.py is the immutable evaluation engine.

v3 redesign (vs v2):
- Multi-witness consensus validation (3 validators per sampled task, >=2 agree)
- Hours-based task economy ($5-$45/hr USD-anchored ladder)
- Risk-weighted sampling: T4-T6=100%, T2-T3=25%, T0-T1=10%
- Graduated slashing (10/25/50% then ban)
- Quality-gated linear hardware-stake unlock
- Revenue-gated fiat ramp with T0-T2 always pure-tokens
- Quality-correlated sell pressure
- Node network as agents (small + many: 3-5 arms, ~$50K capex each)
- Treasury entity with TGE distribution + vesting
- Bootstrap months 1-3: T0/T1 auto-passes
- 36-month simulation horizon
"""

import sys
import time

from prepare import run_monte_carlo, run_simulation, evaluate, print_results


PARAMS = {
    # ─── TOKEN SUPPLY & EMISSIONS ─────────────────────────────────────────
    "supply": {
        "initial_supply": 10_000_000,
        "max_supply": 500_000_000,
        "monthly_emission_rate": 5_000_000,    # tuned down from v2's 20M (sweep will explore)
        "halving_interval_months": 18,         # longer halving period
        "initial_token_price": 1.00,
        "tge_distribution": {
            "team_pct": 0.15,
            "investor_pct": 0.15,
            "treasury_pct": 0.25,
            "initial_liquidity_pct": 0.05,
            "operator_emissions_pct": 0.40,
        },
        "team_vest_months": 48,
        "investor_vest_months": 48,
    },

    # ─── HOURS-BASED TASK MODEL ───────────────────────────────────────────
    # Memo-aligned: $8-$15/hr cost arbitrage vs Tesla's $48/hr
    "task_model": {
        "tier_hours_per_month":   {0: 20,  1: 80,  2: 120, 3: 80,  4: 120, 5: 80,  6: 40},
        "tier_hourly_rate_usd":   {0: 0.0, 1: 5.0, 2: 8.0, 3: 12.0, 4: 18.0, 5: 28.0, 6: 45.0},
        "operator_total_hour_budget": 160,
        "review_minutes_per_task": 15,
        "tier_is_sync": {0: False, 1: False, 2: True, 3: False, 4: True, 5: True, 6: False},
        # Base emission per active operator per month (subsidizes early-stage operators
        # before customer demand kicks in; funds hardware stake accumulation). Memo:
        # "token emissions subsidize training". Tier multiplier rewards advancement.
        "base_emission_per_active_op_per_month": 15.0,
        "emission_tier_multiplier": {0: 0.5, 1: 1.0, 2: 1.2, 3: 1.5, 4: 2.0, 5: 2.5, 6: 3.0},
    },

    # ─── CUSTOMER DEMAND MODEL ────────────────────────────────────────────
    # Per-customer monthly hours wanted by tier. Drives revenue + operator earnings.
    # Memo: enterprise contracts target ~100 operators worth of work per customer.
    # These are the SUPPLY-SIDE numbers — actual revenue capped by operator availability.
    "demand": {
        "per_customer_hours_per_tier": {
            0: 0,
            1: 500,    # heavy labeling demand (training data)
            2: 300,    # browser teleop (warehouse/factory tasks)
            3: 200,    # in-the-wild capture (real-world data collection)
            4: 200,    # VR teleop premium (precision tasks)
            5: 100,    # live deployment on-demand (edge case intervention)
            6: 30,     # failure analysis specialist
        },
        # Customer count S-curve params (memo: 5 by m9, 15 by m12, 50 by m24)
        "max_customers_at_24mo": 60,
        "customer_curve_steepness": 0.4,
        "customer_curve_midpoint_month": 13,
        "customer_growth_post_24mo": 5.0,  # additional customers per month after m24
        "customer_cap": 200,
        "demand_volatility_std": 0.10,
    },

    # ─── MULTI-WITNESS CONSENSUS VALIDATION ───────────────────────────────
    "validation": {
        "sample_rate_by_tier": {0: 0.10, 1: 0.10, 2: 0.25, 3: 0.25, 4: 1.00, 5: 1.00, 6: 1.00},
        "validators_per_task": 3,
        "consensus_threshold": 2,
        "min_validator_tier_offset": 1,
        "validator_base_fee_pct": 0.10,
        "audit_escalation_tier": 6,
        "bootstrap_months": 3,
        "catch_bonus_split_within_group": {"fail_voters": 0.70, "pass_voters": 0.30},
    },

    # ─── GRADUATED SLASHING ───────────────────────────────────────────────
    "slashing": {
        "strike_severities": [0.10, 0.25, 0.50],
        "ban_on_strike": 4,
        "cooldown_months_after_3rd": 1,
        "clean_hours_per_strike_reset": 100,
        "slash_split": {"validators": 0.50, "burn": 0.50},
        "false_positive_penalty_pct": 0.05,
    },

    # ─── HARDWARE STAKING (USD-denominated; auto-converts to tokens at price) ─
    # Memo: "stake equivalent to hardware cost ($300-500)". USD-pegged so stakes
    # don't become impossible if token price moons or moonshots.
    "hardware": {
        "stake_required_t3_usd": 100,    # capture devices: gloves, GoPros, smart glasses ($50-200)
        "stake_required_t4_usd": 400,    # VR headset + haptic wearables ($300-500)
        "stake_required_t6_usd": 800,    # specialized partner hardware
        "hours_to_full_unlock": 100,
        "quality_threshold_for_unlock": 0.65,
        "stack_stakes_independently": True,
    },

    # ─── EARNINGS DENOMINATION (tokens -> fiat ramp) ──────────────────────
    "earnings": {
        "phase_curve": "revenue_gated",
        "phase_revenue_ladder_arr_to_fiat_ratio": [
            (0,            0.00),
            (1_000_000,    0.30),
            (5_000_000,    0.50),
            (20_000_000,   0.70),
        ],
        "phase_exempt_tiers": [0, 1, 2],
        "fiat_split_to_treasury": 0.30,
        "fiat_split_to_operators": 0.70,
    },

    # ─── BURN ─────────────────────────────────────────────────────────────
    "burn": {
        "burn_pct_of_revenue": 0.60,
    },

    # ─── SELL PRESSURE (quality-correlated, fiat-ramp aware) ──────────────
    "sell_pressure": {
        "base_sell_pct_low": 0.25,
        "base_sell_pct_high": 0.55,
        "quality_decay_strength": 0.6,
        "fiat_holding_decay_strength": 0.4,
    },

    # ─── DEPIN NODE NETWORK (small + many) ────────────────────────────────
    "nodes": {
        "arms_per_node": 4,
        "capex_per_node_usd": 50_000,
        "ops_per_node_target": 1_000,
        "partner_revenue_share": 0.15,
        "node_utilization_alarm": 0.80,
        "node_amortization_months": 36,
        "max_concurrent_operators_per_arm": 2,
    },

    # ─── RETENTION MODIFIERS (carried from v2) ────────────────────────────
    "retention": {
        "staking_churn_reduction": 0.90,
        "earnings_churn_reduction": 0.90,
        "nft_retention_bonus": 0.40,
        "gamification_churn_reduction": 0.30,
    },

    # ─── STUDY ASSUMPTION (Q2 2026 validation result baked in) ────────────
    "study_assumption": {
        "sim_trained_quality_bonus": 0.20,
    },
}


if __name__ == "__main__":
    start = time.time()

    print("Running CrowdTrain v3 token economy simulation (36 months, multi-witness validation)...")
    print()

    # Single-run debug pass
    print("Single-run monthly progression (seed=42):")
    history = run_simulation(PARAMS, seed=42)
    for h in history:
        print(
            f"  M{h['month']:2d}: price=${h['token_price']:.4f}  "
            f"rev=${h['monthly_revenue']:>9,.0f}  "
            f"T4+={h['operators_t4_plus']:>5}  "
            f"active={h['active_operators']:>6}  "
            f"nodes={h['node_count']:>3}  util={h['node_utilization_avg']:.0%}  "
            f"slash={h['slash_rate']:.1%}  fpr={h['false_positive_rate']:.1%}  "
            f"fiat={h['fiat_paid_ratio']:.0%}"
        )
    result = evaluate(history)
    print()
    print(f"Single-run composite score: {result['score']}")
    print(f"  Retention:           {result['retention_score']} ({result['retention_pct']}%)")
    print(f"  Stability:           {result['stability_score']}")
    print(f"  Revenue:             {result['revenue_score']}  (cum ${result['cumulative_revenue']:,})")
    print(f"  Fairness (Gini):     {result['gini_score']}  (gini {result['gini']})")
    print(f"  Qualified:           {result['qualified_score']}  (T4+ {result['t4_plus_operators']})")
    print(f"  Quality:             {result['quality_score']}  (slash {result['slash_rate']})")
    print(f"  Validator integrity: {result['validator_integrity_score']}  (fpr {result['false_positive_rate']})")
    print(f"  Node ROI:            {result['node_roi_score']}")
    print(f"  Capacity util:       {result['capacity_utilization_score']}")

    print()
    print("Running Monte Carlo (this may take a minute)...")
    metrics = run_monte_carlo(PARAMS)
    elapsed = time.time() - start

    print_results(PARAMS, metrics)
    print(f"Completed in {elapsed:.1f}s")
    print()
    print(f"score: {metrics['score_mean']:.6f}")
