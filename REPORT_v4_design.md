# CrowdTrain v4 — 3-Pillar Behavioral Redesign

**Date**: 2026-04-26
**Status**: Spec → implementation in this session
**Predecessor**: v3 (multi-witness validation, REPORT_v3.md, winner config 0.6502)

## Goal

Transform the v3 simulation from a mechanical pipeline (rolling churn dice, tier averages) into a **behaviorally alive** simulation across three pillars that interact:

1. **Operator behavior** — heterogeneous personas, learning curves, decision-making, referral acquisition
2. **Customer side** — first-class enterprise customers with industry segments, Pareto sizing, satisfaction-driven churn/expansion
3. **Macro economy** — sentiment cycles (bull/bear), AMM-style price model, external events, era effects

These pillars interact: operator quality → customer satisfaction → expansion/churn → revenue → burn → AMM price → operator decisions → quality.

## Architectural overview

### New modules

| Module | Lines (est) | Purpose |
|---|---|---|
| `customers.py` | ~300 | Customer + Segment dataclasses, Pareto sizing, Poisson arrival, satisfaction model, churn/expansion |
| `macro.py` | ~400 | Sentiment HMM, x*y=k AMM, events catalog, era detection + multipliers |
| `operators_v4.py` | ~500 | Personas + learning + decisions + referrals (merged single file for cohesion) |

### Modified modules

| Module | Lines added (est) | Changes |
|---|---|---|
| `prepare.py` | ~200 | Monthly pipeline gains 6 new steps; evaluate() returns 4 supplemental metrics |
| `train.py` | ~250 | Adds `operators`, `customers`, `macro` PARAMS sections |
| `experiments.py` | ~150 | Adds 4 stress tests + ablation hooks for the 3 new pillars + plot generators |

**Total: ~1800 lines new/modified.**

### Backward compatibility

When PARAMS sections for `operators`, `customers`, `macro` are absent, prepare.py falls back to current v3 behavior. Allows direct A/B between v3 winner and v4 by toggling which PARAMS dict is loaded.

### Monthly pipeline (NEW STEPS in caps)

```
 0. tick clock                        + MACRO.UPDATE_SENTIMENT()
 1. spawn operators                   + PERSONAS.ASSIGN() + REFERRAL.BOOST()
 2. arrive customers                  + CUSTOMERS.ARRIVE_POISSON()
 3. compute demand                    + CUSTOMERS.AGGREGATE_DEMAND()
 4. operator decisions                + DECISIONS.MAKE_DECISIONS()
 5. allocate operator time              (existing)
 6. validate tasks                      (existing)
 7. update skills                     + LEARNING.UPDATE_SKILLS()
 8. compute earnings                     (existing)
 9. apply buys/sells to AMM           + MACRO.AMM_APPLY_FLOWS()
10. customer satisfaction             + CUSTOMERS.UPDATE_SAT() + CHURN/EXPAND
11. fire scheduled events             + MACRO.FIRE_EVENTS()
12. era updates                       + MACRO.UPDATE_ERA()
13. evaluate & log                      (existing + new supplements)
```

## Pillar 1: Operator behavior

### Personas (60/25/10/5 mix)

| Persona | % | Time/mo | Base sell | Stake aggro | Tier-up speed |
|---|---|---|---|---|---|
| Casual | 60% | 40h | 0.55 | 0.05 | × 1.3 (slower) |
| Pro Earner | 25% | 160h | 0.30 | 0.40 | × 0.7 (faster) |
| Validator | 10% | 120h | 0.20 | 0.40 | normal; specialize past T4 |
| HW Investor | 5% | 80h | 0.15 | 0.80 | normal; front-load stake |

### Learning curve

```
skill(t) = α · log(1 + experience_hours / 100)        # α tunable, default 0.10
quality_roll = base_quality(tier) · (1 + skill · persona.quality_focus)
                                  capped at +30% above base
```
`study_assumption.sim_trained_quality_bonus = 0.20` stacks additively as the BASE bonus, not multiplicatively, to avoid double-counting.

### Decision policy (rule-based, persona-weighted)

