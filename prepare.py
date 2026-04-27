"""
CrowdTrain v3 Token Economy Simulator — Multi-Witness Validation Edition
========================================================================
v12 Memo redesign with peer-review hierarchy, hours-based task economy,
DePIN node network as agents, fiat ramp, hardware unlock.

DO NOT MODIFY — modify train.py for parameter experiments.

Major changes vs v2:
- Tasks are first-class (1 task = 1 produced hour), risk-weighted sampling
- 3-validator consensus (>=2 agree) with T6 audit escalation
- Graduated slashing (10/25/50/ban) + 50/50 validator/burn split
- Quality-gated linear hardware-stake unlock (per tier, independent)
- Revenue-gated fiat ramp; T0-T2 always pure tokens
- Quality-correlated sell pressure
- Sync tiers (T2/T4/T5) capped by node arm-hours
- Treasury entity with TGE distribution + linear team/investor vesting
- Bootstrap months 1-3: T0/T1 auto-pass (no validators yet)
- 36-month horizon
"""

import json
import math
import random
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

from validation import (
    Task, select_validators, run_consensus, escalate_to_audit,
    apply_slashing, update_strikes_and_clean_streak,
)
from nodes import (
    Node, maybe_spawn_node, total_arm_hours_available, cap_sync_tier_supply,
    compute_node_utilization, distribute_node_revenue, node_roi_score,
    capacity_utilization_score, HOURS_PER_ARM_PER_MONTH,
)
from treasury import (
    Treasury, initial_treasury, vest_team_and_investors,
    process_customer_fiat, pay_operator_fiat, fiat_ratio_for_arr,
)


# ─── SIMULATION CONSTANTS ──────────────────────────────────────────────────
SIMULATION_MONTHS = 36
RANDOM_SEED = 42
NUM_MONTE_CARLO_RUNS = 15   # reduced from 50 for fast iteration; bump for final report
TARGET_OPERATORS_12MO = 50_000


# ─── 7-TIER PIPELINE ───────────────────────────────────────────────────────
TIERS = {
    0: {"name": "Simulation Training",  "min_months": 0,  "skill_req": 0.0},
    1: {"name": "Data Labeling",         "min_months": 1,  "skill_req": 0.10},
    2: {"name": "Browser Teleop",        "min_months": 2,  "skill_req": 0.20},
    3: {"name": "In-the-Wild Capture",   "min_months": 3,  "skill_req": 0.35},
    4: {"name": "Facility Teleop",       "min_months": 5,  "skill_req": 0.55},
    5: {"name": "Live Deployment",       "min_months": 8,  "skill_req": 0.75},
    6: {"name": "Partner Missions",      "min_months": 12, "skill_req": 0.90},
}

DEFAULT_TIER_HOURS = {0: 20, 1: 80, 2: 120, 3: 80, 4: 120, 5: 80, 6: 40}
DEFAULT_TIER_RATES = {0: 0.0, 1: 5.0, 2: 8.0, 3: 12.0, 4: 18.0, 5: 28.0, 6: 45.0}
DEFAULT_TIER_IS_SYNC = {0: False, 1: False, 2: True, 3: False, 4: True, 5: True, 6: False}
SYNC_TIERS = [t for t, s in DEFAULT_TIER_IS_SYNC.items() if s]

DEFAULT_SAMPLE_RATES = {0: 0.10, 1: 0.10, 2: 0.25, 3: 0.25, 4: 1.00, 5: 1.00, 6: 1.00}

BASE_CHURN_BY_TIER = {0: 0.25, 1: 0.18, 2: 0.10, 3: 0.08, 4: 0.04, 5: 0.025, 6: 0.015}
BASE_PROGRESSION_RATE = {0: 0.55, 1: 0.25, 2: 0.20, 3: 0.12, 4: 0.12, 5: 0.07, 6: 0.00}


# ─── OPERATOR ──────────────────────────────────────────────────────────────
@dataclass
class Operator:
    id: int
    join_month: int
    tier: int = 0
    skill: float = 0.0
    tokens_held: float = 0.0
    tokens_staked: float = 0.0
    hardware_deposit_t3: float = 0.0
    hardware_deposit_t4: float = 0.0
    hardware_deposit_t6: float = 0.0
    qualified_hours_t3: float = 0.0
    qualified_hours_t4: float = 0.0
    qualified_hours_t6: float = 0.0
    unlocked_stake_t3: float = 0.0
    unlocked_stake_t4: float = 0.0
    unlocked_stake_t6: float = 0.0
    months_active: int = 0
    churned: bool = False
    churn_month: Optional[int] = None
    cumulative_earnings_usd: float = 0.0
    fiat_earnings: float = 0.0
    quality_score: float = 0.7
    has_credential: bool = False
    strikes: int = 0
    clean_hours_since_last_strike: float = 0.0
    is_banned: bool = False
    cooldown_until_month: Optional[int] = None
    tasks_produced: int = 0
    tasks_reviewed: int = 0
    false_positive_count: int = 0
    time_budget_used_this_month: float = 0.0
    review_capacity_remaining: float = 0.0
    tier_hours_cap: float = 0.0


# ─── ONBOARDING ────────────────────────────────────────────────────────────
def monthly_onboarding_schedule(month: int) -> int:
    """Community-seeded S-curve, extended through month 36."""
    if month <= 12:
        sched = [300, 500, 1000, 1800, 3000, 5000, 6500, 7500, 8000, 7000, 5500, 4900]
        return sched[month - 1]
    elif month <= 24:
        base = 4500
        factor = (1.02 * 0.95) ** (month - 12)
        return int(base * factor)
    else:
        # Months 25-36: gradual saturation
        base = 4500 * ((1.02 * 0.95) ** 12)
        factor = 0.92 ** (month - 24)
        return max(200, int(base * factor))


