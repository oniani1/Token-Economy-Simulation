"""
Macro — Pillar 3 of CrowdTrain v4.

Provides:
  1. SentimentHMM     — bull/bear Markov chain that modulates sell pressure,
                        customer arrivals, operator acquisition.
  2. AMM              — x · y = k constant-product pool with treasury LP.
                        Replaces v3's naive token_price_model() when enabled.
  3. EventScheduler   — fires scheduled external events (competitor / regulation /
                        recession) with configurable timing and severity.
  4. Era detector     — bootstrap → growth → maturity transitions based on
                        revenue + month + fiat_ratio thresholds.

Hooks into prepare.py at:
  - Step 0  (sentiment update)
  - Step 19 (replaces token_price_model with AMM)
  - Step 11 (fire events)
  - Step 12 (era update)
"""

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ─── SENTIMENT HMM ─────────────────────────────────────────────────────────
@dataclass
class SentimentState:
    state: str = "bull"            # bull | bear
    months_in_state: int = 0
    history: List[str] = field(default_factory=list)


def update_sentiment(
    state: SentimentState,
    month: int,
    p_bull_to_bear: float = 1.0 / 21,
    p_bear_to_bull: float = 1.0 / 9,
    rng: Optional[random.Random] = None,
) -> SentimentState:
    """
    Markov transition each month.
    Default p(bull→bear)=1/21 and p(bear→bull)=1/9 produce mean durations
    of 21 and 9 months, matching crypto-realistic 'long bull, sharp bear'.
    """
    rng = rng or random
    if state.state == "bull":
        if rng.random() < p_bull_to_bear:
            state.state = "bear"
            state.months_in_state = 0
        else:
            state.months_in_state += 1
    else:  # bear
        if rng.random() < p_bear_to_bull:
            state.state = "bull"
            state.months_in_state = 0
        else:
            state.months_in_state += 1
    state.history.append(state.state)
    return state


def sentiment_multipliers(state: SentimentState, params: Dict) -> Dict[str, float]:
    """Return effect multipliers given current sentiment state."""
    mults = params.get("multipliers", {
        "bull": {"sell": 0.6, "customer_arrival": 1.3, "op_acquisition": 1.10},
        "bear": {"sell": 1.5, "customer_arrival": 0.7, "op_acquisition": 0.85},
    })
    return mults.get(state.state, {"sell": 1.0, "customer_arrival": 1.0, "op_acquisition": 1.0})


# ─── AMM (CONSTANT PRODUCT) ────────────────────────────────────────────────
@dataclass
class AMM:
    token_pool: float = 1_000_000.0   # 1M tokens at TGE
    usd_pool: float = 1_000_000.0     # $1M USD at TGE
    k: float = 1e12                   # token_pool * usd_pool
    cumulative_buys_usd: float = 0.0
    cumulative_sells_usd: float = 0.0
    cumulative_tokens_burned: float = 0.0
    last_price: float = 1.0


def init_amm(token_pool: float = 1_000_000, usd_pool: float = 1_000_000) -> AMM:
    """Initialize AMM with given LP depth."""
    amm = AMM(token_pool=token_pool, usd_pool=usd_pool, k=token_pool * usd_pool)
    amm.last_price = usd_pool / max(1.0, token_pool)
    return amm


def amm_price(amm: AMM) -> float:
    """Mid price = usd_pool / token_pool."""
    return amm.usd_pool / max(1.0, amm.token_pool)


def amm_execute_sell(amm: AMM, tokens_in: float) -> Tuple[float, float]:
    """
    Execute a token sell: tokens_in tokens go INTO the pool, USD comes OUT.
    Returns (usd_out, new_price).
    """
    if tokens_in <= 0:
        return 0.0, amm_price(amm)
    new_token_pool = amm.token_pool + tokens_in
    new_usd_pool = amm.k / new_token_pool
    usd_out = amm.usd_pool - new_usd_pool

    amm.token_pool = new_token_pool
    amm.usd_pool = new_usd_pool
    amm.cumulative_sells_usd += usd_out
    new_p = amm_price(amm)
    amm.last_price = new_p
    return usd_out, new_p


def amm_execute_buy(amm: AMM, usd_in: float) -> Tuple[float, float]:
    """
    Execute a USD buy: usd_in USD go INTO the pool, tokens come OUT.
    Returns (tokens_out, new_price).
    """
    if usd_in <= 0:
        return 0.0, amm_price(amm)
    new_usd_pool = amm.usd_pool + usd_in
    new_token_pool = amm.k / new_usd_pool
    tokens_out = amm.token_pool - new_token_pool

    amm.token_pool = new_token_pool
    amm.usd_pool = new_usd_pool
    amm.cumulative_buys_usd += usd_in
    new_p = amm_price(amm)
    amm.last_price = new_p
    return tokens_out, new_p


def amm_buy_and_burn(amm: AMM, usd_amount: float) -> Tuple[float, float]:
    """
    Treasury buy-and-burn: USD enters AMM, tokens come out, tokens are burned
    (removed from circulating supply, tracked here).
    Returns (tokens_burned, new_price).
    """
    tokens_out, new_p = amm_execute_buy(amm, usd_amount)
    amm.cumulative_tokens_burned += tokens_out
    # Tokens are burned: they leave the AMM pool (tracked above) AND the
    # circulating supply (caller must subtract from circulating_supply too).
    return tokens_out, new_p


