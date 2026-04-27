"""
Treasury — token & fiat reserve manager for CrowdTrain v3 simulation.

Tracks:
- TGE distribution (team / investor / treasury / liquidity / operator emissions)
- Linear vesting for team & investor allocations
- Fiat (USD) reserves split into operator_payout_pool + treasury_reserves
- Customer fiat in: burn share -> market-buy-and-burn tokens, remainder split
- Operator fiat out: drains operator_payout_pool, falls back to tokens if dry
"""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Treasury:
    # Token allocations (set at TGE)
    team_locked_tokens: float = 0.0
    investor_locked_tokens: float = 0.0
    treasury_tokens: float = 0.0
    initial_liquidity_tokens: float = 0.0
    operator_emission_pool_tokens: float = 0.0

    # Vesting tracking (for team & investor)
    team_total_tokens: float = 0.0
    investor_total_tokens: float = 0.0
    team_vested_tokens: float = 0.0
    investor_vested_tokens: float = 0.0
    team_vest_months: int = 48
    investor_vest_months: int = 48

    # Fiat reserves (USD)
    operator_payout_pool_usd: float = 0.0  # available to pay operators
    treasury_reserves_usd: float = 0.0     # reserved for non-operator use (node capex, audit, etc.)

    # Stats
    total_fiat_paid_to_operators: float = 0.0
    total_fiat_burned_value: float = 0.0
    total_tokens_burned_via_fiat: float = 0.0
    fiat_payout_failures: int = 0  # tried to pay full but pool insufficient
    fiat_payout_partial_count: int = 0


def initial_treasury(
    initial_supply: float,
    tge_distribution: Dict[str, float],
    team_vest_months: int = 48,
    investor_vest_months: int = 48,
) -> Treasury:
    """Allocate initial supply across TGE buckets."""
    t = Treasury()
    t.team_total_tokens = initial_supply * tge_distribution["team_pct"]
    t.team_locked_tokens = t.team_total_tokens
    t.investor_total_tokens = initial_supply * tge_distribution["investor_pct"]
    t.investor_locked_tokens = t.investor_total_tokens
    t.treasury_tokens = initial_supply * tge_distribution["treasury_pct"]
    t.initial_liquidity_tokens = initial_supply * tge_distribution["initial_liquidity_pct"]
    t.operator_emission_pool_tokens = initial_supply * tge_distribution["operator_emissions_pct"]
    t.team_vest_months = team_vest_months
    t.investor_vest_months = investor_vest_months
    return t


def vest_team_and_investors(treasury: Treasury, current_month: int) -> float:
    """
    Linear vesting. Returns tokens unlocked this month.
    Vested tokens are pessimistically assumed to be sold (added to circulating supply,
    treated as sell pressure by caller).
    """
    unlocked = 0.0

    if current_month <= treasury.team_vest_months and treasury.team_total_tokens > 0:
        per_month = treasury.team_total_tokens / treasury.team_vest_months
        per_month = min(per_month, treasury.team_locked_tokens)
        treasury.team_locked_tokens -= per_month
        treasury.team_vested_tokens += per_month
        unlocked += per_month

    if current_month <= treasury.investor_vest_months and treasury.investor_total_tokens > 0:
        per_month = treasury.investor_total_tokens / treasury.investor_vest_months
        per_month = min(per_month, treasury.investor_locked_tokens)
        treasury.investor_locked_tokens -= per_month
        treasury.investor_vested_tokens += per_month
        unlocked += per_month

    return unlocked


def process_customer_fiat(
    treasury: Treasury,
    fiat_amount_usd: float,
    burn_pct: float,
    fiat_split_to_operators: float,
    fiat_split_to_treasury: float,
    current_token_price: float,
) -> Dict[str, float]:
    """
    Process customer fiat revenue:
      1. burn_pct -> market-buy-and-burn tokens
      2. remainder split: operators / treasury (fractions sum to ~1.0)

    Returns dict with: tokens_burned, fiat_to_operators_pool, fiat_to_treasury,
                       fiat_burned_value
    """
    burn_fiat = fiat_amount_usd * burn_pct
    tokens_burned = burn_fiat / max(0.0001, current_token_price)
    treasury.total_fiat_burned_value += burn_fiat
    treasury.total_tokens_burned_via_fiat += tokens_burned

    remainder = fiat_amount_usd - burn_fiat
    to_operators = remainder * fiat_split_to_operators
    to_treasury = remainder * fiat_split_to_treasury
    treasury.operator_payout_pool_usd += to_operators
    treasury.treasury_reserves_usd += to_treasury

    return {
        "tokens_burned": tokens_burned,
        "fiat_to_operators_pool": to_operators,
        "fiat_to_treasury": to_treasury,
        "fiat_burned_value": burn_fiat,
    }


def pay_operator_fiat(treasury: Treasury, amount_usd: float) -> float:
    """
    Drain operator_payout_pool for an operator payment.
    Returns the amount actually paid (may be less than requested if pool is dry).
    """
    if amount_usd <= 0:
        return 0.0
    if treasury.operator_payout_pool_usd >= amount_usd:
        treasury.operator_payout_pool_usd -= amount_usd
        treasury.total_fiat_paid_to_operators += amount_usd
        return amount_usd

    # Partial payout
    partial = max(0.0, treasury.operator_payout_pool_usd)
    treasury.operator_payout_pool_usd = 0.0
    if partial > 0:
        treasury.total_fiat_paid_to_operators += partial
        treasury.fiat_payout_partial_count += 1
    if partial < amount_usd:
        treasury.fiat_payout_failures += 1
    return partial


def fiat_ratio_for_arr(cumulative_arr: float, ladder: List) -> float:
    """
    Linear interpolation across the (arr_threshold, fiat_ratio) ladder.
    Below first threshold -> 0.0. Above last threshold -> last ratio.
    """
    if not ladder:
        return 0.0
    sorted_ladder = sorted(ladder, key=lambda x: x[0])
    if cumulative_arr <= sorted_ladder[0][0]:
        return sorted_ladder[0][1]
    if cumulative_arr >= sorted_ladder[-1][0]:
        return sorted_ladder[-1][1]
    for i in range(len(sorted_ladder) - 1):
        a_arr, a_r = sorted_ladder[i]
        b_arr, b_r = sorted_ladder[i + 1]
        if a_arr <= cumulative_arr <= b_arr:
            t = (cumulative_arr - a_arr) / max(1.0, (b_arr - a_arr))
            return a_r + t * (b_r - a_r)
    return sorted_ladder[-1][1]
