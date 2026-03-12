"""
CrowdTrain Token Economy Simulator — Fixed World Model (v12 Memo)
=================================================================
DO NOT MODIFY. This file defines the simulation world: operator behavior models,
market conditions, demand curves, and evaluation metrics.

The agent modifies train.py (token economy parameters) and this file evaluates
whether those parameters produce a healthy, sustainable economy.

Calibrated to CrowdTrain v12 memo:
- Solana-native DePIN for robotics operator training
- 7-tier progressive pipeline (Tier 0-6)
- Hardware staking, slashing, soulbound credentials
- Alpha Node in Tbilisi, expanding to university labs
- DeFi Land 100K community as initial recruitment pipeline

Data sources for behavioral calibration:
- Gig economy annual turnover: ~41% (Celayix 2023)
- Mobile app Day-30 retention: ~5.6% (UXCam 2024)
- DePIN operator churn: tiered by stake level (Helium network patterns)
- Tesla teleop pay: $48/hr (referenced in memo)
- CrowdTrain emerging market operators: $8-15/hr (memo cost arbitrage)
- DeFi Land retention: community active 5+ years at 100K MAU
- NEURA RoboGym: $18.5M single facility (memo competitive reference)
"""

import json
import math
import random
import hashlib
from dataclasses import dataclass
from typing import List, Dict, Optional

# ─── SIMULATION CONSTANTS (IMMUTABLE) ───────────────────────────────────────

SIMULATION_MONTHS = 24          # 2-year simulation horizon
RANDOM_SEED = 42                # Reproducibility
NUM_MONTE_CARLO_RUNS = 20       # Statistical significance
TARGET_OPERATORS_12MO = 5_000   # Pre-seed target with DeFi Land community pipeline


def monthly_onboarding_schedule(month: int) -> int:
    """
    Community-seeded S-curve onboarding. Conservative pre-seed ramp.
    DeFi Land's 100K community + Solana/DePIN communities = recruitment pipeline.
    Memo targets: 100 operators Q2, 500+ Q3, scaling with node expansion.
    ~5,100 cumulative by month 12, ~8,500 by month 24.
    """
    if month <= 12:
        schedule = [30, 50, 100, 180, 300, 500, 650, 750, 800, 700, 550, 490]
        return schedule[month - 1]
    else:
        base = 450
        factor = (1.02 * 0.95) ** (month - 12)
        return int(base * factor)


# ─── 7-TIER OPERATOR PIPELINE ────────────────────────────────────────────────
# Mirrors v12 memo's progressive pipeline:
# Sim → Labeling → Browser Teleop → In-the-Wild → Facility Teleop → Live Deploy → Partner
# Tiers 1, 3, 6 are async. Tier 2: <80ms. Tier 4: <50ms. Tier 5: <100ms.

TIERS = {
    0: {"name": "Simulation Training",  "min_months": 0,  "skill_req": 0.0},
    1: {"name": "Data Labeling",         "min_months": 1,  "skill_req": 0.10},
    2: {"name": "Browser Teleop",        "min_months": 2,  "skill_req": 0.20},
    3: {"name": "In-the-Wild Capture",   "min_months": 3,  "skill_req": 0.35},
    4: {"name": "Facility Teleop",       "min_months": 5,  "skill_req": 0.55},
    5: {"name": "Live Deployment",       "min_months": 8,  "skill_req": 0.75},
    6: {"name": "Partner Missions",      "min_months": 12, "skill_req": 0.90},
}

# Base monthly churn rates by tier (before token incentive modifiers)
# T0-T1 benefit from gamification (DeFi Land-style engagement design)
BASE_CHURN_BY_TIER = {
    0: 0.20,   # Sim-only — gamification helps but still app-like churn
    1: 0.14,   # Labeling — annotation platform benchmark + gamification
    2: 0.10,   # Browser teleop — earning tokens, some commitment
    3: 0.08,   # In-the-wild capture — gear invested, community ties
    4: 0.04,   # Facility teleop — hardware-staked, high commitment
    5: 0.025,  # Live deployment — elite, customer-facing
    6: 0.015,  # Partner missions — deep lock-in, highest earnings
}

