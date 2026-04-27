"""
Operators v4 — Pillar 1 of CrowdTrain v4.

Adds behavioral richness on top of v3's mechanical Operator dataclass:
  - Personas (4 archetypes with distinct strategy parameters)
  - Learning curve (per-operator latent skill that grows with experience hours)
  - Decision policy (rule-based stake/sell/advance/specialize, persona-weighted)
  - Referral mechanic (each active op spawns Poisson(0.05) referrals/month;
                      referee inherits parent's persona with P=0.30)

Designed to extend the existing prepare.Operator class via:
  - extra_state dict on the Operator (set by these helpers, not declared in dataclass)
  - top-level helper functions called from prepare.py at the right pipeline steps

Backward compat: when params['operators'] is absent, prepare.py uses v3 mechanics
unchanged.
"""

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ─── PERSONA DEFINITIONS ────────────────────────────────────────────────────
DEFAULT_PERSONAS = {
    "casual": {
        "share":              0.60,    # 60% of new operators
        "time_per_month":     40,      # hours
        "base_sell":          0.55,    # baseline sell rate
        "stake_aggro":        0.05,    # P(convert tokens to stake when eligible)
        "tier_speed":         1.30,    # tier_threshold multiplier (>1 = slower)
        "quality_focus":      0.80,    # learning curve effectiveness
        "validator_share":    0.0,     # fraction of time-budget to validator queue
        "front_load_stake":   0.0,     # fraction of seed allocation auto-staked
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
        "validator_share":    0.50,    # 50% of time-budget to validation queue past T4
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
        "front_load_stake":   0.30,    # auto-stake 30% of seed allocation at acquisition
    },
}


def assign_persona(rng: random.Random = None, persona_dist: Dict = None) -> str:
    """Draw a persona name based on cumulative shares."""
    rng = rng or random
    persona_dist = persona_dist or DEFAULT_PERSONAS
    r = rng.random()
    acc = 0.0
    for name, attrs in persona_dist.items():
        acc += attrs["share"]
        if r <= acc:
            return name
    # Fallback (shouldn't happen if shares sum to 1.0)
    return list(persona_dist.keys())[0]


def get_persona_attrs(persona_name: str, persona_dist: Dict = None) -> Dict:
    """Get the parameter dict for a persona."""
    persona_dist = persona_dist or DEFAULT_PERSONAS
    return persona_dist.get(persona_name, persona_dist["casual"])


def init_operator_state_v4(
    op,
    join_month: int,
    persona_name: str,
    persona_dist: Dict = None,
    referrer_id: Optional[int] = None,
):
    """
    Attach v4 behavioral state to an existing prepare.Operator instance.
    Stored as attributes (not dataclass fields) for backward compat.
    """
    persona_dist = persona_dist or DEFAULT_PERSONAS
    attrs = persona_dist.get(persona_name, persona_dist["casual"])
    op.persona = persona_name
    op.persona_time_budget = attrs["time_per_month"]
    op.persona_base_sell = attrs["base_sell"]
    op.persona_stake_aggro = attrs["stake_aggro"]
    op.persona_tier_speed = attrs["tier_speed"]
    op.persona_quality_focus = attrs["quality_focus"]
    op.persona_validator_share = attrs["validator_share"]
    op.persona_front_load_stake = attrs["front_load_stake"]
    op.referrer_id = referrer_id
    op.experience_hours = 0.0
    op.learning_skill = 0.0       # Range 0..0.30 (capped)
    op.recent_income_history = []  # rolling 3-month USD income
    op.income_volatility = 0.0
    op.referrals_made = 0
    op.last_decision_log = ""


# ─── LEARNING CURVE ─────────────────────────────────────────────────────────
def update_learning_skill(
    op,
    hours_this_month: float,
    alpha: float = 0.10,
    cap: float = 0.30,
):
    """
    skill(t) = min(cap, alpha * log(1 + experience_hours / 100))
    Doubling experience adds ~7% skill (with alpha=0.10).
    """
    op.experience_hours = getattr(op, "experience_hours", 0.0) + hours_this_month
    raw = alpha * math.log(1.0 + op.experience_hours / 100.0)
    op.learning_skill = min(cap, raw)


def quality_modifier_from_learning(op) -> float:
    """
    How much the operator's learning_skill multiplies their base quality.
    Persona's quality_focus modulates the impact:
      effective_skill = learning_skill * persona_quality_focus
      multiplier = 1 + effective_skill   (so 0..30% bonus)
    """
    skill = getattr(op, "learning_skill", 0.0)
    focus = getattr(op, "persona_quality_focus", 1.0)
    return 1.0 + skill * focus


# ─── DECISION POLICY ────────────────────────────────────────────────────────
def make_stake_decision(
    op,
    stake_needed_tokens: float,
    price_30d_momentum: float,
    rng: random.Random = None,
) -> bool:
    """
    Decision: convert tokens to stake when eligible.
    Triggered by: balance_sufficient AND momentum_positive AND persona_aggro_roll.
    Returns True if stake decision was made.
    """
    rng = rng or random
    if op.tokens_held < stake_needed_tokens:
        return False
    if price_30d_momentum <= 0 and getattr(op, "persona", "casual") != "hw_investor":
        # Only HW Investor stakes regardless of momentum (front-loading philosophy)
        return False
    aggro = getattr(op, "persona_stake_aggro", 0.05)
    if rng.random() < aggro:
        return True
    return False


