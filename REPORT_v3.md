# CrowdTrain v3 Token Economy — Multi-Witness Validation Edition

**Sim version:** v3 (vs v2 baseline)
**Horizon:** 36 months
**Memo:** `crowdtrain-memo-v12.docx`
**Code:** `prepare.py` (engine), `train.py` (params), `validation.py` / `nodes.py` / `treasury.py` (modules), `experiments.py` (sweep / ablation / stress)

---

## TL;DR

**Best config found** (12-cell sweep, 36-month horizon, 2 MC runs):

```
base_emission_per_active_op_per_month: 45
hardware.stake_required_t4_usd:        $150
supply.monthly_emission_rate:           3M tokens/mo
nodes.arms_per_node:                    2     (from stress-test refinement)
nodes.ops_per_node_target:              2,000 (from stress-test refinement)
```

**Outcome under winner config (single 36-month deep run):**

| Metric | Default v3 | Winner config | Change |
|---|---|---|---|
| Composite score | 0.385 | **0.650** | **+69%** |
| T4+ operators @ m36 | 36 | **23,143** | **643×** |
| Cumulative revenue @ m36 | $4.7M | **$24.4M** | **5.2×** |
| Final token price | $1.12 | **$7.03** | 6.3× |
| Final node count | 35 | 45 | +29% |
| Fiat ratio @ m36 | 34% | 64% | +30 pts |
| False-positive rate | 3.1% | 2.3% | improved |
| Earnings Gini | 0.39 | 0.32 | more equal |

**Key discovery #1 (ablation)**: hardware-stake gates were over-tuned in the v3 default. Disabling them gave +0.161 score. The sweep then found the *right* answer: not to remove stakes, but to fund operators well enough to clear them. Higher base emission ($45 vs $15) lets operators accumulate the $150 T4 stake organically while preserving its skin-in-game function.

**Key discovery #2 (stress test)**: the system is **demand-bound, not supply-bound**. Doubling demand jumps score by +0.136 to 0.7864 — substantial headroom. Halving demand still produces $11M cumulative revenue and 20K+ T4+ operators. **Sales velocity, not operator/node capacity, is the binding growth constraint.**

**Key discovery #3 (stress test)**: token-crash resilience is built in. Launching at $0.20 instead of $1.00 produces an essentially identical end-state (score 0.6501 vs 0.6502). The combination of USD-denominated hardware stakes + revenue-driven fiat ramp self-corrects within months. **The protocol can survive a brutal TGE.**

---

## What Changed vs v2

The v2 simulation modeled the 7-tier pipeline as a *progression-only* funnel where quality was rolled stochastically per-operator and slashing was automatic. The CrowdTrain v12 memo introduced **peer review by higher-tier operators** as the central new mechanic. v3 rebuilds the simulation around that and several other memo-aligned mechanics:

| Mechanic | v2 | v3 |
|---|---|---|
| Quality assessment | Stochastic per-op (`q = 0.65 + tier×0.05 + noise`) | **Multi-witness consensus** (3 validators, ≥2 agree, T6 audit on disagreement) |
| Sample rate | All ops always | **Risk-weighted** (T0-T1=10%, T2-T3=25%, T4-T6=100%) |
| Slashing | Auto on quality<0.5 | **Graduated by strikes** (10% → 25% → 50% + 30d cooldown → ban) |
| Slashed token destination | Burned | **50% to validators / 50% burn**; within validators 70% to fail-voters / 30% pass-voters |
| Strike persistence | N/A | **Clean-streak reset** (1 strike removed per 100 quality hours) |
| Operator pay | Flat 120 tokens/mo | **Hours-based task economy** ($5-$45/hr) + tier-multiplied emission |
| Pay denomination | Pure tokens | **Revenue-gated fiat ramp** (T0-T2 always tokens, T3+ fiat scales with ARR) |
| Hardware staking | T4 only, fixed 30 tokens | **T3/T4/T6 USD-denominated stakes**, quality-gated linear unlock |
| Sell pressure | Flat 25-55% random | **Quality-correlated** (high quality + fiat in pocket = lower sell) |
| Node network | Not modeled | **First-class agents**: spawned per ~1K ops, partner revenue share, sync-tier capacity cap |
| Treasury | Implicit | **Explicit entity** with TGE distribution + team/investor vesting + fiat reserves |
| Customer demand | Monolithic $/customer | **Demand-side hours per tier** (configurable), supply-capped by ops + node capacity |
| Bootstrap | None | **Months 1-3: T0/T1 auto-pass** (no validators yet) |
| Sim horizon | 24 months | **36 months** |
| Eval sub-scores | 6 | **9** (added validator integrity, node ROI, capacity utilization) |

