"""
CrowdTrain Token Economy Simulator — Fixed World Model
=======================================================
DO NOT MODIFY. This file defines the simulation world: operator behavior models,
market conditions, demand curves, and evaluation metrics.

The agent modifies train.py (token economy parameters) and this file evaluates
whether those parameters produce a healthy, sustainable economy.

Data sources for behavioral calibration:
- Gig economy annual turnover: ~41% (Celayix 2023 North America data)
- Mobile app Day-30 retention: ~5.6% (UXCam 2024 benchmarks)
- Pre-PMF SaaS monthly churn: ~5.7% (Focus Digital 2025 SaaS report)
- DePIN operator churn: tiered by stake level (Helium network patterns)
- Scale AI avg contract: ~$93K/year, robotics higher (Vendr/Sacra data)
- Helium token mechanics: burn-and-mint, 2yr halving, 6-36% staking APR
- Gig worker loyalty: 70% more loyal with same-day pay (Branch 2024)
"""

import json
import math
import random
import hashlib
import sys
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional

# ─── SIMULATION CONSTANTS (IMMUTABLE) ───────────────────────────────────────

SIMULATION_MONTHS = 24          # 2-year simulation horizon
RANDOM_SEED = 42                # Reproducibility
NUM_MONTE_CARLO_RUNS = 20       # Statistical significance
TARGET_OPERATORS_12MO = 20_000  # User's target: 20K operators in first 12 months

# Onboarding curve: S-curve (slow start, acceleration, plateau)
# Models realistic adoption: word-of-mouth + marketing ramp
def monthly_onboarding_schedule(month: int) -> int:
    """
    S-curve onboarding: 20,000 total by month 12, continuing growth to ~35K by month 24.
    Calibrated to crypto/DePIN adoption curves (Helium grew from 0 to ~50K hotspots
    in first 18 months with similar S-curve dynamics).
    """
    if month <= 12:
        # Logistic growth to hit 20K cumulative by month 12
        # Monthly new operators (not cumulative)
        schedule_12mo = [200, 400, 800, 1200, 1800, 2400, 2800, 2800, 2400, 2000, 1600, 1500]
        return schedule_12mo[month - 1]  # sums to 20,000
    else:
        # Months 13-24: steady growth, slightly declining as market matures
        base = 1500
        decay = 0.92 ** (month - 12)
        return int(base * decay)


# ─── OPERATOR BEHAVIOR MODEL ───────────────────────────────────────────────

# Tier definitions (fixed — mirrors CrowdTrain's 6-tier progression)
TIERS = {
    1: {"name": "Sim Academy",           "min_months": 0, "skill_req": 0.0},
    2: {"name": "In-the-Wild Capture",    "min_months": 1, "skill_req": 0.2},
    3: {"name": "Browser Teleop",         "min_months": 2, "skill_req": 0.4},
    4: {"name": "Facility Teleop",        "min_months": 4, "skill_req": 0.6},
    5: {"name": "Failure Analysis",       "min_months": 6, "skill_req": 0.75},
    6: {"name": "Partner Missions",       "min_months": 9, "skill_req": 0.9},
}

# Base monthly churn rates by tier (before token incentive modifiers)
# Calibrated from: gig economy 41% annual (~4.3% monthly avg),
# mobile app 15-20% monthly for casual, DePIN stakers 2-4% monthly
BASE_CHURN_BY_TIER = {
    1: 0.18,   # Sim-only, no commitment, high churn (mobile app-like)
    2: 0.12,   # Some effort invested (shipped devices), moderate churn
    3: 0.08,   # Browser teleop, earning tokens, more engaged
    4: 0.04,   # Hardware-staked facility operators, high commitment
    5: 0.03,   # Specialists, strong community ties
    6: 0.02,   # Elite operators, partner missions, very sticky
}

