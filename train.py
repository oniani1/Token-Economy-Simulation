"""
CrowdTrain Token Economy Parameters (v12 Memo)
================================================
THIS IS THE FILE THE AGENT MODIFIES.

Everything here is fair game: token supply, emission schedules, staking mechanics,
reward structures, burn rates, lockup terms, hardware staking, slashing, etc.

The agent runs this file, which imports prepare.py's simulation engine,
executes a Monte Carlo simulation, and prints the composite score.

Best score (v1): 0.9494 (old prepare.py, 5K operators, 8% vol)
Best score (v2): 0.8876 (updated prepare.py, 50K operators, 50% vol)
Baseline (v2):   0.6823 (before train.py optimization)
"""

import sys
import time
from prepare import run_monte_carlo, print_results

# ─── TOKEN SUPPLY & EMISSIONS ────────────────────────────────────────────────

PARAMS = {
    # Initial circulating supply at TGE (Solana token launch)
    "initial_supply": 10_000_000,

    # Maximum supply cap (hard ceiling)
    "max_supply": 500_000_000,

    # Monthly token emission — high steady emissions smooth price volatility
    "monthly_emission_rate": 20_000_000,

    # No halving during sim horizon (100 months > 24 month sim)
    "halving_interval_months": 12,

    # Initial token price assumption (USD)
    "initial_token_price": 1.00,


    # ─── BURN MECHANICS ───────────────────────────────────────────────────
    # 35% of enterprise fiat revenue → market-buy and permanently burn tokens
    "burn_pct_of_revenue": 0.60,


    # ─── STAKING MECHANICS ────────────────────────────────────────────────
    # Near-zero APY — voluntary staking is irrelevant when earnings churn = 0.90
    "base_staking_apy": 0.01,
    "lockup_bonus_per_month": 0.000,
    "min_lockup_months": 3,
    "max_lockup_months": 24,


    # ─── OPERATOR REWARDS (7 TIERS) ──────────────────────────────────────
    # Higher base rewards — operators need buffer to cover sell pressure + hardware deposit
    "base_monthly_reward_tokens": 120,
    "tier_reward_multipliers": {
        0: 1.0,    # Simulation Training
        1: 1.0,    # Data Labeling
        2: 1.0,    # Browser Teleop
        3: 1.0,    # In-the-Wild Capture
        4: 1.0,    # Facility Teleop
        5: 1.0,    # Live Deployment
        6: 1.0,    # Partner Missions
    },


    # ─── HARDWARE STAKING ─────────────────────────────────────────────────
    # 30 tokens deposit for VR headset/wearable
    # Low barrier — operators accumulate this in 1 month even with 55% sell pressure
    "hardware_stake_tokens": 30,


    # ─── SLASHING ─────────────────────────────────────────────────────────
    "slash_pct": 0.05,
    "quality_threshold": 0.5,


    # ─── RETENTION MECHANICS ──────────────────────────────────────────────
    # High staking + earnings churn reduction = strong retention moat
    "staking_churn_reduction": 0.90,
    "earnings_churn_reduction": 0.90,

    # Soulbound NFT credential retention (T2+ operators)
    "nft_retention_bonus": 0.40,

    # DeFi Land-style gamification for T0-T1 bottom-of-funnel retention
    "gamification_churn_reduction": 0.30,
}


# ─── RUN SIMULATION ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    start = time.time()

    print("Running CrowdTrain token economy simulation (v12 Memo)...")
    print(f"Parameters: {len(PARAMS)} configurable values")
    print()

    # Debug: single run to see monthly progression
    from prepare import run_simulation, evaluate
    history = run_simulation(PARAMS, seed=42)
    print("Monthly progression (seed=42):")
    for h in history:
        m = h["month"]
        p = h["token_price"]
        r = h["monthly_revenue"]
        t4 = h["operators_t4_plus"]
        act = h["active_operators"]
        td = h["tier_distribution"]
        sr = h["slash_rate"]
        print(f"  Month {m:2d}: price=${p:.4f}  revenue=${r:,.0f}  T4+={t4}  active={act}  tiers={td}  slash={sr:.2%}")
    result = evaluate(history)
    print(f"\nSingle-run score: {result['score']}")
    print(f"  Retention: {result['retention_score']} ({result['retention_pct']}%)")
    print(f"  Stability: {result['stability_score']}")
    print(f"  Revenue:   {result['revenue_score']}")
    print(f"  Fairness:  {result['gini_score']}")
    print(f"  Qualified: {result['qualified_score']}")
    print(f"  Quality:   {result['quality_score']}")
    print()

    metrics = run_monte_carlo(PARAMS)
    elapsed = time.time() - start

    print_results(PARAMS, metrics)
    print(f"\nCompleted in {elapsed:.1f}s")
    print(f"\nscore: {metrics['score_mean']:.6f}")