```python
each month, for each operator:
    # STAKE
    if token_balance > stake_needed_next_tier 
       and price_30d_momentum > 0
       and rng() < persona.stake_aggro:
           convert tokens -> stake; advance unlock progress

    # SELL
    sell_pct = persona.base_sell
             * sentiment_mult        # bull=0.6x, bear=1.5x
             * (2 - quality_recent)  # high q = less sell
             * (1 + income_volatility)
    sell_pct = clamp(sell_pct, 0.05, 0.85)

    # ADVANCE (automatic)
    if hours_at_tier >= tier_threshold * persona.tier_speed
       and quality >= tier_min_quality:
           advance to tier+1

    # SPECIALIZE
    if persona == 'validator' and tier >= 4:
        validator_queue_share = 0.50  (vs 0.0 for others)
```

### Referral mechanic

```
each active operator: spawn Poisson(0.05) referrals/month
referee inherits parent's persona with probability 0.30; else default mix
boost is additive on top of organic acquisition curve
referral_mult by era: bootstrap 1.2x, growth 1.5x, maturity 0.8x
```

### HW Investor specifics

- 30% of seed token allocation auto-converts to stake at acquisition
- Quality unlock rate = 1.5%/h (vs 1.0% baseline) when quality > 0.75
- Result: clears T4 stake by ~m6 even with low 80h/mo time budget

## Pillar 2: Customer side

### 4 Industry segments

| Segment | T1 | T2 | T3 | T4 | T5 | T6 | $/mo mean | churn/yr |
|---|---|---|---|---|---|---|---|---|
| Manufacturing | 0.30 | 0.30 | 0.15 | 0.15 | 0.05 | 0.05 | $80k | 15% |
| Warehouse | 0.20 | 0.40 | 0.10 | 0.15 | 0.10 | 0.05 | $60k | 25% |
| Healthcare | 0.05 | 0.15 | 0.15 | 0.20 | 0.25 | 0.20 | $120k | 10% |
| Robotics OEM | 0.05 | 0.10 | 0.15 | 0.30 | 0.25 | 0.15 | $150k | 8% |

### Size distribution

Truncated Pareto with α=1.5, capped at 4× segment mean and floored at 10% of mean. Heavy tail generates concentration naturally.

### Arrival

- 3 design partners at TGE (one per priority segment, fixed $100k/$80k/$150k contracts)
- Stochastic Poisson(λ_segment(t)) per segment after TGE
- λ_segment(t) follows logistic curve, peaks at month 18 at λ_max=3.0/segment/month
- Modulated by sentiment (bull 1.3×, bear 0.7×) and era (growth 1.5×, maturity 1.2×)

### Satisfaction → churn / expansion

```
sat = 0.40·quality_avg + 0.40·demand_fulfill_pct + 0.20·sla_pct
SLA hit per month if (fulfill_pct >= 0.95 AND quality >= 0.70); sla_pct = 6mo rolling avg

if sat < 0.50 for 3 consecutive months -> churn
if sat > 0.80 for 3 consecutive months -> expand demand_multiplier *= 1.20 (cap 3.0x)
else -> hold
```

## Pillar 3: Macro economy

### Sentiment HMM

| State | Mean dur | Sell× | Customer arr× | Op acq× |
|---|---|---|---|---|
| Bull | 21 mo | 0.6 | 1.3 | 1.10 |
| Bear | 9 mo | 1.5 | 0.7 | 0.85 |

Markov: P(bull→bear) = 1/21, P(bear→bull) = 1/9. Initial state at TGE: bull.

### AMM (x · y = k, treasury LP)

```
TGE: treasury LPs 1M tokens + $1M USD. k = 1e12. Mid price = $1.00.
Trade execution:
   buy(usd_in):    tokens_out = token_pool - k / (usd_pool + usd_in)
                   new_price  = (usd_pool + usd_in) / (token_pool - tokens_out)
   sell(tokens_in): usd_out = usd_pool - k / (token_pool + tokens_in)
                    new_price = (usd_pool - usd_out) / (token_pool + tokens_in)
Slippage:
   $10k sell -> -1.0%
   $100k sell -> -9.5%
   $1M sell -> -50%
Burn loop: revenue -> treasury -> buy_back amount = burn_pct * revenue
                   -> treasury executes BUY on AMM (raises price + adds USD)
                   -> bought tokens are burned (removed from supply)
```

### External events catalog (default 36mo schedule)