# Skill progression: monthly probability of advancing to next tier
# Higher than generic platforms due to MuJoCo+Unity gamified training
BASE_PROGRESSION_RATE = {
    0: 0.55,   # Sim designed as fast-track (MuJoCo + Unity gamification)
    1: 0.40,   # Labeling with leaderboards/streaks/squads
    2: 0.30,   # Browser teleop
    3: 0.20,   # In-the-wild capture
    4: 0.12,   # Facility teleop — quality bar is high
    5: 0.07,   # Live deployment — elite selection
    6: 0.00,   # Top tier
}


@dataclass
class Operator:
    """Individual operator agent in the simulation."""
    id: int
    join_month: int
    tier: int = 0               # Start at Tier 0 (Simulation Training)
    skill: float = 0.0          # 0.0 to 1.0
    tokens_held: float = 0.0
    tokens_staked: float = 0.0
    hardware_deposit: float = 0.0   # VR/wearable deposit (forfeited on early churn)
    stake_lockup_months: int = 0
    months_active: int = 0
    churned: bool = False
    churn_month: Optional[int] = None
    cumulative_earnings: float = 0.0
    quality_score: float = 0.7      # Running quality EMA (0-1)
    has_credential: bool = False     # Soulbound NFT credential (T2+)


# ─── DEMAND / REVENUE MODEL ──────────────────────────────────────────────────

def monthly_fiat_revenue(month: int, num_active_t4_plus: int, total_active: int) -> float:
    """
    Revenue model from v12 memo:
    - Months 1-3: Pre-revenue (building sim MVP)
    - Months 4-6: Design partners (free data, $0 revenue)
    - Month 7+: Converting design partners to paid contracts
    - Target: $500K ARR by month 9 (~$42K/month)

    Two revenue streams:
    1. Data services (labeling, demonstrations, failure analysis) — per operator-hour
    2. Facility teleop contracts (T4+ operators, premium pricing)

    Returns monthly USD revenue.
    """
    if month <= 6:
        return 0.0  # Pre-revenue + free design partner phase

    # Customer acquisition: S-curve
    # 3 customers by month 9, 6 by month 12, 12 by month 24
    max_customers = 12
    midpoint = 12
    steepness = 0.35
    demand = max_customers / (1 + math.exp(-steepness * (month - midpoint)))

    # Supply constraint: need operator pool to service customers
    # Each customer needs ~200 operators across tiers (labeling + teleop)
    operator_capacity = total_active / 200
    actual_customers = min(demand, operator_capacity)

    if actual_customers < 0.5:
        return 0.0

    # Base contract: $15K/month (3-6x cheaper than in-house at $48/hr)
    base_contract = 15_000

    # T4+ operators unlock premium teleop contracts
    if num_active_t4_plus >= 10:
        premium = min(10_000, num_active_t4_plus * 100)
        base_contract += premium

    noise = random.gauss(1.0, 0.12)  # 12% monthly variance
    return actual_customers * base_contract * max(0.5, noise)


# ─── TOKEN PRICE MODEL ───────────────────────────────────────────────────────

def token_price_model(
    month: int,
    circulating_supply: float,
    total_burned: float,
    num_staked: float,
    monthly_revenue: float,
    prev_price: float,
) -> float:
    """
    Solana-native token price model.
    Enterprise revenue → market-buy and burn → scarcity → price appreciation.

    NOT a market prediction — a structural model for comparing parameter configs.
    """
    if circulating_supply <= 0:
        return prev_price

    liquid_supply = max(1.0, circulating_supply - num_staked)
    revenue_demand = monthly_revenue * 0.3  # Burn loop demand
    fundamental = (revenue_demand + 1000) / (liquid_supply / 1_000_000)
    price = prev_price * 0.7 + fundamental * 0.3
    noise = random.gauss(1.0, 0.08)  # 8% monthly vol
    price *= max(0.3, noise)
    return max(0.001, price)


# ─── EVALUATION METRICS ──────────────────────────────────────────────────────

