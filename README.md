# Token Economy Simulation

A Monte Carlo simulation that models a token economy for [CrowdTrain](https://crowdtrain.io) — a decentralized robotics operator training platform on Solana. The goal is to find token parameters (emission rates, staking, burns, rewards) that keep the economy healthy over 24 months with 50,000+ operators.

Built using the [autoresearch](https://github.com/karpathy/autoresearch) pattern — an AI agent iterates on parameters while a fixed simulation engine scores each configuration.

## How It Works

The simulation models a full token economy with real behavioral data:

- **50,000 operators** onboarding over 12 months (S-curve adoption)
- **7-tier progression pipeline** — from Sim Training all the way to Partner Missions
- **Churn rates** calibrated from gig economy data (41% annual turnover, Celayix 2023)
- **Token mechanics** — burn-and-mint loops, halving schedules, staking, hardware deposits
- **Revenue model** — enterprise robotics data customers scaling with qualified operator count
- **Token price** — structural supply/demand model (not a market prediction)

Each run simulates 24 months of operator behavior: onboarding, skill progression, token earning/selling, staking decisions, churn. Then it scores the result across 6 dimensions.

### The Score

Every configuration gets a composite score (0-1, higher = better):

| Weight | Metric | What It Measures |
|--------|--------|------------------|
| 25% | Operator retention | Are operators sticking around? (target: >55% at month 24) |
| 25% | Protocol revenue | Is the platform making money? (target: $15M cumulative) |
| 20% | Qualified operators | Are enough operators reaching T4+? (target: 3,000) |
| 15% | Price stability | Is the token price not going crazy? (low coefficient of variation) |
| 10% | Earnings fairness | Is income distributed fairly? (Gini < 0.4) |
| 5% | Data quality | Is the slashing mechanism working? (slash rate < 20%) |

### The Autoresearch Loop

The whole point is that you don't manually guess parameters. An AI agent (Claude, Codex, etc.) reads `program.md`, understands the economics, forms hypotheses, tweaks parameters in `train.py`, runs the sim, and keeps what works.

```
           ┌─────────────┐
           │  program.md  │  ← human writes research strategy
           └──────┬───────┘
                  │
           ┌──────▼───────┐
           │   train.py   │  ← agent modifies parameters
           └──────┬───────┘
                  │
           ┌──────▼───────┐
           │  prepare.py  │  ← fixed simulation engine (DO NOT TOUCH)
           └──────┬───────┘
                  │
           ┌──────▼───────┐
           │    Score      │  ← 50 Monte Carlo runs → composite score
           └──────┬───────┘
                  │
              keep / discard
```

## Quick Start

```bash
git clone https://github.com/oniani1/Token-Economy-Simulation.git
cd Token-Economy-Simulation
python train.py
```

No dependencies needed — just Python 3.7+. Everything is pure Python stdlib.

### Output

You'll see monthly progression for 24 months, then aggregated Monte Carlo results:

```
Month  1: price=$1.00  revenue=$0       T4+=0      active=300
Month  2: price=$0.98  revenue=$0       T4+=0      active=798
...
Month 24: price=$1512  revenue=$305K    T4+=21705  active=84488

COMPOSITE SCORE: 0.8876 (+/-0.022)
```

### Run Autoresearch

Point any AI coding tool at the repo and tell it:

```
Read program.md and start experimenting
```

The agent will create a branch, run experiments, and commit improvements.

## Project Structure

```
prepare.py     Fixed simulation engine. Operator behavior, demand curves,
               token price model, Monte Carlo engine. DO NOT MODIFY.

train.py       Token economy parameters. This is what gets optimized.
               Contains the PARAMS dict with 15+ configurable values.

program.md     Instructions for the AI agent. Research strategy,
               experiment loop, economic insights. Human edits this.

REPORT_v2.md   Detailed findings from the latest optimization run.
               15 experiments, best score 0.8876 (96% of theoretical max).
```

## Results

Best configuration scores **0.8876** out of 1.0 across 50 Monte Carlo runs. That's about 96% of the theoretical maximum (capped by 50% monthly price volatility).

| Metric | Value |
|--------|-------|
| Retention at 24mo | 88.7% |
| Cumulative revenue | $20.3M |
| T4+ operators | 21,705 |
| Final token price | $1,512 (+/- $917) |
| Gini coefficient | 0.189 |
| Active operators | 84,488 |

### Key Findings

1. **Hardware deposit is make-or-break** — reducing it from 200 to 30 tokens moved the score from 0.68 to 0.88. With emerging market sell pressure (25-55%), operators can't accumulate 200 tokens.

2. **Flat rewards work better than tiered** — all tiers earn the same tokens/month. Career progression and credentials provide the incentive, not token premiums.

3. **Higher emissions = more stability** — counter-intuitive, but a large liquid supply pool dampens fundamental price swings. 20M/month with 12-month halving hit the sweet spot.

4. **Burn rate barely matters at high prices** — at $1,000+ token price, burning 60% of revenue removes ~400 tokens from a 490M supply. That's 0.00008%.

5. **Retention is the flywheel** — revenue → burns → price support → earnings → retention → qualified operators → more revenue. Break any link and the economy collapses.

Full analysis in [REPORT_v2.md](REPORT_v2.md).

## The 7-Tier Pipeline

Operators progress through tiers with time and skill gates:

| Tier | Name | Min Months | Skill Required |
|------|------|-----------|----------------|
| T0 | Simulation Training | 0 | 0.00 |
| T1 | Data Labeling | 1 | 0.10 |
| T2 | Browser Teleop | 2 | 0.20 |
| T3 | In-the-Wild Capture | 3 | 0.35 |
| T4 | Facility Teleop | 5 | 0.55 |
| T5 | Live Deployment | 8 | 0.75 |
| T6 | Partner Missions | 12 | 0.90 |

T4+ requires a hardware deposit (VR headset/wearable stake). Soulbound NFT credentials are issued at T2+.

## Data Sources

Behavioral models calibrated from real-world data:

- Gig economy turnover rates — Celayix 2023 (41% annual)
- Mobile app retention — UXCam 2024 (Day-30: 5.6%)
- DePIN staking patterns — Helium network operator behavior
- Robotics data pricing — Scale AI / Vendr enterprise contracts
- Emerging market sell pressure — DePIN operator data (25-55% monthly)
- Earnings threshold — Georgia average salary ($400-600/month)

## Contributing

The simulation is designed for experimentation. Fork it, change the parameters in `train.py`, and see what happens. If you find a configuration that beats 0.8876 — open a PR.

You can also modify `program.md` to change the research strategy for the AI agent.

## License

[MIT](LICENSE)
