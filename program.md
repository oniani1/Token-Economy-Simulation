# CrowdTrain Token Economy — Autoresearch Program

You are an autonomous researcher optimizing the token economy for **CrowdTrain**, a Solana-native decentralized robotics workforce platform. Your goal is to find token economic parameters that produce a healthy, sustainable economy across two simulation generations:

- **v3** — multi-witness peer validation, 36-month horizon, ~120K cumulative operators, 9-sub-score composite
- **v4** — v3 plus three behavioral pillars (operator personas, first-class enterprise customers, macro economy with sentiment + AMM); 36/60-month horizons, 4 supplemental metrics

Read `README.md` first for the full project context. This file is the experiment-loop playbook.

## Context

CrowdTrain manufactures qualified robotics operators at scale through a tiered sim-based training pipeline. Operators progress through seven tiers:

| Tier | Name | Min Months | Skill Required |
|------|------|-----------|----------------|
| T0 | Simulation Training | 0 | 0.00 |
| T1 | Data Labeling | 1 | 0.10 |
| T2 | Browser Teleop | 2 | 0.20 |
| T3 | In-the-Wild Capture | 3 | 0.35 |
| T4 | Facility Teleop | 5 | 0.55 |
| T5 | Live Deployment | 8 | 0.75 |
| T6 | Partner Missions | 12 | 0.90 |

T4+ requires a USD-denominated hardware stake. Soulbound NFT credentials issue at T2+. The token economy needs to:

1. **Retain operators** long enough for them to reach T4+ and become qualified
2. **Maintain token price stability** — no death spirals
3. **Generate protocol revenue** from paying enterprise robotics customers
4. **Keep earnings fair** across operator tiers (Gini < 0.4)
5. **Produce enough qualified operators** (T4+) to service customer demand
6. **Survive macro shocks** (sentiment cycles, regulatory events, recessions, competitor launches) — v4 only
7. **Manage customer concentration** (top-3 < 50% of revenue) — v4 only

The simulation models real behavioral data: gig-economy churn (Celayix 2023), DePIN staking patterns (Helium), robotics-data pricing (Scale AI / Vendr), enterprise SaaS NRR benchmarks.

## Setup

1. **Create a branch**: `git checkout -b autoresearch/<tag>` from current `main`.
2. **Read the engine you'll be evaluating against** — pick one:
   - For **v3 work**: `prepare.py` (immutable engine), `train.py` (params you modify), `validation.py`, `nodes.py`, `treasury.py`
   - For **v4 work**: `prepare_v4.py` (immutable engine — wraps v3 with 3-pillar fallback), `train_v4.py` (params you modify), plus the v4 modules: `operators_v4.py`, `customers.py`, `macro.py`
3. **Initialize results log**: `results.tsv` with header: `experiment\tscore\tretention\tstability\trevenue\tgini\tqualified\tnotes`. Don't commit it.
4. **Run baseline**:
   - v3: `python train.py > run.log 2>&1`
   - v4: `python train_v4.py > run.log 2>&1`
5. **Record baseline composite**, then start experimenting.

## Experiment loop

Each experiment:

1. **Form a hypothesis** about what parameter change will improve the composite score. Think about the economic dynamics — don't random-search.
2. **Edit `train.py` (v3) or `train_v4.py` (v4)** to implement your hypothesis. Each experiment changes 1–3 parameters max so you can isolate effects.
3. **Run**: `python train.py` or `python train_v4.py` (with stdout redirected to a log).
4. **Read results**: the harness prints `Composite Score: <value>` near the bottom; sub-scores follow. If empty, the run crashed — check the tail of the log.
5. **Record** the score and notes in `results.tsv`.
6. **Keep or discard**:
   - If composite improved → `git add train.py && git commit -m "experiment: <description>, score: <value>"`
   - If equal or worse → `git checkout -- train.py` (or `train_v4.py`)
7. **Repeat.**

For broader exploration use the experiment harnesses (each takes MC count as a CLI argument):
- `python experiments.py small_sweep` — v3 12-cell parameter sweep
- `python experiments.py ablation` — v3 mechanic-by-mechanic attribution
- `python experiments.py stress` — v3 stress tests (token crash, demand shock, node bottleneck)
- `python experiments_v4.py 3` — v4 8-cell pillar ablation + stress (~50 min @ MC=3)
- `python experiments_v4_iter2.py 2` — v4 tuned-persona iteration
- `python experiments_v4_iter3.py 2` — 60-month long horizon

## Research strategy

### Phase 1: Understand the baseline (experiments 1–3)
- Run baseline. Inspect each sub-score.
- Identify which sub-score is dragging composite down the most.
- Focus the next 5–10 experiments on the weakest sub-score.