# ─── DEMAND MODEL ──────────────────────────────────────────────────────────
def monthly_customer_demand_hours(
    month: int,
    num_t4_plus: int,
    total_active: int,
    per_customer_hours: Optional[Dict[int, float]] = None,
    max_customers_at_24mo: int = 60,
    curve_steepness: float = 0.4,
    curve_midpoint_month: int = 13,
    growth_post_24mo: float = 5.0,
    customer_cap: int = 200,
    volatility_std: float = 0.10,
) -> Dict[int, float]:
    """
    Customer demand for hours per tier. Pre-revenue m1-6, S-curve from m7.
    Configurable so the sweep can explore demand-constrained vs supply-constrained regimes.
    """
    if month <= 6:
        return {t: 0.0 for t in range(7)}

    if month <= 24:
        customers = max(0, int(max_customers_at_24mo /
                               (1 + math.exp(-curve_steepness * (month - curve_midpoint_month)))))
    else:
        customers = min(customer_cap, int(max_customers_at_24mo - 5 + (month - 24) * growth_post_24mo))

    if per_customer_hours is None:
        per_customer_hours = {0: 0, 1: 500, 2: 300, 3: 200, 4: 200, 5: 100, 6: 30}

    noise = max(0.5, 1.0 + random.gauss(0.0, volatility_std))
    return {t: per_customer_hours.get(t, 0) * customers * noise for t in range(7)}


# ─── TIME-BUDGET ALLOCATOR ─────────────────────────────────────────────────
def allocate_time_budgets(
    active_ops: List[Operator],
    customer_demand: Dict[int, float],
    sync_tier_supply: Dict[int, float],
    tier_hours_per_month: Dict[int, int],
    operator_total_budget: int,
    tier_is_sync: Dict[int, bool],
) -> Tuple[Dict[int, float], Dict[int, List[Operator]]]:
    """
    Allocate per-operator tier_hours_cap and review_capacity_remaining.
    Returns (tier_hours_actual, ops_by_tier).
    """
    # Reset per-op state
    for op in active_ops:
        op.time_budget_used_this_month = 0.0
        op.review_capacity_remaining = 0.0
        op.tier_hours_cap = 0.0

    ops_by_tier: Dict[int, List[Operator]] = {t: [] for t in range(7)}
    for op in active_ops:
        if op.is_banned or op.cooldown_until_month is not None:
            continue
        ops_by_tier[op.tier].append(op)

    tier_hours_actual: Dict[int, float] = {}
    for tier in range(7):
        ops = ops_by_tier[tier]
        if not ops:
            tier_hours_actual[tier] = 0.0
            continue
        nominal = tier_hours_per_month.get(tier, 0)
        max_supply = nominal * len(ops)
        demand = customer_demand.get(tier, 0.0)
        if tier_is_sync.get(tier, False):
            demand = min(demand, sync_tier_supply.get(tier, 0.0))
        actual = min(max_supply, demand)
        tier_hours_actual[tier] = actual

        per_op = actual / len(ops) if ops else 0.0
        for op in ops:
            op.tier_hours_cap = per_op
            if tier >= 2:
                op.review_capacity_remaining = max(0.0, operator_total_budget - per_op)

    return tier_hours_actual, ops_by_tier


# ─── TOKEN PRICE MODEL ─────────────────────────────────────────────────────
def token_price_model(
    month: int,
    circulating_supply: float,
    locked_stake: float,
    total_burned: float,
    monthly_revenue: float,
    prev_price: float,
    sell_pressure_tokens: float = 0.0,
) -> float:
    """
    Structural model. Price reverts to a fundamental valuation:
      fundamental = (annualized_revenue * multiplier) / float_supply
    Mild momentum + lognormal noise. Floors prevent zero, ceiling prevents runaway.
    """
    float_supply = max(1.0, circulating_supply - locked_stake)
    burn_factor = 1.0 + (total_burned / max(1.0, circulating_supply + total_burned)) * 0.5

    # Fundamental: revenue-multiple per token (P/S ratio analog)
    # Annualized revenue × revenue multiple = market cap. Divide by float = price.
    REVENUE_MULTIPLE = 30.0  # SaaS-like multiple
    annualized_revenue = monthly_revenue * 12
    fundamental = (annualized_revenue * REVENUE_MULTIPLE * burn_factor) / float_supply
    fundamental = max(0.001, fundamental)

    # Sell-pressure short-term drag (token dump weighs price down briefly)
    sell_drag = 1.0 - min(0.30, sell_pressure_tokens / max(1.0, float_supply) * 2.0)

    # Slow mean reversion toward fundamental + sell drag
    new_price = prev_price * 0.85 + fundamental * 0.15
    new_price *= sell_drag

    # Lognormal noise (relative)
    noise_factor = math.exp(random.gauss(0.0, 0.20))  # ~20% monthly vol
    new_price *= max(0.50, min(2.0, noise_factor))

    return max(0.001, new_price)


