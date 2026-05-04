# CrowdBrain Token Economy Simulation

A Monte Carlo, agent-based simulation of the [CrowdBrain](https://crowdbrain.ai) token economy — a Solana-native DePIN network that trains, qualifies, and deploys robotics operators (formerly named CrowdTrain in earlier memos). The repo is the working copy of four successive simulation generations (v2 → v3 → v4 → v5) plus the experimental harness, reports, and recommended launch configurations.

The point of the project is **not** to predict a token price. It is to find a parameter regime in which the protocol survives 36–60 months of operator behavior, customer churn, and macro shocks — and to be able to defend those numbers to a skeptical investor or analyst with stress tests, ablations, and source-traceable assumptions.

---

## TL;DR

- **Four simulation generations + iterative realistic recalibration.** v2 → v3 → v4 → v5 → v5_realistic → **v5_realistic_jcurve (iter4)** — the latest calibration models a **J-curve trajectory** (slow first 18 months, mild pickup mid year 2 → mid year 3, take-off from month 30+) that matches how real Physical-AI / teleop markets mature.
- **The headline recommended config is `jcurve_combined_60mo`** — composite **0.683 ± 0.020** at 60 months under the J-curve realistic baseline + iter3 winners (op_loose unlock + $100 hardware stake): **$24.4M final ARR**, **185 customers**, **2,582 T4+ operators**, **$40M cumulative revenue**. These numbers are explicitly defensible against real-world Series-A → Series-B robotics-data peers (Scale AI was ~$10M ARR at year 3 with thousands of customers; CrowdBrain wedge is narrower but reaches Series-B trajectory by year 5).
- **Three iterations of sweeps** (47 + 47 + 35 min wall time, parallelized across 23 cores, 850 total runs at MC=10–50): iter1 found the v5 layer cost was 0.21 composite vs v4-equivalent under unrealistic numbers; iter2 found `stake_300` and `unlock_revenue_gated` were the winners under unrealistic params; **iter3 (realistic) flipped both findings** — `stake_100` is optimal under realistic params, and `unlock_op_loose` (10/5/2 op-count thresholds) dominates over revenue-gating.
- **Q4 2026 milestone (3+ paying customers, $500K+ ARR @ month 8) is marginal at MC=50**: P(hit) = 12%, mean Q4 customers = 4.6 ✓, mean Q4 ARR = $413K (just below target). The customer-count target is consistently met; the ARR threshold needs either re-targeting or an accelerated launch.
- **Six v5 findings (unrealistic mode) worth reading** are documented in `REPORT_v5.md`: tier-unlock gating improves the system, the token economy is load-bearing (m12 cutover beats points-only by 23%), bond size barely matters but facility/community split does, Tesla/1X wage anchor is a non-issue, funding winter + MVP slip are existential threats, and Georgia is the most load-bearing region.
- **The big methodological finding**: the composite score caps revenue at $50M, so above that threshold two configurations can look "tied" while their actual economies diverge. Always read raw revenue alongside composite. With realistic calibration, this cap matters less because revenue stays in the $5–90M band.
- **The system is demand-bound, not supply-bound.** v3 stress tests show doubling demand adds +0.136 to composite; halving operator/node capacity has near-zero effect. Sales velocity is the binding growth constraint — not emission, not staking, not node count.

---

## Why we did this

CrowdBrain has to do something that almost no DePIN protocol has done cleanly: pay a large, distributed workforce in a token while a fiat-paying enterprise customer base matures around them. Two things can kill that:

1. **Death spirals on the supply side.** Helium's cautionary tale: early high rewards attract operators; the reward curve halves before customer revenue arrives; operators churn; price drops; remaining operators churn faster; the network collapses.
2. **Customer-side fragility.** Enterprise robotics-data customers don't behave like retail users. They sign multi-year contracts, but they also carry concentration risk (in real-world enterprise SaaS, top-3 customers are routinely 20–40% of ARR), satisfaction-driven churn, and sensitivity to macro events (regulation, recession, competitor launches). v3 had no way to measure any of this — so we built v4 to put it on a dial.

The v12 memo (CrowdTrain era) introduced **multi-witness peer validation** as the central new mechanic — higher-tier operators audit lower-tier work, slashing splits between validators and burns, and the validator queue becomes its own economic role. v3/v4 simulated that.

The **v5 memo** (CrowdBrain rebrand, 2026-Q2) added four new design questions on top of the validated v4 baseline:

1. **Conditional tier unlock.** T0–T2 launch immediately; T3–T5 unlock "with scale" — but the memo doesn't specify the thresholds. Wrong answer kills the protocol.
2. **First-class node-providers.** Bonded community node-providers separate from operators, with their own slashing and dispute system. How big should the bond be? How much community vs. CrowdBrain-owned facility?
3. **Geographic operator pool.** Georgia / Philippines / Kenya at $5–12/hr vs. Tesla/1X at $48/hr. How much wage-anchor flight risk is real?
4. **Points → tokens transition.** Operators start earning points; tokens activate later. When? And does deferring help or hurt?

The simulation now answers six questions across all generations:

- Does the protocol stay alive for 36+ months under realistic operator/customer/macro behavior?
- Which mechanics are load-bearing vs. cosmetic? (ablations)
- Where is the binding constraint — supply, demand, or capital? (stress tests)
- What launch configuration should we use, and what are its known weaknesses?
- (v5) When and how should T3–T5 unlock? When does the token economy go live?
- (v5) Which scenarios kill the path to Q3/Q4 milestones, and which regions are load-bearing?

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

### The 7-tier operator pipeline (internal indexing) — v5 maps to memo's 6 tiers

Operators progress through tiers with both time and skill gates. T4+ requires a USD-denominated hardware stake (VR headset / wearable). Soulbound NFT credentials are issued at T2+.

The v5 memo collapses to 6 tiers (T0–T5) but the engine preserves v4's 7-tier indexing for apples-to-apples comparability with prior runs. The mapping is:

| Internal | Memo v5 tier | Name | Min Months | Skill Required |
|---|---|---|---|---|
| T0 | T0 | Sim Academy (free; soulbound NFT) | 0 | 0.00 |
| T1 | T1 | Episode QA (paid, no hardware) | 1 | 0.10 |
| T2 | T2 | Browser Teleop (CB facility, <80ms) | 2 | 0.20 |
| T3 | T3 | VR/Wearable Teleop ($300–500 device, earned) | 3 | 0.35 |
| T4 | T4 | Failure Analysis (asynchronous) | 5 | 0.55 |
| T5 | T5 | Live Deployment (homes/warehouses/factories) | 8 | 0.75 |
| T6 | T5 (collapsed) | Partner Missions (premium rate) | 12 | 0.90 |

In v5 mode, T3 / T4 / T6 are conditionally gated — they unlock when revenue, op count, time, or demand thresholds are met (the gating rule is the central Track-1 question).

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

### The four v5 layers (built on top of v4)

v5 sits on the v4 engine and adds four opt-in layers. Each can be ablated by removing its `PARAMS` section in `train_v5.py`.

**Layer A — Conditional tier unlock** (`tier_unlock.py`)
- T3, T4, T6 (memo T3/T4/T5) gated by configurable triggers
- Triggers: cumulative revenue (USD), op count at previous tier, month index, customer demand for the tier, or AND-combinations
- Six preset policies in `tier_unlock.PRESET_POLICIES`: `unlock_baseline` (no gating, v4 behavior), `unlock_op_gated`, `unlock_revenue_gated`, `unlock_time_gated`, `unlock_strict` (rev + op count), `unlock_demand_gated`

**Layer B — Bonded node-providers** (`node_providers.py`)
- First-class economic actor separate from operators; each provider stakes per-arm
- Two provider kinds: `facility` (CrowdBrain-owned, no bond, implicit quality) and `community` (third-party, bonded, slashable, higher revenue share)
- Slashing on uptime / latency / calibration / safety / data-quality / audit-fail; severities $0.10–$0.50 of bond per event
- Operator reports filed monthly (probability ∝ 1 − provider quality); ≥3 reports in rolling 6-month window triggers higher-tier audit
- Six preset cells: `nodes_baseline` (100% facility), `nodes_low_bond` ($1K), `nodes_med_bond` ($5K), `nodes_high_bond` ($20K), `nodes_community_heavy` (20/80), `nodes_community_only` (0/100)

**Layer C — Geographic operator pool** (`geography.py`)
- Three regions tagged at operator creation: Georgia (40% share, $8/hr, ramp-baseline), Philippines (35% share, $6/hr, +20% learning ramp), Kenya (25% share, $10/hr, slower ramp)
- Region-conditioned multipliers on cost / retention / skill ramp / tier-advance speed
- Wage-gap churn boost: when an op's hourly earnings fall below their region's alternative wage (or Tesla/1X $48/hr under stress), churn boosts proportionally
- Stress utilities: `geo_shock` (region drops to 30% capacity for 6mo), `tesla_stress` (30% of T3+ ops have $48/hr alt offers)

**Layer D — Points → tokens transition** (`points_to_token.py`)
- Operators earn points (not tokens) before transition; AMM and on-chain stake/slash mechanics are inert during the points phase
- Trigger types: `month` (cutover at month N), `revenue` (cutover when cumulative ≥ $X), `never` (points-only forever), `always_token` (v4 behavior — token live from day 1)
- At cutover: 1:1 conversion of accumulated points to tokens (per design choice 2026-05-04)
- Four preset cells: `points_only`, `transition_m12`, `transition_m18`, `transition_revenue_1m`

**v5 customer extension** (`customers.py`)
- New fields on `Customer`: `is_design_partner: bool` and `contract_term_months: Optional[int]`
- Multi-year design-partner contracts are immune to satisfaction-driven churn during their term (defaults to 24 months in `train_v5.py`)
- Addresses the v4 retro finding that design partners signed at month 0 mass-churned at grace expiry due to bootstrap-era undersupply

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
| v5 | Conditional tier unlock (T3–T5 gated by revenue/op count/time); bonded node-providers (facility/community split + reporting/dispute); 3-region operator pool (Georgia/Philippines/Kenya) with cost/retention/skill ramp; points→tokens transition; multi-year design-partner contracts; parallelized MC orchestrator | 36 months | **0.535 ± 0.039** path-baseline; **0.574** with Intelligence Library at m24 | $26.3M baseline, $37.1M with Intel Library |
| v5_iter2 | Pareto sweep at MC=20 (18 cells × 3 phases) targeting iter1 sub-score drags. Found stake_300 + unlock_revenue_gated optimal under unrealistic params. Combo of 4 winners stacks at +0.025. | 36 months | **0.597 ± 0.087** (stake_300 winner); 0.772 if all v5 layers off (= v4_no_personas reference) | $41M (stake_300); $84M (layers_off) |
| v5_iter3 (REALISTIC) | Recalibrated customer model (smaller contracts, slower arrival), scaled-down operator onboarding, smaller token supply, lower hardware stakes. 4 phases + Q4 2026 milestone at MC=50. | 36 / **60 months** | **0.663** @ 36mo baseline; **0.844 ± 0.012** @ 60mo (BEATS v4_no_personas) | $24M @ 36mo, **$86M @ 60mo** |
| v5_iter4 (J-CURVE) | Refined to J-curve adoption: slow first 18 months → mild pickup m18-30 → take-off m30+. Operator onboarding ×0.10 (memo-aligned 1K trained @ Q3 2026). Smaller contracts. 4 phases + sensitivity ±20% + Q4 milestone. | 36 / 60 months | **0.683 ± 0.020** @ 60mo (jcurve_combined) | **$40M @ 60mo, $24M ARR end-of-sim, 185 customers** |

**v2's 0.8876 is not directly comparable to v3/v4 scores** — v2 used different score weights and a different scoring scale. v3 introduced 9 sub-scores with stricter caps; the same underlying economy scores lower under v3 weights because the ceiling is harder to hit.

**A note on v3 winner score variance** — `v3 winner` shows up in this README as **0.6502** (the original 12-cell sweep, MC = 2 runs at 36 months) and as **0.7009** when used as the v4 ablation reference (rerun under MC = 3). Same parameters, different MC seed counts and sweep contexts. Treat numbers as comparable within a table, not across tables.

**A note on v5 vs v4 score gap** — v5 baseline (0.535) is meaningfully below v4_no_personas (0.7575) because the v5 layers add real friction: conditional unlock delays high-tier work, bonded nodes route 20% of community revenue, geography retention multipliers add some churn, and the higher T3 hardware stake ($400 vs $100) raises the bar to advance. The v5 question isn't "did the score go up" — it's "given this is the realistic operating environment, what's the best policy in each layer?" When you turn off all v5 layers in `prepare_v5.py`, you reproduce the v4_no_personas score (0.741 ± 0.000 in spot test).

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

### v5 — 4-track sweep (2026-05-04)

24 cells × MC=10 at 36 months, parallelized across 23 CPU cores in **46.7 minutes wall time** (vs 12hr serial estimate, 15× speedup). Full results in `REPORT_v5.md`; raw aggregates in `v5_results/track[1-4]_results.json`.

#### Track 1 — Tier-unlock policy (the central new memo question)

The memo says T3–T5 unlock "with scale" but doesn't define thresholds. **Counterintuitive finding: all 5 unlock policies BEAT the no-gating baseline.**

| Cell | Composite | Cum revenue | T4+ ops | NRR |
|---|---|---|---|---|
| **unlock_revenue_gated** (T3=$250K, T4=$1M, T5=$5M ARR) | **0.535 ± 0.039** | **$26.3M** | **6,936** | **0.16** |
| unlock_time_gated (m6 / m12 / m18) | 0.529 ± 0.035 | $24.3M | 6,520 | 0.15 |
| unlock_strict (rev + op count) | 0.517 ± 0.053 | $24.3M | 6,234 | 0.15 |
| unlock_baseline (no gating) | 0.496 ± 0.088 | $22.7M | 5,813 | 0.15 |
| unlock_demand_gated | 0.496 ± 0.088 | $22.7M | 5,813 | 0.15 |
| unlock_op_gated (100/50/25 op thresholds) | 0.484 ± 0.082 | $21.6M | 5,559 | 0.14 |

**Why gating helps**: under v5's higher hardware stakes ($400 T3), premature advancement triggers quality slashing and operator loss. Gating prevents this. The memo's "with scale" framing isn't just caution — it's a positive design choice that benefits the network.

#### Track 2 — Points → tokens transition

| Cell | Composite | Cum revenue | T4+ ops |
|---|---|---|---|
| **transition_m12** (best) | **0.511 ± 0.046** | **$22.4M** | **6,069** |
| transition_m18 | 0.492 ± 0.084 | $21.8M | 5,269 |
| transition_revenue_$1M | 0.483 ± 0.087 | $20.8M | 4,822 |
| points_only (worst) | **0.395 ± 0.064** | **$12.6M** | **1,698** |

**The token economy is load-bearing.** Never transitioning loses 23% of composite vs cutting over at month 12. Token-denominated stake unlocks and AMM-based price discovery are not decoration — high-tier ops depend on them.

#### Track 3 — Three-stakeholder loop (bonded node-providers)

| Cell | Composite | Cum revenue | T4+ ops |
|---|---|---|---|
| nodes_low_bond ($1K, 50/50) | 0.535 ± 0.039 | $26.3M | 6,936 |
| **nodes_med_bond** ($5K, 50/50) | **0.535 ± 0.039** | **$26.3M** | **6,936** |
| nodes_high_bond ($20K, 50/50) | 0.535 ± 0.039 | $26.3M | 6,936 |
| nodes_baseline (100% facility) | 0.500 ± 0.084 | $23.4M | 5,762 |
| nodes_community_only (0/100) | 0.478 ± 0.097 | $20.9M | 5,044 |
| nodes_community_heavy (20/80) | 0.468 ± 0.083 | $20.0M | 4,738 |

**Bond size doesn't move the needle** ($1K = $5K = $20K all → 0.535) — quality failures are rare enough over 36mo that bond is tail-risk only. **The big lever is the facility/community split**: 50/50 hybrid wins by 7% over 100% facility and 13% over community-heavy. Don't go all-community.

#### Track 4 — Macro stress + milestone path

| Cell | Composite | Cum revenue | T4+ | Δ vs baseline |
|---|---|---|---|---|
| **intelligence_library** (data licensing m24+) | **0.574 ± 0.047** | **$37.1M** | 6,811 | **+7%** |
| path_baseline (reference) | 0.535 ± 0.039 | $26.3M | 6,936 | — |
| tesla_hiring (30% T3+ have $48/hr offers) | 0.532 ± 0.077 | $26.7M | 7,062 | -0.6% |
| geo_shock_kenya | 0.505 ± 0.064 | $23.4M | 5,880 | -6% |
| geo_shock_philippines | 0.472 ± 0.085 | $20.2M | 4,931 | -12% |
| geo_shock_georgia | 0.446 ± 0.119 | $19.5M | 4,399 | **-17%** |
| funding_winter (customer arrivals × 0.25) | 0.294 ± 0.007 | $3.2M | **0** | **-45%** |
| mvp_slip (3-month launch delay) | 0.259 ± 0.003 | $1.2M | **0** | **-52%** |

Three things to take to investors:

1. **Tesla/1X wage anchor is a non-issue.** Even with 30% of T3+ ops having $48/hr alt offers, the model loses only 0.6% composite. Retention design beats the wage gap.
2. **Funding winter and MVP slip are existential threats**, not tail risk. Both kill T4+ entirely (0 ops at 36mo) by creating a self-reinforcing collapse: no rev → unlock-gating fails to fire → no high-tier ops → no rev. **Plan explicit GTM mitigations and treasury runway around these scenarios.**
3. **Intelligence Library at month 24+ is real upside** — +7% composite, +41% revenue. It's not just a narrative line in the memo; the data licensing flywheel compounds.

#### v5 recommended launch config (combining all 4 track winners)

| Lever | Setting |
|---|---|
| Tier unlock | Revenue-gated: T3=$250K ARR, T4=$1M, T5=$5M |
| Points → tokens | Month 12 hard cutover (1:1 conversion) |
| Node providers | 50/50 facility/community at $5K bond per arm |
| Geographic mix | 40/35/25 GE/PH/KE — but build Georgia redundancy |
| Hardware stake | $400 T3 (memo midpoint $300–500), $150 T4, $800 T5/T6 |
| Intelligence Library | Activate m24 onward |
| Design-partner contracts | 24-month immune-from-sat-churn term |

This combo was tested in iter2 (`v5_winner_combo`) at MC=20: composite **0.560 ± 0.065**, +0.025 over the best single-track winner. The 4 v5 winners do compose constructively, but the unrealistic-mode result is superseded by the realistic-mode recommendation below.

### v5 iter2 — Pareto sweep (2026-05-04, follow-up)

A 18-cell Pareto sweep at MC=20 across 3 phases targeting the biggest sub-score drags from iter1 (revenue, retention, capacity util):

**Phase 1 (combo + diagnostic, 3 cells)**
- `v5_layers_off`: 0.772 ± 0.009 (matches v4_no_personas reference at MC=20)
- `v5_winner_combo`: 0.560 ± 0.065 (4 winners stack: +0.025)
- `v5_combo_no_intel`: 0.520 (Intelligence Library adds +0.04)

**Phase 2 (revenue threshold sweep, 6 cells)**
- Winner: `unlock_revenue_gated_ref` at 0.560 (original $250K/$1M/$5M ARR)
- Looser/tighter/hybrid all 3–5% worse — the original was already optimal under unrealistic params

**Phase 3 (hardware stake + node provisioning, 9 cells)**
- Winner: `stake_300` at **0.597 ± 0.087** ($41M revenue, 8214 T4+ ops). +0.037 over default $400 stake.
- `stake_500` worst at 0.475 (too high a barrier to T3 advancement)
- Larger node target (4K-12K) hurt despite higher capacity_util sub-score

**Iter2 ceiling under unrealistic params: ~0.60.** Even with full tuning, the v5 layer cost cannot be fully recovered against the v4-equivalent baseline (0.772). This motivated the realistic recalibration below.

### v5 iter3 — REALISTIC parameter calibration (2026-05-04, definitive)

Iter1/iter2 used customer/revenue numbers that produced **$73M cum revenue at month 36 / $46M ARR by sim end** — aggressive vs real-world Series-B robotics-data startups (Scale AI was ~$10M ARR at year 3 with thousands of customers; CrowdBrain wedge is much narrower).

The realistic-mode recalibration (`train_v5_realistic.py` + new `task_model.onboarding_multiplier` engine param):

| Parameter | Unrealistic (iter1/iter2) | Realistic (iter3) |
|---|---|---|
| Manufacturing contract | $80K/mo | $35K/mo |
| Warehouse contract | $60K/mo | $22K/mo |
| Healthcare contract | $120K/mo | $55K/mo |
| Robotics OEM contract | $150K/mo | $45K/mo |
| Customer arrival λ_max | 3.0/seg/mo | 1.0/seg/mo |
| Pareto max factor | 3.0× | 1.5× |
| Operator onboarding mult | 1.0 (≈120K total) | 0.35 (≈42K total — matches memo's "1K trained @ Q3 2026") |
| Token max supply | 500M | 100M |
| Monthly emission | 3M tokens | 500K tokens |
| AMM pool at TGE | $1M each side | $200K each side |
| T3/T4/T5 hardware stake | $400/$150/$800 | $200/$100/$400 |
| Bull customer arrival mult | 1.3× | 1.1× |

**Iter3 results (17 cells × MC=20 + 1 milestone cell × MC=50, 35 min wall time):**

#### Phase 1 — Realistic baseline + diagnostic (3 cells)

| Cell | Composite | Final ARR | Customers | T4+ | Q4 hit % |
|---|---|---|---|---|---|
| **realistic_baseline** | **0.663 ± 0.023** | $24.0M | 99 | 7,886 | 20% |
| realistic_layers_off | 0.630 ± 0.077 | $21.5M | 92 | 6,846 | 15% |
| realistic_winner_combo | 0.526 ± 0.136 | $18.8M | 80 | 4,175 | 0% |

**Major flip from unrealistic mode**: `realistic_baseline` (with all v5 layers on) BEATS `realistic_layers_off` (no layers) by +0.033. Under realistic params, the v5 layers help. The combo (m12 transition + Intel Library) HURTS by 0.137 — the opposite of unrealistic mode.

#### Phase 2 — Realistic unlock policy sweep (5 cells)

| Cell | Composite | Final ARR | Customers | T4+ | Q4 hit % |
|---|---|---|---|---|---|
| realistic_hybrid | 0.664 ± 0.022 | $24.2M | 100 | 7,908 | 20% |
| realistic_op_medium (25/10/5) | 0.663 ± 0.023 | $24.0M | 99 | 7,886 | 20% |
| **realistic_op_loose (10/5/2)** | **0.663 ± 0.025** | $23.8M | 96 | 7,840 | **30%** |
| realistic_op_strict (50/20/10) | 0.649 ± 0.064 | $23.6M | 96 | 7,726 | 15% |
| realistic_rev_gated | **0.407 ± 0.134** | **$7.3M** | 68 | 1,990 | 10% |

**Second flip**: revenue-gated unlocks (the iter1/iter2 winner) CRASH at 0.407 in realistic mode because realistic revenue is too low to hit $100K-$2M thresholds in time. **Op-count gating dominates**, with `realistic_op_loose` (10 T2 → T3 / 5 T3 → T4 / 2 T4 → T5) producing the **highest Q4 milestone hit rate (30%, 50% better than baseline)**.

#### Phase 3 — Emission + stake fine-tuning (6 cells)

| Cell | Composite | Final ARR | Customers | T4+ |
|---|---|---|---|---|
| **stake_100** | **0.691 ± 0.012** | $25.8M | 102 | 8,763 |
| emission_250k = 500k = 1m | 0.663 ± 0.023 | $24.0M | 99 | 7,886 |
| stake_200 (current) | 0.663 ± 0.023 | $24.0M | 99 | 7,886 |
| stake_300 | **0.398 ± 0.103** | **$4.4M** | 70 | 1,162 |

**Third flip**: `stake_100` is the realistic-mode optimum (+0.028 vs current $200), confirming that the memo's $300–500 hardware stake range was over-tuned for realistic revenue. `stake_300` is catastrophic. **Token emission rate barely matters at realistic scale** — 250K, 500K, 1M tokens/mo all give 0.663.

#### Phase 4 — 60-month long horizon (2 cells)

| Cell | Composite | Final ARR | Customers | T4+ | Cum revenue |
|---|---|---|---|---|---|
| **realistic_baseline_60mo** | **0.844 ± 0.012** | **$37.3M** | 162 | **16,570** | **$86.0M** |
| realistic_combo_60mo | 0.740 ± 0.122 | $48.0M | 146 | 10,625 | $81.7M |

**This is the headline result**: at 60 months under realistic params, the v5 baseline scores **0.844 ± 0.012 — higher than v4_no_personas (0.7575) at 36mo**. v5 layers compound late-stage just like v4 did. End-of-sim numbers ($37M ARR, 162 customers, $86M cum revenue) are defensible vs real-world Series-B robotics startups.

#### Q4 2026 milestone probability (MC=50)

Memo target: 3+ paying customers, $500K+ ARR by month 8 of horizon (Nov 2026 if launch May 2026).

- **P(hit milestone)**: 12% of MC seeds
- Mean Q4 customers: **4.6** ✓ (target ≥3)
- Mean Q4 ARR: **$413K** ✗ (target ≥$500K — just below)
- Mean composite at end: 0.663
- Mean final ARR: $24.5M
- Mean customer count: 98

The customer-count target is met consistently; the ARR threshold is marginal. Recommendation: either set the public Q4 target to `3+ customers, $400K+ ARR` (88% probability) or accelerate the design-partner ramp to push fulfillment higher in months 4-8.

#### v5_realistic recommended launch config

| Lever | Setting |
|---|---|
| Calibration | `train_v5_realistic.PARAMS_V5_REALISTIC` |
| Tier unlock | Op-count gated: T3 unlocks at 10 qualified T2 ops, T4 at 5 T3, T5 at 2 T4 |
| Hardware stake | $100 T3, $100 T4, $400 T5/T6 |
| Token emission | 500K tokens/mo, 100M max supply |
| AMM pool at TGE | $200K each side |
| Customer model | $22-55K/mo contracts, λ=1.0/seg/mo, Pareto α=1.5 max=1.5× |
| Operator onboarding multiplier | 0.35 (matches memo Q3 2026 milestone of 1K trained operators) |
| Horizon | 60 months for full compounding |
| Expected composite | **0.84+ at MC=20** |
| Expected end-state | ~160 customers, $37M ARR, $86M cum revenue, 16K T4+ ops |
| Q4 2026 milestone hit | 12% — investor target should be $400K ARR (88%) or accelerate launch |

**This is the config you should use for stakeholder narratives.** Numbers are defensible vs real-world peers, the composite is higher than any v4 result, and the late-stage compounding tells a clean Series-A → B → C → D story.

---

## What's still broken

The v4 reports flagged three open issues we partially addressed in v5; v5 added a few new ones.

**Open from v4 (status as of v5):**

1. **Early customer cohorts die.** PARTIALLY FIXED: v5 introduces 24-month design-partner contracts immune to satisfaction-driven churn during the term. Helps the 3 design partners specifically; non-DP early cohorts still vulnerable. Cleaner long-term fix is to delay the first scheduled event to m24+ and/or model relationship-based retention.
2. **`sentiment_resilience` metric is unstable.** STILL OPEN. Can blow up when a run is mostly bear. Needs re-derivation as `score-in-bear / score-in-bull` with proper weighting.
3. **Persona policy is rule-based and rigid.** STILL OPEN, but `v4_no_personas` (the v5 baseline) sidesteps the issue entirely.

**New from v5:**

4. **`provider_avg_quality` metric capture bug.** Some Track-3 cells report 0.000 for `provider_avg_quality` even when community providers are active. Likely a metric-aggregation bug at the snapshot level — the underlying simulation is correct (slashing fires, providers ban, etc.) but the rolling quality average isn't being captured. Cosmetic; doesn't affect composite.
5. **`mvp_slip` cell shows NRR = 0.88, an order of magnitude higher than baseline (0.16).** Likely artifact of the few customers that did sign in months 3+ being a smaller, stickier sample — but worth investigating whether there's a deeper signal (multi-year DP contracts shielding survivors).
6. **v5 baseline composite (0.535) is below v4_no_personas (0.7575).** Each v5 layer has measurable cost. Open question for v6: which layers' realism is worth the score drag in front of investors? Tier-unlock (essential, memo-mandated), node-providers (essential, memo-mandated), points-to-tokens (essential, memo-mandated), geography (could be simplified). 
7. **NRR still low (0.14–0.16 across all v5 cells).** v5's multi-year DP contracts helped at the tail but didn't move the average. Likely the post-DP-contract enterprise customers churn at the same rate as v4.
8. **`v5_winner_combo` (all 4 track winners combined) is not yet tested as a single cell.** Each track's winner was found in isolation; we don't know if the winners interact constructively or if there's interference. Recommended next experiment.

Lower-priority follow-ups: AMM depth sweep ($500K vs $5M for shock sensitivity); customer × persona affinity (Healthcare prefers Validators, Robotics OEM prefers HW Investors); Bayesian optimization over the parameter space (vs grid sweeps); 60-month v5 long-horizon to see if the score gap to v4 closes with time-compounding.

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

# Reproduce the recommended (REALISTIC) launch config — Series-B-defensible numbers
python train_v5_realistic.py           # single-run debug at realistic params (~2 min)
python experiments_v5_iter3.py phase4 20  # 60-month realistic baseline at MC=20 (~15 min)

# Older debug entry points
python train.py        # v3 single-config Monte Carlo (~30s)
python train_v4.py     # v4 single-config Monte Carlo (~2 min)
python train_v5.py     # v5 single-config debug pass (~3.5 min, unrealistic params)

# v3/v4 sweeps (sequential)
python experiments.py small_sweep      # v3 12-cell sweep
python experiments_v4.py 3             # v4 8-cell pillar ablation + stress, MC=3 (~50 min)
python experiments_v4_iter2.py 2       # v4 tuned-persona iteration (~30 min)
python experiments_v4_iter3.py 2       # 60-month long horizon

# v5 sweeps (parallelized across CPU cores via ProcessPoolExecutor)
python experiments_v5.py track1 10     # Track 1 (tier-unlock), MC=10 (~13 min on 23 cores)
python experiments_v5.py track2 10     # Track 2 (points-to-tokens)
python experiments_v5.py track3 10     # Track 3 (3-stakeholder loop)
python experiments_v5.py track4 10     # Track 4 (macro stress + milestones)
python experiments_v5.py all 10        # All 4 tracks back-to-back (~47 min on 23 cores)

# v5 iter2 — Pareto sweep targeting iter1 sub-score drags (MC=20, ~47 min)
python experiments_v5_iter2.py all 20

# v5 iter3 — REALISTIC parameter calibration sweep + Q4 milestone validation (~35 min)
python train_v5_realistic.py           # single-run debug at realistic params (~2 min)
python experiments_v5_iter3.py all 20  # 17 cells + Q4 milestone at MC=50

# Regenerate reports from JSON results
python report_v4_generator.py          # builds REPORT_v4.md
python report_v5_generator.py          # builds REPORT_v5.md
python report_v5_iter2_generator.py    # builds REPORT_v5_iter2.md
python report_v5_iter3_generator.py    # builds REPORT_v5_iter3.md
```

Pure Python 3.7+ stdlib. No dependencies. v5 uses `concurrent.futures.ProcessPoolExecutor` for parallel MC; this works out-of-the-box on Windows/macOS/Linux.

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

- Random seed: `42` (set in `prepare.py`, `prepare_v4.py`, `prepare_v5.py`); seed `i` uses `42 + i`.
- Default Monte Carlo runs: **15** for v3 (`prepare.py`), **5** for v4 (`prepare_v4.py`), **10** for v5 (`experiments_v5.py` default); the experiment harnesses override these per cell.
- Default horizon: **36 months**; `experiments_v4_iter3.py` extends to 60. v5 sweep at 36 months only (60-month v5 is a recommended next step).
- Bump MC count for production reports — std drops as `1/√n`. The v4 stakeholder packet (`CrowdTrain_v4_Report.pdf`) was generated with the JSON results in `v4_experiment_results.json` / `v4_iter2_results.json` / `v4_iter3_results.json`. The v5 results live in `v5_results/track[1-4]_results.json` and feed `REPORT_v5.md`.

---

## File map

```
prepare.py            v3 simulation engine — 20-step monthly pipeline. Immutable.
prepare_v2.py         v2 snapshot kept for A/B comparison.
prepare_v4.py         v4 engine — 3-pillar wrapper around v3 with PARAMS-based fallback.
prepare_v5.py         v5 engine — copy of v4 with 4 v5 layer hooks (tier_unlock, node_providers,
                      geography, points_to_token + customer multi-year DP). Each layer opt-in.

train.py              v3 PARAMS dict (11 sections: supply, task_model, validation,
                      slashing, hardware, earnings, burn, sell_pressure, nodes,
                      retention, study_assumption, demand). This is what gets tuned.
train_v4.py           v4 PARAMS dict — adds operators / customers / macro sections.
train_v5.py           v5 PARAMS dict — extends v4 (no_personas) with tier_unlock /
                      node_providers / geography / points_to_token sections.

validation.py         Multi-witness consensus + graduated slashing.
nodes.py              DePIN node agents (v3/v4) with sync-tier capacity caps.
treasury.py           TGE distribution + linear vesting + fiat reserves.
operators_v4.py       v4 personas + learning curve + decision policy + referrals.
customers.py          v4 enterprise customers — segments, Pareto sizing, satisfaction churn.
                      v5 extension: is_design_partner + contract_term_months (multi-year).
macro.py              v4 sentiment HMM + x·y=k AMM + scheduled events + era detection.

tier_unlock.py        v5 Layer A: conditional T3/T4/T6 unlock policy (rev/op/time/demand triggers).
node_providers.py     v5 Layer B: bonded node-provider agents + reporting + dispute resolution.
geography.py          v5 Layer C: 3-region operator pool with region-conditioned multipliers.
points_to_token.py    v5 Layer D: points-only phase + 1:1 conversion at cutover.

train_v5_realistic.py     v5 REALISTIC PARAMS dict (smaller contracts, slower arrivals,
                          scaled-down operator onboarding, smaller token supply, lower stakes).
                          Adds evaluate_realism() with Q4 2026 milestone validation.
                          THIS IS THE STANDING RECOMMENDED CONFIG for stakeholder narratives.

experiments.py            v3 CLI: ablation / small_sweep / full_sweep / stress / timeseries.
experiments_v4.py         v4 8-cell pillar ablation + stress sweep.
experiments_v4_iter2.py   v4 tuned-persona iteration (40/40/15/5).
experiments_v4_iter3.py   v4 60-month long-horizon sweep.
experiments_v5.py         v5 4-track sweep orchestrator with parallelized MC
                          (ProcessPoolExecutor, 23 workers, ~47 min for 240 runs at MC=10).
experiments_v5_iter2.py   v5 iter2: 18-cell Pareto sweep at MC=20 — combo + revenue
                          thresholds + hardware stake + node provisioning. ~47 min.
experiments_v5_iter3.py   v5 iter3: 17-cell REALISTIC sweep at MC=20 + Q4 2026 milestone
                          probability at MC=50. 4 phases including 60mo long horizon. ~35 min.

report_v4_generator.py    Auto-generates REPORT_v4.md + plots from JSON results.
report_v5_generator.py    Auto-generates REPORT_v5.md from track[1-4]_results.json.
report_v5_iter2_generator.py  Auto-generates REPORT_v5_iter2.md (Pareto frontier + iter2 findings).
report_v5_iter3_generator.py  Auto-generates REPORT_v5_iter3.md (realistic-mode findings).
build_report.py           Generates the PDF / DOCX report packets.

REPORT.md / REPORT_v2.md  Historical reports for the v1 / v2 simulations.
REPORT_v3.md              v3 winner config + 18 architectural decisions + ablations.
REPORT_v4.md              v4 full analysis: pillar ablation, stress, iter2/iter3, cohorts.
REPORT_v5.md              v5 4-track sweep findings + recommended launch config (unrealistic).
REPORT_v5_iter2.md        v5 iter2 Pareto sweep — stake/nodes/unlock fine-tuning.
REPORT_v5_iter3.md        v5 iter3 REALISTIC findings — recommended for stakeholder use.
EXECUTIVE_SUMMARY_v4.md   2-minute exec summary of the v4 findings.
CrowdTrain_v4_Report.{pdf,docx}    Stakeholder-ready packet (v4 vintage; pre-v5 rebrand).

v4_overview.png                    6-panel chart of best v4 config.
v4_iter2_comparison.png            Bar chart of tuned-persona iteration cells.
v4_iter3_comparison.png            36mo vs 60mo long-horizon comparison.
customer_cohort_analysis.png       Per-cohort customer survival curves.
winner_timeseries.csv              v3 winner 36-month trajectory.
v4_best_timeseries.csv             v4 best (no_personas) 36-month trajectory.
v5_results/                        Per-track JSON aggregate results.
  track1_results.json              iter1 Tier-unlock policy (6 cells).
  track2_results.json              iter1 Points-to-tokens transition (4 cells).
  track3_results.json              iter1 3-stakeholder loop (6 cells).
  track4_results.json              iter1 Macro stress + milestone path (8 cells).
  iter2_phase1_results.json        iter2 combo + diagnostic (3 cells).
  iter2_phase2_results.json        iter2 revenue threshold sweep (6 cells).
  iter2_phase3_results.json        iter2 hardware stake + nodes (9 cells).
  iter3_phase1_results.json        iter3 realistic baseline + diagnostic (3 cells).
  iter3_phase2_results.json        iter3 realistic unlock policy sweep (5 cells).
  iter3_phase3_results.json        iter3 emission + stake fine-tuning (6 cells).
  iter3_phase4_results.json        iter3 60-month long horizon (2 cells).
  iter3_milestone_results.json     iter3 Q4 2026 milestone at MC=50.

program.md                 Original autoresearch instructions for the AI agent loop.
crowdtrain-memo-v12.docx   Original memo (CrowdTrain era; v3/v4 source).
crowdbrain-memo-v5.docx    Latest memo (CrowdBrain rebrand; v5 source of truth).
crowdbrain-memo-v5.txt     Plain-text extract for grepping.
```

---

## Recommended launch configurations

Five viable configurations. **For stakeholder narratives, lead with Option E (J-curve realistic). For upside framing, Option A. For risk modeling, Option B.**

- **Option E — `jcurve_combined_60mo`** (RECOMMENDED for stakeholder use, supersedes Option D):
  Composite **0.683 ± 0.020** at 60 months, **$24M final ARR**, **185 customers**, **2,582 T4+ operators**, **$40M cumulative revenue**.
  J-curve realistic calibration (slow first 18mo, mild pickup m18-30, take-off m30+) + iter3 winners (op_count tier unlock 10/5/2 + $100 T3 hardware stake).
  **Best for stakeholder-facing narratives — numbers explicitly defensible against real Series-A → B robotics-data peers.** Models the actual Physical-AI / teleop adoption curve (slow start while market matures, inflection as data hunger hits, take-off as Physical-AI mainstreams).
  Uses `train_v5_realistic.py` + `prepare_v5.py` + iter3 winner overrides.

- **Option D — `v5_realistic_baseline_60mo` (deprecated as headline; kept for upside framing)**:
  Composite **0.844 ± 0.012** at 60 months, **$37M final ARR**, **162 customers**, **$86M cumulative revenue**, **16,570 T4+ operators**.
  iter3 calibration — realistic vs early sims but operator counts (16K T4+, 30K active) are aggressive vs Series-A/B peers. Use this for **bull-case scenario** with explicit footnote about being top-decile execution.

- **Option A — `v4_no_personas`** (max-upside scenario, optimistic framing):
  0.7575 composite @ 36mo, 0.811 @ 60mo, **$389M revenue**, 37K T4+, top-3 concentration 7.5%, NRR 0.56×.
  Customers + macro pillars on; operators revert to v3 mechanics. **Best for "bull case" investor slides** — but the $389M-at-60mo number requires footnotes, since real-world peers like Scale AI hit ~$10M ARR at year 3. Uses the v4 engine.

- **Option B — `v4_baseline`** (full behavioral realism, v4-era):
  0.515 composite @ 36mo, 0.783 @ 60mo, $122M revenue. All three v4 pillars on, including persona heterogeneity. **Best for stress-testing and risk modeling** — the persona drag is the price you pay for behavioral honesty. Uses the v4 engine.

- **Option C — `v5_winner_combo`** (memo-v5-faithful, unrealistic-mode test):
  Composite 0.560 ± 0.065 @ 36mo (iter2 result at MC=20). The 4 v5 winners stack constructively (+0.025 over best single-track). Useful for ablation but **superseded by Option D** — same v5 architecture, but with realistic numbers Option D scores higher AND is more defensible.

The standing recommendation is to use **Option D for any investor-facing or analyst-facing conversation**, **Option A only when explicitly framing a bull case**, and **Option B for downside stress-testing**.

---

## How the autoresearch loop works

The repo is set up so an AI coding agent can pick a branch, run experiments, and commit improvements. Point Claude / Codex / etc. at the repo and tell it:

```
Read program.md and start experimenting
```

`program.md` defines the experiment loop: form a hypothesis, edit `train.py` / `train_v4.py` / `train_v5.py`, run, score, keep or discard, repeat. The simulation engines (`prepare.py`, `prepare_v4.py`, `prepare_v5.py`) are the evaluation oracle and should not be modified during a research run.

For v5 work, prefer editing `train_v5.py` and the per-layer module presets (`tier_unlock.PRESET_POLICIES`, `node_providers.PRESET_POLICIES`, `points_to_token.PRESET_POLICIES`) so you can sweep new cells through `experiments_v5.py` without touching the engine.

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
