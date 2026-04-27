# CrowdTrain Token Economy Simulation

A Monte Carlo, agent-based simulation of the [CrowdTrain](https://crowdtrain.io) token economy — a decentralized robotics workforce platform on Solana. The repo is the working copy of three successive simulation generations (v2 → v3 → v4) plus the experimental harness, reports, and recommended launch configurations.

The point of the project is **not** to predict a token price. It is to find a parameter regime in which the protocol survives 36–60 months of operator behavior, customer churn, and macro shocks — and to be able to defend those numbers to a skeptical investor or analyst with stress tests, ablations, and source-traceable assumptions.

---

## TL;DR

- **Three simulation generations.** v2 (24-month, supply-side only) → v3 (36-month, multi-witness peer validation, treasury & nodes as first-class agents) → v4 (36/60-month, layered persona + customer + macro pillars on top of v3).
- **The recommended launch config is `v4_no_personas`** — v4 with the customer and macro pillars on, operators reverted to v3 mechanics. At 36 months it scores **0.7575 composite** (+8% over v3 winner) with **$73M cumulative revenue** (+204%); at 60 months it generates **$389M revenue with 37K T4+ operators — about 5× the revenue of v3 winner at the same operator count**.
- **The big methodological finding**: the composite score caps revenue at $50M, so above that threshold two configurations can look "tied" while their actual economies diverge by 5×. Always read raw revenue alongside composite at long horizons.
- **The biggest known weakness**: the first 18 months of customer cohorts churn at 100% in v4_baseline — the scheduled event stack at m18 / m24 / m30 hits before satisfaction has stabilized. m24+ cohorts show 100% survival. Fix candidates are documented below.
- **The system is demand-bound, not supply-bound.** v3 stress tests show doubling demand adds +0.136 to composite; halving operator/node capacity has near-zero effect. Sales velocity is the binding growth constraint — not emission, not staking, not node count.

---

## Why we did this

CrowdTrain has to do something that almost no DePIN protocol has done cleanly: pay a large, distributed workforce in a token while a fiat-paying enterprise customer base matures around them. Two things can kill that:

1. **Death spirals on the supply side.** Helium's cautionary tale: early high rewards attract operators; the reward curve halves before customer revenue arrives; operators churn; price drops; remaining operators churn faster; the network collapses.
2. **Customer-side fragility.** Enterprise robotics-data customers don't behave like retail users. They sign multi-year contracts, but they also carry concentration risk (in real-world enterprise SaaS, top-3 customers are routinely 20–40% of ARR), satisfaction-driven churn, and sensitivity to macro events (regulation, recession, competitor launches). v3 had no way to measure any of this — so we built v4 to put it on a dial.

The CrowdTrain v12 memo introduced **multi-witness peer validation** as the central new mechanic — higher-tier operators audit lower-tier work, slashing splits between validators and burns, and the validator queue becomes its own economic role. We needed to know whether that mechanic actually closes the quality loop the memo claims, and what parameter regime supports it.

The simulation answers four questions:

- Does the protocol stay alive for 36+ months under realistic operator/customer/macro behavior?
- Which mechanics are load-bearing vs. cosmetic? (ablations)
- Where is the binding constraint — supply, demand, or capital? (stress tests)
- What launch configuration should we use, and what are its known weaknesses?

---

## What we simulated

The simulation is an agent-based, stochastic, monthly-tick model. A run is a sequence of `~36–60` monthly snapshots; each snapshot is the state of every operator, every customer, every node, the treasury, the AMM, and the macro regime.

### Population scale

Onboarding follows a community-seeded S-curve calibrated against early-stage DePIN networks:
- Months 1–12: ramp from 300 to ~8K new operators/month, ~51K cumulative
- Months 13–24: ~45K additional, decaying
- Months 25–36: gradual saturation, ~120K cumulative ever-onboarded under v3
- v4 referrals (Pillar 1) push total ever-onboarded to ~130–150K at month 36 (active 40K–53K)
- 60-month runs reach ~130K–170K ever-onboarded with 43K–55K active

### The 7-tier operator pipeline

Operators progress through tiers with both time and skill gates. T4+ requires a USD-denominated hardware stake (VR headset / wearable). Soulbound NFT credentials are issued at T2+.

| Tier | Name | Min Months | Skill Required |
|------|------|-----------|----------------|
| T0 | Simulation Training | 0 | 0.00 |
| T1 | Data Labeling | 1 | 0.10 |
| T2 | Browser Teleop | 2 | 0.20 |
| T3 | In-the-Wild Capture | 3 | 0.35 |
| T4 | Facility Teleop | 5 | 0.55 |
| T5 | Live Deployment | 8 | 0.75 |
| T6 | Partner Missions | 12 | 0.90 |

### The three pillars (v4)

v4 splits the world into three behaviorally-rich pillars on top of the v3 mechanics. Each pillar can be ablated by removing its `PARAMS` section — the engine cleanly falls back to v3 behavior.

**Pillar 1 — Operators** (`operators_v4.py`)
- 4 personas with different stake aggressiveness and tier-advancement speeds: Casual (60%), Pro Earner (25%), Validator (10%), Hardware Investor (5%)
- Learning curve `skill = α·log(1 + experience_hours/100)`, capped at +30%
- Persona-weighted decision policy for stake / sell / advance / specialize
- Referral acquisition: each active operator spawns Poisson(0.02)/mo new operators with 30% persona inheritance

**Pillar 2 — Customers** (`customers.py`)
- 4 industry segments, each with its own size, demand profile, and annual churn baseline:

  | Segment | Mean contract size | Annual churn baseline | Demand profile skew |
  |---|---|---|---|
  | Manufacturing | $80K/mo | 15% | T1–T2 heavy |
  | Warehouse | $60K/mo | 25% | T2 heavy |
  | Healthcare | $120K/mo | 10% | T4–T6 heavy |
  | Robotics OEM | $150K/mo | 8% | T4–T5 heavy |

- Pareto-distributed contract sizes (α = 1.5, capped 0.10× to 3.0× of segment mean) — a few customers are large
- 3 design partners seeded at TGE: manufacturing $100K, warehouse $80K, healthcare $150K
- Stochastic per-segment Poisson(λ_segment(t)) arrivals after TGE; λ follows a logistic curve (peaks ~m18) modulated by sentiment + era
- Satisfaction = 0.40 · quality + 0.40 · fulfill_pct + 0.20 · sla_pct (6-month rolling)
- Hybrid churn: sat < 0.50 for 3 months → churn; sat > 0.80 for 3 months → expand 1.20× (cap 3.0×)
- 12-month bootstrap grace period for design partners (sat updates skip during grace)

**Pillar 3 — Macro** (`macro.py`)
- Sentiment HMM (bull/bear): `p(bull→bear)=1/21`, `p(bear→bull)=1/9`
- x·y=k AMM seeded from treasury LP at TGE (1M tokens + $1M USD; $100k sell ≈ -10% price)
- Default scheduled events: month 18 competitor launch (arrivals × 0.7 for 6 mo), month 24 regulatory shock (price × 0.75), month 30 recession (churn × 1.5 for 4 mo)
- Era detection: bootstrap → growth (rev > $5M or month ≥ 12) → maturity (rev > $50M or month ≥ 36)

### Validation (peer-review by higher-tier operators)

The v3 rebuild centered on the memo's multi-witness validation:

- **Multi-witness consensus**: 3 validators per sampled task; ≥2 must agree; T6 audit on disagreement
- **Risk-weighted sampling**: T0–T1 = 10%, T2–T3 = 25%, T4–T6 = 100%
- **Graduated slashing**: 10% → 25% → 50% → 30-day cooldown → ban
- **Slashed-token split**: 50% to validators / 50% burn; within validators 70% to fail-voters / 30% to pass-voters
- **Clean-streak reset**: 1 strike removed per 100 high-quality hours
- **Bootstrap**: T0/T1 auto-pass in months 1–3 (no validators yet)

### Treasury, nodes, and pay denomination

- **Treasury** (`treasury.py`): explicit entity with TGE distribution + linear team/investor vesting + fiat reserves accumulated from customer revenue
- **Nodes** (`nodes.py`): first-class agents, ~1 per 1,000 ops, partner revenue share, sync-tier capacity cap
- **Pay denomination**: T0–T2 always pure tokens; T3+ shifts toward fiat as ARR grows (revenue-gated fiat ramp)
- **Hardware stakes**: USD-denominated (T3 / T4 / T6), quality-gated linear unlock (1% per qualified hour, max 100h)

---

## Version history

| Version | Mechanics added | Horizon | Best score | Cumulative revenue |
|---|---|---|---|---|
| v2 | 7-tier pipeline; flat rewards; stochastic per-op quality; auto-slash on quality<0.5; emerging-market sell pressure | 24 months | 0.8876 (capped scoring) | $20.3M |
| v3 | Multi-witness peer validation; graduated slashing; risk-weighted sampling; node network; treasury entity; fiat ramp; USD-denominated stakes; 36-month horizon; 9 sub-scores | 36 months | **0.6502** (winner config) | $24.4M |
| v4 | Operator personas + learning + referrals; first-class enterprise customers; sentiment HMM; AMM-based pricing; scheduled macro events; era detection; 4 supplemental metrics | 36 / 60 months | **0.7575** @ 36mo (no_personas), **0.8110** @ 60mo | $73M @ 36mo, **$389M @ 60mo** |

**v2's 0.8876 is not directly comparable to v3/v4 scores** — v2 used different score weights and a different scoring scale. v3 introduced 9 sub-scores with stricter caps; the same underlying economy scores lower under v3 weights because the ceiling is harder to hit.

**A note on v3 winner score variance** — `v3 winner` shows up in this README as **0.6502** (the original 12-cell sweep, MC = 2 runs at 36 months) and as **0.7009** when used as the v4 ablation reference (rerun under MC = 3). Same parameters, different MC seed counts and sweep contexts. Treat numbers as comparable within a table, not across tables.

---

## Headline results

### v3 — peer-validation rebuild (2026-04-25)

Winning configuration from a 12-cell sweep at 36 months, 2 Monte Carlo runs:

```
base_emission_per_active_op_per_month: 45
hardware.stake_required_t4_usd:        $150
supply.monthly_emission_rate:          3M tokens/mo
nodes.arms_per_node:                   2
nodes.ops_per_node_target:             2,000
```

| Metric | Default v3 | Winner config | Change |
|---|---|---|---|
| Composite score | 0.385 | **0.650** | **+69%** |
| T4+ operators @ m36 | 36 | **23,143** | **643×** |
| Cumulative revenue @ m36 | $4.7M | **$24.4M** | **5.2×** |
| Final token price | $1.12 | $7.03 | 6.3× |
| Fiat ratio @ m36 | 34% | 64% | +30 pts |
| Earnings Gini | 0.39 | 0.32 | more equal |

**Three v3 discoveries (full attribution in `REPORT_v3.md`):**

1. **Hardware stakes were over-tuned.** The ablation showed +0.161 score from disabling them, but the right answer is to fund operators well enough to clear the stake organically (higher base emission), not to remove the skin-in-game function.
2. **The system is demand-bound, not supply-bound.** Doubling demand jumps score by +0.136. Halving operator/node capacity has near-zero effect. Sales velocity is the binding growth constraint.
3. **Token-crash resilience is built in.** Launching at $0.20 instead of $1.00 produces a near-identical end state (0.6501 vs 0.6502). USD-denominated stakes + revenue-driven fiat ramp self-correct within months.

### v4 — 3-pillar behavioral redesign (2026-04-26)

**The decisive cell ablation at 36 months:**

| Config | Score | T4+ | Cum Revenue | NRR | Top-3 conc |
|---|---|---|---|---|---|
| v3 winner (reference) | 0.7009 | 22,458 | $24.1M | n/a | n/a |
| v4 baseline (all 3 pillars on) | 0.5150 | 2,288 | $26.2M | 0.14× | 8.3% |
| **v4 no_personas (cust + macro)** | **0.7575** | **18,986** | **$73.0M** | **0.37×** | **7.5%** |
| v4 no_customers | 0.5834 | 3,764 | $19.8M | 1.00× | n/a |
| v4 no_macro | 0.5783 | 2,356 | $33.2M | 0.25× | 13.2% |

**The 60-month long horizon (decisive):**

| Cell @ 60mo | Score | Cum Revenue | T4+ | NRR |
|---|---|---|---|---|
| v3 winner | 0.8379 | $78.5M | 37,328 | n/a |
| v4 baseline (3 pillars) | 0.7832 | $122.1M | 6,108 | 0.25× |
| **v4 no_personas** | **0.8110** | **$389.2M** | **36,748** | **0.56×** |

**The big finding**: at 60 months, `v4_no_personas` generates **5× the revenue of v3 winner** ($389M vs $78M) with **equivalent T4+ counts** (36.7K vs 37.3K). The composite score difference (-0.027) is a measurement artifact — the scoring function caps revenue at $50M cumulative, so both configs already saturate that sub-score even though v4's actual revenue is 5× larger. The customer + macro pillars produce a structurally superior token economy that just needs time to compound.

**Per-pillar attribution:**

| Pillar | Δ on composite when ON | What it adds | What it costs |
|---|---|---|---|
| Customers | -0.07 | Concentration, NRR, segment mix, churn dynamics | Early-cohort customer mortality |
| Macro | -0.06 | Sentiment cycles, AMM price impact, scheduled events | Volatility hits the stability sub-score |
| Personas | **-0.24** | Persona diversity, behavioral realism, learning curve | 60% Casual operators rarely reach T4+ |

The personas pillar is honest about user heterogeneity but penalises the qualified-operator sub-score. Tuning the persona mix (40% Casual / 40% Pro Earner / 15% Validator / 5% HW) recovers ~0.06; the rest is structural.

### Stress tests (vs v4 baseline 0.515)

| Scenario | Score | Δ | Note |
|---|---|---|---|
| Biggest customer churns @ m18 | 0.431 | -0.084 | Meaningful revenue cliff; high σ depending on Pareto draw of #1 |
| Manufacturing segment collapses (80% churn) | 0.515 | ±0 | Other 3 segments backfill demand |
| New-customer drought (×0.1 for 6 mo) | 0.465 | -0.050 | Existing book carries the economy |
| Composite shock (bear bias + faster transitions) | 0.554 | **+0.039** | Counterintuitive — protocol is asymmetrically robust to bear |

---

## What's still broken

The v4 reports flag three open issues we haven't closed yet:

1. **Early customer cohorts die.** In v4_baseline, 100% of m0–17 customer cohorts churn — the event stack at m18 / m24 / m30 hits while their satisfaction is still ramping up. m24+ cohorts show 100% survival. Fix candidates: extend grace for design partners to 24mo; delay first event to m24+; model relationship-based retention (real enterprise customers don't churn over 3 bad months).
2. **`sentiment_resilience` metric is unstable.** It can blow up when a run is mostly bear. Needs re-derivation as `score-in-bear / score-in-bull` with proper weighting.
3. **Persona policy is rule-based and rigid.** Adaptive policies (operators that change behavior in response to price / earnings) would be more realistic but require more parameters to defend.

Lower-priority follow-ups: AMM depth sweep ($500K vs $5M for shock sensitivity); customer × persona affinity (Healthcare prefers Validators, Robotics OEM prefers HW Investors); Bayesian optimization over the parameter space (vs grid sweeps).

---

## Scoring

The composite score is a weighted sum of sub-scores, each clipped to [0, 1]:

| Weight | Sub-score | What it measures | Target |
|--------|-----------|------------------|--------|
| 20% | Retention | Active operators / total ever onboarded | ≥55% |
| 10% | Price stability | 1 − coefficient-of-variation over last 12 months (with peak-collapse penalty) | low CV |
| 20% | Revenue | Cumulative revenue / $50M | $50M |
| 10% | Fairness (Gini) | 1 − Gini / 0.6 of operator earnings | <0.4 |
| 15% | Qualified ops | T4+ operators / 5,000 | 5,000 |
| 5%  | Data quality | 1 − slash_rate × 5 | slash <20% |
| 10% | Validator integrity | 1 − false_positive_rate / 0.10 | FPR <10% |
| 5%  | Node ROI | Node operator profitability score | ≥0.5 |
| 5%  | Capacity utilization | Network capacity used / available | ≥0.5 |

v4 reports four supplemental metrics on top of the composite (not weighted in, but logged):
**top-3 customer concentration**, **net revenue retention (blended)**, **sentiment resilience**, **persona diversity index**.

The revenue cap at $50M is one reason `v3_winner` and `v4_no_personas` both score ~1.0 on revenue at 60mo even though their actual revenues differ by 5×. We have not retuned the cap — when comparing long-horizon configs, look at raw cumulative revenue alongside composite.

---

## Quick start

```bash
git clone https://github.com/oniani1/Token-Economy-Simulation.git
cd Token-Economy-Simulation

python train.py        # v3 single-config Monte Carlo (~30s)
python train_v4.py     # v4 single-config Monte Carlo (~2 min)

# Sweeps (longer)
python experiments.py small_sweep      # v3 12-cell sweep
python experiments_v4.py 3             # v4 8-cell pillar ablation + stress, MC=3 (~50 min)
python experiments_v4_iter2.py 2       # v4 tuned-persona iteration (~30 min)
python experiments_v4_iter3.py 2       # 60-month long horizon

# Regenerate the v4 report from the JSON results
python report_v4_generator.py
```

Pure Python 3.7+ stdlib. No dependencies.

### Output

A Monte Carlo run prints monthly progression followed by the aggregated scoreboard. The v4 print format (illustrative — exact numbers vary by config and MC count):

```
Month  1: price=$1.00  revenue=$0       T4+=0      active=300
Month  2: price=$0.98  revenue=$0       T4+=0      active=798
...

==============================================================================
CrowdTrain v4 Monte Carlo Results — 3-Pillar Behavioral Edition
==============================================================================
  Composite Score:   0.7575 ± 0.0218

  Base sub-scores (mean ± std):
    Retention                 0.8920 ± 0.0140
    Price stability           0.5430 ± 0.0410
    Revenue                   1.0000 ± 0.0000
    Fairness (Gini)           0.8110 ± 0.0260
    Qualified ops             1.0000 ± 0.0000
    Data quality              0.9620 ± 0.0070
    Validator integrity       0.9540 ± 0.0090
    Node ROI                  0.6100 ± 0.0500
    Capacity utilization      0.7400 ± 0.0300

  v4 Supplements:
    Top-3 customer concentration       7.5%   (target <50%)
    NRR (blended)                      0.37x  (target >1.00)
    Sentiment resilience               0.91   (target >0.7)
    Persona diversity                  0.00   (off — no_personas config)

  Key Metrics:
    Cumulative Revenue:     $73,012,400
    Final Token Price:      $9.42
    T4+ Operators:          18,986
    Active Customers:       237
```

### Reproducibility

- Random seed: `42` (set in `prepare.py` and `prepare_v4.py`); seed `i` uses `42 + i`.
- Default Monte Carlo runs: **15** for v3 (`prepare.py`), **5** for v4 (`prepare_v4.py`); the experiment harnesses override these per cell (typically MC = 2–3).
- Default horizon: **36 months**; `experiments_v4_iter3.py` extends to 60.
- Bump MC count for production reports — std drops as `1/√n`. The CrowdTrain v4 stakeholder packet (`CrowdTrain_v4_Report.pdf`) was generated with the JSON results in `v4_experiment_results.json` / `v4_iter2_results.json` / `v4_iter3_results.json`.

---

## File map

```
prepare.py            v3 simulation engine — 20-step monthly pipeline. Immutable.
prepare_v2.py         v2 snapshot kept for A/B comparison.
prepare_v4.py         v4 engine — 3-pillar wrapper around v3 with PARAMS-based fallback.

train.py              v3 PARAMS dict (11 sections: supply, task_model, validation,
                      slashing, hardware, earnings, burn, sell_pressure, nodes,
                      retention, study_assumption, demand). This is what gets tuned.
train_v4.py           v4 PARAMS dict — adds operators / customers / macro sections.

validation.py         Multi-witness consensus + graduated slashing.
nodes.py              DePIN node agents with sync-tier capacity caps.
treasury.py           TGE distribution + linear vesting + fiat reserves.
operators_v4.py       v4 personas + learning curve + decision policy + referrals.
customers.py          v4 enterprise customers — segments, Pareto sizing, satisfaction churn.
macro.py              v4 sentiment HMM + x·y=k AMM + scheduled events + era detection.

experiments.py            v3 CLI: ablation / small_sweep / full_sweep / stress / timeseries.
experiments_v4.py         v4 8-cell pillar ablation + stress sweep.
experiments_v4_iter2.py   v4 tuned-persona iteration (40/40/15/5).
experiments_v4_iter3.py   v4 60-month long-horizon sweep.

report_v4_generator.py    Auto-generates REPORT_v4.md + plots from JSON results.
build_report.py           Generates the PDF / DOCX report packets.

REPORT.md / REPORT_v2.md  Historical reports for the v1 / v2 simulations.
REPORT_v3.md              v3 winner config + 18 architectural decisions + ablations.
REPORT_v4.md              v4 full analysis: pillar ablation, stress, iter2/iter3, cohorts.
EXECUTIVE_SUMMARY_v4.md   2-minute exec summary of the v4 findings.
CrowdTrain_v4_Report.{pdf,docx}    Stakeholder-ready packet.

v4_overview.png                    6-panel chart of best config (price, revenue, ops,
                                   customers, sentiment, NRR).
v4_iter2_comparison.png            Bar chart of tuned-persona iteration cells.
v4_iter3_comparison.png            36mo vs 60mo long-horizon comparison.
customer_cohort_analysis.png       Per-cohort customer survival curves — visualizes
                                   the m0–17 mortality issue described in "What's still broken".
winner_timeseries.csv              v3 winner 36-month trajectory.
v4_best_timeseries.csv             v4 best (no_personas) 36-month trajectory.

program.md                 Original autoresearch instructions for the AI agent loop.
crowdtrain-memo-v12.docx   Source memo (defines the peer-validation mechanic).
```

---

## Recommended launch configurations

Two viable configurations depending on what you need to defend:

- **Option A — `v4_no_personas`** (max composite + new supplements):
  0.7575 composite @ 36mo, 0.811 @ 60mo, $389M revenue, 37K T4+, top-3 concentration 7.5%, NRR 0.56×.
  Customers + macro pillars on; operators revert to v3 mechanics. **Best for headline numbers in investor materials.**

- **Option B — `v4_baseline`** (full behavioral realism):
  0.515 composite @ 36mo, 0.783 @ 60mo, $122M revenue. All three pillars on, including persona heterogeneity. **Best for defending assumptions to skeptical analysts** — the persona drag is the price you pay for behavioral honesty.

The standing recommendation is to use **Option A for headline numbers with explicit persona-modeling footnotes**, and to keep **Option B for stress-testing and risk modeling**.

---

## How the autoresearch loop works

The repo is set up so an AI coding agent can pick a branch, run experiments, and commit improvements. Point Claude / Codex / etc. at the repo and tell it:

```
Read program.md and start experimenting
```

`program.md` defines the experiment loop: form a hypothesis, edit `train.py` (or `train_v4.py`), run, score, keep or discard, repeat. The simulation engines (`prepare.py`, `prepare_v4.py`) are the evaluation oracle and should not be modified during a research run.

---

## Data sources

Behavioral models are calibrated from real-world data. Where a number isn't directly sourced, the assumption is documented in `REPORT_v3.md` or `REPORT_v4.md`.

- Gig economy turnover — Celayix 2023 (41% annual)
- Mobile app retention — UXCam 2024 (Day-30: 5.6%)
- DePIN staking patterns — Helium operator behavior
- Robotics data pricing — Scale AI / Vendr enterprise contracts
- Emerging-market sell pressure — DePIN operator data (25–55% monthly)
- Operator earnings threshold — Georgia average salary ($400–600/month)
- Enterprise customer concentration / NRR benchmarks — public SaaS S-1 filings

---

## License

[MIT](LICENSE)
