"""
CrowdTrain Token Economy Parameters
====================================
THIS IS THE FILE THE AGENT MODIFIES.

Everything here is fair game: token supply, emission schedules, staking mechanics,
reward structures, burn rates, lockup terms, hardware staking requirements, etc.

The agent runs this file, which imports prepare.py's simulation engine,
executes a Monte Carlo simulation, and prints the composite score.
The score is what gets optimized — higher is better.

Current best score: <BASELINE>
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
    "base_staking_apy": 0.15,   # 15% base APY
    
    # Additional APY bonus per month of lockup commitment
    "lockup_bonus_per_month": 0.005,  # +0.5% per month locked
    
    # Lockup period bounds (months)
    "min_lockup_months": 3,
    "max_lockup_months": 24,
    
    
    # ─── OPERATOR REWARDS ───────────────────────────────────────────────
    
    # Base monthly token reward for a Tier 1 operator
    "base_monthly_reward_tokens": 50,
    
    # Multiplier by tier (higher tiers earn more)
    "tier_reward_multipliers": {
        1: 1.0,    # 50 tokens/month
        2: 1.5,    # 75 tokens/month
        3: 2.5,    # 125 tokens/month
        4: 4.0,    # 200 tokens/month
        5: 6.0,    # 300 tokens/month
        6: 10.0,   # 500 tokens/month
    },
    
    
    # ─── HARDWARE STAKING ───────────────────────────────────────────────
    
    # Minimum tokens that must be staked to unlock Tier 4+ (facility access)
    # This is the "skin in the game" requirement
    "hardware_stake_requirement": 1000,
    
    
    # ─── RETENTION MECHANICS ────────────────────────────────────────────
    
    # How much staking reduces base churn rate (0 = no effect, 1 = eliminates churn)
    "staking_churn_reduction": 0.50,
    
    # How much meaningful earnings reduce churn (0 = no effect, 1 = eliminates churn)
    "earnings_churn_reduction": 0.30,
    
    # Soulbound NFT credential retention bonus (T3+ operators)
    "nft_retention_bonus": 0.10,
}


# ─── RUN SIMULATION ────────────────────────────────────────────────────────

if __name__ == "__main__":
    start = time.time()
    
    print("Running CrowdTrain token economy simulation...")
    print(f"Parameters: {len(PARAMS)} configurable values")
    print()
    
    metrics = run_monte_carlo(PARAMS)
    
    elapsed = time.time() - start
    
    print_results(PARAMS, metrics)
    print(f"\nCompleted in {elapsed:.1f}s")
    
    # Output the key metric for autoresearch tracking
    print(f"\nscore: {metrics['score_mean']:.6f}")
