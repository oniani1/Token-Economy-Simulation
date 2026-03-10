# CrowdTrain Token Economy Autoresearch

Autonomous optimization of CrowdTrain's token economy using the [autoresearch](https://github.com/karpathy/autoresearch) pattern.

## What This Does

An AI agent iterates on token economy parameters (emission rates, staking mechanics, burn rates, reward structures) while a fixed simulation engine evaluates each configuration across 20 Monte Carlo runs of a 24-month agent-based model.

The simulation models:
- **20,000 operators** onboarding over 12 months with S-curve adoption
- **6-tier progression** from Sim Academy to Partner Missions
- **Realistic churn** calibrated from gig economy data (41% annual) and DePIN patterns
- **Token mechanics**: burn-and-mint, halving, staking, hardware stake requirements
- **Revenue model**: robotics data customers scaling with qualified operator count
- **Token price**: structural supply/demand model (not a market prediction)

## Files

```
prepare.py    — Fixed simulation world. Operator behavior, demand curves,
                evaluation metrics, Monte Carlo engine. DO NOT MODIFY.
train.py      — Token economy parameters. THE AGENT MODIFIES THIS.
program.md    — Agent instructions. THE HUMAN MODIFIES THIS.
```

## Quick Start

```bash
# Run baseline
python train.py

# Start autoresearch (point Claude Code / Codex at the repo)
# "Read program.md and start experimenting"
```

## Score

The composite score (0-1) optimizes for:
- 30% Operator retention
- 25% Token price stability  
- 20% Protocol revenue
- 15% Earnings fairness
- 10% Qualified operator production

## Data Sources

Behavioral models calibrated from:
- Gig economy turnover rates (Celayix 2023)
- Mobile app retention benchmarks (UXCam 2024)
- DePIN staking patterns (Helium network)
- Robotics data pricing (Scale AI / Vendr)
- SaaS churn benchmarks (Focus Digital 2025)
