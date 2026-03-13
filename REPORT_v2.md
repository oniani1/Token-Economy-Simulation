# CrowdTrain Token Economy — Simulation Report v2

## What Changed: Fixed World Model Updates

This simulation run recalibrates `prepare.py` against 2025 crypto/DePIN and robotics industry benchmarks. The previous model used parameters from 2023 data and a 5,000-operator scale. This version targets **50,000 operators by month 12** with **50% monthly price volatility**.

### Changes to Fixed Parameters (prepare.py)

| Parameter | Old Value | New Value | Rationale |
|-----------|-----------|-----------|-----------|
| **Target operators (12mo)** | 5,000 | 50,000 | User-specified scale-up |
| **Onboarding schedule** | ~5,100 cumulative/12mo | ~51,000 cumulative/12mo | 10x to match 50K target |
| **Price volatility** | 8% monthly | 50% monthly | User-specified; realistic for low-liquidity DePIN tokens |
| **Monte Carlo runs** | 20 | 50 | Higher vol needs more samples for stable estimates |
| **T0 base churn** | 20%/month | 25%/month | Earning app Day-30 retention is 15-25% (UXCam 2024) |
| **T1 base churn** | 14%/month | 18%/month | Appen/Toloka annotator turnover benchmarks |
| **T1→T2 progression** | 40%/month | 25%/month | Real-time teleop is a major skill jump from async labeling |
| **T2→T3 progression** | 30%/month | 20%/month | Field capture requires different skillset + gear |
| **T3→T4 progression** | 20%/month | 12%/month | Hardware-stake gate; Helium node upgrade ~10-15% conversion |
| **Max customers** | 12 | 50 | Scale-up for 50K operator workforce |
| **Base contract** | $15K/month | $30K/month | Scale AI enterprise contracts $50-200K; CrowdTrain at 3-6x discount |
| **Operator/customer ratio** | 200 | 100 | Mix of light (labeling) and heavy (teleop) contracts |
| **Revenue target** | $2M cumulative | $15M cumulative | Scaled for 50K operators and higher contract values |
| **T4+ target** | 300 | 3,000 | 10x operator pool yields 10x qualified pipeline |
| **Revenue noise** | 12% | 18% | Early enterprise sales have higher month-to-month variance |
| **Sell pressure** | 10-30% of holdings | 25-55% of holdings | Emerging market operators sell aggressively (DePIN data) |
| **Earnings churn threshold** | $50/month | $150/month | $50 is below meaningful income even in Georgia ($400-600 avg salary) |

### What Was NOT Changed (validated as correct)

- 7-tier pipeline time/skill gates (align with robotics training timelines)
- T4-T6 churn rates (match hardware-staked DePIN operator retention)
- T0→T1 progression at 55% (sim is designed as fast-track via MuJoCo/Unity)
- Token price model structure (70/30 momentum/fundamental blend)
- Quality EMA (0.8/0.2 prevents noisy slashing)
- Soulbound credential gate at T2+

---

## Experiment Results

### New Baseline (after prepare.py changes)