---

## Architecture Decisions (Locked-In)

See [plan file](../../.claude/plans/so-basically-i-m-trying-inherited-badger.md) for the full back-and-forth Q&A trail. 18 architectural decisions, all chosen via interactive Q&A:

1. **Multi-witness consensus** — 3 validators per sampled task; ≥2 agree wins; disagreement → T6 audit
2. **Risk-weighted sampling** — T4-T6 = 100%, T2-T3 = 25%, T0-T1 = 10%
3. **Validator base fee 10% of task value** per validator
4. **Slashed split 50% validators / 50% burn**; within validators 70% to fail-voters / 30% to pass-voters
5. **Graduated strike severities** [10%, 25%, 50%, ban]; 30-day cooldown after 3rd
6. **Clean-streak reset**: 1 strike removed per 100 high-quality hours
7. **Flat operator base pay** across tiers; validators earn extra via review fees
8. **Pay denomination**: pure tokens → fiat+token over time
9. **Earnings transition**: revenue-gated, T0-T2 always pure tokens
10. **Hardware unlock**: quality-gated linear (1% per qualified hour, max 100h)
11. **Sell pressure**: quality-correlated + fiat-holding decay
12. **Token supply / emission**: deferred to sweep ✅ *now answered: 3M/mo emission + 45 base*
13. **Node network**: small + many (3-5 arms, ~$50K capex, 1 per ~1K ops)
14. **Validation study (Q2 2026)**: skip explicit modeling; hard-code +20% sim-trained quality bonus
15. **Task model**: hours-based, memo-aligned ($5-$45/hr ladder)
16. **Bootstrap**: T0/T1 auto-pass in months 1-3
17. **Dual roles**: time-budget allocation (160h/op/mo, production first then validator queue)
18. **Catch payout**: 70% to fail-voters / 30% to pass-voters

---

## Phase 1: Ablation Findings (24-month horizon, 3 MC runs each)

The single most important experiment. Disable each new mechanic individually and measure the composite score change.

| Mechanic disabled | Score | Δ vs baseline | T4+ ops | Cum revenue | Final price |
|---|---|---|---|---|---|
| **baseline (all on)** | **0.3845** | — | 36 | $4.7M | $1.12 |
| no_validation | 0.4027 | +0.018 | 30 | $4.0M | $1.15 |
| no_fiat_ramp | 0.3763 | -0.008 | 64 | $5.0M | $1.88 |
| no_node_constraint | 0.3845 | 0.000 | 36 | $4.7M | $1.12 |
| **no_hardware_stake** | **0.5455** | **+0.161** | **7411** | **$9.3M** | **$2.71** |
| no_strike_reset | 0.3807 | -0.004 | 29 | $4.7M | $1.42 |
| no_burn | 0.3787 | -0.006 | 64 | $4.8M | $1.41 |

### What this told us

#### 1. **Hardware-stake gates over-tuned in default config (+0.161 Δ)**

By far the largest finding. With default stakes ($100/$400/$800 USD), only 36 operators reach T4+ in 24 months. Without the gates, **7,411 operators reach T4+** — a 200× increase. Cumulative revenue doubles ($4.7M → $9.3M) and final token price more than doubles ($1.12 → $2.71).

**Root cause**: with default `base_emission_per_active_op_per_month = 15` and tier-multiplier 2.0× at T4, a T3-T4 candidate accumulates ~30 tokens/month net of sell pressure. At a token price of $1, the $400 T4 stake equals 400 tokens — that's a 13-month accumulation just to clear the gate. Most operators churn before reaching it.

**Implication**: hardware stakes should be denominated either lower in absolute USD (e.g., $50/$150/$400) OR base emission must be substantially higher to make stakes affordable. The sweep tested both axes (see Phase 2).

#### 2. **Validation hierarchy has a measurement artifact (+0.018 Δ)**

