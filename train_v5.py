"""
CrowdBrain v5 Token Economy Parameters
========================================
Extends v4_no_personas winner (best v4 config; no persona pillar) with v5 layers:
  - tier_unlock        (Track 1)
  - node_providers     (Track 3)
  - geography          (Track 4 / general realism)
  - points_to_token    (Track 2)
  - customers v5 ext   (multi-year design partner contracts)

Each v5 layer can be removed (delete its section) to ablate it back to v4 mechanics.
The 'operators' pillar is INTENTIONALLY OMITTED to match the v4_no_personas winner
which gave the best 36mo composite (0.7575) and best long-horizon revenue.

Edit this for parameter experiments. prepare_v5.py is the immutable engine.
"""

import sys
import time

from prepare_v5 import (
    run_simulation_v5, run_monte_carlo_v5, evaluate_v5, print_results_v5,
)


PARAMS_V5 = {
    # ─── TOKEN SUPPLY & EMISSIONS (v3/v4 winner) ──────────────────────────
    "supply": {
        "initial_supply": 10_000_000,
        "max_supply": 500_000_000,
        "monthly_emission_rate": 3_000_000,
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

    # ─── HOURS-BASED TASK MODEL (v3/v4 winner) ────────────────────────────
    "task_model": {
        "tier_hours_per_month":   {0: 20,  1: 80,  2: 120, 3: 80,  4: 120, 5: 80,  6: 40},
        "tier_hourly_rate_usd":   {0: 0.0, 1: 5.0, 2: 8.0, 3: 12.0, 4: 18.0, 5: 28.0, 6: 45.0},
        "operator_total_hour_budget": 160,
        "review_minutes_per_task": 15,
        "tier_is_sync": {0: False, 1: False, 2: True, 3: False, 4: True, 5: True, 6: False},
        "base_emission_per_active_op_per_month": 45.0,
        "emission_tier_multiplier": {0: 0.5, 1: 1.0, 2: 1.2, 3: 1.5, 4: 2.0, 5: 2.5, 6: 3.0},
    },

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

    "slashing": {
        "strike_severities": [0.10, 0.25, 0.50],
        "ban_on_strike": 4,
        "cooldown_months_after_3rd": 1,
        "clean_hours_per_strike_reset": 100,
        "slash_split": {"validators": 0.50, "burn": 0.50},
        "false_positive_penalty_pct": 0.05,
    },

    # v5: hardware stake range $300-500 per memo (was $150 in v4 winner)
    # Use $400 mid-range as default for T3 (VR teleop hardware)
    "hardware": {
        "stake_required_t3_usd": 400,    # v5: $300-500 range, midpoint
        "stake_required_t4_usd": 150,    # v4 winner kept (failure analysis is async, no hardware)
        "stake_required_t6_usd": 800,    # v4 winner kept (live deployment)
        "hours_to_full_unlock": 100,
        "quality_threshold_for_unlock": 0.65,
        "stack_stakes_independently": True,
    },

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

    # NOTE: 'operators' (Pillar 1 personas) intentionally OMITTED to match
    # v4_no_personas winner (best composite at 36mo per session 2026-04-26).

    # ─── CUSTOMERS (v4 + v5 design-partner extension) ──────────────────────
    "customers": {
        "design_partner_contract_term_months": 24,    # v5: DPs immune to sat-churn for 24mo
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
            "alpha":      1.5,
            "min_factor": 0.10,
            "max_factor": 3.0,
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
            "grace_months_after_signing": 12,
        },
        "usd_per_hour_blended": 25.0,
    },

    # ─── MACRO (v4) ────────────────────────────────────────────────────────
    "macro": {
        "sentiment": {
            "p_bull_to_bear": 1.0 / 21,
            "p_bear_to_bull": 1.0 / 9,
            "initial":        "bull",
            "multipliers": {
                "bull": {"sell": 0.6, "customer_arrival": 1.3, "op_acquisition": 1.10},
                "bear": {"sell": 1.5, "customer_arrival": 0.7, "op_acquisition": 0.85},
            },
        },
        "amm": {
            "initial_token_pool": 1_000_000,
            "initial_usd_pool":   1_000_000,
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

    # ═══ V5 LAYER A: TIER UNLOCK ════════════════════════════════════════════
    "tier_unlock": {
        "rules": {
            # Default v5 baseline: revenue-gated unlock per memo's "with scale" framing
            3: {"cumulative_revenue_usd": 250_000},
            4: {"cumulative_revenue_usd": 1_000_000},
            6: {"cumulative_revenue_usd": 5_000_000},
        },
        "op_count_qualifier": "active_with_credential",
    },

    # ═══ V5 LAYER B: NODE PROVIDERS ═════════════════════════════════════════
    "node_providers": {
        "params": {
            "bond_per_arm_usd": 5_000,
            "facility_share":   0.5,    # 50/50 facility/community by default
            "community_revenue_share":  0.20,
            "facility_revenue_share":   0.0,
            "protocol_fee_pct":         0.10,
            "report_audit_threshold":   3,
            "auto_check_failure_pct":   0.02,
            "slash_severities": {
                "uptime":      0.10,
                "latency":     0.10,
                "calibration": 0.15,
                "safety":      0.30,
                "data_quality":0.15,
                "audit_fail":  0.50,
            },
            "ban_after_full_slash":     True,
            "report_false_positive_pct": 0.10,
        },
    },

    # ═══ V5 LAYER C: GEOGRAPHY ══════════════════════════════════════════════
    "geography": {
        "regions": {
            "georgia": {
                "share":               0.40,
                "hourly_cost_usd":     8.0,
                "retention_multiplier": 0.85,
                "learning_alpha":      0.10,
                "max_tier_advance_speed": 1.00,
                "alt_wage_usd":         12.0,
            },
            "philippines": {
                "share":               0.35,
                "hourly_cost_usd":     6.0,
                "retention_multiplier": 0.90,
                "learning_alpha":      0.12,
                "max_tier_advance_speed": 1.10,
                "alt_wage_usd":         8.0,
            },
            "kenya": {
                "share":               0.25,
                "hourly_cost_usd":    10.0,
                "retention_multiplier": 1.10,
                "learning_alpha":      0.09,
                "max_tier_advance_speed": 0.95,
                "alt_wage_usd":         11.0,
            },
        },
        # geo_shock and tesla_stress are off in baseline; activated by sweep cells
    },

    # ═══ V5 LAYER D: POINTS-TO-TOKEN TRANSITION ═════════════════════════════
    # Default baseline: tokens active from day 1 (matches v4 behavior).
    # Track 2 sweep cells override this.
    "points_to_token": {
        "trigger_type": "always_token",   # v4 behavior — token live from start
    },
}


if __name__ == "__main__":
    start = time.time()

    print("Running CrowdBrain v5 token economy simulation (36 months)...")
    print()

    # Single-run debug pass
    print("Single-run monthly progression (seed=42):")
    history, customers = run_simulation_v5(PARAMS_V5, seed=42)
    for h in history:
        sentiment = h.get("sentiment_state", "n/a")[:4]
        era_short = h.get("era", "n/a")[:4]
        cust_active = h.get("customer_count_active", 0)
        top3 = h.get("customer_top_3_concentration_pct", 0)
        nrr = h.get("customer_nrr_blended", 1.0)
        events = h.get("events_fired_this_month", [])
        ev_str = "+".join(events) if events else ""
        unlock = h.get("tier_unlock_state", {})
        unlock_str = f" T3={int(unlock.get(3, True))}T4={int(unlock.get(4, True))}T5={int(unlock.get(6, True))}" if unlock else ""
        print(
            f"  M{h['month']:2d}: price=${h['token_price']:.4f}  "
            f"rev=${h['monthly_revenue']:>9,.0f}  "
            f"T4+={h['operators_t4_plus']:>5}  "
            f"active={h['active_operators']:>6}  "
            f"sent={sentiment} era={era_short}  "
            f"cust={cust_active:>3} top3={top3:>4.1f}% nrr={nrr:.2f}  "
            f"slash={h['slash_rate']:.1%}{unlock_str}  "
            f"{ev_str}"
        )
    result = evaluate_v5(history, customers)
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
    print("  v4/v5 Supplements:")
    print(f"    Top-3 concentration:    {result['top_3_concentration_pct']:.1f}%")
    print(f"    NRR (blended):          {result['nrr_blended']:.2f}x")

    # v5-specific final-state metrics
    final = history[-1] if history else {}
    if "tier_unlock_state" in final:
        print(f"    Final tier unlock:      T3={final['tier_unlock_state'].get(3)} T4={final['tier_unlock_state'].get(4)} T5={final['tier_unlock_state'].get(6)}")
    if "providers_count_active" in final:
        print(f"    Active providers:       {final['providers_count_active']} (avg quality {final.get('provider_avg_quality', 0):.3f})")
        print(f"    Provider slashed cum:   ${final.get('provider_slashed_cumulative_usd', 0):,}")
    if "region_op_counts" in final:
        rcounts = final["region_op_counts"]
        print(f"    Region distribution:    GE={rcounts.get('georgia', 0)} PH={rcounts.get('philippines', 0)} KE={rcounts.get('kenya', 0)}")
    if "token_active" in final:
        print(f"    Token active:           {final['token_active']} (transition month: {final.get('transition_month', 'n/a')})")

    elapsed = time.time() - start
    print()
    print(f"Single-run completed in {elapsed:.1f}s")