# ─── EVALUATE (9 SUB-SCORES) ───────────────────────────────────────────────
def evaluate(history: List[Dict]) -> Dict:
    if not history:
        return {"score": 0.0}
    final = history[-1]

    total_ever = max(1, final.get("total_operators_ever", 1))
    active_end = final.get("active_operators", 0)
    retention_raw = active_end / total_ever
    retention_score = min(1.0, retention_raw / 0.55)

    prices = [h.get("token_price", 0.01) for h in history[-12:]]
    if len(prices) > 1 and sum(prices) > 0:
        mean_p = sum(prices) / len(prices)
        var_p = sum((p - mean_p) ** 2 for p in prices) / len(prices)
        cv = (var_p ** 0.5) / max(0.001, mean_p)
        stability_score = max(0.0, 1.0 - cv)
    else:
        stability_score = 0.5
    peak = max(h.get("token_price", 0.01) for h in history)
    if final.get("token_price", 0.01) < peak * 0.2:
        stability_score *= 0.3

    cumulative_revenue = sum(h.get("monthly_revenue", 0) for h in history)
    revenue_score = min(1.0, cumulative_revenue / 50_000_000)

    gini = final.get("earnings_gini", 0.5)
    gini_score = max(0.0, 1.0 - gini / 0.6)

    t4_plus = final.get("operators_t4_plus", 0)
    qualified_score = min(1.0, t4_plus / 5_000)

    slash_rate = final.get("slash_rate", 0.0)
    quality_score = max(0.0, 1.0 - slash_rate * 5)

    fp_rate = final.get("false_positive_rate", 0.0)
    validator_integrity_score = max(0.0, min(1.0, 1.0 - fp_rate / 0.10))

    nroi = final.get("node_roi_score", 0.5)
    cap_util = final.get("capacity_utilization_score", 0.5)

    score = (
        retention_score * 0.20
        + stability_score * 0.10
        + revenue_score * 0.20
        + gini_score * 0.10
        + qualified_score * 0.15
        + quality_score * 0.05
        + validator_integrity_score * 0.10
        + nroi * 0.05
        + cap_util * 0.05
    )

    return {
        "score": round(score, 6),
        "retention_score": round(retention_score, 4),
        "stability_score": round(stability_score, 4),
        "revenue_score": round(revenue_score, 4),
        "gini_score": round(gini_score, 4),
        "qualified_score": round(qualified_score, 4),
        "quality_score": round(quality_score, 4),
        "validator_integrity_score": round(validator_integrity_score, 4),
        "node_roi_score": round(nroi, 4),
        "capacity_utilization_score": round(cap_util, 4),
        "retention_pct": round(retention_raw * 100, 1),
        "cumulative_revenue": round(cumulative_revenue),
        "final_price": round(final.get("token_price", 0), 4),
        "peak_price": round(peak, 4),
        "gini": round(gini, 4),
        "t4_plus_operators": t4_plus,
        "active_operators_final": active_end,
        "total_operators_ever": total_ever,
        "slash_rate": round(slash_rate, 4),
        "false_positive_rate": round(fp_rate, 4),
    }


def compute_gini(values: List[float]) -> float:
    if not values or len(values) < 2:
        return 0.0
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    total = sum(sorted_vals)
    if total == 0:
        return 0.0
    gini_sum = 0.0
    for i, v in enumerate(sorted_vals):
        gini_sum += (2 * (i + 1) - n - 1) * v
    return gini_sum / (n * total)


# ─── PARAM HELPER ──────────────────────────────────────────────────────────
def get_nested(params: Dict, path: str, default):
    """Dot-path getter: get_nested(p, 'supply.initial_supply', 10M)."""
    cur = params
    for k in path.split("."):
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


