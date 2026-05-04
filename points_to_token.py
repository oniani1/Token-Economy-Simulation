"""
CrowdBrain v5 — Points-only phase + Points-to-Token transition
================================================================
v5 memo says "Operators begin with points and transition to tokens later."
This module models that transition.

In the points phase:
- Operators earn POINTS instead of tokens (1 point = 1 future token at 1:1 conversion)
- No AMM activity (token doesn't exist yet)
- No staking, no slashing in token terms (slashing operates on points; if your bond
  is points, you can lose points)
- All revenue paid in fiat (operators paid in fiat, points are reputation/loyalty)

At cutover:
- All accumulated points convert 1:1 to tokens (per user pick 2026-05-04)
- AMM activates with TGE liquidity
- Token-denominated stakes/slashes become live
- Sell pressure begins

Triggers (in PARAMS):
- "trigger_type": "month" -> "month_index": int
- "trigger_type": "revenue" -> "cumulative_revenue_usd": int
- "trigger_type": "never"  -> points-only baseline (no transition)
"""

from dataclasses import dataclass
from typing import Dict, Optional


# ─── PRESETS ──────────────────────────────────────────────────────────────────
PRESET_POLICIES = {
    "points_only": {
        "trigger_type": "never",
    },
    "transition_m12": {
        "trigger_type": "month",
        "month_index": 12,
    },
    "transition_m18": {
        "trigger_type": "month",
        "month_index": 18,
    },
    "transition_revenue_1m": {
        "trigger_type": "revenue",
        "cumulative_revenue_usd": 1_000_000,
    },
}


@dataclass
class TokenizationState:
    """State of the points-to-token transition for a single sim run."""
    is_token_active: bool = False
    transition_month: Optional[int] = None
    points_at_cutover: float = 0.0
    tokens_minted_at_cutover: float = 0.0
    conversion_rate: float = 1.0   # 1.0 = 1:1 (per user pick 2026-05-04)


def init_state(params: Optional[Dict]) -> TokenizationState:
    """If params absent or trigger_type='always_token', start in token mode (v4 behavior)."""
    if params is None:
        return TokenizationState(is_token_active=True, transition_month=0)
    trigger = params.get("trigger_type", "always_token")
    if trigger == "always_token":
        return TokenizationState(is_token_active=True, transition_month=0)
    return TokenizationState(is_token_active=False)


def maybe_trigger_transition(
    state: TokenizationState,
    params: Optional[Dict],
    month: int,
    cumulative_revenue_usd: float,
    operators: list,
) -> Dict:
    """
    Check if the transition should fire this month. If so, mutate state and operators
    (convert points balances to token balances at conversion_rate). Returns event dict
    describing what happened (empty if no transition).
    """
    if params is None or state.is_token_active:
        return {}

    trigger = params.get("trigger_type", "never")

    fired = False
    if trigger == "month":
        fired = month >= params.get("month_index", 9999)
    elif trigger == "revenue":
        fired = cumulative_revenue_usd >= params.get("cumulative_revenue_usd", 1e18)
    # "never" -> never fires

    if not fired:
        return {}

    state.is_token_active = True
    state.transition_month = month
    state.conversion_rate = params.get("conversion_rate", 1.0)

    # Convert all operators' points to tokens
    total_points = 0.0
    for op in operators:
        pts = getattr(op, "points_earned", 0.0)
        if pts > 0:
            converted = pts * state.conversion_rate
            op.tokens_held = getattr(op, "tokens_held", 0.0) + converted
            op.points_earned = 0.0
            total_points += pts

    state.points_at_cutover = total_points
    state.tokens_minted_at_cutover = total_points * state.conversion_rate

    return {
        "event": "points_to_token_transition",
        "month": month,
        "points_converted": total_points,
        "tokens_minted": state.tokens_minted_at_cutover,
        "conversion_rate": state.conversion_rate,
    }


def credit_operator_for_work(op, amount_units: float, state: TokenizationState):
    """
    Credit an operator for work output:
    - Pre-transition: amount goes to op.points_earned
    - Post-transition: amount goes to op.tokens_held
    """
    if state.is_token_active:
        op.tokens_held = getattr(op, "tokens_held", 0.0) + amount_units
    else:
        op.points_earned = getattr(op, "points_earned", 0.0) + amount_units


def slashable_balance(op, state: TokenizationState) -> float:
    """During points phase, slashing operates on points balance."""
    if state.is_token_active:
        return getattr(op, "tokens_staked", 0.0)
    return getattr(op, "points_earned", 0.0) * 0.5   # only half of points are at stake (rest is unbonded)


def is_amm_active(state: TokenizationState) -> bool:
    """AMM only operates when tokens are active."""
    return state.is_token_active
