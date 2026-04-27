"""
Customers — Pillar 2 of CrowdTrain v4.

Replaces v3's monolithic `monthly_customer_demand_hours()` (a single S-curve
× per-tier hours dict) with first-class Customer agents.

Each customer has:
  - industry segment (manufacturing / warehouse / healthcare / robotics_oem)
  - per-tier demand profile drawn from segment template
  - Pareto-distributed contract size
  - 6-month rolling satisfaction history (quality + fulfillment + SLA)
  - status: active | churned | expanded
  - demand_multiplier that ratchets up on expansion events (cap 3.0x)

Lifecycle:
  - 3 design partners seeded at month 0 (one per priority segment, fixed sizes)
  - Stochastic Poisson(λ_segment(t)) arrivals after TGE
  - λ_segment(t) is logistic (peaks at month ~18) modulated by sentiment + era
  - Each month: compute satisfaction, apply churn (sat<0.5 for 3mo) or expansion
    (sat>0.8 for 3mo)

Hooks into prepare.py at:
  - Step 2 (arrival)
  - Step 3 (aggregate demand)
  - Step 10 (satisfaction update + churn/expansion)
"""

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ─── DEFAULT SEGMENT TEMPLATES ─────────────────────────────────────────────
# Per-tier demand weights sum to ~1.0 (each customer's hours normalized).
# Multiplied by contract_size_usd to produce per-tier hours.
DEFAULT_SEGMENTS = {
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
}

# Hours/$ — converts contract_size_usd (per month) into total demanded hours.
# Calibrated so a $80k/mo manufacturing contract demands ~6,400 hours (assuming
# blended hourly rate ~$12.5/hr across the segment's demand profile).
DEFAULT_USD_PER_HOUR_BLENDED = 12.5

# Default hourly rates per tier (matches v3 task_model.tier_hourly_rate_usd).
# Used to convert per-tier hours back to revenue.
DEFAULT_TIER_RATES = {0: 0.0, 1: 5.0, 2: 8.0, 3: 12.0, 4: 18.0, 5: 28.0, 6: 45.0}

DEFAULT_DESIGN_PARTNERS = [
    ("manufacturing", 100_000),
    ("warehouse",     80_000),
    ("healthcare",    150_000),
]


@dataclass
class Customer:
    id: int
    segment: str
    signed_month: int
    contract_size_usd: float          # base monthly contract size, drawn at signing
    demand_multiplier: float = 1.0    # ratchets up on expansion (cap 3.0x)
    sat_history: List[float] = field(default_factory=list)   # last 6 months
    sla_history: List[int] = field(default_factory=list)     # 1=hit, 0=miss; last 6 months
    status: str = "active"            # active | churned
    churn_month: Optional[int] = None
    expansion_count: int = 0
    cumulative_revenue: float = 0.0
    months_active: int = 0
    monthly_quality_avg: List[float] = field(default_factory=list)         # last 6 months avg quality of operators serving this customer
    monthly_fulfill_pct: List[float] = field(default_factory=list)         # last 6 months hours_fulfilled / hours_demanded


# ─── SIZE DISTRIBUTION ─────────────────────────────────────────────────────
def draw_pareto_size(
    mean_usd: float,
    alpha: float = 1.5,
    min_factor: float = 0.10,
    max_factor: float = 4.0,
    rng: Optional[random.Random] = None,
) -> float:
    """
    Truncated Pareto draw.
    For α=1.5 the mean of an unbounded Pareto with x_min=1 is α/(α-1)=3.
    To get a draw with mean ≈ mean_usd, use x_min = mean_usd * (α-1)/α
    and truncate to [mean_usd*min_factor, mean_usd*max_factor].
    """
    rng = rng or random
    x_min = mean_usd * (alpha - 1) / alpha
    # Pareto sample: x_min * (1 - U)^(-1/alpha)
    u = rng.random()
    raw = x_min * (1.0 - u) ** (-1.0 / alpha)
    lo = mean_usd * min_factor
    hi = mean_usd * max_factor
    return max(lo, min(hi, raw))