# ─── MAIN SIMULATION ──────────────────────────────────────────────────────
def run_simulation(params: Dict, seed: int = RANDOM_SEED) -> List[Dict]:
    random.seed(seed)

    # ── Param shortcuts ──
    initial_supply = get_nested(params, "supply.initial_supply", 10_000_000)
    max_supply = get_nested(params, "supply.max_supply", 500_000_000)
    emission_rate = get_nested(params, "supply.monthly_emission_rate", 20_000_000)
    halving_interval = get_nested(params, "supply.halving_interval_months", 12)
    initial_token_price = get_nested(params, "supply.initial_token_price", 1.0)
    tge_dist = get_nested(params, "supply.tge_distribution", {
        "team_pct": 0.15, "investor_pct": 0.15, "treasury_pct": 0.25,
        "initial_liquidity_pct": 0.05, "operator_emissions_pct": 0.40,
    })
    team_vest = get_nested(params, "supply.team_vest_months", 48)
    investor_vest = get_nested(params, "supply.investor_vest_months", 48)

    tier_hours = get_nested(params, "task_model.tier_hours_per_month", DEFAULT_TIER_HOURS)
    tier_rates = get_nested(params, "task_model.tier_hourly_rate_usd", DEFAULT_TIER_RATES)
    tier_is_sync = get_nested(params, "task_model.tier_is_sync", DEFAULT_TIER_IS_SYNC)
    op_total_budget = get_nested(params, "task_model.operator_total_hour_budget", 160)
    base_emission_per_op = get_nested(params, "task_model.base_emission_per_active_op_per_month", 20.0)
    emission_tier_mult = get_nested(params, "task_model.emission_tier_multiplier",
                                     {0: 0.5, 1: 1.0, 2: 1.0, 3: 1.5, 4: 2.0, 5: 2.5, 6: 3.0})

    # Demand model params
    per_customer_hours = get_nested(params, "demand.per_customer_hours_per_tier",
                                     {0: 0, 1: 500, 2: 300, 3: 200, 4: 200, 5: 100, 6: 30})
    max_customers = get_nested(params, "demand.max_customers_at_24mo", 60)
    curve_steepness = get_nested(params, "demand.customer_curve_steepness", 0.4)
    curve_midpoint = get_nested(params, "demand.customer_curve_midpoint_month", 13)
    customer_growth_post = get_nested(params, "demand.customer_growth_post_24mo", 5.0)
    customer_cap = get_nested(params, "demand.customer_cap", 200)
    demand_vol_std = get_nested(params, "demand.demand_volatility_std", 0.10)

    sample_rates = get_nested(params, "validation.sample_rate_by_tier", DEFAULT_SAMPLE_RATES)
    validators_per_task = get_nested(params, "validation.validators_per_task", 3)
    min_offset = get_nested(params, "validation.min_validator_tier_offset", 1)
    base_fee_pct = get_nested(params, "validation.validator_base_fee_pct", 0.10)
    audit_tier = get_nested(params, "validation.audit_escalation_tier", 6)
    bootstrap_months = get_nested(params, "validation.bootstrap_months", 3)
    catch_split = get_nested(params, "validation.catch_bonus_split_within_group",
                              {"fail_voters": 0.70, "pass_voters": 0.30})

    strike_severities = get_nested(params, "slashing.strike_severities", [0.10, 0.25, 0.50])
    ban_strike = get_nested(params, "slashing.ban_on_strike", 4)
    cooldown_months = get_nested(params, "slashing.cooldown_months_after_3rd", 1)
    clean_per_reset = get_nested(params, "slashing.clean_hours_per_strike_reset", 100)
    slash_split = get_nested(params, "slashing.slash_split", {"validators": 0.50, "burn": 0.50})

    # Hardware stakes: USD-denominated, auto-converts to tokens at current price
    stake_t3_usd = get_nested(params, "hardware.stake_required_t3_usd", 100)
    stake_t4_usd = get_nested(params, "hardware.stake_required_t4_usd", 400)
    stake_t6_usd = get_nested(params, "hardware.stake_required_t6_usd", 800)
    # Backward-compat: also read token-denominated if present
    stake_t3_tokens_legacy = get_nested(params, "hardware.stake_required_t3", None)
    stake_t4_tokens_legacy = get_nested(params, "hardware.stake_required_t4", None)
    stake_t6_tokens_legacy = get_nested(params, "hardware.stake_required_t6", None)
    hours_to_unlock = get_nested(params, "hardware.hours_to_full_unlock", 100)
    quality_thresh_unlock = get_nested(params, "hardware.quality_threshold_for_unlock", 0.65)

    phase_ladder = get_nested(params, "earnings.phase_revenue_ladder_arr_to_fiat_ratio",
                               [(0, 0.0), (1_000_000, 0.30), (5_000_000, 0.50), (20_000_000, 0.70)])
    phase_exempt = set(get_nested(params, "earnings.phase_exempt_tiers", [0, 1, 2]))
    fiat_to_ops = get_nested(params, "earnings.fiat_split_to_operators", 0.70)
    fiat_to_treas = get_nested(params, "earnings.fiat_split_to_treasury", 0.30)

    burn_pct = get_nested(params, "burn.burn_pct_of_revenue", 0.60)

    sell_low = get_nested(params, "sell_pressure.base_sell_pct_low", 0.25)
    sell_high = get_nested(params, "sell_pressure.base_sell_pct_high", 0.55)
    sell_decay = get_nested(params, "sell_pressure.quality_decay_strength", 0.6)
    fiat_decay = get_nested(params, "sell_pressure.fiat_holding_decay_strength", 0.4)

    arms_per_node = get_nested(params, "nodes.arms_per_node", 4)
    capex_per_node = get_nested(params, "nodes.capex_per_node_usd", 50_000)
    ops_per_node_target = get_nested(params, "nodes.ops_per_node_target", 1_000)
    partner_share = get_nested(params, "nodes.partner_revenue_share", 0.15)
    node_amort = get_nested(params, "nodes.node_amortization_months", 36)
    max_concurrent_per_arm = get_nested(params, "nodes.max_concurrent_operators_per_arm", 2)

    staking_churn_red = get_nested(params, "retention.staking_churn_reduction", 0.90)
    earnings_churn_red = get_nested(params, "retention.earnings_churn_reduction", 0.90)
    nft_bonus = get_nested(params, "retention.nft_retention_bonus", 0.40)
    gam_bonus = get_nested(params, "retention.gamification_churn_reduction", 0.30)

    sim_trained_bonus = get_nested(params, "study_assumption.sim_trained_quality_bonus", 0.20)

    # ── State ──
    treasury = initial_treasury(initial_supply, tge_dist, team_vest, investor_vest)
    operators: List[Operator] = []
    nodes_list: List[Node] = []
    next_id = 0
    next_task_id = 0
    history: List[Dict] = []

    circulating_supply = initial_supply
    total_burned = 0.0
    total_emitted = initial_supply
    token_price = initial_token_price
    cumulative_revenue = 0.0
    cumulative_validator_payouts = 0.0
    cumulative_audit_escalations = 0
    cumulative_false_positives = 0
    cumulative_review_attempts = 0

    # ── MAIN LOOP ──
    for month in range(1, SIMULATION_MONTHS + 1):
        # Step 1: Halving + emission
        halvings = (month - 1) // halving_interval
        current_emission = emission_rate / (2 ** halvings)
        if total_emitted + current_emission > max_supply:
            current_emission = max(0.0, max_supply - total_emitted)
        circulating_supply += current_emission
        total_emitted += current_emission

        # Step 2: Vest team & investor (treated as added to circulating, sold pessimistically)
        vested = vest_team_and_investors(treasury, month)
        circulating_supply += vested

        # Step 3: Onboard new operators
        new_count = monthly_onboarding_schedule(month)
        for _ in range(new_count):
            operators.append(Operator(id=next_id, join_month=month))
            next_id += 1

        active_ops = [op for op in operators if not op.churned and not op.is_banned]
        op_by_id = {op.id: op for op in active_ops}  # perf: O(1) lookup

        # Base emission per active op (memo: "token emissions subsidize training")
        # Tier multiplier rewards advancement (helps T3+ accumulate for next-tier stake).
        if base_emission_per_op > 0:
            for op in active_ops:
                tier_mult = emission_tier_mult.get(op.tier, 1.0)
                emission = base_emission_per_op * tier_mult
                op.tokens_held += emission
                op.cumulative_earnings_usd += emission * token_price

        # Step 4: Update node network (spawn as needed)
        for _ in range(50):
            node = maybe_spawn_node(
                len(active_ops), nodes_list, ops_per_node_target,
                month, arms_per_node, capex_per_node,
            )
            if node is None:
                break
            nodes_list.append(node)

        # Step 5: Customer demand + sync capacity
        t4_plus = sum(1 for op in active_ops if op.tier >= 4)
        customer_demand = monthly_customer_demand_hours(
            month, t4_plus, len(active_ops),
            per_customer_hours=per_customer_hours,
            max_customers_at_24mo=max_customers,
            curve_steepness=curve_steepness,
            curve_midpoint_month=curve_midpoint,
            growth_post_24mo=customer_growth_post,
            customer_cap=customer_cap,
            volatility_std=demand_vol_std,
        )
        total_arm_h = total_arm_hours_available(nodes_list, max_concurrent_ops_per_arm=max_concurrent_per_arm)
        sync_demand = {t: customer_demand.get(t, 0.0) for t in SYNC_TIERS}
        sync_supplied = cap_sync_tier_supply(sync_demand, total_arm_h)

        # Step 6: Allocate time budgets
        tier_hours_actual, ops_by_tier = allocate_time_budgets(
            active_ops, customer_demand, sync_supplied,
            tier_hours, op_total_budget, tier_is_sync,
        )

        # Step 7-11: Generate sampled tasks + run consensus + slashing
        review_attempts = 0
        false_positives_this_month = 0
        audit_escalations_this_month = 0
        slash_count = 0
        slash_amount_total = 0.0
        burn_amount_validators = 0.0
        validator_payout_total = 0.0
        validator_base_fee_total = 0.0
        hours_per_op: Dict[int, float] = {}
        ops_quality_updates: Dict[int, List[float]] = {}
        total_tasks_produced = 0
        tier_pass_revenue: Dict[int, float] = {t: 0.0 for t in range(7)}
        tier_fail_count: Dict[int, int] = {t: 0 for t in range(7)}

        # Pass A: track per-op hours produced (no Task objects yet)
        for tier in range(7):
            tops = ops_by_tier.get(tier, [])
            if not tops or tier_hours_actual[tier] <= 0:
                continue
            per_op = tier_hours_actual[tier] / len(tops)
            for op in tops:
                op_h = min(per_op, op.tier_hours_cap if op.tier_hours_cap else per_op)
                hours_per_op[op.id] = op_h
                op.tasks_produced += int(op_h)
                total_tasks_produced += int(op_h)

        # Pre-compute eligible validator pools per producer-tier (perf optimization)
        # Validator must have tier >= producer_tier + min_offset, not banned, not in cooldown.
        # We filter once per month and skip the per-task filtering. Capacity (review_capacity_remaining)
        # is tracked but not enforced here for perf (small overshoot acceptable).
        eligible_validator_pool_by_producer_tier: Dict[int, List[Operator]] = {}
        for ptier in range(7):
            min_v_tier = ptier + min_offset
            pool = []
            for vtier in range(min_v_tier, 7):
                pool.extend(ops_by_tier.get(vtier, []))
            eligible_validator_pool_by_producer_tier[ptier] = pool
        t6_audit_pool = ops_by_tier.get(audit_tier, [])

        # Pass B: sample tasks for review (only sampled tasks get Task objects)
        for tier in range(7):
            tops = ops_by_tier.get(tier, [])
            if not tops or tier_hours_actual[tier] <= 0:
                continue
            sample_rate = sample_rates.get(tier, 0.0)
            expected_reviews = int(round(tier_hours_actual[tier] * sample_rate))
            if expected_reviews <= 0:
                continue

            # Pick reviewed tasks: random producer per review (weighted by hours)
            weights = [hours_per_op.get(op.id, 0.0) for op in tops]
            total_w = sum(weights)
            if total_w <= 0:
                continue

            eligible_validators = eligible_validator_pool_by_producer_tier.get(tier, [])

            for _ in range(expected_reviews):
                # Weighted random producer
                r = random.random() * total_w
                acc = 0.0
                producer = tops[-1]
                for op, w in zip(tops, weights):
                    acc += w
                    if r <= acc:
                        producer = op
                        break

                # Generate raw quality
                base_q = 0.65
                tier_bonus = tier * 0.05
                skill_factor = (producer.skill - 0.5) * 0.20
                noise = random.gauss(0.0, 0.10)
                raw_q = max(0.0, min(1.0, base_q + tier_bonus + sim_trained_bonus + skill_factor + noise))

                task = Task(
                    id=next_task_id,
                    producer_id=producer.id,
                    tier=tier,
                    hours=1.0,
                    value_usd=tier_rates.get(tier, 0.0),
                    value_tokens=tier_rates.get(tier, 0.0) / max(0.0001, token_price),
                    raw_quality_score=raw_q,
                    sampled_for_review=True,
                )
                next_task_id += 1
                review_attempts += 1

                # Fast validator selection: random sample from pre-filtered pool
                # (skip per-task filtering since pool was filtered once at month start)
                if len(eligible_validators) < validators_per_task:
                    if len(t6_audit_pool) >= validators_per_task:
                        validators = random.sample(t6_audit_pool, validators_per_task)
                    elif len(eligible_validators) >= 2:
                        validators = random.sample(eligible_validators, min(validators_per_task, len(eligible_validators)))
                    else:
                        task.final_verdict = "auto_pass"
                        tier_pass_revenue[tier] += task.value_usd
                        ops_quality_updates.setdefault(producer.id, []).append(raw_q)
                        continue
                else:
                    validators = random.sample(eligible_validators, validators_per_task)

                # Skip the producer if they happened to get sampled as their own validator
                validators = [v for v in validators if v.id != producer.id]
                if len(validators) < 2:
                    task.final_verdict = "auto_pass"
                    tier_pass_revenue[tier] += task.value_usd
                    ops_quality_updates.setdefault(producer.id, []).append(raw_q)
                    continue

                verdict = run_consensus(task, validators, month, bootstrap_months)
                if verdict is None and task.escalated:
                    audit_escalations_this_month += 1
                    verdict = escalate_to_audit(task, t6_audit_pool)

                # Validator base fees (paid even on auto_pass when validators were assigned but not used? No — only on actual review)
                if verdict not in ("auto_pass", None):
                    fee_per = task.value_tokens * base_fee_pct
                    for v in validators:
                        v.tokens_held += fee_per
                        validator_base_fee_total += fee_per

                if verdict == "fail":
                    slash_result = apply_slashing(
                        producer, task, validators,
                        strike_severities, slash_split, catch_split,
                        ban_strike, cooldown_months, month,
                    )
                    slash_count += 1
                    slash_amount_total += slash_result["slash_amount"]
                    burn_amount_validators += slash_result["burn_amount"]
                    validator_payout_total += slash_result["validator_payout_total"]
                    false_positives_this_month += len(slash_result["false_positive_validator_ids"])
                    tier_fail_count[tier] += 1
                    sample_q = max(0.0, raw_q - 0.20)
                    ops_quality_updates.setdefault(producer.id, []).append(sample_q)
                    # Producer earns nothing on fail
                else:
                    # Pass (or auto_pass)
                    tier_pass_revenue[tier] += task.value_usd
                    ops_quality_updates.setdefault(producer.id, []).append(raw_q)

        # Burn slashed tokens
        circulating_supply -= burn_amount_validators
        total_burned += burn_amount_validators
        cumulative_validator_payouts += validator_payout_total
        cumulative_audit_escalations += audit_escalations_this_month
        cumulative_false_positives += false_positives_this_month
        cumulative_review_attempts += review_attempts

        # Update producer quality_scores from samples (EMA)
        for op_id, samples in ops_quality_updates.items():
            op = op_by_id.get(op_id)
            if op:
                avg = sum(samples) / len(samples)
                op.quality_score = op.quality_score * 0.85 + avg * 0.15

        # Step 12: Compute monthly revenue (pass tasks * rate, both sampled-pass & unreviewed)
        # Reviewed tasks: only "pass" verdict tasks count as revenue (failed tasks earn nothing for the producer)
        # Unreviewed tasks: all count
        sampled_pass_revenue = sum(tier_pass_revenue.values())
        # Unreviewed hours = total hours - sampled hours
        unreviewed_revenue = 0.0
        for tier in range(7):
            sampled_h = int(round(tier_hours_actual[tier] * sample_rates.get(tier, 0.0)))
            unreviewed_h = max(0.0, tier_hours_actual[tier] - sampled_h)
            unreviewed_revenue += unreviewed_h * tier_rates.get(tier, 0.0)
        monthly_rev_usd = sampled_pass_revenue + unreviewed_revenue

        # Step 13: Process customer fiat through treasury (burn + split)
        if monthly_rev_usd > 0:
            burn_result = process_customer_fiat(
                treasury, monthly_rev_usd, burn_pct, fiat_to_ops, fiat_to_treas, token_price,
            )
            circulating_supply -= burn_result["tokens_burned"]
            total_burned += burn_result["tokens_burned"]

        # Compute current fiat ratio (trailing 12mo as ARR proxy)
        trailing_12 = sum(h.get("monthly_revenue", 0) for h in history[-11:]) + monthly_rev_usd if history else monthly_rev_usd
        current_arr = trailing_12  # 12mo sum approximates ARR
        fiat_ratio = fiat_ratio_for_arr(current_arr, phase_ladder)

        # Step 14: Pay producers (token + fiat split, fiat-ramp aware)
        total_token_distributed = 0.0
        total_fiat_paid = 0.0
        producer_payouts_value_usd: Dict[int, float] = {}

        for tier in range(7):
            tops = ops_by_tier.get(tier, [])
            if not tops or tier_hours_actual[tier] <= 0:
                continue
            sample_rate = sample_rates.get(tier, 0.0)
            tier_total_hours = tier_hours_actual[tier]
            sampled_hours = tier_total_hours * sample_rate
            unreviewed_hours = tier_total_hours - sampled_hours
            # Per-tier net per-hour value:
            #   reviewed-pass: gross_rate * (1 - base_fee_pct * validators_per_task)
            #   unreviewed:    gross_rate
            # Split estimated per op proportional to their hours
            gross_rate = tier_rates.get(tier, 0.0)
            net_rate_reviewed = gross_rate * max(0.0, 1.0 - base_fee_pct * validators_per_task)

            # Estimate per-op pass rate from quality (proxy)
            for op in tops:
                op_h = hours_per_op.get(op.id, 0.0)
                if op_h <= 0:
                    continue
                share_of_tier = op_h / tier_total_hours if tier_total_hours > 0 else 0.0
                op_sampled = op_h * sample_rate
                op_unreviewed = op_h - op_sampled
                # Pass rate estimated from quality_score
                op_pass_rate = max(0.5, min(0.99, op.quality_score + sim_trained_bonus * 0.5))
                op_passed_sampled_value = op_sampled * net_rate_reviewed * op_pass_rate
                op_unreviewed_value = op_unreviewed * gross_rate
                op_total_usd = op_passed_sampled_value + op_unreviewed_value

                producer_payouts_value_usd[op.id] = op_total_usd

                # Apply fiat-ramp (skip exempt tiers)
                if op.tier in phase_exempt:
                    fiat_part = 0.0
                    token_part_usd = op_total_usd
                else:
                    fiat_part = op_total_usd * fiat_ratio
                    token_part_usd = op_total_usd * (1.0 - fiat_ratio)

                # Token portion (always paid in tokens at current price)
                token_amt = token_part_usd / max(0.0001, token_price)
                op.tokens_held += token_amt
                total_token_distributed += token_amt

                # Fiat portion: drain treasury operator pool
                if fiat_part > 0:
                    paid = pay_operator_fiat(treasury, fiat_part)
                    op.fiat_earnings += paid
                    total_fiat_paid += paid
                    # Convert unpaid to tokens
                    unpaid = fiat_part - paid
                    if unpaid > 0:
                        fallback_tokens = unpaid / max(0.0001, token_price)
                        op.tokens_held += fallback_tokens
                        total_token_distributed += fallback_tokens

                op.cumulative_earnings_usd += op_total_usd

        # Step 15: Distribute node revenue (sync-tier subset)
        sync_revenue_usd = 0.0
        for t in SYNC_TIERS:
            sync_revenue_usd += sync_supplied.get(t, 0.0) * tier_rates.get(t, 0.0)
        if sync_revenue_usd > 0 and nodes_list:
            distribute_node_revenue(nodes_list, sync_revenue_usd, partner_share)
        avg_node_util = compute_node_utilization(
            nodes_list, sum(sync_supplied.values()),
            max_concurrent_ops_per_arm=max_concurrent_per_arm,
        )

        cumulative_revenue += monthly_rev_usd

        # Step 16: Hardware unlock (per-tier independent, quality-gated linear)
        for op in active_ops:
            if op.quality_score < quality_thresh_unlock:
                continue
            h = hours_per_op.get(op.id, 0.0)
            if op.tier == 3 and op.hardware_deposit_t3 > 0:
                op.qualified_hours_t3 += h
                u = min(1.0, op.qualified_hours_t3 / hours_to_unlock)
                op.unlocked_stake_t3 = op.hardware_deposit_t3 * u
            elif op.tier == 4 and op.hardware_deposit_t4 > 0:
                op.qualified_hours_t4 += h
                u = min(1.0, op.qualified_hours_t4 / hours_to_unlock)
                op.unlocked_stake_t4 = op.hardware_deposit_t4 * u
            elif op.tier == 6 and op.hardware_deposit_t6 > 0:
                op.qualified_hours_t6 += h
                u = min(1.0, op.qualified_hours_t6 / hours_to_unlock)
                op.unlocked_stake_t6 = op.hardware_deposit_t6 * u

        # Step 17: Skill + tier progression (with hardware stake gates)
        for op in active_ops:
            op.months_active += 1
            sgain = max(0.0, 0.06 + random.gauss(0.02, 0.01))
            op.skill = min(1.0, op.skill + sgain)

            if op.tier < 6:
                next_tier = op.tier + 1
                info = TIERS[next_tier]
                if op.months_active >= info["min_months"] and op.skill >= info["skill_req"]:
                    rate = BASE_PROGRESSION_RATE.get(op.tier, 0.0)
                    if random.random() < rate:
                        # Hardware stake gate (USD-denominated, converts to tokens at current price)
                        required = 0
                        target_attr = None
                        if next_tier == 3:
                            required = (stake_t3_tokens_legacy if stake_t3_tokens_legacy is not None
                                        else stake_t3_usd / max(0.01, token_price))
                            target_attr = "hardware_deposit_t3"
                        elif next_tier == 4:
                            required = (stake_t4_tokens_legacy if stake_t4_tokens_legacy is not None
                                        else stake_t4_usd / max(0.01, token_price))
                            target_attr = "hardware_deposit_t4"
                        elif next_tier == 6:
                            required = (stake_t6_tokens_legacy if stake_t6_tokens_legacy is not None
                                        else stake_t6_usd / max(0.01, token_price))
                            target_attr = "hardware_deposit_t6"

                        if required > 0:
                            if op.tokens_held >= required:
                                op.tokens_held -= required
                                op.tokens_staked += required
                                setattr(op, target_attr, required)
                                op.tier = next_tier
                            # else: stuck — needs more tokens
                        else:
                            op.tier = next_tier

            if op.tier >= 2 and not op.has_credential:
                op.has_credential = True

        # Step 18: Quality-correlated sell pressure
        sell_pressure_total = 0.0
        for op in active_ops:
            if op.tokens_held > 10:
                base = random.uniform(sell_low, sell_high)
                fiat_share = min(1.0, op.fiat_earnings / max(1.0, op.cumulative_earnings_usd))
                pct = base * (1.0 - op.quality_score * sell_decay) * (1.0 - fiat_share * fiat_decay)
                pct = max(0.05, min(0.85, pct))
                amt = op.tokens_held * pct
                op.tokens_held -= amt
                sell_pressure_total += amt

        # Step 19: Token price update
        total_locked_stake = sum(op.tokens_staked for op in active_ops)
        token_price = token_price_model(
            month, circulating_supply, total_locked_stake,
            total_burned, monthly_rev_usd, token_price,
            sell_pressure_tokens=sell_pressure_total,
        )

        # Step 20: Strike maintenance + cooldown countdown
        update_strikes_and_clean_streak(
            active_ops, hours_per_op, clean_per_reset, quality_thresh_unlock,
        )
        for op in active_ops:
            if op.cooldown_until_month is not None and month >= op.cooldown_until_month:
                op.cooldown_until_month = None

        # Step 21: Churn
        for op in active_ops:
            if op.is_banned:
                # Banned ops permanently churn
                if not op.churned:
                    op.churned = True
                    op.churn_month = month
                    op.tokens_staked = 0
                    op.tokens_held = 0
                continue
            base_churn = BASE_CHURN_BY_TIER.get(op.tier, 0.15)
            if op.tier <= 1:
                base_churn *= (1 - gam_bonus)
            if op.tokens_staked > 0:
                base_churn *= (1 - staking_churn_red)
            monthly_earn_usd = op.cumulative_earnings_usd / max(1, op.months_active)
            if monthly_earn_usd > 150:
                base_churn *= (1 - earnings_churn_red)
            if op.has_credential:
                base_churn *= (1 - nft_bonus)
            if month > 3 and history:
                recent = [h.get("token_price", token_price) for h in history[-3:]]
                if recent and token_price < sum(recent) / len(recent) * 0.7:
                    base_churn *= 1.5
            base_churn = max(0.005, min(0.50, base_churn))

            if random.random() < base_churn:
                op.churned = True
                op.churn_month = month
                refund = op.unlocked_stake_t3 + op.unlocked_stake_t4 + op.unlocked_stake_t6
                locked = max(0.0, op.tokens_staked - refund)
                op.tokens_held += refund
                circulating_supply -= locked  # locked portion burned
                total_burned += locked
                op.tokens_staked = 0
                op.unlocked_stake_t3 = op.unlocked_stake_t4 = op.unlocked_stake_t6 = 0
                op.hardware_deposit_t3 = op.hardware_deposit_t4 = op.hardware_deposit_t6 = 0
                op.tokens_held = 0  # operators take their tokens off-chain

        # ── Snapshot ──
        active_end = [op for op in operators if not op.churned]
        t4_end = [op for op in active_end if op.tier >= 4]
        earnings_list = [op.cumulative_earnings_usd for op in active_end if op.months_active > 0]
        gini_val = compute_gini(earnings_list) if earnings_list else 0.0
        tier_dist = {t: sum(1 for op in active_end if op.tier == t) for t in range(7)}
        validators_active = [op for op in active_end if op.tier >= 2]
        banned_count = sum(1 for op in operators if op.is_banned)
        unlocked_total = sum(op.unlocked_stake_t3 + op.unlocked_stake_t4 + op.unlocked_stake_t6 for op in active_end)

        nroi = node_roi_score(nodes_list, month, node_amort)
        cap_util_score = capacity_utilization_score(nodes_list)
        false_positive_rate = cumulative_false_positives / max(1, cumulative_review_attempts)
        total_demand_h = sum(customer_demand.values())
        total_supplied_h = sum(tier_hours_actual.values())
        unmet_pct = max(0.0, (total_demand_h - total_supplied_h) / max(1, total_demand_h))

        snap = {
            "month": month,
            "active_operators": len(active_end),
            "total_operators_ever": len(operators),
            "new_operators": new_count,
            "churned_this_month": sum(1 for op in operators if op.churn_month == month),
            "operators_t4_plus": len(t4_end),
            "tier_distribution": tier_dist,
            "circulating_supply": round(circulating_supply),
            "total_burned": round(total_burned),
            "total_staked": round(sum(op.tokens_staked for op in active_end)),
            "total_unlocked_stake": round(unlocked_total),
            "token_price": round(token_price, 6),
            "monthly_revenue": round(monthly_rev_usd),
            "total_token_rewards_distributed": round(total_token_distributed),
            "total_fiat_paid": round(total_fiat_paid),
            "total_validator_payouts": round(validator_payout_total),
            "total_validator_base_fees": round(validator_base_fee_total),
            "earnings_gini": round(gini_val, 4),
            "sell_pressure_tokens": round(sell_pressure_total),
            "slash_rate": round(slash_count / max(1, review_attempts), 4),
            "slash_count_this_month": slash_count,
            "audit_escalations": audit_escalations_this_month,
            "false_positive_rate": round(false_positive_rate, 4),
            "validator_count": len(validators_active),
            "node_count": len(nodes_list),
            "node_utilization_avg": round(avg_node_util, 3),
            "node_roi_score": round(nroi, 3),
            "capacity_utilization_score": round(cap_util_score, 3),
            "fiat_paid_ratio": round(fiat_ratio, 3),
            "treasury_operator_pool_usd": round(treasury.operator_payout_pool_usd),
            "treasury_reserves_usd": round(treasury.treasury_reserves_usd),
            "banned_operators_count": banned_count,
            "customer_demand_unmet_pct": round(unmet_pct, 3),
            "total_tasks_produced": total_tasks_produced,
            "total_tasks_reviewed": review_attempts,
        }
        history.append(snap)

    return history


