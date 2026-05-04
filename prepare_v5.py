"""
CrowdBrain v5 Simulation Engine — built on top of v4 baseline.
================================================================
Adds 4 v5 layers on top of the v4 engine:
  Layer A (tier_unlock)  — conditional unlock for T3/T4/T6 (memo: T3-T5 unlock with scale)
  Layer B (node_providers) — first-class bonded node-providers (separate from operators)
  Layer C (geography)    — 3-region operator pool (Georgia/Philippines/Kenya) cost+retention+skill
  Layer D (points_to_token) — points-only phase + transition trigger

Each v5 layer is opt-in via PARAMS:
  params['tier_unlock'] absent  -> all tiers unlocked (v4 behavior)
  params['node_providers'] absent -> v4 nodes_list only
  params['geography'] absent    -> single global pool (v4 behavior)
  params['points_to_token'] absent -> tokens active from day 1 (v4 behavior)

Plus v5 customer extension: design partners with multi-year contracts (immune to
satisfaction-driven churn during contract term).

DO NOT MODIFY (engine). Edit train_v5.py for parameter experiments.
"""

import json
import math
import random
import hashlib
from typing import List, Dict, Optional, Tuple

from prepare import (
    Operator, TIERS, DEFAULT_TIER_HOURS, DEFAULT_TIER_RATES, DEFAULT_TIER_IS_SYNC,
    SYNC_TIERS, DEFAULT_SAMPLE_RATES, BASE_CHURN_BY_TIER, BASE_PROGRESSION_RATE,
    monthly_onboarding_schedule, allocate_time_budgets, monthly_customer_demand_hours,
    token_price_model, evaluate as evaluate_base, compute_gini, get_nested,
)
from validation import (
    Task, run_consensus, escalate_to_audit, apply_slashing, update_strikes_and_clean_streak,
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
from customers import (
    DEFAULT_SEGMENTS, DEFAULT_DESIGN_PARTNERS, DEFAULT_USD_PER_HOUR_BLENDED, Customer,
    spawn_design_partners, arrive_new_customers, aggregate_demand_across_customers,
    update_customer_satisfaction, evaluate_churn_or_expansion,
    compute_concentration_metrics, compute_segment_revenue_mix, compute_nrr_blended,
)
from macro import (
    SentimentState, update_sentiment, sentiment_multipliers,
    AMM, init_amm, amm_price, amm_execute_sell, amm_execute_buy, amm_buy_and_burn,
    amm_apply_one_shot_price_shock,
    EventSchedule, init_event_schedule, fire_events, DEFAULT_EVENTS_36MO,
    EraState, update_era, era_multipliers,
)
from operators_v4 import (
    DEFAULT_PERSONAS, assign_persona, get_persona_attrs, init_operator_state_v4,
    update_learning_skill, quality_modifier_from_learning,
    make_stake_decision, compute_sell_pct, update_income_volatility,
    income_volatility_churn_boost, tier_advance_threshold_multiplier,
    validator_queue_share, hw_investor_unlock_rate,
    referral_count_this_month, assign_referee_persona,
    persona_distribution, persona_diversity_index, avg_persona_metric,
)

# ─── V5 LAYERS ────────────────────────────────────────────────────────────
from tier_unlock import (
    DEFAULT_UNLOCK, compute_unlock_state, operator_can_advance_to,
)
from node_providers import (
    DEFAULT_PROVIDER_PARAMS, NodeProvider, init_providers_for_arms,
    monthly_node_quality_check, simulate_operator_reports,
    average_node_quality, distribute_provider_revenue, total_arms_active,
)
from geography import (
    DEFAULT_REGIONS, assign_region, region_cost_per_hour,
    region_retention_multiplier, region_learning_alpha, region_tier_speed,
    region_alt_wage, wage_gap_churn_boost, regions_active_share,
    aggregate_region_stats, TESLA_HIRING_STRESS,
)
from points_to_token import (
    TokenizationState, init_state as init_token_state,
    maybe_trigger_transition, credit_operator_for_work,
    is_amm_active,
)


# ─── ENGINE CONSTANTS ─────────────────────────────────────────────────────
SIMULATION_MONTHS = 36
RANDOM_SEED = 42
NUM_MONTE_CARLO_RUNS = 5    # smaller default for fast iteration; bump for final


# ─── MAIN SIMULATION ──────────────────────────────────────────────────────
def run_simulation_v5(params: Dict, seed: int = RANDOM_SEED) -> Tuple[List[Dict], List[Customer]]:
    """
    v5 main loop. Returns (history, final_customers_state). Adds 4 v5 layers on top
    of v4. Each layer can be ablated by removing its PARAMS section.
    """
    random.seed(seed)

    # Detect which pillars are active (v4)
    personas_on = "operators" in params
    customers_on = "customers" in params
    macro_on = "macro" in params

    # ── V5 layer detection ──
    tier_unlock_on = "tier_unlock" in params
    node_providers_on = "node_providers" in params
    geography_on = "geography" in params
    points_token_on = "points_to_token" in params

    # ── v3 param shortcuts (always loaded) ──
    initial_supply = get_nested(params, "supply.initial_supply", 10_000_000)
    max_supply = get_nested(params, "supply.max_supply", 500_000_000)
    emission_rate = get_nested(params, "supply.monthly_emission_rate", 5_000_000)
    halving_interval = get_nested(params, "supply.halving_interval_months", 18)
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
    base_emission_per_op = get_nested(params, "task_model.base_emission_per_active_op_per_month", 45.0)
    emission_tier_mult = get_nested(params, "task_model.emission_tier_multiplier",
                                     {0: 0.5, 1: 1.0, 2: 1.2, 3: 1.5, 4: 2.0, 5: 2.5, 6: 3.0})

    # Demand model (v3 fallback)
    per_customer_hours_v3 = get_nested(params, "demand.per_customer_hours_per_tier",
                                        {0: 0, 1: 500, 2: 300, 3: 200, 4: 200, 5: 100, 6: 30})
    max_customers_v3 = get_nested(params, "demand.max_customers_at_24mo", 60)
    curve_steepness_v3 = get_nested(params, "demand.customer_curve_steepness", 0.4)
    curve_midpoint_v3 = get_nested(params, "demand.customer_curve_midpoint_month", 13)
    customer_growth_post_v3 = get_nested(params, "demand.customer_growth_post_24mo", 5.0)
    customer_cap_v3 = get_nested(params, "demand.customer_cap", 200)
    demand_vol_std_v3 = get_nested(params, "demand.demand_volatility_std", 0.10)

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

    stake_t3_usd = get_nested(params, "hardware.stake_required_t3_usd", 100)
    stake_t4_usd = get_nested(params, "hardware.stake_required_t4_usd", 150)
    stake_t6_usd = get_nested(params, "hardware.stake_required_t6_usd", 800)
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

    arms_per_node = get_nested(params, "nodes.arms_per_node", 2)
    capex_per_node = get_nested(params, "nodes.capex_per_node_usd", 50_000)
    ops_per_node_target = get_nested(params, "nodes.ops_per_node_target", 2_000)
    partner_share = get_nested(params, "nodes.partner_revenue_share", 0.15)
    node_amort = get_nested(params, "nodes.node_amortization_months", 36)
    max_concurrent_per_arm = get_nested(params, "nodes.max_concurrent_operators_per_arm", 2)

    staking_churn_red = get_nested(params, "retention.staking_churn_reduction", 0.90)
    earnings_churn_red = get_nested(params, "retention.earnings_churn_reduction", 0.90)
    nft_bonus = get_nested(params, "retention.nft_retention_bonus", 0.40)
    gam_bonus = get_nested(params, "retention.gamification_churn_reduction", 0.30)

    sim_trained_bonus = get_nested(params, "study_assumption.sim_trained_quality_bonus", 0.20)

    # ── v4 param shortcuts (per-pillar) ──
    if personas_on:
        persona_dist = get_nested(params, "operators.personas", DEFAULT_PERSONAS)
        learning_alpha = get_nested(params, "operators.learning.alpha", 0.10)
        learning_cap = get_nested(params, "operators.learning.cap", 0.30)
        referral_base_rate = get_nested(params, "operators.referrals.base_rate_per_op", 0.05)
        referral_inheritance = get_nested(params, "operators.referrals.persona_inheritance_prob", 0.30)
    else:
        persona_dist = None

    if customers_on:
        segments = get_nested(params, "customers.segments", DEFAULT_SEGMENTS)
        design_partner_specs = get_nested(params, "customers.arrival.design_partners",
                                          DEFAULT_DESIGN_PARTNERS)
        arrival_params = get_nested(params, "customers.arrival", {
            "lambda_max_per_segment": 3.0, "lambda_curve_midpoint": 13, "lambda_curve_steepness": 0.4,
        })
        size_dist = get_nested(params, "customers.size_distribution",
                               {"alpha": 1.5, "min_factor": 0.10, "max_factor": 4.0})
        sat_params = get_nested(params, "customers.satisfaction", {
            "weights": {"quality": 0.40, "demand_fulfill": 0.40, "sla": 0.20},
            "churn_threshold": 0.50, "churn_consecutive": 3,
            "expand_threshold": 0.80, "expand_consecutive": 3,
            "expand_pct": 0.20, "expansion_cap": 3.0,
            "sla_fulfill_min": 0.95, "sla_quality_min": 0.70,
        })
        usd_per_hour_blended = get_nested(params, "customers.usd_per_hour_blended", DEFAULT_USD_PER_HOUR_BLENDED)

    # ── v5 param shortcuts ──
    tier_unlock_rules = get_nested(params, "tier_unlock.rules", DEFAULT_UNLOCK) if tier_unlock_on else DEFAULT_UNLOCK
    op_count_qualifier = get_nested(params, "tier_unlock.op_count_qualifier", "active_with_credential")

    node_provider_params = get_nested(params, "node_providers.params", DEFAULT_PROVIDER_PARAMS) if node_providers_on else None

    region_params = get_nested(params, "geography.regions", DEFAULT_REGIONS) if geography_on else None
    geo_shock = get_nested(params, "geography.geo_shock", None)
    tesla_stress = get_nested(params, "geography.tesla_stress", None)

    point_token_params = get_nested(params, "points_to_token", None) if points_token_on else None

    # v5 customer extension: design partner contract term (multi-year)
    dp_contract_term = get_nested(params, "customers.design_partner_contract_term_months", None) if customers_on else None

    # v5 hardware-stake range: $300-500 (memo). v4 default $150 stays unless params override.
    # Use stake_t3_usd / t4_usd / t6_usd already loaded above.

    # Stress test: customer_arrival_multiplier (e.g., funding winter = 0.25)
    stress_arrival_mult = get_nested(params, "stress.customer_arrival_multiplier", 1.0)
    stress_arrival_start_month = get_nested(params, "stress.customer_arrival_start_month", 0)

    # MVP-slip: simulation only starts at this month (operators don't onboard before)
    mvp_start_month = get_nested(params, "stress.mvp_start_month", 0)

    # Intelligence Library: revenue line from m24 onwards
    intel_lib_active_from = get_nested(params, "stress.intelligence_library_start_month", None)
    intel_lib_factor = get_nested(params, "stress.intelligence_library_factor", 0.005)   # 0.5% per cum-op-hour

    if macro_on:
        sentiment_params = get_nested(params, "macro.sentiment", {
            "p_bull_to_bear": 1.0 / 21, "p_bear_to_bull": 1.0 / 9, "initial": "bull",
            "multipliers": {
                "bull": {"sell": 0.6, "customer_arrival": 1.3, "op_acquisition": 1.10},
                "bear": {"sell": 1.5, "customer_arrival": 0.7, "op_acquisition": 0.85},
            },
        })
        amm_params = get_nested(params, "macro.amm", {
            "initial_token_pool": 1_000_000, "initial_usd_pool": 1_000_000,
        })
        events_spec = get_nested(params, "macro.events", DEFAULT_EVENTS_36MO)
        era_params = get_nested(params, "macro.era", {
            "growth_rev_threshold": 5_000_000, "growth_month_threshold": 12,
            "maturity_rev_threshold": 50_000_000, "maturity_month_threshold": 36,
            "maturity_fiat_threshold": 0.70,
            "era_multipliers": {
                "bootstrap": {"emission": 1.0, "referral": 1.2, "customer_arrival": 1.0},
                "growth":    {"emission": 1.0, "referral": 1.5, "customer_arrival": 1.5},
                "maturity":  {"emission": 0.5, "referral": 0.8, "customer_arrival": 1.2},
            },
        })

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

    # v4 state
    customers_list: List[Customer] = []
    next_cust_id = 0
    if customers_on:
        customers_list, next_cust_id = spawn_design_partners(
            0, design_partner_specs,
            contract_term_months=dp_contract_term,    # v5: multi-year DP contracts
        )

    # ── V5 STATE ──
    # Layer A: tier-unlock state — recomputed each month
    unlock_state_curr = {3: True, 4: True, 6: True}   # default all unlocked

    # Layer B: node-providers — initialized from arms count
    providers_list: List[NodeProvider] = []
    cumulative_provider_slashed_usd = 0.0
    cumulative_provider_audits = 0
    cumulative_node_reports_filed = 0

    # Layer C: geography — operator regions are tagged at creation
    cumulative_wage_gap_churns = 0

    # Layer D: points-to-token state
    token_state = init_token_state(point_token_params)
    cumulative_points_at_cutover = 0.0

    # Intelligence Library accounting
    cumulative_op_hours = 0.0

    sentiment_state = SentimentState(state=sentiment_params.get("initial", "bull")) if macro_on else None
    amm_state = init_amm(
        token_pool=amm_params.get("initial_token_pool", 1_000_000),
        usd_pool=amm_params.get("initial_usd_pool", 1_000_000),
    ) if macro_on else None
    if amm_state:
        # Sync initial price with TGE token price (defaults are 1:1)
        token_price = amm_price(amm_state)
    event_schedule = init_event_schedule(events_spec) if macro_on else None
    era_state = EraState() if macro_on else None

    # Total referrals for metrics
    cumulative_referrals = 0

    # ── MAIN LOOP ──
    for month in range(1, SIMULATION_MONTHS + 1):

        # ─ Step 0 (NEW): Update sentiment ─
        if macro_on:
            sentiment_state = update_sentiment(
                sentiment_state, month,
                p_bull_to_bear=sentiment_params.get("p_bull_to_bear", 1.0 / 21),
                p_bear_to_bull=sentiment_params.get("p_bear_to_bull", 1.0 / 9),
            )
            sent_mults = sentiment_multipliers(sentiment_state, sentiment_params)
        else:
            sent_mults = {"sell": 1.0, "customer_arrival": 1.0, "op_acquisition": 1.0}

        # ─ Step 1: Halving + emission ─
        halvings = (month - 1) // halving_interval
        current_emission = emission_rate / (2 ** halvings)
        if total_emitted + current_emission > max_supply:
            current_emission = max(0.0, max_supply - total_emitted)
        # Era multiplier on emission
        emission_era_mult = 1.0
        if macro_on:
            era_mults = era_multipliers(era_state, era_params)
            emission_era_mult = era_mults.get("emission", 1.0)
        current_emission *= emission_era_mult
        circulating_supply += current_emission
        total_emitted += current_emission

        # ─ Step 2: Vest team & investor ─
        vested = vest_team_and_investors(treasury, month)
        circulating_supply += vested

        # ─ Step 3: Onboard new operators (with personas + referrals) ─
        organic_count = monthly_onboarding_schedule(month)
        # Apply sentiment multiplier to acquisition
        organic_count = int(organic_count * sent_mults.get("op_acquisition", 1.0))
        # v5: realistic-mode onboarding multiplier (scales to memo's 1K trained @ Q3 2026 target)
        op_onboarding_mult = get_nested(params, "task_model.onboarding_multiplier", 1.0)
        organic_count = int(organic_count * op_onboarding_mult)

        new_count = organic_count

        # Referral boost (from existing active operators)
        referrals_this_month = 0
        if personas_on and operators:
            active_ops_for_refs = [op for op in operators if not op.churned and not op.is_banned]
            era_ref_mult = 1.0
            if macro_on:
                era_ref_mult = era_multipliers(era_state, era_params).get("referral", 1.0)
            referrals_this_month = referral_count_this_month(
                active_ops_for_refs, base_rate=referral_base_rate, era_referral_mult=era_ref_mult,
            )
            new_count += referrals_this_month
            cumulative_referrals += referrals_this_month

        # v5: Adjust region shares if a geo_shock is active this month
        if geography_on:
            current_region_shares = regions_active_share(region_params, geo_shock, month)

        for ref_idx in range(new_count):
            op = Operator(id=next_id, join_month=month)
            # v5: tag operator with region (used downstream for cost/retention/skill)
            if geography_on:
                # weighted draw using current_region_shares
                items = list(current_region_shares.items())
                weights = [w for _, w in items]
                op.region = random.choices([r for r, _ in items], weights=weights, k=1)[0]
            else:
                op.region = "global"
            # v5: points-only phase — operator earns points before transition
            op.points_earned = 0.0
            if personas_on:
                # Pick persona
                if ref_idx < referrals_this_month and active_ops_for_refs:
                    parent = random.choice(active_ops_for_refs)
                    persona = assign_referee_persona(
                        parent, inheritance_prob=referral_inheritance, persona_dist=persona_dist,
                    )
                    init_operator_state_v4(op, month, persona, persona_dist=persona_dist,
                                           referrer_id=parent.id)
                else:
                    persona = assign_persona(persona_dist=persona_dist)
                    init_operator_state_v4(op, month, persona, persona_dist=persona_dist)
                # HW Investor: front-load stake from seed allocation
                seed_allocation = base_emission_per_op * 0.5  # half a month of emission as seed
                front_load = seed_allocation * op.persona_front_load_stake
                if front_load > 0:
                    op.tokens_held += seed_allocation
                    op.tokens_held -= front_load
                    op.tokens_staked += front_load
            operators.append(op)
            next_id += 1

        active_ops = [op for op in operators if not op.churned and not op.is_banned]
        op_by_id = {op.id: op for op in active_ops}

        # Base emission per active op
        if base_emission_per_op > 0:
            for op in active_ops:
                tier_mult = emission_tier_mult.get(op.tier, 1.0)
                emission = base_emission_per_op * tier_mult * emission_era_mult
                op.tokens_held += emission
                op.cumulative_earnings_usd += emission * token_price

        # ─ Step 4: Update node network ─
        for _ in range(50):
            node = maybe_spawn_node(
                len(active_ops), nodes_list, ops_per_node_target,
                month, arms_per_node, capex_per_node,
            )
            if node is None:
                break
            nodes_list.append(node)

        # ─ Step 5 (modified): Customer demand ─
        if customers_on:
            # Compute event-driven and era multipliers (only when macro+events are on)
            if macro_on and event_schedule is not None:
                event_effects = fire_events(event_schedule, month, amm_state)
            else:
                event_effects = {"customer_arrival_mult": 1.0, "customer_churn_mult": 1.0,
                                 "fired_event_types": [], "price_shocked": False}
            # Handle key_customer_loss event: drop largest active customer
            if "key_customer_loss" in event_effects.get("fired_event_types", []):
                active_custs = sorted(
                    [c for c in customers_list if c.status == "active"],
                    key=lambda c: c.contract_size_usd * c.demand_multiplier,
                    reverse=True,
                )
                if active_custs:
                    biggest = active_custs[0]
                    biggest.status = "churned"
                    biggest.churn_month = month
            era_arr_mult = 1.0
            if macro_on:
                era_arr_mult = era_multipliers(era_state, era_params).get("customer_arrival", 1.0)
            # v5 stress: funding winter multiplies arrival rate
            stress_mult = stress_arrival_mult if month >= stress_arrival_start_month else 1.0
            eff_arr_mult = (
                sent_mults.get("customer_arrival", 1.0)
                * era_arr_mult
                * event_effects.get("customer_arrival_mult", 1.0)
                * stress_mult
            )
            new_custs, next_cust_id = arrive_new_customers(
                month, next_cust_id, segments, arrival_params,
                sentiment_arrival_mult=eff_arr_mult,
                era_arrival_mult=1.0,  # already folded above
                pareto_alpha=size_dist.get("alpha", 1.5),
                pareto_min_factor=size_dist.get("min_factor", 0.10),
                pareto_max_factor=size_dist.get("max_factor", 4.0),
            )
            customers_list.extend(new_custs)

            customer_demand, per_customer_demand = aggregate_demand_across_customers(
                customers_list, segments, tier_rates, usd_per_hour_blended,
            )
        else:
            event_effects = {"customer_arrival_mult": 1.0, "customer_churn_mult": 1.0,
                             "fired_event_types": [], "price_shocked": False}
            t4_plus_pre = sum(1 for op in active_ops if op.tier >= 4)
            customer_demand = monthly_customer_demand_hours(
                month, t4_plus_pre, len(active_ops),
                per_customer_hours=per_customer_hours_v3,
                max_customers_at_24mo=max_customers_v3,
                curve_steepness=curve_steepness_v3,
                curve_midpoint_month=curve_midpoint_v3,
                growth_post_24mo=customer_growth_post_v3,
                customer_cap=customer_cap_v3,
                volatility_std=demand_vol_std_v3,
            )
            per_customer_demand = {}

        total_arm_h = total_arm_hours_available(nodes_list, max_concurrent_ops_per_arm=max_concurrent_per_arm)
        sync_demand = {t: customer_demand.get(t, 0.0) for t in SYNC_TIERS}
        sync_supplied = cap_sync_tier_supply(sync_demand, total_arm_h)

        # ─ Step 6: Allocate time budgets ─
        tier_hours_actual, ops_by_tier = allocate_time_budgets(
            active_ops, customer_demand, sync_supplied,
            tier_hours, op_total_budget, tier_is_sync,
        )

        # ─ Step 7-11: Tasks, consensus, slashing (v3 logic preserved) ─
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

        # Pass A: hours per op
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

        # Validator pools
        eligible_validator_pool_by_producer_tier: Dict[int, List[Operator]] = {}
        for ptier in range(7):
            min_v_tier = ptier + min_offset
            pool = []
            for vtier in range(min_v_tier, 7):
                pool.extend(ops_by_tier.get(vtier, []))
            eligible_validator_pool_by_producer_tier[ptier] = pool
        t6_audit_pool = ops_by_tier.get(audit_tier, [])

        # Pass B: sample tasks for review
        for tier in range(7):
            tops = ops_by_tier.get(tier, [])
            if not tops or tier_hours_actual[tier] <= 0:
                continue
            sample_rate = sample_rates.get(tier, 0.0)
            expected_reviews = int(round(tier_hours_actual[tier] * sample_rate))
            if expected_reviews <= 0:
                continue

            weights = [hours_per_op.get(op.id, 0.0) for op in tops]
            total_w = sum(weights)
            if total_w <= 0:
                continue

            eligible_validators = eligible_validator_pool_by_producer_tier.get(tier, [])

            for _ in range(expected_reviews):
                r = random.random() * total_w
                acc = 0.0
                producer = tops[-1]
                for op, w in zip(tops, weights):
                    acc += w
                    if r <= acc:
                        producer = op
                        break

                # Quality (with learning bonus if v4 personas on)
                base_q = 0.65
                tier_bonus = tier * 0.05
                skill_factor = (producer.skill - 0.5) * 0.20
                noise = random.gauss(0.0, 0.10)
                raw_q = base_q + tier_bonus + sim_trained_bonus + skill_factor + noise
                if personas_on:
                    raw_q *= quality_modifier_from_learning(producer)
                raw_q = max(0.0, min(1.0, raw_q))

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

                if len(eligible_validators) < validators_per_task:
                    if len(t6_audit_pool) >= validators_per_task:
                        validators = random.sample(t6_audit_pool, validators_per_task)
                    elif len(eligible_validators) >= 2:
                        validators = random.sample(eligible_validators,
                                                   min(validators_per_task, len(eligible_validators)))
                    else:
                        task.final_verdict = "auto_pass"
                        tier_pass_revenue[tier] += task.value_usd
                        ops_quality_updates.setdefault(producer.id, []).append(raw_q)
                        continue
                else:
                    validators = random.sample(eligible_validators, validators_per_task)

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
                else:
                    tier_pass_revenue[tier] += task.value_usd
                    ops_quality_updates.setdefault(producer.id, []).append(raw_q)

        circulating_supply -= burn_amount_validators
        total_burned += burn_amount_validators
        cumulative_validator_payouts += validator_payout_total
        cumulative_audit_escalations += audit_escalations_this_month
        cumulative_false_positives += false_positives_this_month
        cumulative_review_attempts += review_attempts

        # Update producer quality_scores from samples
        for op_id, samples in ops_quality_updates.items():
            op = op_by_id.get(op_id)
            if op:
                avg = sum(samples) / len(samples)
                op.quality_score = op.quality_score * 0.85 + avg * 0.15

        # ─ Step 12: Compute monthly revenue ─
        sampled_pass_revenue = sum(tier_pass_revenue.values())
        unreviewed_revenue = 0.0
        for tier in range(7):
            sampled_h = int(round(tier_hours_actual[tier] * sample_rates.get(tier, 0.0)))
            unreviewed_h = max(0.0, tier_hours_actual[tier] - sampled_h)
            unreviewed_revenue += unreviewed_h * tier_rates.get(tier, 0.0)
        monthly_rev_usd = sampled_pass_revenue + unreviewed_revenue

        # ─ Customer revenue attribution ─
        if customers_on and per_customer_demand:
            for c in customers_list:
                if c.status != "active":
                    continue
                cust_demand = per_customer_demand.get(c.id, {})
                cust_demand_total = sum(cust_demand.values())
                if cust_demand_total <= 0:
                    continue
                # Estimate fulfillment %: sum across tiers of (tier_actual / tier_total_demand) * cust's_share
                cust_fulfilled = 0.0
                for tier, td in cust_demand.items():
                    if td > 0 and customer_demand.get(tier, 0) > 0:
                        tier_fulfill_ratio = min(1.0, tier_hours_actual.get(tier, 0.0) / customer_demand[tier])
                        cust_fulfilled += td * tier_fulfill_ratio
                fulfill_pct = cust_fulfilled / cust_demand_total
                effective_contract = c.contract_size_usd * c.demand_multiplier
                c.cumulative_revenue += effective_contract * fulfill_pct

        # ─ Step 13 (modified): Process customer fiat (AMM if enabled) ─
        if monthly_rev_usd > 0:
            if macro_on and amm_state is not None:
                # AMM buy-and-burn
                burn_fiat = monthly_rev_usd * burn_pct
                tokens_burned, new_price = amm_buy_and_burn(amm_state, burn_fiat)
                circulating_supply -= tokens_burned
                total_burned += tokens_burned
                # Remainder goes to operator/treasury pools as before
                remainder = monthly_rev_usd - burn_fiat
                treasury.operator_payout_pool_usd += remainder * fiat_to_ops
                treasury.treasury_reserves_usd += remainder * fiat_to_treas
                token_price = new_price
            else:
                burn_result = process_customer_fiat(
                    treasury, monthly_rev_usd, burn_pct, fiat_to_ops, fiat_to_treas, token_price,
                )
                circulating_supply -= burn_result["tokens_burned"]
                total_burned += burn_result["tokens_burned"]

        # Compute current fiat ratio (trailing 12mo as ARR proxy)
        trailing_12 = sum(h.get("monthly_revenue", 0) for h in history[-11:]) + monthly_rev_usd if history else monthly_rev_usd
        current_arr = trailing_12
        fiat_ratio = fiat_ratio_for_arr(current_arr, phase_ladder)

        # ─ Step 14: Pay producers ─
        total_token_distributed = 0.0
        total_fiat_paid = 0.0
        per_op_income_usd: Dict[int, float] = {}

        for tier in range(7):
            tops = ops_by_tier.get(tier, [])
            if not tops or tier_hours_actual[tier] <= 0:
                continue
            sample_rate = sample_rates.get(tier, 0.0)
            tier_total_hours = tier_hours_actual[tier]
            gross_rate = tier_rates.get(tier, 0.0)
            net_rate_reviewed = gross_rate * max(0.0, 1.0 - base_fee_pct * validators_per_task)

            for op in tops:
                op_h = hours_per_op.get(op.id, 0.0)
                if op_h <= 0:
                    continue
                op_sampled = op_h * sample_rate
                op_unreviewed = op_h - op_sampled
                op_pass_rate = max(0.5, min(0.99, op.quality_score + sim_trained_bonus * 0.5))
                op_passed_sampled_value = op_sampled * net_rate_reviewed * op_pass_rate
                op_unreviewed_value = op_unreviewed * gross_rate
                op_total_usd = op_passed_sampled_value + op_unreviewed_value
                per_op_income_usd[op.id] = op_total_usd

                if op.tier in phase_exempt:
                    fiat_part = 0.0
                    token_part_usd = op_total_usd
                else:
                    fiat_part = op_total_usd * fiat_ratio
                    token_part_usd = op_total_usd * (1.0 - fiat_ratio)

                token_amt = token_part_usd / max(0.0001, token_price)
                # v5 Layer D: route to points or tokens based on transition state
                if points_token_on and not token_state.is_token_active:
                    op.points_earned = getattr(op, "points_earned", 0.0) + token_amt
                else:
                    op.tokens_held += token_amt
                total_token_distributed += token_amt

                if fiat_part > 0:
                    paid = pay_operator_fiat(treasury, fiat_part)
                    op.fiat_earnings += paid
                    total_fiat_paid += paid
                    unpaid = fiat_part - paid
                    if unpaid > 0:
                        fallback_tokens = unpaid / max(0.0001, token_price)
                        op.tokens_held += fallback_tokens
                        total_token_distributed += fallback_tokens

                op.cumulative_earnings_usd += op_total_usd

        # ─ Step 15: Distribute node revenue ─
        sync_revenue_usd = 0.0
        for t in SYNC_TIERS:
            sync_revenue_usd += sync_supplied.get(t, 0.0) * tier_rates.get(t, 0.0)
        if sync_revenue_usd > 0 and nodes_list:
            distribute_node_revenue(nodes_list, sync_revenue_usd, partner_share)
        avg_node_util = compute_node_utilization(
            nodes_list, sum(sync_supplied.values()),
            max_concurrent_ops_per_arm=max_concurrent_per_arm,
        )

        # ── v5 Layer B: Node providers (bonded community providers) ──
        if node_providers_on:
            # Total arms in the network = sum of arm_count in nodes_list
            total_network_arms = sum(n.arm_count for n in nodes_list)
            # Re-init providers when arm count changes (new nodes spawned this month)
            current_provider_arms = total_arms_active(providers_list)
            if total_network_arms != current_provider_arms:
                providers_list = init_providers_for_arms(total_network_arms, node_provider_params, month)

            # Operator reports against community nodes
            n_reports = simulate_operator_reports(providers_list, len(active_ops), month)
            cumulative_node_reports_filed += n_reports

            # Monthly node quality check + slashing
            node_quality_result = monthly_node_quality_check(
                providers_list, node_provider_params, month,
            )
            cumulative_provider_slashed_usd += node_quality_result["total_slashed_usd"]
            cumulative_provider_audits += node_quality_result["audits_resolved"]

            # Reroute revenue through providers
            provider_split = distribute_provider_revenue(
                providers_list, sync_revenue_usd, node_provider_params,
            )
            # provider_split tells us how much goes to treasury vs community providers

        # v5: Track cumulative operator hours (for Intelligence Library)
        for h in tier_hours_actual.values():
            cumulative_op_hours += h

        # v5: Intelligence Library — additional revenue line from m24 onward
        intel_lib_revenue = 0.0
        if intel_lib_active_from is not None and month >= intel_lib_active_from:
            intel_lib_revenue = cumulative_op_hours * intel_lib_factor
            monthly_rev_usd += intel_lib_revenue

        cumulative_revenue += monthly_rev_usd

        # ── v5 Layer A: Compute tier-unlock state for this month ──
        if tier_unlock_on:
            # Build op_count_by_tier (qualified ops at each tier)
            op_counts_by_tier = {t: 0 for t in range(7)}
            for op in active_ops:
                # Qualifier: active + has_credential + not banned
                if op.has_credential and not op.is_banned and not op.churned:
                    op_counts_by_tier[op.tier] = op_counts_by_tier.get(op.tier, 0) + 1
            unlock_state_curr = compute_unlock_state(
                tier_unlock_rules, month, cumulative_revenue, op_counts_by_tier,
                customer_demand_by_tier=customer_demand,
            )

        # v5 Layer D: Maybe trigger points->token transition
        if points_token_on:
            transition_event = maybe_trigger_transition(
                token_state, point_token_params, month, cumulative_revenue, operators,
            )
            if transition_event:
                cumulative_points_at_cutover = transition_event.get("points_converted", 0.0)
                # On transition, also activate AMM if not already (use macro AMM if defined)

        # ─ Step 16: Hardware unlock (with HW Investor fast-track) ─
        for op in active_ops:
            if op.quality_score < quality_thresh_unlock:
                continue
            h = hours_per_op.get(op.id, 0.0)
            if personas_on:
                # Effective unlock rate: 1.5x for HW Investor when q > 0.75
                rate = hw_investor_unlock_rate(op, base_rate=1.0/hours_to_unlock)
                effective_h = h * rate * hours_to_unlock  # convert to legacy 'qualified hours' units
            else:
                effective_h = h
            if op.tier == 3 and op.hardware_deposit_t3 > 0:
                op.qualified_hours_t3 += effective_h
                u = min(1.0, op.qualified_hours_t3 / hours_to_unlock)
                op.unlocked_stake_t3 = op.hardware_deposit_t3 * u
            elif op.tier == 4 and op.hardware_deposit_t4 > 0:
                op.qualified_hours_t4 += effective_h
                u = min(1.0, op.qualified_hours_t4 / hours_to_unlock)
                op.unlocked_stake_t4 = op.hardware_deposit_t4 * u
            elif op.tier == 6 and op.hardware_deposit_t6 > 0:
                op.qualified_hours_t6 += effective_h
                u = min(1.0, op.qualified_hours_t6 / hours_to_unlock)
                op.unlocked_stake_t6 = op.hardware_deposit_t6 * u

        # ─ Step 17 (modified): Skill + tier progression ─
        # Pre-compute price 30d momentum for stake decisions
        price_30d_mom = 0.0
        if len(history) >= 3:
            recent_prices = [h["token_price"] for h in history[-3:]]
            mean_recent = sum(recent_prices) / len(recent_prices)
            price_30d_mom = (token_price - mean_recent) / max(0.001, mean_recent)

        for op in active_ops:
            op.months_active += 1
            # v3 mechanical skill gain — drives tier progression gate (always)
            sgain = max(0.0, 0.06 + random.gauss(0.02, 0.01))
            op.skill = min(1.0, op.skill + sgain)
            # v4 learning curve — drives EXTRA quality bonus on top of skill_factor
            if personas_on:
                update_learning_skill(op, hours_per_op.get(op.id, 0.0),
                                       alpha=learning_alpha, cap=learning_cap)

            # Tier progression with persona-modulated speed
            tier_speed = tier_advance_threshold_multiplier(op) if personas_on else 1.0
            # v5 Layer C: geography may speed/slow advancement
            if geography_on and getattr(op, "region", None):
                tier_speed *= 1.0 / max(0.1, region_tier_speed(op.region, region_params))
            if op.tier < 6:
                next_tier = op.tier + 1
                info = TIERS[next_tier]
                effective_min_months = int(info["min_months"] * tier_speed)
                # v5 Layer A: gate by tier-unlock state for T3, T4, T6
                if tier_unlock_on and not operator_can_advance_to(next_tier, unlock_state_curr):
                    continue   # tier locked; skip advance for this op this month
                if op.months_active >= effective_min_months and op.skill >= info["skill_req"]:
                    rate = BASE_PROGRESSION_RATE.get(op.tier, 0.0)
                    if random.random() < rate:
                        required = 0
                        target_attr = None
                        if next_tier == 3:
                            required = stake_t3_usd / max(0.01, token_price)
                            target_attr = "hardware_deposit_t3"
                        elif next_tier == 4:
                            required = stake_t4_usd / max(0.01, token_price)
                            target_attr = "hardware_deposit_t4"
                        elif next_tier == 6:
                            required = stake_t6_usd / max(0.01, token_price)
                            target_attr = "hardware_deposit_t6"

                        # Persona-aware stake decision
                        if required > 0:
                            should_stake = True
                            if personas_on:
                                should_stake = make_stake_decision(op, required, price_30d_mom)
                            if should_stake and op.tokens_held >= required:
                                op.tokens_held -= required
                                op.tokens_staked += required
                                setattr(op, target_attr, required)
                                op.tier = next_tier
                        else:
                            op.tier = next_tier

            if op.tier >= 2 and not op.has_credential:
                op.has_credential = True

        # ─ Step 18 (modified): Sell pressure ─
        sell_pressure_total = 0.0
        for op in active_ops:
            if op.tokens_held <= 10:
                continue
            if personas_on:
                # Update income volatility from this month's earnings
                op_income = per_op_income_usd.get(op.id, 0.0)
                vol = update_income_volatility(op, op_income)
                pct = compute_sell_pct(op, sent_mults["sell"], op.quality_score, vol)
            else:
                base = random.uniform(sell_low, sell_high)
                fiat_share = min(1.0, op.fiat_earnings / max(1.0, op.cumulative_earnings_usd))
                pct = base * (1.0 - op.quality_score * sell_decay) * (1.0 - fiat_share * fiat_decay)
                pct = max(0.05, min(0.85, pct))
            amt = op.tokens_held * pct
            op.tokens_held -= amt
            sell_pressure_total += amt

        # ─ Step 19 (modified): Token price update (AMM if enabled) ─
        total_locked_stake = sum(op.tokens_staked for op in active_ops)
        if macro_on and amm_state is not None:
            if sell_pressure_total > 0:
                # Clamp to max 30% of pool to avoid degenerate price collapse
                clamped = min(sell_pressure_total, amm_state.token_pool * 0.30)
                amm_execute_sell(amm_state, clamped)
            token_price = amm_price(amm_state)
        else:
            token_price = token_price_model(
                month, circulating_supply, total_locked_stake,
                total_burned, monthly_rev_usd, token_price,
                sell_pressure_tokens=sell_pressure_total,
            )

        # ─ Step 20: Strike maintenance + cooldown ─
        update_strikes_and_clean_streak(
            active_ops, hours_per_op, clean_per_reset, quality_thresh_unlock,
        )
        for op in active_ops:
            if op.cooldown_until_month is not None and month >= op.cooldown_until_month:
                op.cooldown_until_month = None

        # ─ Step 21 (modified): Churn (with v4 income volatility boost) ─
        for op in active_ops:
            if op.is_banned:
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
            if personas_on:
                base_churn += income_volatility_churn_boost(op)
            # v5 Layer C: geography retention multiplier
            if geography_on and getattr(op, "region", None):
                base_churn *= region_retention_multiplier(op.region, region_params)
                # Wage-gap churn boost (Tesla/1X anchor scenario)
                hourly_earn = op.cumulative_earnings_usd / max(1.0, op.months_active * 80.0)   # ~80hr/mo proxy
                gap_boost = wage_gap_churn_boost(
                    hourly_earn, op.region, op.tier,
                    regions_params=region_params,
                    tesla_stress=tesla_stress,
                )
                if gap_boost > 1.0:
                    cumulative_wage_gap_churns += 1
                base_churn *= gap_boost
            base_churn = max(0.005, min(0.50, base_churn))

            if random.random() < base_churn:
                op.churned = True
                op.churn_month = month
                refund = op.unlocked_stake_t3 + op.unlocked_stake_t4 + op.unlocked_stake_t6
                locked = max(0.0, op.tokens_staked - refund)
                op.tokens_held += refund
                circulating_supply -= locked
                total_burned += locked
                op.tokens_staked = 0
                op.unlocked_stake_t3 = op.unlocked_stake_t4 = op.unlocked_stake_t6 = 0
                op.hardware_deposit_t3 = op.hardware_deposit_t4 = op.hardware_deposit_t6 = 0
                op.tokens_held = 0

        # ─ Step 22 (NEW): Customer satisfaction + churn/expansion ─
        churn_count_cust = 0
        expand_count_cust = 0
        if customers_on:
            for c in customers_list:
                if c.status != "active":
                    continue
                cust_demand = per_customer_demand.get(c.id, {})
                cust_demand_total = sum(cust_demand.values())
                if cust_demand_total <= 0:
                    # No demand for this customer (sim hasn't reached its tier mix yet)
                    continue

                # Quality avg = mean of producer quality_scores on cust's tiers WITH OPS
                # (weighted by demand). Tiers with no ops don't contribute (no signal).
                quality_weighted = 0.0
                quality_weight_total = 0.0
                for tier, td in cust_demand.items():
                    tops = ops_by_tier.get(tier, [])
                    if tops and td > 0:
                        tier_qavg = sum(o.quality_score for o in tops) / len(tops)
                        quality_weighted += tier_qavg * td
                        quality_weight_total += td
                quality_avg = quality_weighted / quality_weight_total if quality_weight_total > 0 else 0.7

                # Fulfillment %: only count what was REALISTICALLY DELIVERABLE.
                # If a customer demands T6 work and there are no T6 ops yet, that's
                # a platform-bootstrap issue, not a service failure. Penalize lightly
                # for unfillable tiers (0.3x weight) but mainly judge on what was supplied.
                fulfillable_demand = 0.0
                cust_fulfilled = 0.0
                for tier, td in cust_demand.items():
                    if td > 0 and ops_by_tier.get(tier):
                        fulfillable_demand += td
                        if customer_demand.get(tier, 0) > 0:
                            tier_fulfill_ratio = min(
                                1.0, tier_hours_actual.get(tier, 0.0) / customer_demand[tier]
                            )
                            cust_fulfilled += td * tier_fulfill_ratio
                if fulfillable_demand > 0:
                    fulfill_pct_raw = cust_fulfilled / fulfillable_demand
                else:
                    fulfill_pct_raw = 0.0
                unfillable_share = max(0.0, 1.0 - fulfillable_demand / cust_demand_total)
                fulfill_pct = fulfill_pct_raw * (1.0 - 0.3 * unfillable_share)

                # If no signal (no ops at ANY demanded tier), skip sat update for this month
                if quality_weight_total <= 0:
                    continue

                # Skip sat-history updates during grace period — sat would be poisoned
                # by bootstrap-era undersupply, then trigger instant churn the moment
                # grace ends. Real enterprise customers don't keep ledger of every month.
                grace_months = sat_params.get("grace_months_after_signing", 12)
                if (month - c.signed_month) < grace_months:
                    c.months_active += 1
                    continue

                update_customer_satisfaction(c, quality_avg, fulfill_pct, sat_params)

                # Apply event multiplier to baseline churn risk (recession boost)
                churn_mult = event_effects.get("customer_churn_mult", 1.0)
                # If recession is ON, force a churn-risk roll for satisfied customers too
                if churn_mult > 1.0:
                    if random.random() < (0.02 * (churn_mult - 1.0)):  # extra churn from recession
                        c.status = "churned"
                        c.churn_month = month
                        churn_count_cust += 1
                        continue

                outcome = evaluate_churn_or_expansion(c, sat_params, month)
                if outcome == "churn":
                    churn_count_cust += 1
                elif outcome == "expand":
                    expand_count_cust += 1

        # ─ Step 23 (NEW): Update era ─
        if macro_on:
            era_state = update_era(
                era_state, month, cumulative_revenue, fiat_ratio,
                growth_rev_threshold=era_params.get("growth_rev_threshold", 5_000_000),
                growth_month_threshold=era_params.get("growth_month_threshold", 12),
                maturity_rev_threshold=era_params.get("maturity_rev_threshold", 50_000_000),
                maturity_month_threshold=era_params.get("maturity_month_threshold", 36),
                maturity_fiat_threshold=era_params.get("maturity_fiat_threshold", 0.70),
            )

        # ─ Snapshot ─
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
            "referrals_this_month": referrals_this_month if personas_on else 0,
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

        # v4-specific snapshot fields
        if macro_on:
            snap["sentiment_state"] = sentiment_state.state
            snap["era"] = era_state.era
            snap["amm_token_pool"] = round(amm_state.token_pool)
            snap["amm_usd_pool"] = round(amm_state.usd_pool)
            snap["events_fired_this_month"] = event_effects.get("fired_event_types", [])
            snap["event_arrival_mult"] = round(event_effects.get("customer_arrival_mult", 1.0), 3)
            snap["event_churn_mult"] = round(event_effects.get("customer_churn_mult", 1.0), 3)

        if customers_on:
            conc = compute_concentration_metrics(customers_list)
            seg_mix = compute_segment_revenue_mix(customers_list)
            nrr = compute_nrr_blended(customers_list, month)
            active_custs = [c for c in customers_list if c.status == "active"]
            avg_sat = sum(c.sat_history[-1] for c in active_custs if c.sat_history) / max(1, len([c for c in active_custs if c.sat_history]))
            snap["customer_count_active"] = conc["active_count"]
            snap["customer_count_total"] = len(customers_list)
            snap["customer_count_churned_this_month"] = churn_count_cust
            snap["customer_expansions_this_month"] = expand_count_cust
            snap["customer_top_1_concentration_pct"] = conc["top_1_pct"]
            snap["customer_top_3_concentration_pct"] = conc["top_3_pct"]
            snap["customer_top_10_concentration_pct"] = conc["top_10_pct"]
            snap["customer_segment_mix"] = seg_mix
            snap["customer_nrr_blended"] = round(nrr, 3)
            snap["customer_avg_satisfaction"] = round(avg_sat, 3)

        if personas_on:
            persona_dist_count = persona_distribution(active_end)
            pdi = persona_diversity_index(active_end)
            snap["persona_distribution"] = persona_dist_count
            snap["persona_diversity_index"] = round(pdi, 3)
            snap["cumulative_referrals"] = cumulative_referrals

        # ── v5 snapshot fields ──
        if tier_unlock_on:
            snap["tier_unlock_state"] = dict(unlock_state_curr)
        if node_providers_on:
            snap["providers_count_active"] = sum(1 for p in providers_list if not p.is_banned)
            snap["providers_arms_active"] = total_arms_active(providers_list)
            snap["provider_avg_quality"] = round(average_node_quality(providers_list), 3)
            snap["provider_slashed_cumulative_usd"] = round(cumulative_provider_slashed_usd)
            snap["provider_audits_cumulative"] = cumulative_provider_audits
            snap["node_reports_cumulative"] = cumulative_node_reports_filed
        if geography_on:
            geo_stats = aggregate_region_stats(active_end)
            snap["region_op_counts"] = geo_stats["counts"]
            snap["region_earnings_usd"] = {k: round(v) for k, v in geo_stats["earnings_usd"].items()}
            snap["wage_gap_churns_cumulative"] = cumulative_wage_gap_churns
        if points_token_on:
            snap["token_active"] = token_state.is_token_active
            snap["transition_month"] = token_state.transition_month
            snap["points_at_cutover"] = round(cumulative_points_at_cutover)
            snap["operator_total_points"] = round(sum(getattr(op, "points_earned", 0.0) for op in active_end))
        if intel_lib_active_from is not None:
            snap["intelligence_library_revenue"] = round(intel_lib_revenue)
            snap["cumulative_op_hours"] = round(cumulative_op_hours)

        history.append(snap)

    return history, customers_list


# ─── EVALUATE V4 (9 base + 4 supplements) ─────────────────────────────────
def evaluate_v5(history: List[Dict], customers: List[Customer]) -> Dict:
    """
    Returns the v3 9-sub-score composite (for direct comparability) PLUS
    4 supplemental v4 metrics:
      top_3_concentration_pct
      nrr_blended
      sentiment_resilience  (avg_score_in_bear / avg_score_in_bull, or 1.0 if no cycle)
      persona_diversity_index
    """
    base = evaluate_base(history)

    final = history[-1] if history else {}

    # Supplemental: concentration
    top_3 = final.get("customer_top_3_concentration_pct", 0.0)

    # Supplemental: NRR
    nrr = final.get("customer_nrr_blended", 1.0)

    # Supplemental: sentiment resilience
    bull_revs = [h["monthly_revenue"] for h in history if h.get("sentiment_state") == "bull"]
    bear_revs = [h["monthly_revenue"] for h in history if h.get("sentiment_state") == "bear"]
    if bull_revs and bear_revs:
        bull_avg = sum(bull_revs) / len(bull_revs)
        bear_avg = sum(bear_revs) / len(bear_revs)
        sent_resil = bear_avg / max(1.0, bull_avg)
    else:
        sent_resil = 1.0  # no cycle observed

    # Supplemental: persona diversity
    pdi = final.get("persona_diversity_index", 0.0)

    base["top_3_concentration_pct"] = top_3
    base["nrr_blended"] = nrr
    base["sentiment_resilience"] = round(sent_resil, 3)
    base["persona_diversity_index"] = pdi

    # Pass-through key metrics for reporting
    base["customer_count_active"] = final.get("customer_count_active", 0)
    base["customer_count_total"] = final.get("customer_count_total", 0)
    base["era_final"] = final.get("era", "n/a")
    base["sentiment_final"] = final.get("sentiment_state", "n/a")
    base["amm_token_pool_final"] = final.get("amm_token_pool", 0)
    base["amm_usd_pool_final"] = final.get("amm_usd_pool", 0)
    base["cumulative_referrals"] = final.get("cumulative_referrals", 0)

    return base


# ─── MONTE CARLO ──────────────────────────────────────────────────────────
def run_monte_carlo_v5(params: Dict, n_runs: int = NUM_MONTE_CARLO_RUNS) -> Dict:
    all_results = []
    final_states = []
    for i in range(n_runs):
        history, customers = run_simulation_v5(params, seed=RANDOM_SEED + i)
        result = evaluate_v5(history, customers)
        all_results.append(result)
        final_states.append((history[-1] if history else {}, customers))

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


def print_results_v5(params: Dict, metrics: Dict):
    print()
    print("=" * 78)
    print("CrowdBrain v5 Monte Carlo Results — Tier-Unlock + Nodes + Geo + Token-Transition")
    print("=" * 78)
    print(f"  Composite Score:   {metrics.get('score_mean', 0):.4f} ± {metrics.get('score_std', 0):.4f}")
    print()
    print("  Base sub-scores (mean ± std):")
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
    print("  v4 Supplements:")
    supplements = [
        ("top_3_concentration_pct", "Top-3 customer concentration", "%", "<50%"),
        ("nrr_blended",             "NRR (blended)",                 "x",  ">1.00"),
        ("sentiment_resilience",    "Sentiment resilience",          "",   ">0.7"),
        ("persona_diversity_index", "Persona diversity",             "",   "tracking"),
    ]
    for k, label, unit, target in supplements:
        m = metrics.get(k + "_mean", metrics.get(k, 0))
        print(f"    {label:34s}  {m:.3f}{unit}  (target {target})")
    print()
    print("  Key Metrics:")
    print(f"    Cumulative Revenue:     ${metrics.get('cumulative_revenue_mean', 0):,.0f}")
    print(f"    Final Token Price:      ${metrics.get('final_price_mean', 0):.4f}")
    print(f"    T4+ Operators:          {metrics.get('t4_plus_operators_mean', 0):.0f}")
    print(f"    Active Customers:       {metrics.get('customer_count_active_mean', 0):.0f}")
    print(f"    Total Customers:        {metrics.get('customer_count_total_mean', 0):.0f}")
    print(f"    Slash Rate:             {metrics.get('slash_rate_mean', 0):.2%}")
    print()
    h = hashlib.sha256(json.dumps(params, sort_keys=True, default=str).encode()).hexdigest()[:12]
    print(f"  Param hash:  {h}")