# ─── ARRIVAL ───────────────────────────────────────────────────────────────
def lambda_segment(
    month: int,
    lambda_max: float,
    midpoint_month: int,
    steepness: float,
) -> float:
    """Logistic curve for per-segment monthly arrival rate."""
    return lambda_max / (1.0 + math.exp(-steepness * (month - midpoint_month)))


def spawn_design_partners(
    starting_id: int,
    design_partner_specs: List[Tuple[str, float]] = None,
) -> Tuple[List[Customer], int]:
    """Seed customers at month 0, one per priority segment with fixed contract size."""
    specs = design_partner_specs or DEFAULT_DESIGN_PARTNERS
    customers = []
    cid = starting_id
    for segment, size in specs:
        customers.append(Customer(
            id=cid,
            segment=segment,
            signed_month=0,
            contract_size_usd=size,
        ))
        cid += 1
    return customers, cid


def arrive_new_customers(
    month: int,
    next_id: int,
    segments: Dict[str, Dict],
    arrival_params: Dict,
    sentiment_arrival_mult: float = 1.0,
    era_arrival_mult: float = 1.0,
    pareto_alpha: float = 1.5,
    pareto_min_factor: float = 0.10,
    pareto_max_factor: float = 4.0,
    rng: Optional[random.Random] = None,
) -> Tuple[List[Customer], int]:
    """
    Stochastic arrivals via Poisson(λ_segment(t)) per segment.
    λ is modulated by sentiment (bull 1.3x, bear 0.7x) and era (growth 1.5x, etc).
    """
    rng = rng or random
    lambda_max = arrival_params.get("lambda_max_per_segment", 3.0)
    midpoint = arrival_params.get("lambda_curve_midpoint", 13)
    steepness = arrival_params.get("lambda_curve_steepness", 0.4)

    new_customers = []
    cid = next_id

    for seg_name, seg_def in segments.items():
        base_lambda = lambda_segment(month, lambda_max, midpoint, steepness)
        eff_lambda = base_lambda * sentiment_arrival_mult * era_arrival_mult
        # Poisson draw
        n_arrivals = _poisson_sample(eff_lambda, rng)
        for _ in range(n_arrivals):
            size = draw_pareto_size(
                seg_def["size_mean_usd"],
                alpha=pareto_alpha,
                min_factor=pareto_min_factor,
                max_factor=pareto_max_factor,
                rng=rng,
            )
            new_customers.append(Customer(
                id=cid,
                segment=seg_name,
                signed_month=month,
                contract_size_usd=size,
            ))
            cid += 1

    return new_customers, cid


def _poisson_sample(lam: float, rng: random.Random) -> int:
    """Knuth's algorithm. Adequate for small λ."""
    if lam <= 0:
        return 0
    if lam > 30:
        # Approximation for large λ (Gaussian, rounded)
        v = rng.gauss(lam, math.sqrt(lam))
        return max(0, int(round(v)))
    L = math.exp(-lam)
    k = 0
    p = 1.0
    while p > L:
        k += 1
        p *= rng.random()
    return k - 1


# ─── DEMAND AGGREGATION ────────────────────────────────────────────────────
def compute_demand_for_customer(
    customer: Customer,
    segments: Dict[str, Dict],
    tier_rates_usd: Dict[int, float] = None,
    usd_per_hour_blended: float = DEFAULT_USD_PER_HOUR_BLENDED,
) -> Dict[int, float]:
    """
    Convert a customer's contract_size_usd into per-tier hours demanded.

    Approach:
      total_hours = contract_size_usd / blended_hourly_rate
      per_tier_hours = total_hours * demand_profile[tier]

    The blended rate is an implicit average across the segment's demand profile.
    """
    if customer.status != "active":
        return {t: 0.0 for t in range(7)}

    seg = segments.get(customer.segment, {})
    profile = seg.get("demand_profile", {t: 1.0 / 7 for t in range(7)})

    effective_size = customer.contract_size_usd * customer.demand_multiplier
    total_hours = effective_size / usd_per_hour_blended

    return {t: total_hours * profile.get(t, 0.0) for t in range(7)}