def compute_sell_pct(
    op,
    sentiment_sell_mult: float,
    quality_recent: float,
    income_volatility: float,
) -> float:
    """
    sell_pct = persona.base_sell
             * sentiment_mult         (bull 0.6x, bear 1.5x)
             * (2 - quality_recent)   (high quality = less sell)
             * (1 + income_volatility)
    Clamped to [0.05, 0.85].
    """
    base = getattr(op, "persona_base_sell", 0.40)
    raw = base * sentiment_sell_mult * (2.0 - quality_recent) * (1.0 + income_volatility)
    return max(0.05, min(0.85, raw))


def update_income_volatility(op, monthly_income_usd: float) -> float:
    """
    Maintain rolling 3-month income history. Volatility = (max-min)/mean.
    If income drops >50% from prior month, return high volatility (1.0).
    """
    history = getattr(op, "recent_income_history", [])
    history.append(monthly_income_usd)
    history = history[-3:]
    op.recent_income_history = history

    if len(history) < 2 or sum(history) == 0:
        op.income_volatility = 0.0
        return 0.0

    mean = sum(history) / len(history)
    if mean <= 0.01:
        op.income_volatility = 0.0
        return 0.0

    vol = (max(history) - min(history)) / mean
    # Penalize sharp drops specifically
    if len(history) >= 2 and history[-2] > 0 and history[-1] < history[-2] * 0.5:
        vol = max(vol, 1.0)
    op.income_volatility = min(2.0, vol)
    return op.income_volatility


def income_volatility_churn_boost(op) -> float:
    """If income dropped >50% recently, add 0.10 to base churn probability."""
    history = getattr(op, "recent_income_history", [])
    if len(history) < 2:
        return 0.0
    if history[-2] > 0 and history[-1] < history[-2] * 0.5:
        return 0.10
    return 0.0


def tier_advance_threshold_multiplier(op) -> float:
    """
    Persona-specific tier advance speed.
    Pro Earner advances faster (multiplier < 1).
    Casual advances slower (multiplier > 1).
    """
    return getattr(op, "persona_tier_speed", 1.0)


def validator_queue_share(op) -> float:
    """
    Fraction of time-budget allocated to validator queue (vs production).
    Validator persona gets 0.50 past T4. Others 0.0.
    """
    if getattr(op, "tier", 0) < 4:
        return 0.0
    return getattr(op, "persona_validator_share", 0.0)


def hw_investor_unlock_rate(op, base_rate: float = 0.01) -> float:
    """
    HW Investor gets 1.5%/h unlock rate (vs 1%/h baseline) when quality > 0.75.
    """
    if getattr(op, "persona", "casual") != "hw_investor":
        return base_rate
    if getattr(op, "quality_score", 0.7) > 0.75:
        return base_rate * 1.5
    return base_rate


# ─── REFERRAL MECHANIC ──────────────────────────────────────────────────────
def referral_count_this_month(
    active_ops: List,
    base_rate: float = 0.05,
    era_referral_mult: float = 1.0,
    rng: random.Random = None,
) -> int:
    """
    Each active op spawns Poisson(base_rate * era_mult) referrals.
    Returns total referrals this month.
    """
    rng = rng or random
    if not active_ops:
        return 0
    eff_rate = base_rate * era_referral_mult
    if eff_rate <= 0:
        return 0

    total = 0
    # Vectorized Poisson approximation: total ~ Poisson(N * lambda).
    # For N up to 100K, mean = 5000 * eff_rate, ~Gaussian approx is fine.
    n_active = len(active_ops)
    mean_total = n_active * eff_rate
    if mean_total > 30:
        v = rng.gauss(mean_total, math.sqrt(mean_total))
        return max(0, int(round(v)))

    # Per-operator draw for small populations
    for _ in active_ops:
        if rng.random() < eff_rate:
            total += 1
    return total


def assign_referee_persona(
    parent_op,
    inheritance_prob: float = 0.30,
    rng: random.Random = None,
    persona_dist: Dict = None,
) -> str:
    """
    Referee inherits parent's persona with probability `inheritance_prob`,
    else drawn from default mix.
    """
    rng = rng or random
    persona_dist = persona_dist or DEFAULT_PERSONAS
    if rng.random() < inheritance_prob:
        return getattr(parent_op, "persona", "casual")
    return assign_persona(rng=rng, persona_dist=persona_dist)


# ─── METRICS ────────────────────────────────────────────────────────────────
def persona_distribution(active_ops: List) -> Dict[str, int]:
    """Count of active operators by persona."""
    counts = {name: 0 for name in DEFAULT_PERSONAS.keys()}
    for op in active_ops:
        p = getattr(op, "persona", "casual")
        counts[p] = counts.get(p, 0) + 1
    return counts


def persona_diversity_index(active_ops: List) -> float:
    """
    Shannon entropy of persona distribution, normalized to [0, 1].
    Max entropy = log(N_personas). Higher = more diverse.
    """
    counts = persona_distribution(active_ops)
    total = sum(counts.values())
    if total <= 0:
        return 0.0
    entropy = 0.0
    for n in counts.values():
        if n > 0:
            p = n / total
            entropy -= p * math.log(p)
    max_entropy = math.log(len(counts)) if len(counts) > 1 else 1.0
    return entropy / max_entropy if max_entropy > 0 else 0.0


def avg_persona_metric(active_ops: List, metric_attr: str) -> Dict[str, float]:
    """Average value of an attr per persona."""
    by_persona: Dict[str, List[float]] = {name: [] for name in DEFAULT_PERSONAS.keys()}
    for op in active_ops:
        p = getattr(op, "persona", "casual")
        v = getattr(op, metric_attr, None)
        if v is not None and isinstance(v, (int, float)):
            by_persona.setdefault(p, []).append(float(v))
    return {p: (sum(vs) / len(vs) if vs else 0.0) for p, vs in by_persona.items()}