def evaluate(history: List[Dict]) -> Dict[str, float]:
    """
    Composite score optimized by the autoresearch agent. Higher is better.

    Weights reflect v12 memo priorities:
    1. Operator retention (24mo)       — 0.25 (core thesis: retention moat)
    2. Token price stability           — 0.15 (matters for staking utility)
    3. Protocol revenue                — 0.25 ($500K ARR target, enterprise traction)
    4. Operator earnings fairness      — 0.10 (global cost arbitrage fairness)
    5. Qualified operator production   — 0.20 (manufacturing operators IS the product)
    6. Data quality (slash rate)       — 0.05 (staking/slashing effectiveness)
    """
    if not history:
        return {"score": 0.0}

    final = history[-1]

    # 1. Retention at 24 months — target: 55%+ of all-time operators still active
    total_ever = final.get("total_operators_ever", 1)
    active_end = final.get("active_operators", 0)
    retention_raw = active_end / max(1, total_ever)
    retention_score = min(1.0, retention_raw / 0.55)

    # 2. Token price stability (last 12 months)
    prices = [h.get("token_price", 0.01) for h in history[-12:]]
    if len(prices) > 1 and sum(prices) > 0:
        mean_p = sum(prices) / len(prices)
        var_p = sum((p - mean_p) ** 2 for p in prices) / len(prices)
        cv = (var_p ** 0.5) / max(0.001, mean_p)
        stability_score = max(0.0, 1.0 - cv)
    else:
        stability_score = 0.5

    peak_price = max(h.get("token_price", 0.01) for h in history)
    final_price = final.get("token_price", 0.01)
    if final_price < peak_price * 0.2:
        stability_score *= 0.3  # Heavy penalty for death spiral

    # 3. Protocol revenue — target: $2M cumulative by month 24
    cumulative_revenue = sum(h.get("monthly_revenue", 0) for h in history)
    revenue_score = min(1.0, cumulative_revenue / 2_000_000)

    # 4. Operator earnings fairness (Gini)
    gini = final.get("earnings_gini", 0.5)
    gini_score = max(0.0, 1.0 - (gini / 0.6))

    # 5. Qualified operator production (T4+ by month 24)
    t4_plus = final.get("operators_t4_plus", 0)
    qualified_score = min(1.0, t4_plus / 300)

    # 6. Data quality — low slash rate = staking/slashing working well
    slash_rate = final.get("slash_rate", 0.0)
    quality_score = max(0.0, 1.0 - slash_rate * 5)  # <20% slash = full score

    score = (
        retention_score * 0.25 +
        stability_score * 0.15 +
        revenue_score * 0.25 +
        gini_score * 0.10 +
        qualified_score * 0.20 +
        quality_score * 0.05
    )

    return {
        "score": round(score, 6),
        "retention_score": round(retention_score, 4),
        "stability_score": round(stability_score, 4),
        "revenue_score": round(revenue_score, 4),
        "gini_score": round(gini_score, 4),
        "qualified_score": round(qualified_score, 4),
        "quality_score": round(quality_score, 4),
        "retention_pct": round(retention_raw * 100, 1),
        "cumulative_revenue": round(cumulative_revenue),
        "final_price": round(final_price, 4),
        "peak_price": round(peak_price, 4),
        "gini": round(gini, 4),
        "t4_plus_operators": t4_plus,
        "active_operators_final": active_end,
        "total_operators_ever": total_ever,
        "slash_rate": round(slash_rate, 4),
    }


def compute_gini(values: List[float]) -> float:
    """Compute Gini coefficient. 0 = perfect equality, 1 = max inequality."""
    if not values or len(values) < 2:
        return 0.0
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    total = sum(sorted_vals)
    if total == 0:
        return 0.0
    cumulative = 0.0
    gini_sum = 0.0
    for i, v in enumerate(sorted_vals):
        cumulative += v
        gini_sum += (2 * (i + 1) - n - 1) * v
    return gini_sum / (n * total)


# ─── SIMULATION ENGINE ────────────────────────────────────────────────────────