def aggregate_demand_across_customers(
    customers: List[Customer],
    segments: Dict[str, Dict],
    tier_rates_usd: Dict[int, float] = None,
    usd_per_hour_blended: float = DEFAULT_USD_PER_HOUR_BLENDED,
) -> Tuple[Dict[int, float], Dict[int, Dict[int, float]]]:
    """
    Aggregate per-tier hours across all active customers.
    Returns (total_hours_by_tier, per_customer_demand {customer_id: {tier: hours}}).
    """
    total_by_tier: Dict[int, float] = {t: 0.0 for t in range(7)}
    per_customer: Dict[int, Dict[int, float]] = {}

    for c in customers:
        if c.status != "active":
            continue
        d = compute_demand_for_customer(c, segments, tier_rates_usd, usd_per_hour_blended)
        per_customer[c.id] = d
        for t, h in d.items():
            total_by_tier[t] += h

    return total_by_tier, per_customer


# ─── SATISFACTION + CHURN/EXPANSION ────────────────────────────────────────
def update_customer_satisfaction(
    customer: Customer,
    quality_avg: float,
    demand_fulfill_pct: float,
    sat_params: Dict,
) -> float:
    """
    Compute monthly satisfaction = w1·quality + w2·fulfill + w3·sla_pct
    Update the rolling 6-month sat_history and sla_history.
    Returns the satisfaction score for this month.
    """
    weights = sat_params.get("weights", {"quality": 0.40, "demand_fulfill": 0.40, "sla": 0.20})
    sla_fulfill_min = sat_params.get("sla_fulfill_min", 0.95)
    sla_quality_min = sat_params.get("sla_quality_min", 0.70)

    # SLA hit this month?
    sla_hit = 1 if (demand_fulfill_pct >= sla_fulfill_min and quality_avg >= sla_quality_min) else 0
    customer.sla_history.append(sla_hit)
    customer.sla_history = customer.sla_history[-6:]

    sla_pct = sum(customer.sla_history) / max(1, len(customer.sla_history))

    sat = (
        weights["quality"] * quality_avg
        + weights["demand_fulfill"] * demand_fulfill_pct
        + weights["sla"] * sla_pct
    )

    customer.sat_history.append(sat)
    customer.sat_history = customer.sat_history[-6:]
    customer.monthly_quality_avg.append(quality_avg)
    customer.monthly_quality_avg = customer.monthly_quality_avg[-6:]
    customer.monthly_fulfill_pct.append(demand_fulfill_pct)
    customer.monthly_fulfill_pct = customer.monthly_fulfill_pct[-6:]
    customer.months_active += 1

    return sat


def evaluate_churn_or_expansion(
    customer: Customer,
    sat_params: Dict,
    current_month: int,
    rng: Optional[random.Random] = None,
) -> str:
    """
    Returns 'churn' | 'expand' | 'hold'.
    Hybrid: satisfaction-driven thresholds (3 consecutive months below/above),
    plus a small base churn-risk applied even at neutral satisfaction.

    NEW: bootstrap grace period — customers in their first `grace_months`
    after signing don't churn from low satisfaction (the platform is still
    ramping operator supply; this matches real-world enterprise buyer patience).
    """
    rng = rng or random
    if customer.status != "active":
        return "hold"

    churn_threshold = sat_params.get("churn_threshold", 0.50)
    expand_threshold = sat_params.get("expand_threshold", 0.80)
    churn_consecutive = sat_params.get("churn_consecutive", 3)
    expand_consecutive = sat_params.get("expand_consecutive", 3)
    expand_pct = sat_params.get("expand_pct", 0.20)
    expansion_cap = sat_params.get("expansion_cap", 3.0)
    grace_months = sat_params.get("grace_months_after_signing", 6)

    months_since_signing = current_month - customer.signed_month

    # Bootstrap grace: no churn evaluation in first N months after signing
    in_grace = months_since_signing < grace_months

    # Need at least N months of history
    if len(customer.sat_history) < churn_consecutive:
        return "hold"

    if not in_grace:
        last_n_churn = customer.sat_history[-churn_consecutive:]
        if all(s < churn_threshold for s in last_n_churn):
            customer.status = "churned"
            customer.churn_month = current_month
            return "churn"

    if len(customer.sat_history) >= expand_consecutive:
        last_n_expand = customer.sat_history[-expand_consecutive:]
        if all(s > expand_threshold for s in last_n_expand):
            new_mult = customer.demand_multiplier * (1.0 + expand_pct)
            if new_mult <= expansion_cap:
                customer.demand_multiplier = new_mult
                customer.expansion_count += 1
                # Reset sat history so we don't keep re-expanding
                customer.sat_history = customer.sat_history[-1:]
                return "expand"

    return "hold"