| Month | Event | Effect | Duration |
|---|---|---|---|
| 18 | Competitor enters | customer_arrival_λ × 0.7 | 6 months |
| 24 | SEC inquiry | one-shot AMM hit (price × 0.75) | instant |
| 30 | Macro recession | customer_churn × 1.5 | 4 months |

Stress mode: all 3 fire ("composite shock"). Override-able via `params.macro.events`.

### Era detection

```
era = 'bootstrap'
if cum_revenue > $5M OR month >= 12: era = 'growth'
if cum_revenue > $50M OR month >= 36 OR fiat_ratio > 70%: era = 'maturity'

Era multipliers:
              | Bootstrap | Growth | Maturity
emission_mult |    1.0    |  1.0   |   0.5
referral_mult |    1.2    |  1.5   |   0.8
arrival_mult  |    1.0    |  1.5   |   1.2
```

## Metrics

### Composite score (UNCHANGED 9 sub-scores from v3)

retention, stability, revenue, fairness, qualified, quality, validator_integrity, node_roi, capacity_utilization

Preserves direct comparability between v3 winner (0.6502) and v4 baseline.

### Supplemental metrics (NEW, reported separately, NOT in composite)

| Metric | Target | Description |
|---|---|---|
| top_3_concentration_pct | < 50% | Top 3 customers as % of revenue |
| nrr_blended | > 100% | Net revenue retention across all cohorts |
| sentiment_resilience | > 0.7 | (score in bear months) / (score in bull months) |
| persona_diversity_index | tracking | Shannon entropy of active operator persona mix |

## Run plan (8 runs, ~25 min)

| # | Run | Purpose |
|---|---|---|
| 1 | v4_baseline | All 3 pillars on |
| 2 | v4_no_personas | P1 → revert to v3 mechanical model |
| 3 | v4_no_customers | P2 → revert to v3 monolithic S-curve |
| 4 | v4_no_macro | P3 → revert to v3 naive price + no events |
| 5 | stress: biggest customer churn | At m18, drop #1 customer |
| 6 | stress: segment collapse | One segment churns over 3mo |
| 7 | stress: new-customer drought | Arrival rate × 0.1 for 6mo starting m12 |
| 8 | stress: composite shock | All 3 default events + 50% sentiment-bear bias |

Plus comparison to v3 winner config (0.6502).

## Deliverables

- `REPORT_v4.md` — architecture + per-pillar attribution + investor-facing summary
- `v4_baseline_timeseries.csv` — 36-month detailed trajectory
- `v4_ablation_results.json` — pillar-level attribution
- `v4_stress_results.json` — stress survival profile
- `v4_customers_timeseries.csv` — per-customer monthly state
- `v4_overview.png` — 4-panel chart (operator personas / customer cohorts / macro cycles / scoreboard)

## Resolved gaps (defaults baked in)

| # | Gap | Decision |
|---|---|---|
| 1 | Persona evolution | Sticky (no morphing in MVP) |
| 2 | Learning vs study_assumption | study_assumption is BASE; learning adds capped at +30% |
| 3 | Customer quality attribution | Tier-pool mean (no per-customer task assignment in MVP) |
| 4 | Event × sentiment | Independent in MVP |
| 5 | Income volatility churn | If income drops >50%, +0.10 churn prob |
| 6 | Era detection | Revenue + month thresholds (above) |
| 7 | Initial sentiment | Bull at TGE |
| 8 | Operator-customer matching | Tier-pool aggregation; per-customer fulfillment % via demand ratio |
| 9 | Referral specifics | Poisson(0.05)/mo per active op; 30% persona inheritance |
| 10 | Validator-queue × persona | Validator persona prioritizes queue (50% time-budget) past T4 |
| 11 | HW Investor mechanics | 30% seed-stake auto-convert + 1.5%/h unlock at q>0.75 |
| 12 | v4 starting PARAMS | Inherit v3 winner (base=45, stake=$150, emit=3M, arms=2, ops_per_node=2k) |

## Open questions for next iteration (NOT this session)

1. Should persona % itself be sweepable / time-varying?
2. Should sentiment/event interaction be modeled (regulation worse in bear)?
3. Should customer x persona affinity be modeled (Healthcare prefers Validators)?
4. Should AMM depth scale with treasury reserves over time?
5. Should we extend horizon to 60mo to see full sentiment cycles + maturity era?