# ─── MONTE CARLO ──────────────────────────────────────────────────────────
def run_monte_carlo(params: Dict, n_runs: int = NUM_MONTE_CARLO_RUNS) -> Dict:
    all_results = []
    for i in range(n_runs):
        history = run_simulation(params, seed=RANDOM_SEED + i)
        result = evaluate(history)
        all_results.append(result)

    if not all_results:
        return {"score_mean": 0.0}

    keys = all_results[0].keys()
    agg: Dict = {"n_runs": n_runs}
    for k in keys:
        vals = [r.get(k, 0) for r in all_results if isinstance(r.get(k), (int, float))]
        if vals:
            mean_v = sum(vals) / len(vals)
            std_v = (sum((v - mean_v) ** 2 for v in vals) / len(vals)) ** 0.5
            agg[k + "_mean"] = round(mean_v, 4)
            agg[k + "_std"] = round(std_v, 4)
    return agg


def print_results(params: Dict, metrics: Dict):
    print()
    print("=" * 78)
    print("CrowdTrain v3 Monte Carlo Results")
    print("=" * 78)
    print(f"  Composite Score:   {metrics.get('score_mean', 0):.4f} ± {metrics.get('score_std', 0):.4f}")
    print()
    print("  Sub-scores (mean ± std):")
    sub_scores = [
        ("retention_score",            "Retention"),
        ("stability_score",            "Price stability"),
        ("revenue_score",              "Revenue"),
        ("gini_score",                 "Fairness (Gini)"),
        ("qualified_score",            "Qualified ops"),
        ("quality_score",              "Data quality"),
        ("validator_integrity_score",  "Validator integrity"),
        ("node_roi_score",             "Node ROI"),
        ("capacity_utilization_score", "Capacity utilization"),
    ]
    for k, label in sub_scores:
        m = metrics.get(k + "_mean", 0)
        s = metrics.get(k + "_std", 0)
        print(f"    {label:24s}  {m:.4f} ± {s:.4f}")
    print()
    print("  Key Metrics:")
    print(f"    Retention %:            {metrics.get('retention_pct_mean', 0):.1f}%")
    print(f"    Cumulative Revenue:     ${metrics.get('cumulative_revenue_mean', 0):,.0f}")
    print(f"    Final Token Price:      ${metrics.get('final_price_mean', 0):.4f}")
    print(f"    Earnings Gini:          {metrics.get('gini_mean', 0):.3f}")
    print(f"    T4+ Operators:          {metrics.get('t4_plus_operators_mean', 0):.0f}")
    print(f"    Slash Rate:             {metrics.get('slash_rate_mean', 0):.2%}")
    print(f"    False Positive Rate:    {metrics.get('false_positive_rate_mean', 0):.2%}")
    print()
    h = hashlib.sha256(json.dumps(params, sort_keys=True, default=str).encode()).hexdigest()[:12]
    print(f"  Param hash:  {h}")