# ─── METRICS ───────────────────────────────────────────────────────────────
def compute_concentration_metrics(customers: List[Customer]) -> Dict:
    """Top-N concentration as % of revenue. Cumulative revenue across all active customers."""
    actives = [c for c in customers if c.status == "active"]
    if not actives:
        return {
            "top_1_pct": 0.0, "top_3_pct": 0.0, "top_10_pct": 0.0,
            "active_count": 0, "total_revenue": 0.0,
        }
    revenues = sorted([c.cumulative_revenue for c in actives], reverse=True)
    total = sum(revenues)
    if total <= 0:
        return {
            "top_1_pct": 0.0, "top_3_pct": 0.0, "top_10_pct": 0.0,
            "active_count": len(actives), "total_revenue": 0.0,
        }
    top1 = sum(revenues[:1]) / total * 100
    top3 = sum(revenues[:3]) / total * 100
    top10 = sum(revenues[:10]) / total * 100
    return {
        "top_1_pct": round(top1, 1),
        "top_3_pct": round(top3, 1),
        "top_10_pct": round(top10, 1),
        "active_count": len(actives),
        "total_revenue": round(total),
    }


def compute_segment_revenue_mix(customers: List[Customer]) -> Dict[str, float]:
    """% of cumulative revenue by segment, active customers only."""
    by_seg: Dict[str, float] = {}
    actives = [c for c in customers if c.status == "active"]
    for c in actives:
        by_seg[c.segment] = by_seg.get(c.segment, 0.0) + c.cumulative_revenue
    total = sum(by_seg.values())
    if total <= 0:
        return {seg: 0.0 for seg in by_seg}
    return {seg: round(v / total * 100, 1) for seg, v in by_seg.items()}


def compute_nrr_blended(customers: List[Customer], current_month: int) -> float:
    """
    Blended NRR = (current MRR of customers who existed 12mo ago)
                / (their MRR 12mo ago)
    For 36mo sims this stabilizes after month 13. Return 1.0 (neutral) if no
    eligible cohort yet.
    """
    if current_month < 13:
        return 1.0

    cohort = [c for c in customers if c.signed_month <= (current_month - 12)]
    if not cohort:
        return 1.0

    starting_mrr = sum(c.contract_size_usd for c in cohort)
    current_mrr = sum(
        c.contract_size_usd * c.demand_multiplier for c in cohort if c.status == "active"
    )

    if starting_mrr <= 0:
        return 1.0
    return current_mrr / starting_mrr


def churn_count_this_month(customers: List[Customer], month: int) -> int:
    return sum(1 for c in customers if c.churn_month == month)


def expansion_count_this_month(customers: List[Customer]) -> int:
    """Count of customers who expanded recently (proxy for "this month": expansion_count > 0 with reset history)."""
    # The reset of sat_history after expansion makes this hard to query post-hoc.
    # Caller should track expansion events at the call site.
    return sum(c.expansion_count for c in customers if c.status == "active")