**Score: 0.6823** — massive drop from old 0.9494 because:
- Qualified ops = 0 (operators can't accumulate 200 tokens for hardware deposit with 25-55% sell pressure)
- Stability = 0.44 (50% vol inherently limits this)

### Experiment Log

| # | Changes | Score | Stability | Fairness | Qualified | Key Insight |
|---|---------|-------|-----------|----------|-----------|-------------|
| Baseline | (prepare.py changes only) | 0.6823 | 0.438 | 0.683 | 0.000 | Hardware deposit gate blocks T4+ entirely |
| 1 | hw_stake=30, reward=200 | **0.8840** | 0.448 | 0.667 | 1.000 | Low deposit barrier unlocks T4+ production |
| 2 | reward=120 (from 200) | 0.8840 | 0.448 | 0.667 | 1.000 | Reward level doesn't affect Gini (scale-invariant) |
| 3 | emission=5M, burn=50% | 0.8857 | 0.451 | 0.681 | 1.000 | Lower emissions slightly improve stability |
| 4 | initial_price=$1, halving=12 | 0.8868 | 0.448 | 0.695 | 1.000 | Higher initial price compresses earnings disparity |
| 5 | initial_price=$100 | 0.8833 | 0.424 | 0.697 | 1.000 | Too-high initial price destabilizes |
| 6 | staking_apy=0.20, lockup=0.005 | 0.8815 | 0.404 | 0.709 | 1.000 | High APY reduces liquid supply → volatile fundamental |
| 7 | initial_supply=100M, emission=2M | 0.8839 | 0.407 | 0.729 | 1.000 | Large supply great for fairness, bad for stability |
| 8 | max_supply=50M (cap at month 8) | 0.8835 | 0.415 | 0.724 | 1.000 | Supply cap doesn't help enough |
| **9** | **emission=20M, halving=12, burn=60%** | **0.8876** | **0.460** | **0.686** | **1.000** | **Best: high emissions dampen fundamental volatility** |
| 10 | emission=40M, burn=70% | 0.8837 | 0.417 | 0.712 | 1.000 | Over-emission dilutes too much |
| 11 | emission=20M, no halving | 0.8840 | 0.448 | 0.667 | 1.000 | Halving at 12mo DOES help |
| 12 | Inverted tier multipliers (T0=1.3..T6=0.7) | 0.8824 | 0.408 | 0.712 | 1.000 | Helps fairness, hurts stability more |
| 13 | max_supply=200M | 0.8844 | 0.415 | 0.721 | 1.000 | Supply cap hurts stability |
| 14 | initial_supply=500M (no emissions) | 0.8811 | 0.374 | 0.749 | 1.000 | Best Gini ever (0.15) but worst stability |
| 15 | burn=55% (from 60%) | 0.8876 | 0.460 | 0.686 | 1.000 | Burn rate barely matters at high token prices |

### Best Configuration (Experiment 9)

```
Score: 0.8876 (+/- 0.022)

initial_supply:          10,000,000
max_supply:              500,000,000
monthly_emission_rate:   20,000,000
halving_interval_months: 12
initial_token_price:     $1.00
burn_pct_of_revenue:     60%
base_staking_apy:        1%
hardware_stake_tokens:   30
base_monthly_reward:     120 tokens (flat across all tiers)
staking_churn_reduction: 90%
earnings_churn_reduction:90%
nft_retention_bonus:     40%
gamification_churn_red:  30%
```

### Key Outcomes (50 Monte Carlo runs)

| Metric | Value |
|--------|-------|
| Retention at 24mo | 88.7% (target: 55%) |
| Cumulative revenue | $20.3M (target: $15M) |
| T4+ operators | 21,705 (target: 3,000) |
| Final token price | $1,512 (+/- $917) |
| Peak token price | $2,596 (+/- $1,079) |
| Gini coefficient | 0.189 (+/- 0.037) |
| Active ops at month 24 | 84,488 |
| Total ops ever onboarded | 95,259 |
| Slash rate | ~0% |

---

## Key Findings

### 1. Hardware Deposit is the Make-or-Break Parameter

The single most impactful change was reducing `hardware_stake_tokens` from 200 to 30. With 25-55% monthly sell pressure (realistic for emerging market operators), a 200-token deposit is nearly unreachable. This alone moved the score from **0.68 to 0.88** (+0.20). The deposit exists as a commitment mechanism, not an accumulation challenge — 30 tokens serves the same purpose without blocking pipeline flow.

### 2. Price Stability Has a Hard Ceiling at 50% Volatility

With 50% monthly noise in the price model, the theoretical maximum stability score is ~0.50 (CV = std/mean = noise_std = 0.50, stability = 1.0 - CV = 0.50). Our best achieved 0.46, very close to this ceiling. **No parameter combination can push stability above ~0.50 with this volatility level.** This represents 0.075 of the 0.15 maximum stability contribution — a structural loss of 0.075 in the composite score.

### 3. Fairness vs. Stability Trade-off

Every change that improves fairness (larger supply, inverted multipliers) hurts stability, and vice versa. The root cause:
- **Better fairness** requires stable/flat price trajectory (so all cohorts earn similar USD)
- **Better stability** requires stable fundamental (large supply, steady emissions)
- But large supply + revenue growth = rising fundamental = upward price trend = more earnings inequality

The optimal point balances these tensions at Gini ~0.19, stability ~0.46.

### 4. Emission Rate Sweet Spot

Counter-intuitively, **higher emissions improve price stability**. A large liquid supply pool dampens the fundamental price sensitivity to revenue and staking changes. 20M tokens/month with 12-month halving was optimal — enough to maintain a large supply cushion while the halving signals long-term scarcity.

### 5. Burn Rate is Irrelevant at High Token Prices

At $1,000+ token prices, burning 60% of revenue removes ~400 tokens/month from a 490M circulating supply. That's 0.00008% — negligible. The burn mechanism matters most in early months when prices are low and more tokens are removed per dollar.

### 6. Theoretical Score Ceiling

Given the 50% volatility constraint, the maximum achievable score is approximately **0.925**:
- Retention: 0.25 (maxed)
- Stability: 0.075 (capped at ~0.50 by noise)
- Revenue: 0.25 (maxed)
- Fairness: 0.10 (would require Gini = 0, unreachable)
- Qualified: 0.20 (maxed)
- Quality: 0.05 (maxed)

Our score of **0.888 achieves ~96% of the theoretical maximum**.

---

## Comparison: v1 vs v2

| Metric | v1 (old prepare.py) | v2 (updated prepare.py) |
|--------|---------------------|-------------------------|
| Best score | 0.9494 | 0.8876 |
| Operator scale | ~5,000 by 12mo | ~50,000 by 12mo |
| Price volatility | 8% monthly | 50% monthly |
| Revenue model | 12 customers, $15K each | 50 customers, $30K each |
| Churn calibration | 2023 benchmarks | 2025 DePIN/gig economy data |
| Progression rates | Aggressive | Realistic (skill jump gates) |
| Sell pressure | 10-30% | 25-55% (emerging market) |

The lower absolute score in v2 reflects **more realistic and challenging conditions**, not worse economics. The model now accounts for:
- 10x operator scale creating more complex dynamics
- Realistic emerging-market sell behavior
- Realistic skill progression bottlenecks
- Higher price volatility typical of new DePIN tokens
- Enterprise contract values benchmarked against Scale AI

---

## Recommendations for the Token Economy

1. **Keep hardware deposit minimal** ($15-50 equivalent in tokens). The commitment signal comes from time invested in training, not token accumulation.

2. **Flat reward structure works** — tiered multipliers don't improve the economy and increase inequality. Operators are compensated by career progression and credential value, not token premiums.

3. **Front-load emissions** with scheduled halving. 20M/month halving at 12 months provides liquidity while signaling long-term scarcity.

4. **The burn loop is a marketing narrative, not an economic lever** at the scale we're modeling. At high token prices, burn quantities are negligible. Focus revenue retention on operations and growth instead.

5. **Accept ~0.50 stability score** as the cost of realistic DePIN token volatility. If stability is critical, the 50% monthly vol assumption should be revisited.
