"""
CrowdTrain v4 Token Economy Parameters
========================================
Edit these to experiment. prepare_v4.py is the immutable evaluation engine.

v4 redesign (vs v3 winner config):
- Pillar 1: Operators get personas + learning curve + decisions + referrals
- Pillar 2: Customers as first-class agents (segments, Pareto, satisfaction)
- Pillar 3: Macro economy (sentiment HMM, AMM, events, era detection)

Base config inherits the v3 winner (base_emission=45, stake=$150, emit=3M, arms=2, ops=2k).

Each pillar can be removed (delete its section) to ablate it back to v3 mechanics.
"""

import sys
import time

from prepare_v4 import (
    run_simulation_v4, run_monte_carlo_v4, evaluate_v4, print_results_v4,
)


PARAMS_V4 = {
    # ─── TOKEN SUPPLY & EMISSIONS (v3 winner) ──────────────────────────────
    "supply": {
        "initial_supply": 10_000_000,
        "max_supply": 500_000_000,
        "monthly_emission_rate": 3_000_000,    # winner
        "halving_interval_months": 18,
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

    # ─── HOURS-BASED TASK MODEL (v3 winner) ────────────────────────────────
    "task_model": {
        "tier_hours_per_month":   {0: 20,  1: 80,  2: 120, 3: 80,  4: 120, 5: 80,  6: 40},
        "tier_hourly_rate_usd":   {0: 0.0, 1: 5.0, 2: 8.0, 3: 12.0, 4: 18.0, 5: 28.0, 6: 45.0},
        "operator_total_hour_budget": 160,
        "review_minutes_per_task": 15,
        "tier_is_sync": {0: False, 1: False, 2: True, 3: False, 4: True, 5: True, 6: False},
        "base_emission_per_active_op_per_month": 45.0,    # winner (was 15 default)
        "emission_tier_multiplier": {0: 0.5, 1: 1.0, 2: 1.2, 3: 1.5, 4: 2.0, 5: 2.5, 6: 3.0},
    },

    # NOTE: 'demand' section is NOT included — Pillar 2 (customers) replaces it.
    # If you remove the 'customers' section below, prepare_v4 falls back to the
    # default v3 demand model.

    # ─── VALIDATION (v3 winner) ────────────────────────────────────────────
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

    # ─── SLASHING (v3 winner) ──────────────────────────────────────────────
    "slashing": {
        "strike_severities": [0.10, 0.25, 0.50],
        "ban_on_strike": 4,
        "cooldown_months_after_3rd": 1,
        "clean_hours_per_strike_reset": 100,
        "slash_split": {"validators": 0.50, "burn": 0.50},
        "false_positive_penalty_pct": 0.05,
    },

    # ─── HARDWARE (v3 winner) ──────────────────────────────────────────────
    "hardware": {
        "stake_required_t3_usd": 100,
        "stake_required_t4_usd": 150,    # winner (was 400 default)
        "stake_required_t6_usd": 800,
        "hours_to_full_unlock": 100,
        "quality_threshold_for_unlock": 0.65,
        "stack_stakes_independently": True,
    },

    # ─── EARNINGS DENOMINATION (v3 winner) ─────────────────────────────────
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

    "burn": {
        "burn_pct_of_revenue": 0.60,
    },

    "sell_pressure": {
        "base_sell_pct_low": 0.25,
        "base_sell_pct_high": 0.55,
        "quality_decay_strength": 0.6,
        "fiat_holding_decay_strength": 0.4,
    },

    # ─── NODES (post-stress-test refinement: arms=2, ops_per_node=2000) ────
    "nodes": {
        "arms_per_node": 2,
        "capex_per_node_usd": 50_000,
        "ops_per_node_target": 2_000,
        "partner_revenue_share": 0.15,
        "node_utilization_alarm": 0.80,
        "node_amortization_months": 36,
        "max_concurrent_operators_per_arm": 2,
    },

    "retention": {
        "staking_churn_reduction": 0.90,
        "earnings_churn_reduction": 0.90,
        "nft_retention_bonus": 0.40,
        "gamification_churn_reduction": 0.30,
    },

    "study_assumption": {
        "sim_trained_quality_bonus": 0.20,
    },

    # ═══ V4 PILLAR 1: OPERATORS ════════════════════════════════════════════
    "operators": {
        "personas": {
            "casual": {
                "share":              0.60,
                "time_per_month":     40,
                "base_sell":          0.55,
                "stake_aggro":        0.05,
                "tier_speed":         1.30,
                "quality_focus":      0.80,
                "validator_share":    0.0,
                "front_load_stake":   0.0,
            },
            "pro_earner": {
                "share":              0.25,
                "time_per_month":     160,
                "base_sell":          0.30,
                "stake_aggro":        0.40,
                "tier_speed":         0.70,
                "quality_focus":      1.10,
                "validator_share":    0.0,
                "front_load_stake":   0.0,
            },
            "validator": {
                "share":              0.10,
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
        },
        "learning": {
            "alpha":   0.10,    # skill = alpha * log(1 + experience_hours / 100)
            "cap":     0.30,    # cap learning bonus at +30%
        },
        "referrals": {
            "base_rate_per_op":              0.02,    # Poisson rate per active op per month (was 0.05 — too aggressive)
            "persona_inheritance_prob":      0.30,    # P(referee inherits parent persona)
        },
    },

    # ═══ V4 PILLAR 2: CUSTOMERS ════════════════════════════════════════════
    "customers": {
        "segments": {
            "manufacturing": {
                "demand_profile": {0: 0.0, 1: 0.30, 2: 0.30, 3: 0.15, 4: 0.15, 5: 0.05, 6: 0.05},
                "size_mean_usd": 80_000,
                "churn_baseline_yr": 0.15,
            },
            "warehouse": {
                "demand_profile": {0: 0.0, 1: 0.20, 2: 0.40, 3: 0.10, 4: 0.15, 5: 0.10, 6: 0.05},
                "size_mean_usd": 60_000,
                "churn_baseline_yr": 0.25,
            },
            "healthcare": {
                "demand_profile": {0: 0.0, 1: 0.05, 2: 0.15, 3: 0.15, 4: 0.20, 5: 0.25, 6: 0.20},
                "size_mean_usd": 120_000,
                "churn_baseline_yr": 0.10,
            },
            "robotics_oem": {
                "demand_profile": {0: 0.0, 1: 0.05, 2: 0.10, 3: 0.15, 4: 0.30, 5: 0.25, 6: 0.15},
                "size_mean_usd": 150_000,
                "churn_baseline_yr": 0.08,
            },
        },
        "size_distribution": {
            "alpha":      1.5,    # lower α = heavier tail = more concentration
            "min_factor": 0.10,   # floor at 10% of segment mean
            "max_factor": 3.0,    # cap at 3× segment mean (tighter than 4.0 to avoid mega-whales)
        },
        "arrival": {
            "design_partners": [
                ("manufacturing", 100_000),
                ("warehouse",      80_000),
                ("healthcare",    150_000),
            ],
            "lambda_max_per_segment":   3.0,
            "lambda_curve_midpoint":    13,
            "lambda_curve_steepness":   0.4,
        },
        "satisfaction": {
            "weights":            {"quality": 0.40, "demand_fulfill": 0.40, "sla": 0.20},
            "churn_threshold":    0.50,
            "churn_consecutive":  3,
            "expand_threshold":   0.80,
            "expand_consecutive": 3,
            "expand_pct":         0.20,
            "expansion_cap":      3.0,
            "sla_fulfill_min":    0.95,
            "sla_quality_min":    0.70,
            "grace_months_after_signing": 12,   # NEW: bootstrap grace (12mo for enterprise; healthcare needs T6 supply that takes a year+ to exist)
        },
        "usd_per_hour_blended": 25.0,    # cut demand in half vs v3 to prevent overload in early months
    },

    # ═══ V4 PILLAR 3: MACRO ECONOMY ════════════════════════════════════════
    "macro": {
        "sentiment": {
            "p_bull_to_bear": 1.0 / 21,    # mean bull duration ~21 months
            "p_bear_to_bull": 1.0 / 9,     # mean bear duration ~9 months
            "initial":        "bull",       # TGE in bull market (memo-aligned)
            "multipliers": {
                "bull": {"sell": 0.6, "customer_arrival": 1.3, "op_acquisition": 1.10},
                "bear": {"sell": 1.5, "customer_arrival": 0.7, "op_acquisition": 0.85},
            },
        },
        "amm": {
            "initial_token_pool": 1_000_000,    # 1M TOKEN side at TGE
            "initial_usd_pool":   1_000_000,    # $1M USD side at TGE (medium depth)
        },
        "events": [
            {"event_type": "competitor",  "fire_month": 18, "duration_months": 6, "severity": 0.7},
            {"event_type": "regulation",  "fire_month": 24, "duration_months": 0, "severity": 0.75},
            {"event_type": "recession",   "fire_month": 30, "duration_months": 4, "severity": 1.5},
        ],
        "era": {
            "growth_rev_threshold":     5_000_000,
            "growth_month_threshold":   12,
            "maturity_rev_threshold":  50_000_000,
            "maturity_month_threshold": 36,
            "maturity_fiat_threshold":  0.70,
            "era_multipliers": {
                "bootstrap": {"emission": 1.0, "referral": 1.2, "customer_arrival": 1.0},
                "growth":    {"emission": 1.0, "referral": 1.5, "customer_arrival": 1.5},
                "maturity":  {"emission": 0.5, "referral": 0.8, "customer_arrival": 1.2},
            },
        },
    },
}


if __name__ == "__main__":
    start = time.time()

    print("Running CrowdTrain v4 token economy simulation (36 months, 3-pillar behavioral redesign)...")
    print()

    # Single-run debug pass
    print("Single-run monthly progression (seed=42):")
    history, customers = run_simulation_v4(PARAMS_V4, seed=42)
    for h in history:
        sentiment = h.get("sentiment_state", "n/a")[:4]   # 'bull' or 'bear'
        era_short = h.get("era", "n/a")[:4]
        cust_active = h.get("customer_count_active", 0)
        top3 = h.get("customer_top_3_concentration_pct", 0)
        nrr = h.get("customer_nrr_blended", 1.0)
        events = h.get("events_fired_this_month", [])
        ev_str = "+".join(events) if events else ""
        print(
            f"  M{h['month']:2d}: price=${h['token_price']:.4f}  "
            f"rev=${h['monthly_revenue']:>9,.0f}  "
            f"T4+={h['operators_t4_plus']:>5}  "
            f"active={h['active_operators']:>6}  "
            f"sent={sentiment} era={era_short}  "
            f"cust={cust_active:>3} top3={top3:>4.1f}% nrr={nrr:.2f}  "
            f"slash={h['slash_rate']:.1%}  "
            f"{ev_str}"
        )
    result = evaluate_v4(history, customers)
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
    print("  v4 Supplements:")
    print(f"    Top-3 concentration:    {result['top_3_concentration_pct']:.1f}%")
    print(f"    NRR (blended):          {result['nrr_blended']:.2f}x")
    print(f"    Sentiment resilience:   {result['sentiment_resilience']:.2f}")
    print(f"    Persona diversity:      {result['persona_diversity_index']:.2f}")
    print()
    print(f"  Active customers:  {result['customer_count_active']}")
    print(f"  Total customers:   {result['customer_count_total']}")
    print(f"  Final era:         {result['era_final']}")
    print(f"  Final sentiment:   {result['sentiment_final']}")
    print(f"  Cumulative refs:   {result['cumulative_referrals']}")

    elapsed = time.time() - start
    print()
    print(f"Single-run completed in {elapsed:.1f}s")
