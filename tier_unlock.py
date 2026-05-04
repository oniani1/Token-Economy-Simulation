"""
CrowdBrain v5 — Conditional tier-unlock policy
================================================
The v5 memo collapses to 6 tiers (T0-T5), with T0-T2 launching immediately and
T3-T5 unlocking conditionally "with scale". This module models that gating.

Internally the simulator preserves v4's 7-tier indexing (T0-T6) for apples-to-apples
comparability with prior runs. v5 reporting maps T1-T6 -> T1-T5 (T5+T6 collapsed
into "Live Deployment"). Unlock policy gates internal T3, T4, T6 (the high-value
hardware tiers) — that maps cleanly to v5's T3, T4, T5 in the memo.

Unlock triggers can be combined (any rule satisfied unlocks the tier):
- op_count: count of qualified ops at the previous tier
- revenue:  cumulative ARR (annualized monthly_revenue * 12)
- time:     month index >= threshold
- demand:   customer demand for the tier exists this month
- always:   always unlocked (matches v4 default)

Each gated tier (T3, T4, T6) has its own UnlockRule. If a rule's section is absent
from PARAMS, the tier defaults to always-on (preserves v4 behavior).
"""

from typing import Dict, Optional


# ─── DEFAULTS ─────────────────────────────────────────────────────────────────
DEFAULT_UNLOCK = {
    # Each gated tier: dict of trigger->threshold; tier unlocks when ANY trigger fires.
    # Empty dict = always unlocked (v4 behavior).
    3: {},
    4: {},
    6: {},   # internal T6 == memo T5 "Live Deployment"
}

# Cells the experiments_v5 sweep uses. Convenience dict for orchestrator.
PRESET_POLICIES = {
    "unlock_baseline": {
        3: {},
        4: {},
        6: {},
    },
    "unlock_op_gated": {
        3: {"op_count_at_prev_tier": 100},   # 100 qualified T2 ops -> T3 unlocks
        4: {"op_count_at_prev_tier": 50},    # 50 qualified T3 ops -> T4 unlocks
        6: {"op_count_at_prev_tier": 25},    # 25 qualified T4 ops -> T6 unlocks
    },
    "unlock_revenue_gated": {
        3: {"cumulative_revenue_usd": 250_000},
        4: {"cumulative_revenue_usd": 1_000_000},
        6: {"cumulative_revenue_usd": 5_000_000},
    },
    "unlock_time_gated": {
        3: {"month_index": 6},
        4: {"month_index": 12},
        6: {"month_index": 18},
    },
    "unlock_strict": {
        # Require BOTH conditions (use a synthetic combo trigger)
        3: {"op_count_at_prev_tier": 200, "cumulative_revenue_usd": 500_000, "_require_all": True},
        4: {"op_count_at_prev_tier": 100, "cumulative_revenue_usd": 2_000_000, "_require_all": True},
        6: {"op_count_at_prev_tier": 50,  "cumulative_revenue_usd": 10_000_000, "_require_all": True},
    },
    "unlock_demand_gated": {
        3: {"customer_demand_hours_for_tier": 1.0},   # any demand for the tier
        4: {"customer_demand_hours_for_tier": 1.0},
        6: {"customer_demand_hours_for_tier": 1.0},
    },
}


# ─── CORE ─────────────────────────────────────────────────────────────────────
def is_tier_unlocked(
    tier: int,
    rules: Dict,
    month: int,
    cumulative_revenue_usd: float,
    op_counts_by_tier: Dict[int, int],
    customer_demand_by_tier: Optional[Dict[int, float]] = None,
) -> bool:
    """
    Check if a gated tier has unlocked under the given rules.

    `op_counts_by_tier` should map tier -> count of QUALIFIED ops at that tier
    (qualified = active, has_credential, not banned). Caller decides what counts.

    Returns True if unlocked. Empty rules dict = always unlocked.
    """
    rule = rules.get(tier, {})
    if not rule:
        return True

    # Strict mode: all listed triggers must fire
    require_all = rule.get("_require_all", False)
    triggers = {k: v for k, v in rule.items() if not k.startswith("_")}
    if not triggers:
        return True

    fired = []

    # Trigger: month index
    if "month_index" in triggers:
        fired.append(month >= triggers["month_index"])

    # Trigger: cumulative revenue (USD)
    if "cumulative_revenue_usd" in triggers:
        fired.append(cumulative_revenue_usd >= triggers["cumulative_revenue_usd"])

    # Trigger: ARR (annualized monthly run rate, USD)
    if "arr_usd" in triggers:
        # caller must pre-compute arr from monthly_revenue * 12
        # if not provided we fall back to cumulative
        fired.append(cumulative_revenue_usd >= triggers["arr_usd"])  # conservative

    # Trigger: op count at previous tier
    if "op_count_at_prev_tier" in triggers:
        prev = tier - 1
        fired.append(op_counts_by_tier.get(prev, 0) >= triggers["op_count_at_prev_tier"])

    # Trigger: customer demand for this tier
    if "customer_demand_hours_for_tier" in triggers and customer_demand_by_tier is not None:
        fired.append(customer_demand_by_tier.get(tier, 0.0) >= triggers["customer_demand_hours_for_tier"])

    if not fired:
        return True

    return all(fired) if require_all else any(fired)


def compute_unlock_state(
    rules: Dict,
    month: int,
    cumulative_revenue_usd: float,
    op_counts_by_tier: Dict[int, int],
    customer_demand_by_tier: Optional[Dict[int, float]] = None,
) -> Dict[int, bool]:
    """
    Convenience wrapper: return dict of tier -> unlocked-bool for the gated tiers.
    Tiers not in `rules` default to True (unlocked).
    """
    state = {}
    for tier in (3, 4, 6):
        state[tier] = is_tier_unlocked(
            tier, rules, month, cumulative_revenue_usd,
            op_counts_by_tier, customer_demand_by_tier,
        )
    return state


def operator_can_advance_to(
    target_tier: int,
    unlock_state: Dict[int, bool],
) -> bool:
    """Wrapper for the engine's tier-progression check. Lower tiers always allowed."""
    if target_tier <= 2:
        return True
    return unlock_state.get(target_tier, True)