def run_simulation(params: Dict, seed: int = RANDOM_SEED) -> List[Dict]:
    """
    Run one full 24-month simulation with the given token economy parameters.
    """
    random.seed(seed)

    operators: List[Operator] = []
    next_id = 0
    history = []

    circulating_supply = params.get("initial_supply", 10_000_000)
    total_burned = 0.0
    total_emitted = circulating_supply
    token_price = params.get("initial_token_price", 0.05)
    total_staked = 0.0

    emission_rate = params.get("monthly_emission_rate", 2_000_000)
    halving_interval = params.get("halving_interval_months", 18)
    burn_pct = params.get("burn_pct_of_revenue", 0.25)

    staking_apy = params.get("base_staking_apy", 0.12)
    lockup_bonus = params.get("lockup_bonus_per_month", 0.003)
    min_lockup = params.get("min_lockup_months", 3)
    max_lockup = params.get("max_lockup_months", 24)

    tier_multipliers = params.get("tier_reward_multipliers", {
        0: 1.0, 1: 1.5, 2: 2.0, 3: 3.0, 4: 5.0, 5: 8.0, 6: 12.0
    })
    base_reward = params.get("base_monthly_reward_tokens", 80)

    hardware_stake = params.get("hardware_stake_tokens", 5000)
    slash_pct = params.get("slash_pct", 0.05)
    quality_threshold = params.get("quality_threshold", 0.5)

    staking_churn_red = params.get("staking_churn_reduction", 0.50)
    earnings_churn_red = params.get("earnings_churn_reduction", 0.40)
    nft_bonus = params.get("nft_retention_bonus", 0.15)
    gamification_bonus = params.get("gamification_churn_reduction", 0.15)

    max_supply = params.get("max_supply", 500_000_000)

    for month in range(1, SIMULATION_MONTHS + 1):
        # ── Halving ──
        halvings = (month - 1) // halving_interval
        current_emission = emission_rate / (2 ** halvings)
        if total_emitted + current_emission > max_supply:
            current_emission = max(0, max_supply - total_emitted)
        circulating_supply += current_emission
        total_emitted += current_emission

        # ── Onboard new operators ──
        new_count = monthly_onboarding_schedule(month)
        for _ in range(new_count):
            operators.append(Operator(id=next_id, join_month=month))
            next_id += 1

        active_ops = [op for op in operators if not op.churned]
        t4_plus = [op for op in active_ops if op.tier >= 4]

        # ── Revenue ──
        monthly_rev = monthly_fiat_revenue(month, len(t4_plus), len(active_ops))

        # ── Token burns from revenue (the burn loop) ──
        burn_amount = monthly_rev * burn_pct / max(0.001, token_price)
        circulating_supply -= burn_amount
        total_burned += burn_amount

        # ── Distribute rewards + skill progression ──
        total_rewards = 0.0
        for op in active_ops:
            op.months_active += 1

            # Skill progression (gamification-accelerated via MuJoCo+Unity)
            skill_gain = 0.06 + random.gauss(0.02, 0.01)
            op.skill = min(1.0, op.skill + max(0, skill_gain))

            # Tier progression check
            if op.tier < 6:
                next_tier = op.tier + 1
                info = TIERS[next_tier]
                if (op.months_active >= info["min_months"] and
                        op.skill >= info["skill_req"]):
                    rate = BASE_PROGRESSION_RATE[op.tier]
                    if random.random() < rate:
                        # T4+ requires hardware deposit (VR/wearable stake)
                        if next_tier >= 4 and op.hardware_deposit == 0:
                            if op.tokens_held >= hardware_stake:
                                op.tokens_held -= hardware_stake
                                op.hardware_deposit = hardware_stake
                                op.tokens_staked += hardware_stake
                                op.tier = next_tier
                            # else: can't advance without deposit
                        else:
                            op.tier = next_tier

            # Soulbound credential at T2+ (on-chain verification)
            if op.tier >= 2 and not op.has_credential:
                op.has_credential = True

            # Monthly token reward
            mult = tier_multipliers.get(op.tier, 1.0)
            reward = base_reward * mult

            # Staking rewards
            if op.tokens_staked > 0:
                lb = lockup_bonus * min(op.stake_lockup_months, max_lockup)
                eff_apy = staking_apy + lb
                monthly_stake_reward = op.tokens_staked * (eff_apy / 12)
                reward += monthly_stake_reward

            op.tokens_held += reward
            op.cumulative_earnings += reward * token_price
            total_rewards += reward

        # ── Voluntary staking decisions ──
        for op in active_ops:
            if op.tokens_staked == 0 and op.tokens_held > 100:
                stake_prob = min(0.3, staking_apy * 0.5)
                if random.random() < stake_prob:
                    pct = random.uniform(0.2, 0.6)
                    amt = op.tokens_held * pct
                    op.tokens_held -= amt
                    op.tokens_staked += amt
                    op.stake_lockup_months = random.randint(min_lockup, max_lockup)

        # ── Quality check + slashing ──
        slash_count = 0
        staked_ops_count = 0
        for op in active_ops:
            if op.tokens_staked > 0:
                staked_ops_count += 1
                # Quality: higher tiers produce better data
                q = 0.65 + op.tier * 0.05 + random.gauss(0, 0.15)
                op.quality_score = op.quality_score * 0.8 + q * 0.2  # EMA
                if op.quality_score < quality_threshold:
                    slash_amt = op.tokens_staked * slash_pct
                    op.tokens_staked -= slash_amt
                    circulating_supply -= slash_amt  # Slashed tokens burned
                    total_burned += slash_amt
                    slash_count += 1

        # ── Operator sell pressure ──
        sell_pressure = 0.0
        for op in active_ops:
            if op.tokens_held > 10:
                pct = random.uniform(0.10, 0.30)
                amt = op.tokens_held * pct
                op.tokens_held -= amt
                sell_pressure += amt

        # Update staked totals
        total_staked = sum(op.tokens_staked for op in active_ops)

        # ── Token price update ──
        token_price = token_price_model(
            month=month,
            circulating_supply=circulating_supply,
            total_burned=total_burned,
            num_staked=total_staked,
            monthly_revenue=monthly_rev,
            prev_price=token_price,
        )

        # ── Churn ──
        for op in active_ops:
            base_churn = BASE_CHURN_BY_TIER.get(op.tier, 0.15)

            # Gamification reduces churn for lower tiers (DeFi Land design)
            if op.tier <= 1:
                base_churn *= (1 - gamification_bonus)

            # Staking reduces churn (skin in the game)
            if op.tokens_staked > 0:
                base_churn *= (1 - staking_churn_red)

            # Meaningful earnings reduce churn
            monthly_earn = op.cumulative_earnings / max(1, op.months_active)
            if monthly_earn > 50:
                base_churn *= (1 - earnings_churn_red)

            # Soulbound credential retention bonus (T2+)
            if op.has_credential:
                base_churn *= (1 - nft_bonus)

            # Token price crash amplifies churn
            if month > 3:
                recent = [h.get("token_price", token_price) for h in history[-3:]]
                if recent and token_price < sum(recent) / len(recent) * 0.7:
                    base_churn *= 1.5

            base_churn = max(0.005, min(0.50, base_churn))

            if random.random() < base_churn:
                op.churned = True
                op.churn_month = month
                # Hardware deposit forfeited on churn (burned)
                forfeited = op.hardware_deposit
                circulating_supply -= forfeited
                total_burned += forfeited
                op.hardware_deposit = 0
                op.tokens_staked = 0
                op.tokens_held = 0

        # ── Lockup countdown ──
        for op in [o for o in operators if not o.churned]:
            if op.stake_lockup_months > 0:
                op.stake_lockup_months -= 1

        # ── Record snapshot ──
        active_end = [op for op in operators if not op.churned]
        t4_end = [op for op in active_end if op.tier >= 4]

        earnings_list = [op.cumulative_earnings for op in active_end if op.months_active > 0]
        gini_val = compute_gini(earnings_list) if earnings_list else 0.0

        tier_dist = {}
        for t in range(7):
            tier_dist[t] = len([op for op in active_end if op.tier == t])

        snapshot = {
            "month": month,
            "active_operators": len(active_end),
            "total_operators_ever": len(operators),
            "new_operators": new_count,
            "churned_this_month": len([op for op in operators if op.churn_month == month]),
            "operators_t4_plus": len(t4_end),
            "tier_distribution": tier_dist,
            "circulating_supply": round(circulating_supply),
            "total_burned": round(total_burned),
            "total_staked": round(total_staked),
            "token_price": round(token_price, 6),
            "monthly_revenue": round(monthly_rev),
            "total_rewards_distributed": round(total_rewards),
            "earnings_gini": round(gini_val, 4),
            "sell_pressure_tokens": round(sell_pressure),
            "slash_rate": round(slash_count / max(1, staked_ops_count), 4),
        }
        history.append(snapshot)

    return history