### Phase 2: Core economic tensions (experiments 4–15)
- **Emission rate vs. price stability** — high emissions fund rewards but dilute price; low emissions starve early operators.
- **Burn rate vs. cash retention** — burning more tokens is deflationary but the protocol keeps less cash.
- **Hardware stake vs. T4+ production** — high stakes ensure commitment but slow advancement. v3 finding: don't lower the stake; raise base emission so operators can clear it.
- **Reward multipliers across tiers** — steeper curves incentivize progression but increase Gini.
- **Halving schedule** — faster halvings are deflationary but may kill rewards before customer revenue ramps.
- **(v4) Customer satisfaction grace** — too short and design partners die at m12; too long and bad signals stay invisible.
- **(v4) Sentiment / AMM depth** — shallow AMM amplifies macro shocks; deep AMM dampens dynamics that we want to observe.
- **(v4) Persona mix** — Casual-heavy mixes are realistic but kill T4+ count; Pro-Earner-heavy mixes hit T4+ but lose behavioral honesty.

### Phase 3: Fine-tuning (experiments 15+)
- Try non-linear reward curves and dynamic emission rates.
- Test extreme parameter values to find where behavior breaks.
- Look for parameter interactions (e.g., high burn + low emission = supply crunch).
- For v4: explore customer × persona affinity (e.g., Healthcare prefers Validators).

## What drives the composite score

The score is a weighted sum of nine sub-scores, each clipped to [0, 1]:

| Weight | Sub-score | Cap / target |
|--------|-----------|--------------|
| 20% | Retention | active / total_ever ≥ 55% |
| 10% | Price stability | low CV over last 12 months (peak-collapse penalty) |
| 20% | Revenue | cumulative ≥ $50M (capped — be careful at long horizons) |
| 10% | Fairness (Gini) | Gini < 0.6 (target ~0.4) |
| 15% | Qualified ops | T4+ ≥ 5,000 (capped) |
| 5%  | Data quality | slash_rate < 20% |
| 10% | Validator integrity | false_positive_rate < 10% |
| 5%  | Node ROI | ≥ 0.5 |
| 5%  | Capacity utilization | ≥ 0.5 |

v4 also reports four supplemental metrics (logged but not weighted into the composite): **top-3 customer concentration**, **NRR (blended)**, **sentiment resilience**, **persona diversity index**.

⚠️ **The revenue sub-score caps at $50M cumulative.** At 60-month horizons, two configs can both score 1.0 on revenue while their actual revenues differ by 5×. When comparing long-horizon configs, always read raw `cumulative_revenue` alongside composite.

## Important notes

- **Monte Carlo defaults**: 15 runs in `prepare.py`, 5 in `prepare_v4.py`. The experiment harnesses override these (typically 2–3 to keep sweeps fast). Look at both **mean and std** — high mean with high std means fragile parameters.
- **The price model is structural, not predictive.** It responds to supply / demand / burn / emission flows, not market sentiment outside the modeled HMM (v4).
- **Operator behavior is probabilistic.** Churn rates are modulated by staking status, earnings level, price trends, and (in v4) persona type.
- **Don't optimize one sub-score in isolation.** A config with 0.9 retention but 0.1 stability is worse than balanced 0.6 / 0.6.
- **Unknown PARAMS keys are ignored.** You can add new keys to `train.py` / `train_v4.py` as long as the engine has a `.get()` with a sensible default — both engines do this throughout.
- **v4 pillars are independently ablatable.** Removing `params['operators']` reverts Pillar 1 to v3 mechanical behavior; same for `customers` and `macro`. Use this for clean A/B.

## Key insights from prior runs

Read `REPORT_v3.md` and `REPORT_v4.md` for the full attribution. The headline lessons:

- **Helium's lesson**: Reward decline as the network grew caused massive churn. CrowdTrain needs the reward → qualification → revenue pipeline to work BEFORE emissions halve.
- **Death spiral risk**: token price drops → operator earnings drop → churn ↑ → fewer qualified ops → less revenue → less burn → more sell pressure → price drops further.
- **The flywheel**: revenue → burns → price support → operator earnings → retention → more qualified ops → more revenue.
- **v3 finding (demand-bound)**: doubling demand adds +0.136 to composite; halving operator/node capacity has near-zero effect. Sales velocity is the binding constraint.
- **v3 finding (crash-resilient)**: launching at $0.20 vs $1.00 produces near-identical end state. USD-denominated stakes + revenue-driven fiat ramp self-correct.
- **v4 finding (revenue compounding)**: at 60 months, `v4_no_personas` generates 5× the revenue of v3 winner with equivalent T4+ counts. Customers + macro pillars produce a structurally superior economy that just needs time.
- **v4 known weakness**: m0–17 customer cohorts churn at 100% in v4_baseline. The scheduled event stack (m18 / m24 / m30) hits before satisfaction stabilizes. Fix candidates documented in `REPORT_v4.md`.

## Guardrails

- **Do NOT modify** `prepare.py` or `prepare_v4.py` — these are evaluation oracles. Modify only `train.py` / `train_v4.py` and add new pillar logic in the dedicated modules if a hypothesis genuinely requires it.
- Keep `train.py` / `train_v4.py` as a single PARAMS dict + run block.
- After 20+ experiments, write a summary to `results.tsv` of what you've learned about the parameter landscape — useful for the next agent.
- If you get stuck in a local maximum, try a radical change to escape (e.g., halve emission, double burn, swap persona mix).
- For v4: if you change a v4 module (`operators_v4.py`, `customers.py`, `macro.py`), test the v3 fallback path still works by removing the corresponding PARAMS section and running once.
