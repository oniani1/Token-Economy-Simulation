# CrowdTrain Token Economy — Autoresearch Program

You are an autonomous researcher optimizing the token economy for **CrowdTrain**, a Solana-native decentralized robotics workforce platform. Your goal is to find token economic parameters that produce a healthy, sustainable economy for 20,000+ operators over 24 months.

## Context

CrowdTrain manufactures qualified robotics operators at scale through a tiered sim-based training pipeline. Operators progress from Sim Academy (Tier 1) through Browser Teleop, Facility Teleop, Failure Analysis, and Partner Missions (Tier 6). The token economy needs to:

1. **Retain operators** long enough for them to become qualified (T4+)
2. **Maintain token price stability** — no death spirals
3. **Generate protocol revenue** from paying robotics customers
4. **Keep earnings fair** across operator tiers (Gini < 0.4)
5. **Produce enough qualified operators** (T4+) to service customers

The simulation models real behavioral data: gig economy churn rates, DePIN staking patterns (Helium), and robotics data service pricing (Scale AI benchmarks).

## Setup

1. Create branch: `git checkout -b autoresearch/<tag>` from current master
2. Read the files:
   - `README.md` — project context
   - `prepare.py` — **DO NOT MODIFY**. Contains the simulation world: operator behavior models, demand/revenue curves, token price model, evaluation metrics, and Monte Carlo engine. Read this carefully to understand what drives the score.
   - `train.py` — **THE FILE YOU MODIFY**. Contains all token economy parameters. Everything is fair game.
3. Initialize `results.tsv` with header: `experiment\tscore\tretention\tstability\trevenue\tgini\tqualified\tnotes`
4. Run baseline: `python train.py > run.log 2>&1`
5. Record baseline score, then start experimenting.

## Experiment Loop

Each experiment:

1. **Form a hypothesis** about what parameter change will improve the score. Think about the economic dynamics — don't just random-search.
2. **Edit `train.py`** to implement your hypothesis.
3. **Run**: `python train.py > run.log 2>&1`
4. **Read results**: `grep "^score:" run.log`
   - If empty, the run crashed. Check `tail -n 50 run.log` and fix.
5. **Record** in `results.tsv` (don't commit this file).
6. **Keep or discard**:
   - If score improved → `git add train.py && git commit -m "experiment: <description>, score: <value>"`
   - If score equal or worse → `git checkout -- train.py`
7. **Repeat.**

## Research Strategy

### Phase 1: Understand the baseline (experiments 1-3)
- Run baseline and study the sub-scores
- Identify which component is dragging the composite score down the most
- Focus initial experiments on the weakest sub-score

### Phase 2: Core economics (experiments 4-15)
Key tensions to explore:
- **Emission rate vs. price stability**: High emissions fund rewards but dilute price. Low emissions starve early operators.
- **Burn rate vs. cash retention**: Burning more tokens is deflationary but the protocol keeps less cash.
- **Staking APY vs. sell pressure**: High APY retains operators but increases future sell pressure when they unstake.
- **Hardware stake requirement vs. T4+ production**: High requirements ensure commitment but slow operator advancement.
- **Reward multipliers across tiers**: Steeper curves incentivize progression but increase inequality.
- **Halving schedule**: Faster halvings are more deflationary but may kill early-stage rewards before revenue kicks in.

### Phase 3: Fine-tuning (experiments 15+)
- Try non-linear reward curves
- Experiment with dynamic emission rates
- Test extreme parameter values to understand boundaries
- Look for parameter interactions (e.g., high burn + low emission may create supply crunch)

### Key Insights from DePIN History
- **Helium's lesson**: Early high rewards attracted operators, but reward decline as network grew caused massive churn. CrowdTrain needs the reward→qualification→revenue pipeline to work BEFORE emissions halve.
- **Death spiral risk**: If token price drops → operator earnings drop → churn increases → fewer qualified operators → less revenue → less burn → more sell pressure → price drops further.
- **The flywheel**: Revenue → burns → price support → operator earnings → retention → more qualified operators → more revenue.

## What Drives the Score

The composite score (0 to 1, higher is better) is:
- **30%** Operator retention at 24 months (target: >60% of all-time operators still active)
- **25%** Token price stability (low coefficient of variation over last 12 months, heavy penalty if price collapses below 20% of peak)
- **20%** Protocol revenue (target: $3M cumulative by month 24)
- **15%** Earnings fairness / Gini coefficient (target: Gini < 0.4)
- **10%** Qualified operator production (target: 500+ T4+ operators by month 24)

## Important Notes

- The simulation runs 20 Monte Carlo iterations with different random seeds. Look at both mean AND std — a high mean with high std means your parameters are fragile.
- The token price model is structural, not predictive. It responds to supply/demand dynamics — burns push price up, emissions push it down, revenue creates demand.
- Operator behavior is probabilistic. Churn rates are modified by staking status, earnings level, and price trends.
- Don't just optimize one sub-score — the composite matters. A parameter set with 0.9 retention but 0.1 price stability is worse than balanced 0.6/0.6.
- You can add new parameters to `train.py` as long as `prepare.py` handles unknown params gracefully (it does — unknown keys are ignored via `.get()` with defaults).
- Think like a token economist, not just a parameter optimizer. Ask: "Would this parameter set create a sustainable economy that real operators would participate in?"

## Guardrails

- Do NOT modify `prepare.py` — this is your evaluation oracle
- Keep `train.py` as a single file with the PARAMS dict and the run block
- Each experiment should change 1-3 parameters max (isolate effects)
- If you get stuck in a local maximum, try a radical change to escape
- After 20+ experiments, consider writing a summary of what you've learned about the parameter landscape