def run_monte_carlo(params: Dict, n_runs: int = NUM_MONTE_CARLO_RUNS) -> Dict:
    """Run multiple simulations with different seeds and aggregate results."""
    all_results = []
    for i in range(n_runs):
        history = run_simulation(params, seed=RANDOM_SEED + i)
        result = evaluate(history)
        all_results.append(result)

    metrics = {}
    for key in all_results[0]:
        values = [r[key] for r in all_results]
        mean_val = sum(values) / len(values)
        var_val = sum((v - mean_val) ** 2 for v in values) / len(values)
        std_val = var_val ** 0.5
        metrics[f"{key}_mean"] = round(mean_val, 6)
        metrics[f"{key}_std"] = round(std_val, 6)

    return metrics


def print_results(params: Dict, metrics: Dict):
    """Pretty-print simulation results."""
    print("=" * 70)
    print("CROWDTRAIN TOKEN ECONOMY SIMULATION RESULTS (v12 Memo)")
    print("=" * 70)
    print()
    print(f"  COMPOSITE SCORE:  {metrics['score_mean']:.4f}  (+/-{metrics['score_std']:.4f})")
    print()
    print("  Sub-scores (mean +/- std):")
    print(f"    Retention:       {metrics['retention_score_mean']:.4f}  (+/-{metrics['retention_score_std']:.4f})")
    print(f"    Price Stability: {metrics['stability_score_mean']:.4f}  (+/-{metrics['stability_score_std']:.4f})")
    print(f"    Revenue:         {metrics['revenue_score_mean']:.4f}  (+/-{metrics['revenue_score_std']:.4f})")
    print(f"    Fairness (Gini): {metrics['gini_score_mean']:.4f}  (+/-{metrics['gini_score_std']:.4f})")
    print(f"    Qualified Ops:   {metrics['qualified_score_mean']:.4f}  (+/-{metrics['qualified_score_std']:.4f})")
    print(f"    Data Quality:    {metrics['quality_score_mean']:.4f}  (+/-{metrics['quality_score_std']:.4f})")
    print()
    print("  Key metrics:")
    print(f"    Retention %:     {metrics['retention_pct_mean']:.1f}%  (+/-{metrics['retention_pct_std']:.1f}%)")
    print(f"    Cumul Revenue:   ${metrics['cumulative_revenue_mean']:,.0f}  (+/-${metrics['cumulative_revenue_std']:,.0f})")
    print(f"    Final Price:     ${metrics['final_price_mean']:.4f}  (+/-${metrics['final_price_std']:.4f})")
    print(f"    Peak Price:      ${metrics['peak_price_mean']:.4f}  (+/-${metrics['peak_price_std']:.4f})")
    print(f"    Gini Coeff:      {metrics['gini_mean']:.4f}  (+/-{metrics['gini_std']:.4f})")
    print(f"    T4+ Operators:   {metrics['t4_plus_operators_mean']:.0f}  (+/-{metrics['t4_plus_operators_std']:.0f})")
    print(f"    Active Ops (24): {metrics['active_operators_final_mean']:.0f}  (+/-{metrics['active_operators_final_std']:.0f})")
    print(f"    Total Ops Ever:  {metrics['total_operators_ever_mean']:.0f}")
    print(f"    Slash Rate:      {metrics['slash_rate_mean']:.4f}  (+/-{metrics['slash_rate_std']:.4f})")
    print()

    params_str = json.dumps(params, sort_keys=True)
    params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
    print(f"  Params hash: {params_hash}")
    print("=" * 70)


if __name__ == "__main__":
    print("prepare.py loaded successfully (v12 Memo model).")
    print(f"Simulation: {SIMULATION_MONTHS} months, {NUM_MONTE_CARLO_RUNS} Monte Carlo runs")
    print(f"Target: {TARGET_OPERATORS_12MO:,} operators in first 12 months")
    print(f"Tiers: {len(TIERS)} (0-6)")
    print()
    print("Onboarding schedule (first 12 months):")
    total = 0
    for m in range(1, 13):
        count = monthly_onboarding_schedule(m)
        total += count
        print(f"  Month {m:2d}: {count:,} new operators  (cumulative: {total:,})")
    print()
    print("Run 'python train.py' to execute simulation with current parameters.")