def amm_apply_one_shot_price_shock(amm: AMM, shock_factor: float) -> float:
    """
    Apply a one-shot price shock (e.g. SEC inquiry causes price × 0.75).
    Adjusts the pool ratio while preserving k. Approximates the effect of
    a large external sell/buy without modeling it explicitly.

    To shock price by factor f, we need:
      new_price = price * f = (usd_pool * f) / token_pool
    Achieve by: new_token = sqrt(k / (price * f)), new_usd = sqrt(k * price * f)
    Returns new price.
    """
    if shock_factor <= 0:
        return amm_price(amm)
    target_price = amm_price(amm) * shock_factor
    if target_price <= 0:
        return amm_price(amm)
    new_token_pool = math.sqrt(amm.k / target_price)
    new_usd_pool = math.sqrt(amm.k * target_price)
    amm.token_pool = new_token_pool
    amm.usd_pool = new_usd_pool
    amm.last_price = target_price
    return target_price


# ─── EVENTS ─────────────────────────────────────────────────────────────────
@dataclass
class Event:
    event_type: str          # 'competitor' | 'regulation' | 'recession' | 'key_customer_loss'
    fire_month: int
    duration_months: int = 0
    severity: float = 1.0    # interpretation depends on event_type
    fired: bool = False
    expires_at_month: Optional[int] = None


@dataclass
class EventSchedule:
    events: List[Event] = field(default_factory=list)
    active_competitor_until: Optional[int] = None
    active_recession_until: Optional[int] = None


DEFAULT_EVENTS_36MO = [
    {"event_type": "competitor", "fire_month": 18, "duration_months": 6, "severity": 0.7},
    {"event_type": "regulation", "fire_month": 24, "duration_months": 0, "severity": 0.75},
    {"event_type": "recession",  "fire_month": 30, "duration_months": 4, "severity": 1.5},
]


def init_event_schedule(events_spec: List[Dict] = None) -> EventSchedule:
    """events_spec: list of {event_type, fire_month, duration_months, severity}."""
    if events_spec is None:
        events_spec = DEFAULT_EVENTS_36MO
    schedule = EventSchedule()
    for spec in events_spec:
        schedule.events.append(Event(
            event_type=spec["event_type"],
            fire_month=spec["fire_month"],
            duration_months=spec.get("duration_months", 0),
            severity=spec.get("severity", 1.0),
        ))
    return schedule


def fire_events(
    schedule: EventSchedule,
    month: int,
    amm: Optional[AMM] = None,
) -> Dict:
    """
    Fire any events scheduled for this month.
    Returns dict of effects to apply: {
        'customer_arrival_mult': float (default 1.0),
        'customer_churn_mult':   float (default 1.0),
        'price_shocked':         bool,
        'fired_event_types':     List[str],
    }
    """
    effects = {
        "customer_arrival_mult": 1.0,
        "customer_churn_mult": 1.0,
        "price_shocked": False,
        "fired_event_types": [],
    }

    # Expire any active multi-month effects
    if schedule.active_competitor_until is not None and month > schedule.active_competitor_until:
        schedule.active_competitor_until = None
    if schedule.active_recession_until is not None and month > schedule.active_recession_until:
        schedule.active_recession_until = None

    # Fire new events scheduled for this month
    for ev in schedule.events:
        if ev.fired or ev.fire_month != month:
            continue
        ev.fired = True
        effects["fired_event_types"].append(ev.event_type)

        if ev.event_type == "competitor":
            schedule.active_competitor_until = month + ev.duration_months
        elif ev.event_type == "regulation":
            if amm is not None:
                amm_apply_one_shot_price_shock(amm, ev.severity)
                effects["price_shocked"] = True
        elif ev.event_type == "recession":
            schedule.active_recession_until = month + ev.duration_months
        elif ev.event_type == "key_customer_loss":
            # Caller will look at fired_event_types and drop the largest customer
            pass

    # Apply ongoing effects
    if schedule.active_competitor_until is not None:
        # Find competitor severity from schedule
        for ev in schedule.events:
            if ev.event_type == "competitor" and ev.fired:
                effects["customer_arrival_mult"] *= ev.severity
                break

    if schedule.active_recession_until is not None:
        for ev in schedule.events:
            if ev.event_type == "recession" and ev.fired:
                effects["customer_churn_mult"] *= ev.severity
                break

    return effects


# ─── ERA DETECTION ──────────────────────────────────────────────────────────
@dataclass
class EraState:
    era: str = "bootstrap"           # bootstrap | growth | maturity
    transition_history: List[Tuple[int, str]] = field(default_factory=list)


def update_era(
    state: EraState,
    month: int,
    cumulative_revenue: float,
    fiat_ratio: float,
    growth_rev_threshold: float = 5_000_000,
    growth_month_threshold: int = 12,
    maturity_rev_threshold: float = 50_000_000,
    maturity_month_threshold: int = 36,
    maturity_fiat_threshold: float = 0.70,
) -> EraState:
    """Era transitions are one-way (no reversion)."""
    if state.era == "bootstrap":
        if cumulative_revenue >= growth_rev_threshold or month >= growth_month_threshold:
            state.era = "growth"
            state.transition_history.append((month, "growth"))
    elif state.era == "growth":
        if (
            cumulative_revenue >= maturity_rev_threshold
            or month >= maturity_month_threshold
            or fiat_ratio >= maturity_fiat_threshold
        ):
            state.era = "maturity"
            state.transition_history.append((month, "maturity"))
    return state


def era_multipliers(state: EraState, params: Dict) -> Dict[str, float]:
    """Effect multipliers per era."""
    mults = params.get("era_multipliers", {
        "bootstrap": {"emission": 1.0, "referral": 1.2, "customer_arrival": 1.0},
        "growth":    {"emission": 1.0, "referral": 1.5, "customer_arrival": 1.5},
        "maturity":  {"emission": 0.5, "referral": 0.8, "customer_arrival": 1.2},
    })
    return mults.get(state.era, {"emission": 1.0, "referral": 1.0, "customer_arrival": 1.0})