# Skill progression: monthly probability of advancing to next tier
# Conditional on meeting min_months and skill_req
BASE_PROGRESSION_RATE = {
    1: 0.25,   # 25% of T1 operators progress per month (if eligible)
    2: 0.20,
    3: 0.15,
    4: 0.10,
    5: 0.08,
    6: 0.00,   # Top tier, nowhere to go
}


@dataclass
class Operator:
    """Individual operator agent in the simulation."""
    id: int
    join_month: int
    tier: int = 1
    skill: float = 0.0          # 0.0 to 1.0
    tokens_held: float = 0.0
    tokens_staked: float = 0.0
    stake_lockup_months: int = 0
    months_active: int = 0
    churned: bool = False
    churn_month: Optional[int] = None
    cumulative_earnings: float = 0.0


# ─── DEMAND / REVENUE MODEL ────────────────────────────────────────────────

def monthly_fiat_revenue(month: int, num_active_t4_plus: int) -> float:
    """
    Fiat revenue from paying robotics customers.
    
    Calibration:
    - Scale AI avg contract ~$93K/year (~$7.75K/month), robotics higher
    - CrowdTrain early stage: 0 customers months 1-3, ramp from there
    - Revenue scales with number of qualified operators (T4+)
    - Each paying customer: $10K-$50K/month depending on scope
    
    Returns monthly USD revenue.
    """
    if month <= 3:
        return 0.0  # Pre-revenue
    
    # Customer acquisition: slow ramp
    # Month 4: 1 design partner (free/discounted)
    # Month 6: 1 paying customer
    # Month 9: 2-3 paying customers
    # Month 12: 3-5 paying customers
    # Month 18: 5-8 paying customers
    # Month 24: 8-12 paying customers
    
    # Logistic growth for customer count
    max_customers = 15
    midpoint = 14  # month where growth is fastest
    steepness = 0.35
    customer_count = max_customers / (1 + math.exp(-steepness * (month - midpoint)))
    
    # But constrained by available qualified operators
    # Each customer needs ~20-50 qualified operators (T4+)
    max_serviceable = max(0, num_active_t4_plus // 30)
    actual_customers = min(customer_count, max_serviceable)
    
    if actual_customers < 0.5:
        return 0.0
    
    # Revenue per customer: $15K-$35K/month, averaging $25K
    # (Positioned below Scale AI's enterprise tier but above commodity labeling)
    avg_revenue_per_customer = 25_000
    noise = random.gauss(1.0, 0.15)  # 15% variance
    
    return actual_customers * avg_revenue_per_customer * max(0.5, noise)


# ─── TOKEN PRICE MODEL ─────────────────────────────────────────────────────

def token_price_model(
    month: int,
    circulating_supply: float,
    total_burned: float,
    num_staked: float,
    monthly_revenue: float,
    prev_price: float,
) -> float:
    """
    Simplified token price model based on supply/demand dynamics.
    NOT a market prediction — a structural model for comparing parameter configs.
    
    Inputs that push price up:
    - Token burns (reduce circulating supply)
    - Staking (reduce liquid supply)
    - Revenue growth (fundamental value signal)
    
    Inputs that push price down:
    - Token emissions (increase supply)
    - Operator sell pressure (cashing out rewards)
    - General market volatility
    
    Returns USD price per token.
    """
    if circulating_supply <= 0:
        return prev_price
    
    # Effective liquid supply (circulating minus staked)
    liquid_supply = max(1.0, circulating_supply - num_staked)
    
    # Demand signal: revenue creates buy pressure through burn loop
    # $1 of revenue = some fraction burned into tokens
    revenue_demand = monthly_revenue * 0.3  # 30% of revenue flows to token burns
    
    # Supply pressure from liquid tokens
    supply_pressure = liquid_supply / max(1.0, circulating_supply)
    
    # Simple price: demand / liquid_supply with momentum
    fundamental = (revenue_demand + 1000) / (liquid_supply / 1_000_000)
    
    # Mean reversion + momentum
    price = prev_price * 0.7 + fundamental * 0.3
    
    # Add realistic volatility (crypto markets)
    noise = random.gauss(1.0, 0.08)  # 8% monthly vol
    price *= max(0.3, noise)
    
    # Floor: token can't go below dust
    return max(0.001, price)


# ─── EVALUATION METRICS ────────────────────────────────────────────────────

def evaluate(history: List[Dict]) -> Dict[str, float]:
    """
    Compute the composite score and sub-metrics from a simulation run.
    
    The score is what the autoresearch agent optimizes. Higher is better.
    
    Components:
    1. Operator retention (24-month) — weighted 0.30
    2. Token price stability — weighted 0.25
    3. Protocol revenue (normalized) — weighted 0.20
    4. Operator earnings fairness (Gini) — weighted 0.15
    5. Qualified operator production — weighted 0.10
    
    Each component is normalized to [0, 1].
    """
    if not history:
        return {"score": 0.0}
    
    final = history[-1]
    
    # 1. Operator retention at 24 months
    #    Target: >50% of all-time operators still active
    total_ever = final.get("total_operators_ever", 1)
    active_end = final.get("active_operators", 0)
    retention_raw = active_end / max(1, total_ever)
    retention_score = min(1.0, retention_raw / 0.6)  # 60% retention = perfect score
    
    # 2. Token price stability
    #    Measured as inverse of coefficient of variation over last 12 months
    prices = [h.get("token_price", 0.01) for h in history[-12:]]
    if len(prices) > 1 and sum(prices) > 0:
        mean_p = sum(prices) / len(prices)
        var_p = sum((p - mean_p) ** 2 for p in prices) / len(prices)
        cv = (var_p ** 0.5) / max(0.001, mean_p)
        stability_score = max(0.0, 1.0 - cv)  # CV of 0 = perfect, CV of 1+ = 0
    else:
        stability_score = 0.5
    
    # Also penalize if price collapsed (below 20% of peak)
    peak_price = max(h.get("token_price", 0.01) for h in history)
    final_price = final.get("token_price", 0.01)
    if final_price < peak_price * 0.2:
        stability_score *= 0.3  # Heavy penalty for death spiral
    
    # 3. Protocol revenue (normalized)
    #    Target: $500K+ cumulative by month 24
    cumulative_revenue = sum(h.get("monthly_revenue", 0) for h in history)
    revenue_score = min(1.0, cumulative_revenue / 3_000_000)  # $3M cumulative = perfect
    
    # 4. Operator earnings fairness (Gini coefficient)
    #    Lower Gini = more equal = better
    #    Target: Gini < 0.4
    gini = final.get("earnings_gini", 0.5)
    gini_score = max(0.0, 1.0 - (gini / 0.6))  # Gini of 0.6+ = 0 score
    
    # 5. Qualified operator production
    #    How many operators reached T4+ by month 24
    #    Target: 500+ qualified operators
    t4_plus = final.get("operators_t4_plus", 0)
    qualified_score = min(1.0, t4_plus / 500)
    
    # Composite score
    score = (
        retention_score * 0.30 +
        stability_score * 0.25 +
        revenue_score * 0.20 +
        gini_score * 0.15 +
        qualified_score * 0.10
    )
    
    return {
        "score": round(score, 6),
        "retention_score": round(retention_score, 4),
        "stability_score": round(stability_score, 4),
        "revenue_score": round(revenue_score, 4),
        "gini_score": round(gini_score, 4),
        "qualified_score": round(qualified_score, 4),
        "retention_pct": round(retention_raw * 100, 1),
        "cumulative_revenue": round(cumulative_revenue),
        "final_price": round(final_price, 4),
        "peak_price": round(peak_price, 4),
        "gini": round(gini, 4),
        "t4_plus_operators": t4_plus,
        "active_operators_final": active_end,
        "total_operators_ever": total_ever,
    }


def compute_gini(values: List[float]) -> float:
    """Compute Gini coefficient of a list of values. 0 = perfect equality, 1 = max inequality."""
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


# ─── SIMULATION ENGINE ──────────────────────────────────────────────────────

def run_simulation(params: Dict, seed: int = RANDOM_SEED) -> List[Dict]:
    """
    Run one full 24-month simulation with the given token economy parameters.
    
    Args:
        params: Token economy parameters (from train.py)
        seed: Random seed for reproducibility
    
    Returns:
        List of monthly snapshots (one dict per month)
    """
    random.seed(seed)
    
    operators: List[Operator] = []
    next_id = 0
    history = []
    
    circulating_supply = params.get("initial_supply", 10_000_000)
    total_burned = 0.0
    total_emitted = circulating_supply
    token_price = params.get("initial_token_price", 0.10)
    total_staked = 0.0
    
    emission_rate = params.get("monthly_emission_rate", 500_000)
    halving_interval = params.get("halving_interval_months", 12)
    burn_pct_of_revenue = params.get("burn_pct_of_revenue", 0.30)
    
    # Staking parameters
    staking_apy = params.get("base_staking_apy", 0.15)
    lockup_bonus_per_month = params.get("lockup_bonus_per_month", 0.005)
    min_lockup_months = params.get("min_lockup_months", 3)
    max_lockup_months = params.get("max_lockup_months", 24)
    
    # Operator reward parameters
    tier_reward_multipliers = params.get("tier_reward_multipliers", {
        1: 1.0, 2: 1.5, 3: 2.5, 4: 4.0, 5: 6.0, 6: 10.0
    })
    base_monthly_reward = params.get("base_monthly_reward_tokens", 50)
    
    # Churn reduction from token incentives
    staking_churn_reduction = params.get("staking_churn_reduction", 0.5)
    earnings_churn_reduction = params.get("earnings_churn_reduction", 0.3)
    
    # Hardware staking (T4+ unlock requirement)
    hardware_stake_requirement = params.get("hardware_stake_requirement", 1000)
    
    # Soulbound NFT credential bonus
    nft_retention_bonus = params.get("nft_retention_bonus", 0.1)
    
    # Max supply cap
    max_supply = params.get("max_supply", 100_000_000)
    
    for month in range(1, SIMULATION_MONTHS + 1):
        # ── Halving ──
        halvings = (month - 1) // halving_interval
        current_emission = emission_rate / (2 ** halvings)
        
        # Cap emissions at max supply
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
        
        # ── Count T4+ operators for revenue model ──
        t4_plus = [op for op in active_ops if op.tier >= 4]
        
        # ── Revenue ──
        monthly_rev = monthly_fiat_revenue(month, len(t4_plus))
        
        # ── Token burns from revenue ──
        burn_amount = monthly_rev * burn_pct_of_revenue / max(0.001, token_price)
        circulating_supply -= burn_amount
        total_burned += burn_amount
        
        # ── Distribute rewards ──
        total_rewards_distributed = 0.0
        for op in active_ops:
            op.months_active += 1
            
            # Skill progression (deterministic component + noise)
            skill_gain = 0.03 + random.gauss(0.01, 0.005)
            op.skill = min(1.0, op.skill + max(0, skill_gain))
            
            # Tier progression check
            if op.tier < 6:
                next_tier = op.tier + 1
                tier_info = TIERS[next_tier]
                if (op.months_active >= tier_info["min_months"] and
                    op.skill >= tier_info["skill_req"]):
                    prog_rate = BASE_PROGRESSION_RATE[op.tier]
                    if random.random() < prog_rate:
                        # T4+ requires hardware stake
                        if next_tier >= 4 and op.tokens_held < hardware_stake_requirement:
                            pass  # Can't advance without sufficient stake
                        else:
                            if next_tier >= 4:
                                stake_amount = min(op.tokens_held, hardware_stake_requirement)
                                op.tokens_held -= stake_amount
                                op.tokens_staked += stake_amount
                                op.stake_lockup_months = min_lockup_months
                            op.tier = next_tier
            
            # Monthly token reward
            multiplier = tier_reward_multipliers.get(op.tier, 1.0)
            reward = base_monthly_reward * multiplier
            
            # Staking rewards
            if op.tokens_staked > 0:
                lockup_bonus = lockup_bonus_per_month * min(op.stake_lockup_months, max_lockup_months)
                effective_apy = staking_apy + lockup_bonus
                monthly_staking_reward = op.tokens_staked * (effective_apy / 12)
                reward += monthly_staking_reward
            
            op.tokens_held += reward
            op.cumulative_earnings += reward * token_price
            total_rewards_distributed += reward
        
        # ── Staking decisions (non-T4 operators may voluntarily stake) ──
        for op in active_ops:
            if op.tokens_staked == 0 and op.tokens_held > 100:
                # Probability of staking based on APY attractiveness
                stake_probability = min(0.3, staking_apy * 0.5)
                if random.random() < stake_probability:
                    stake_pct = random.uniform(0.2, 0.6)
                    stake_amount = op.tokens_held * stake_pct
                    op.tokens_held -= stake_amount
                    op.tokens_staked += stake_amount
                    op.stake_lockup_months = random.randint(min_lockup_months, max_lockup_months)
        
        # ── Operator sell pressure ──
        sell_pressure_tokens = 0.0
        for op in active_ops:
            # Operators sell 10-30% of liquid holdings monthly to cover expenses
            if op.tokens_held > 10:
                sell_pct = random.uniform(0.10, 0.30)
                sell_amount = op.tokens_held * sell_pct
                op.tokens_held -= sell_amount
                sell_pressure_tokens += sell_amount
                # These tokens hit the market (not burned, just sold)
        
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
            
            # Reduce churn if operator is staking
            if op.tokens_staked > 0:
                base_churn *= (1 - staking_churn_reduction)
            
            # Reduce churn if earnings are meaningful
            # "Meaningful" = earnings cover at least $50/month equivalent
            monthly_earning_usd = (op.cumulative_earnings / max(1, op.months_active))
            if monthly_earning_usd > 50:
                base_churn *= (1 - earnings_churn_reduction)
            
            # NFT credential retention bonus (operators with T3+ have soulbound NFTs)
            if op.tier >= 3:
                base_churn *= (1 - nft_retention_bonus)
            
            # Token price crash amplifies churn
            if month > 3:
                recent_prices = [h.get("token_price", token_price) for h in history[-3:]]
                if recent_prices and token_price < sum(recent_prices) / len(recent_prices) * 0.7:
                    base_churn *= 1.5  # 50% more churn during price drops
            
            base_churn = max(0.005, min(0.50, base_churn))  # Clamp
            
            if random.random() < base_churn:
                op.churned = True
                op.churn_month = month
                # Unstake and sell everything on exit
                circulating_supply += op.tokens_staked  # Returns to circulation
                op.tokens_staked = 0
                op.tokens_held = 0
        
        # ── Lockup countdown ──
        for op in active_ops:
            if op.stake_lockup_months > 0:
                op.stake_lockup_months -= 1
        
        # ── Record snapshot ──
        active_ops_end = [op for op in operators if not op.churned]
        t4_plus_end = [op for op in active_ops_end if op.tier >= 4]
        
        earnings_list = [op.cumulative_earnings for op in active_ops_end if op.months_active > 0]
        gini = compute_gini(earnings_list) if earnings_list else 0.0
        
        tier_distribution = {}
        for t in range(1, 7):
            tier_distribution[t] = len([op for op in active_ops_end if op.tier == t])
        
        snapshot = {
            "month": month,
            "active_operators": len(active_ops_end),
            "total_operators_ever": len(operators),
            "new_operators": new_count,
            "churned_this_month": len([op for op in operators if op.churn_month == month]),
            "operators_t4_plus": len(t4_plus_end),
            "tier_distribution": tier_distribution,
            "circulating_supply": round(circulating_supply),
            "total_burned": round(total_burned),
            "total_staked": round(total_staked),
            "token_price": round(token_price, 6),
            "monthly_revenue": round(monthly_rev),
            "total_rewards_distributed": round(total_rewards_distributed),
            "earnings_gini": round(gini, 4),
            "sell_pressure_tokens": round(sell_pressure_tokens),
        }
        history.append(snapshot)
    
    return history


def run_monte_carlo(params: Dict, n_runs: int = NUM_MONTE_CARLO_RUNS) -> Dict:
    """
    Run multiple simulations with different seeds and aggregate results.
    Returns mean and std of each metric.
    """
    all_results = []
    for i in range(n_runs):
        history = run_simulation(params, seed=RANDOM_SEED + i)
        result = evaluate(history)
        all_results.append(result)
    
    # Aggregate
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
    print("CROWDTRAIN TOKEN ECONOMY SIMULATION RESULTS")
    print("=" * 70)
    print()
    print(f"  COMPOSITE SCORE:  {metrics['score_mean']:.4f}  (±{metrics['score_std']:.4f})")
    print()
    print("  Sub-scores (mean ± std):")
    print(f"    Retention:       {metrics['retention_score_mean']:.4f}  (±{metrics['retention_score_std']:.4f})")
    print(f"    Price Stability: {metrics['stability_score_mean']:.4f}  (±{metrics['stability_score_std']:.4f})")
    print(f"    Revenue:         {metrics['revenue_score_mean']:.4f}  (±{metrics['revenue_score_std']:.4f})")
    print(f"    Fairness (Gini): {metrics['gini_score_mean']:.4f}  (±{metrics['gini_score_std']:.4f})")
    print(f"    Qualified Ops:   {metrics['qualified_score_mean']:.4f}  (±{metrics['qualified_score_std']:.4f})")
    print()
    print("  Key metrics:")
    print(f"    Retention %:     {metrics['retention_pct_mean']:.1f}%  (±{metrics['retention_pct_std']:.1f}%)")
    print(f"    Cumul Revenue:   ${metrics['cumulative_revenue_mean']:,.0f}  (±${metrics['cumulative_revenue_std']:,.0f})")
    print(f"    Final Price:     ${metrics['final_price_mean']:.4f}  (±${metrics['final_price_std']:.4f})")
    print(f"    Peak Price:      ${metrics['peak_price_mean']:.4f}  (±${metrics['peak_price_std']:.4f})")
    print(f"    Gini Coeff:      {metrics['gini_mean']:.4f}  (±{metrics['gini_std']:.4f})")
    print(f"    T4+ Operators:   {metrics['t4_plus_operators_mean']:.0f}  (±{metrics['t4_plus_operators_std']:.0f})")
    print(f"    Active Ops (24): {metrics['active_operators_final_mean']:.0f}  (±{metrics['active_operators_final_std']:.0f})")
    print(f"    Total Ops Ever:  {metrics['total_operators_ever_mean']:.0f}")
    print()
    
    # Generate deterministic hash of params for tracking
    params_str = json.dumps(params, sort_keys=True)
    params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
    print(f"  Params hash: {params_hash}")
    print("=" * 70)


if __name__ == "__main__":
    # Quick test with default params — agent should import and call run_monte_carlo
    print("prepare.py loaded successfully.")
    print(f"Simulation: {SIMULATION_MONTHS} months, {NUM_MONTE_CARLO_RUNS} Monte Carlo runs")
    print(f"Target: {TARGET_OPERATORS_12MO:,} operators in first 12 months")
    print()
    print("Onboarding schedule (first 12 months):")
    total = 0
    for m in range(1, 13):
        count = monthly_onboarding_schedule(m)
        total += count
        print(f"  Month {m:2d}: {count:,} new operators  (cumulative: {total:,})")
    print()
    print("Run 'python train.py' to execute simulation with current parameters.")