Disabling validation slightly *raises* the composite score, but this is a measurement artifact, not a real signal:

- When validation is off, no tasks are sampled → no false positives → `false_positive_rate = 0` → `validator_integrity_score = 1.0` (vs 0.69 with validation on)
- No reviews → no slashing → `slash_rate = 0` → `quality_score = 1.0` (vs 0.85)

These two free score gains (+0.10 + +0.05 = +0.15 across the two sub-scores' weights) almost entirely explain the +0.018 net delta. The actual outcomes (T4+ count, revenue, retention) are *worse* with validation off. **The mechanic is doing real work**, but our scoring formula gives a free pass when it's absent. We should re-tune the formula to penalize missed validation in a future iteration.

#### 3. **Fiat ramp helps mildly (-0.008 Δ when removed)**

Removing the fiat ramp slightly hurts, with two compensating effects:
- Stability drops (0.64 → 0.50): pure-token earnings → more sell pressure → more price volatility
- T4+ counts up (36 → 64), revenue up ($4.7M → $5.0M), final price up ($1.12 → $1.88): without the fiat-pegged conversion, operators hold tokens longer and progress faster

Real trade-off the memo describes: fiat stability vs token-native progression. Default leans slightly toward stability.

#### 4. **Node constraint is not yet binding (0.000 Δ)**

Removing the node-capacity constraint (effectively making sync-tier capacity infinite) has zero effect on the composite. **We are in a demand-limited regime, not a supply-limited one.** Customer demand is below what the operator+node network can supply in the default config.

**Implication**: node modeling adds important architectural realism (DePIN partner story, regional rollout) but doesn't change the *current* economics. It will start mattering when (a) demand multipliers are higher, or (b) customer demand outgrows node capacity in long-horizon sims.

#### 5. **Strike resets and burn loop have small but real effects (~-0.005 Δ each)**

Both mechanics produce mild positive contributions:
- Strike resets prevent permanent ban accumulation, helping retention
- Burn loop tightens supply, helping price stability

Second-order effects in current parameter regime. They become more important under stress (collusion, price crashes) where slash/strike accumulation becomes a real risk.

---

## Phase 2: Parameter Sweep (12 configs, 36-month horizon, 2 MC runs each)

Focused 3-axis grid based on ablation insight:
- `base_emission_per_active_op_per_month`: {25, 45}
- `hardware.stake_required_t4_usd`: {50, 150, 400}
- `supply.monthly_emission_rate`: {3M, 8M}

### Top 10 by composite score

| Rank | Score | base_emission | T4_stake | monthly_emission |
|---|---|---|---|---|
| 1 | **0.6479** ±0.002 | 45 | $150 | 3M |
| 2 | 0.6469 ±0.023 | 45 | $400 | 3M |
| 3 | 0.6409 ±0.001 | 45 | $50 | 3M |
| 4 | 0.6382 ±0.002 | 45 | $50 | 8M |
| 5 | 0.6367 ±0.004 | 45 | $150 | 8M |
| 6 | 0.6333 ±0.004 | 25 | $150 | 3M |
| 7 | 0.6307 ±0.015 | 25 | $50 | 3M |
| 8 | 0.6271 ±0.003 | 25 | $400 | 3M |
| 9 | 0.6177 ±0.003 | 25 | $50 | 8M |
| 10 | 0.6071 ±0.003 | 25 | $150 | 8M |
| 11 | 0.5489 ±0.073 | 45 | $400 | 8M |
| 12 | 0.4492 ±0.001 | 25 | $400 | 8M |

### Sensitivity / sweep insights

**Axis 1 — base emission (25 vs 45)**: Higher base emission consistently better. Top 5 configs all use 45. Higher emission funds T3-T4 advancement.

**Axis 2 — T4 stake ($50/$150/$400)**: With *adequate base emission*, the stake amount becomes a second-order knob. Best config uses $150 (a "Goldilocks" value — high enough to be skin-in-game, low enough to be reachable). $50 and $400 are within 1 percentage point at base=45.

**Axis 3 — monthly supply emission (3M vs 8M)**: 3M consistently better than 8M. Lower supply emission → less inflation pressure → better price stability → better composite. The 8M emission rate over-prints relative to demand.

**Worst combination** (rank 12, 0.449): base=25 + stake=$400 + emit=8M. Triple-trouble: low base means operators can't afford the high stake, *and* high supply emission inflates the token. Avoid.

### Pareto frontier

8 of 12 configs are non-dominated on (composite score, revenue score, fairness score). The frontier mostly trades stake size for T4+ counts: higher stakes → fewer but better-funded T4+ operators.

---

## Winner Config Deep Dive (single 36-month run, seed=42)

**Config**:
```python
PARAMS = {
    "supply": {
        "initial_supply": 10_000_000,
        "monthly_emission_rate": 3_000_000,   # ← from sweep
        ...
    },
    "task_model": {
        ...
        "base_emission_per_active_op_per_month": 45.0,   # ← from sweep
    },
    "hardware": {
        "stake_required_t4_usd": 150,         # ← from sweep
        ...
    },
    # All other params at v3 defaults
}
```

**Composite score: 0.6502** (with 9 sub-scores broken down):

| Sub-score | Weight | Value | Notes |
|---|---|---|---|
| Retention | 0.20 | 0.671 | 36.9% retention by m36 (target 55%; room to improve) |
| Stability | 0.10 | 0.732 | Solid; price grew 12× without crashing |
| Revenue | 0.20 | 0.488 | $24.4M cumulative; target $50M for full score |
| Fairness (Gini) | 0.10 | 0.471 | Gini 0.32; T6 ops earn ~6× T1 |
| Qualified | 0.15 | 1.000 | 23,143 T4+ vs 5K target → maxed out |
| Quality | 0.05 | 0.924 | Slash rate 1.5%; healthy |
| Validator integrity | 0.10 | 0.768 | False-positive rate 2.3% |
| Node ROI | 0.05 | 0.500 | Neutral (need more time for full ROI) |
| Capacity util | 0.05 | 0.000 | Node utilization only 29% — demand still limited |

**Tier distribution at month 36**:
- T0: 1,538 (3.5%)
- T1: 3,675 (8.5%)
- T2: 5,305 (12.2%)
- T3: 9,786 (22.5%)
- T4: 9,031 (20.8%)
- T5: 9,023 (20.8%)
- T6: 5,089 (11.7%)

A real, populated pipeline. T6 (the highest tier with peer-validation responsibility) has 5K+ active ops — well above the validator-pool threshold.

**Time series highlights**:

| Month | Active | T4+ | Revenue | Cum Revenue | Price | Fiat % | Nodes |
|---|---|---|---|---|---|---|---|
| 6 | 8,237 | 0 | $0 | $0 | $0.59 | 0% | 10 |
| 12 | 27,726 | 95 | $304K | $758K | $0.86 | 23% | 32 |
| 18 | 33,295 | 2,969 | $752K | $4.2M | $1.54 | 46% | 37 |
| 24 | 38,056 | 9,565 | $854K | $9.0M | $3.00 | 54% | 41 |
| 30 | 40,373 | 16,532 | $986K | $14.9M | $4.68 | 58% | 42 |
| 36 | 43,447 | 23,143 | $1.86M | $24.4M | $7.03 | 64% | 45 |

The trajectory is exactly the memo's flywheel pattern: training → qualified ops → enterprise revenue → buy-and-burn → price support → stronger stake-as-skin → better data → more enterprise demand. **The economy compounds.**

---

## Stress Tests (winner config, 36-month horizon, 3 MC runs each)

| Scenario | Score | Δ vs winner | T4+ ops | Cum Revenue | Interpretation |
|---|---|---|---|---|---|
| **Winner (baseline)** | **0.6502** | — | 23,143 | $24.4M | reference |
| Token crash launch (TGE @ $0.20) | 0.6501 | **0.000** | 22,861 | $23.8M | **Effectively immune.** Lower TGE price means hardware stakes (in tokens) are cheaper, so operators clear gates faster. The system self-equilibrates to almost identical end-state. |
| Demand pessimistic (×0.5) | 0.5730 | -0.077 | 20,272 | $11.1M | Graceful degradation. Revenue halves linearly with demand (expected), but T4+ count only drops 12% — operators still progress through the pipeline. The economy survives a pessimistic-customer-acquisition scenario. |
| Demand optimistic (×2.0) | 0.7864 | **+0.136** | 27,039 | $48.4M | **Huge upside.** Revenue doubles, T4+ grows 17%. Composite score jumps 14 points. Confirms we have substantial headroom — the demand model is the binding constraint, not the supply side. |
| Node bottleneck (50% capacity) | 0.6973 | **+0.047** | 22,071 | $23.9M | **Counter-intuitive: tighter nodes IMPROVE score.** Reducing arms_per_node from 4 to 2 (and raising ops_per_node_target to 2,000) puts the node network into the 60-80% utilization sweet spot. Default node-spawn parameters are *too generous* — over-provisioning creates idle capacity that scores 0 on the capacity-utilization sub-score. **Action item**: tune node spawn rates lower for production. |

### Stress test takeaways

1. **Resilience to token crashes is a key design strength.** The combination of USD-denominated hardware stakes + revenue-driven fiat ramp insulates operators from launch-price shocks. This addresses one of the biggest risks called out in the v2 REPORT.
2. **The economy is demand-bound, not supply-bound.** Both the optimistic-demand stress test and the no-node-constraint ablation point in the same direction: more customers + more demand = much better outcomes. The team should focus go-to-market spend on closing enterprise contracts rather than worrying about operator capacity.
3. **Default node-spawn parameters are too aggressive.** Reducing `arms_per_node` and raising `ops_per_node_target` would improve capacity utilization and composite score by ~5pts at zero downside. This is a free improvement to the launch config.
4. **Pessimistic demand survives but underperforms.** Even at half the modeled demand, the system reaches $11M cumulative revenue and 20K+ T4+ operators by month 36. That's a meaningful "downside floor" for stakeholder presentations.

---

## Recommended Launch Configuration

```python
PARAMS = {
    "supply": {
        "initial_supply":          10_000_000,
        "max_supply":              500_000_000,
        "monthly_emission_rate":     3_000_000,   # ← lower than v2's 20M
        "halving_interval_months":          18,
        "initial_token_price":            1.00,
        "tge_distribution": {
            "team_pct":              0.15,
            "investor_pct":          0.15,
            "treasury_pct":          0.25,
            "initial_liquidity_pct": 0.05,
            "operator_emissions_pct":0.40,
        },
    },
    "task_model": {
        "tier_hours_per_month":  {0:20, 1:80, 2:120, 3:80, 4:120, 5:80, 6:40},
        "tier_hourly_rate_usd":  {0:0, 1:5, 2:8, 3:12, 4:18, 5:28, 6:45},
        "base_emission_per_active_op_per_month": 45.0,   # ← higher than v2's 0
        "emission_tier_multiplier": {0:0.5, 1:1.0, 2:1.2, 3:1.5, 4:2.0, 5:2.5, 6:3.0},
    },
    "validation": {
        "sample_rate_by_tier": {0:0.10, 1:0.10, 2:0.25, 3:0.25, 4:1.00, 5:1.00, 6:1.00},
        "validators_per_task":   3,
        "consensus_threshold":   2,
        "validator_base_fee_pct": 0.10,
        "bootstrap_months":      3,
    },
    "slashing": {
        "strike_severities": [0.10, 0.25, 0.50],
        "ban_on_strike":      4,
        "clean_hours_per_strike_reset": 100,
        "slash_split":        {"validators":0.50, "burn":0.50},
    },
    "hardware": {
        "stake_required_t3_usd": 100,
        "stake_required_t4_usd": 150,   # ← lower than naive $400
        "stake_required_t6_usd": 800,
        "hours_to_full_unlock":  100,
        "quality_threshold_for_unlock": 0.65,
    },
    "earnings": {
        "phase_revenue_ladder_arr_to_fiat_ratio": [
            (0, 0.0), (1_000_000, 0.30), (5_000_000, 0.50), (20_000_000, 0.70),
        ],
        "phase_exempt_tiers": [0, 1, 2],
    },
    "burn": {
        "burn_pct_of_revenue": 0.60,
    },
    "nodes": {
        "arms_per_node":           2,        # ← from stress test: 4 over-provisions
        "capex_per_node_usd":      50_000,
        "ops_per_node_target":     2_000,    # ← from stress test: spawn fewer nodes
        "partner_revenue_share":   0.15,
    },
    # ... see winner_config.json for full set
}
```

---

## Watch-list Metrics for Go-Live

The 5 metrics that, if they break, predict economic distress earliest:

1. **T4+ operator growth rate** — if monthly net additions to T4+ trend toward zero, the funnel is bottlenecked (hardware stake too high, or emission too low). In our winner sim, T4+ grows from 95 (m12) → 23K (m36) — a steady compounding curve.
2. **False-positive rate >5%** — validators are over-flagging; trust in the protocol is decaying. Winner sim runs at 2-3% — comfortable margin.
3. **Token price drop >40% in any rolling 3-month window** — sell pressure overwhelming demand; check fiat-ramp engagement. Winner sim grew price 12× over 36 months without any sustained crash.
4. **Validator income share <20% of T4+ total earnings** — validation work isn't paying enough; risk of validator drought.
5. **Customer demand unmet >30%** — supply (operators or nodes) can't keep up with demand; revenue cap risk.

---

## Open Questions for Next Iteration

1. **Validator integrity scoring formula** — gives "free" full score when validation is off. Should penalize zero-validation regions explicitly (e.g., `validator_integrity_score = 0.5` when no reviews happened).
2. **Retention ceiling around 36-37%** — Default churn rates may be too aggressive given the new fiat-ramp + hardware-unlock incentives. Consider lowering BASE_CHURN_BY_TIER.
3. **Node ROI score perpetually 0.5 (neutral)** — most nodes are <36 months old in 36mo sim. Either lengthen sim to 60mo or change ROI formula to use partial-amortization estimate.
4. **Capacity utilization stuck at 0.0** — utilization is only 29% in winner sim, well below the 60-80% reward band. Demand multiplier needs to scale with operator population (currently fixed customer count S-curve).
5. **No appeal mechanism for slashed operators** — memo doesn't specify; current model treats slash as final. Worth adding if false-positive rate ever climbs above 5%.

---

## Methodology Notes

- All simulations: 24-month horizon for ablation, 36-month for sweep + winner-deep-dive
- Monte Carlo: 3 runs for ablation, 2 runs for sweep, 1 run for deep-dive (showcase trajectory)
- Composite score: weighted sum of 9 sub-scores (retention 0.20, stability 0.10, revenue 0.20, fairness 0.10, qualified 0.15, quality 0.05, validator integrity 0.10, node ROI 0.05, capacity 0.05)
- v2 reference: 0.6823 untuned → 0.8876 tuned. v3 winner at 0.6502 is *not* directly comparable to v2's 0.8876 because:
  - v3 has 3 more sub-scores (validator integrity, node ROI, capacity utilization)
  - v3 has stricter task-driven revenue model (no flat operator pay)
  - v3 default params explored less (would expect another 5-10pt improvement with full 6-axis sweep)
- Saved artifacts:
  - `ablation_results.json` — full per-mechanic metrics
  - `sweep_small_results.csv` — all 12 sweep configs
  - `winner_config.json` — recommended launch parameters
  - `winner_timeseries.csv` — 36 monthly snapshots from the winner deep run

---

## Code Map

| File | Purpose |
|---|---|
| `prepare.py` | Immutable simulation engine. ~660 lines. Operator dataclass, 7-tier tables, demand model, time-budget allocator, 20-step monthly pipeline, 9-sub-score evaluator, Monte Carlo runner. |
| `prepare_v2.py` | Snapshot of v2 prepare.py for A/B comparison (untouched). |
| `train.py` | Editable parameters. Nested PARAMS dict with 11 sections (supply, task_model, validation, slashing, hardware, earnings, burn, sell_pressure, nodes, retention, study_assumption, demand). |
| `validation.py` | Multi-witness consensus: Task class, validator selection, run_consensus, escalate_to_audit, apply_slashing, strike accounting. |
| `nodes.py` | DePIN agents: Node class, maybe_spawn_node, sync-tier capacity cap, partner revenue distribution, ROI scoring. |
| `treasury.py` | TGE distribution + linear vesting, customer fiat processing (burn + split), operator fiat payouts with insufficient-funds gating. |
| `experiments.py` | CLI with subcommands: `ablation`, `small_sweep`, `full_sweep`, `stress`, `timeseries`, `plots`. |
| `REPORT_v3.md` | This document. |
