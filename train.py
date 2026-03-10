"""
CrowdTrain Token Economy Parameters
====================================
THIS IS THE FILE THE AGENT MODIFIES.

Everything here is fair game: token supply, emission schedules, staking mechanics,
reward structures, burn rates, lockup terms, hardware staking requirements, etc.

The agent runs this file, which imports prepare.py's simulation engine,
executes a Monte Carlo simulation, and prints the composite score.
The score is what gets optimized — higher is better.

Current best score: 0.4422 (baseline)
"""

import sys
import time
from prepare import run_monte_carlo, print_results

# ─── TOKEN SUPPLY & EMISSIONS ──────────────────────────────────────────────

PARAMS = {
    # Initial circulating supply at launch
    "initial_supply": 10_000_000,

    # Maximum supply cap (hard ceiling, emissions stop here)
    "max_supply": 100_000_000,

    # Monthly token emission (new tokens minted for rewards)
    # This gets halved every `halving_interval_months`
    "monthly_emission_rate": 500_000,

    # Halving interval in months (Helium uses 24, Bitcoin uses ~48)
    "halving_interval_months": 12,

    # Initial token price assumption (USD)
    "initial_token_price": 0.10,


    # ─── BURN MECHANICS ─────────────────────────────────────────────────

    # What percentage of fiat revenue gets converted to token burns
    # Higher = more deflationary pressure, but less cash retained
    "burn_pct_of_revenue": 0.30,


    # ─── STAKING MECHANICS ──────────────────────────────────────────────

    # Base annual percentage yield for stakers
    # Higher APY → more operators stake → more churn reduction
    # stake_probability = min(0.3, staking_apy * 0.5)
    "base_staking_apy": 0.60,   # 60% APY → 30% monthly stake probability (cap)

    # Additional APY bonus per month of lockup commitment
    "lockup_bonus_per_month": 0.005,  # +0.5% per month locked

    # Lockup period bounds (months)
    "min_lockup_months": 1,
    "max_lockup_months": 12,


    # ─── OPERATOR REWARDS ───────────────────────────────────────────────

    # Base monthly token reward for a Tier 1 operator
    "base_monthly_reward_tokens": 50,

    # Multiplier by tier — flatter curve for better Gini
    "tier_reward_multipliers": {
        1: 1.0,    # 50 tokens/month
        2: 1.2,    # 60 tokens/month
        3: 1.5,    # 75 tokens/month
        4: 2.0,    # 100 tokens/month
        5: 2.5,    # 125 tokens/month
        6: 3.0,    # 150 tokens/month
    },


    # ─── HARDWARE STAKING ───────────────────────────────────────────────

    # Minimum tokens that must be staked to unlock Tier 4+ (facility access)
    "hardware_stake_requirement": 200,


    # ─── RETENTION MECHANICS ────────────────────────────────────────────

    # How much staking reduces base churn rate (0 = no effect, 1 = eliminates churn)
    "staking_churn_reduction": 0.80,

    # How much meaningful earnings reduce churn (0 = no effect, 1 = eliminates churn)
    "earnings_churn_reduction": 0.60,

    # Soulbound NFT credential retention bonus (T3+ operators)
    "nft_retention_bonus": 0.30,
}


# ─── RUN SIMULATION ────────────────────────────────────────────────────────

if __name__ == "__main__":
    start = time.time()

    print("Running CrowdTrain token economy simulation...")
    print(f"Parameters: {len(PARAMS)} configurable values")
    print()

    # Debug: single run to see monthly prices
    from prepare import run_simulation, evaluate
    history = run_simulation(PARAMS, seed=42)
    print("Monthly prices (seed=42):")
    for h in history:
        m = h["month"]
        p = h["token_price"]
        r = h["monthly_revenue"]
        t4 = h["operators_t4_plus"]
        act = h["active_operators"]
        print(f"  Month {m:2d}: price=${p:.4f}  revenue=${r:,.0f}  T4+={t4}  active={act}")
    result = evaluate(history)
    print(f"\nSingle-run score: {result['score']}")
    print(f"Stability: {result['stability_score']}")
    print(f"Retention: {result['retention_score']} ({result['retention_pct']}%)")
    prices_last12 = [h["token_price"] for h in history[-12:]]
    mean_p = sum(prices_last12) / len(prices_last12)
    var_p = sum((p - mean_p)**2 for p in prices_last12) / len(prices_last12)
    cv = var_p**0.5 / max(0.001, mean_p)
    print(f"CV (last 12mo): {cv:.4f}")
    print()

    metrics = run_monte_carlo(PARAMS)

    elapsed = time.time() - start

    print_results(PARAMS, metrics)
    print(f"\nCompleted in {elapsed:.1f}s")

    # Output the key metric for autoresearch tracking
    print(f"\nscore: {metrics['score_mean']:.6f}")
