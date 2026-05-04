"""
CrowdBrain v5 — Three-region operator pool
============================================
v5 memo names Georgia, Philippines, Kenya as the operator base. Each region has
distinct cost, retention, and skill-ramp characteristics. Tesla/1X anchor at $48/hr
sets the wage gap.

Cost: per-hour wage paid to operators (proxy for opportunity cost).
      Region with higher cost = ops have other options = higher churn baseline.

Retention: multiplier on baseline tier-by-tier churn.
           Lower-cost regions have STICKIER ops (fewer alternative jobs).

Skill ramp: alpha coefficient for the learning curve (skill = alpha * log(1 + hours/100)).
            Regions with stronger labor pools or robotics-adjacent talent ramp faster.

The operator class is unchanged; we tag each operator with a region at spawn.
The engine queries this module to get region-conditioned multipliers.
"""

import random
from typing import Dict, List, Optional


# ─── DEFAULTS ─────────────────────────────────────────────────────────────────
DEFAULT_REGIONS = {
    "georgia": {
        "share":               0.40,    # Founders' home base; Alpha Node located here
        "hourly_cost_usd":     8.0,     # mid-range in $5-12/hr band
        "retention_multiplier": 0.85,    # 15% churn reduction (closest cultural+linguistic to founders + tax incentive)
        "learning_alpha":      0.10,    # baseline ramp
        "max_tier_advance_speed": 1.00,  # multiplier on tier_speed
        "alt_wage_usd":         12.0,   # local opportunity cost
    },
    "philippines": {
        "share":               0.35,
        "hourly_cost_usd":     6.0,     # cheapest in band
        "retention_multiplier": 0.90,    # 10% churn reduction (BPO-experienced, sticky)
        "learning_alpha":      0.12,    # +20% faster learning (BPO + remote-work culture, English fluency)
        "max_tier_advance_speed": 1.10,
        "alt_wage_usd":         8.0,
    },
    "kenya": {
        "share":               0.25,
        "hourly_cost_usd":    10.0,     # higher in band (smaller talent pool, growing tech sector)
        "retention_multiplier": 1.10,    # 10% churn increase (more alternative work)
        "learning_alpha":      0.09,    # slightly slower (smaller robotics-adjacent talent pool today)
        "max_tier_advance_speed": 0.95,
        "alt_wage_usd":         11.0,
    },
}

# Tesla/1X wage anchor — alternative employment outside CrowdBrain
TESLA_WAGE_USD = 48.0
ONEXTECH_WAGE_USD = 40.0   # 1X estimate

# Stress preset: 30% of T3+ ops have access to Tesla/1X-tier offers
TESLA_HIRING_STRESS = {
    "fraction_of_t3plus_with_alt_offer": 0.30,
    "alt_wage_usd": TESLA_WAGE_USD,
    "wage_gap_churn_multiplier_per_dollar": 0.005,   # 0.5% churn boost per $/hr gap
}


def assign_region(rng: Optional[random.Random] = None, regions_params: Optional[Dict] = None) -> str:
    """Assign an operator to a region based on share weights."""
    rng = rng or random
    regions = regions_params or DEFAULT_REGIONS
    items = list(regions.items())
    weights = [r["share"] for _, r in items]
    return rng.choices([k for k, _ in items], weights=weights, k=1)[0]


def region_cost_per_hour(region: str, regions_params: Optional[Dict] = None) -> float:
    regions = regions_params or DEFAULT_REGIONS
    return regions.get(region, {"hourly_cost_usd": 8.0})["hourly_cost_usd"]


def region_retention_multiplier(region: str, regions_params: Optional[Dict] = None) -> float:
    regions = regions_params or DEFAULT_REGIONS
    return regions.get(region, {"retention_multiplier": 1.0})["retention_multiplier"]


def region_learning_alpha(region: str, regions_params: Optional[Dict] = None) -> float:
    regions = regions_params or DEFAULT_REGIONS
    return regions.get(region, {"learning_alpha": 0.10})["learning_alpha"]


def region_tier_speed(region: str, regions_params: Optional[Dict] = None) -> float:
    regions = regions_params or DEFAULT_REGIONS
    return regions.get(region, {"max_tier_advance_speed": 1.0})["max_tier_advance_speed"]


def region_alt_wage(region: str, regions_params: Optional[Dict] = None) -> float:
    regions = regions_params or DEFAULT_REGIONS
    return regions.get(region, {"alt_wage_usd": 10.0})["alt_wage_usd"]


def wage_gap_churn_boost(
    op_hourly_earnings_usd: float,
    op_region: str,
    op_tier: int,
    regions_params: Optional[Dict] = None,
    tesla_stress: Optional[Dict] = None,
) -> float:
    """
    Returns a multiplicative churn boost (>=1.0) based on the gap between op's
    actual hourly earnings and the BEST alternative wage available to them.

    For most ops: alt = local alt_wage (modest gap).
    For T3+ ops with Tesla/1X access (stress scenario): alt = TESLA_WAGE_USD.
    """
    regions = regions_params or DEFAULT_REGIONS
    base_alt = regions.get(op_region, {"alt_wage_usd": 10.0})["alt_wage_usd"]

    alt_wage = base_alt
    if tesla_stress and op_tier >= 3:
        if random.random() < tesla_stress.get("fraction_of_t3plus_with_alt_offer", 0.0):
            alt_wage = max(alt_wage, tesla_stress.get("alt_wage_usd", TESLA_WAGE_USD))

    gap = max(0.0, alt_wage - op_hourly_earnings_usd)
    if gap == 0:
        return 1.0

    boost_per_dollar = (tesla_stress or TESLA_HIRING_STRESS).get(
        "wage_gap_churn_multiplier_per_dollar", 0.005
    )
    return 1.0 + gap * boost_per_dollar


def regions_active_share(
    regions_params: Dict,
    geo_shock: Optional[Dict] = None,
    month: int = 0,
) -> Dict[str, float]:
    """
    Return current effective share for each region.

    geo_shock: dict like {"region": "philippines", "start_month": 6, "duration": 6, "capacity_factor": 0.30}
    During the shock, that region's share is multiplied by capacity_factor.
    Other regions absorb the displaced share proportionally.
    """
    base = {k: r["share"] for k, r in regions_params.items()}
    if not geo_shock:
        return base
    target = geo_shock.get("region")
    start = geo_shock.get("start_month", 0)
    dur = geo_shock.get("duration", 6)
    factor = geo_shock.get("capacity_factor", 0.30)

    if target not in base or month < start or month >= start + dur:
        return base

    displaced = base[target] * (1.0 - factor)
    out = {k: v for k, v in base.items()}
    out[target] = base[target] * factor
    others = [k for k in out if k != target]
    if others:
        per_other = displaced / len(others)
        for k in others:
            out[k] += per_other
    return out


def aggregate_region_stats(operators: List) -> Dict:
    """
    For reporting: count of ops + cumulative earnings per region.
    `operators` is a list of v4/v5 Operator objects (must have .region tag).
    """
    counts = {r: 0 for r in DEFAULT_REGIONS}
    earn = {r: 0.0 for r in DEFAULT_REGIONS}
    for op in operators:
        r = getattr(op, "region", None)
        if r is None:
            continue
        if r in counts:
            counts[r] += 1
            earn[r] += getattr(op, "cumulative_earnings_usd", 0.0)
    return {"counts": counts, "earnings_usd": earn}
