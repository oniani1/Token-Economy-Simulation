## Active Project
CrowdTrain Token Economy Autoresearch (v12 Memo)

## Current State
Last completed: Optimization sweep — best score 0.9494 (from baseline 0.7217)
Currently attempting: Done — reporting findings
Next action: Resume experimenting if desired

## Best Configuration (score: 0.9494)
- initial_supply: 10M, max_supply: 500M
- emission: 20M/month, halving: 100 (never during sim)
- initial_token_price: $0.05
- burn_pct: 0.35
- staking_apy: 0.01, lockup_bonus: 0.00
- base_reward: 80 tokens/month, flat multipliers (all 1.0x)
- hardware_stake: 200 tokens
- slash_pct: 0.05, quality_threshold: 0.5
- staking_churn_reduction: 0.90, earnings_churn_reduction: 0.90
- nft_retention_bonus: 0.40, gamification_churn_reduction: 0.30

## Key Decisions
- 7-tier pipeline (0-6) matching v12 memo's progressive operator pipeline
- Conservative onboarding: 5K by month 12 (pre-seed scale)
- Revenue model: free design partners months 4-6, paid contracts from month 7
- Flat rewards maximize fairness at cost of tier incentive differentiation
- Hardware stake 200 tokens is sweet spot (achievable in ~3 months)
- Stability ceiling ~0.88 is structural (revenue-driven price appreciation)
- Fairness ceiling ~0.68 is structural (tenure-based inequality)

## Blockers
- Revenue capped by customer acquisition curve (prepare.py)
- T4+ operators can't appear before month 8 (skill progression + hardware stake)
- Price stability impossible to max with growing revenue (0→$305K/month)
