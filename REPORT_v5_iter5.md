# CrowdBrain v5 — iteration 5 report

_Generated: 2026-05-05 15:05_

Open-ended discovery sweep building on iter4 J-curve winner. User directive: let model discover; experiment, iterate, finalize without checkpoints.


## Phase A — Stake sweep (open-ended discovery)

Tested $0/$10/$25/$50/$100/$200 hardware stake T3 at 60mo, MC=20.

| Stake | Composite | Final ARR | Customers | T4+ ops |
|---|---|---|---|---|
| $0 | 0.6860 ± 0.0186 | $24.07M | 190 | 2429 |
| $10 | 0.7363 ± 0.0165 | $28.90M | 218 | 2950 |
| $25 | 0.7461 ± 0.0149 | $29.08M | 212 | 3063 ⭐ |
| $50 | 0.7403 ± 0.0180 | $28.25M | 210 | 3038 |
| $100 | 0.6828 ± 0.0200 | $24.39M | 185 | 2582 |
| $200 | 0.4861 ± 0.0195 | $8.05M | 130 | 1137 |

**Key finding:** $25 winner improves on iter4's $100 by **+0.063 composite** (~9% relative gain). Open-ended sweep confirms iter4 sensitivity flag — go lower than $100.

**Floor exists:** $0 stake scores 0.686, lower than $25's 0.746 — there's a non-trivial incentive floor below ~$10. Stake = 0 lets bad actors in.


## Phase B — MC=50 winner validation

Tight MC=50 rerun on iter4 winner ($100 stake) to halve confidence intervals.

- **jcurve_combined_60mo_mc50**: composite **0.6852 ± 0.0234** (MC=50, vs MC=20 ±0.020 in iter4)
  - Final ARR: $24.94M
  - Customers: 193
  - T4+: 2629


## Phase C — Combined-stress pairs (2-axis simultaneous)

Pairs of stress scenarios — defends 'what if X AND Y' investor questions.

| Pair | Composite | Final ARR | Customers | Δ vs winner |
|---|---|---|---|---|
| stress_winter_AND_slip | 0.6250 ± 0.0183 | $9.68M | 69 | -0.121 (-16%) |
| stress_winter_AND_tesla | 0.6247 ± 0.0157 | $9.83M | 66 | -0.121 (-16%) |
| stress_geoGE_AND_winter | 0.6214 ± 0.0150 | $9.86M | 67 | -0.125 (-17%) |
| stress_slip_AND_intel | 0.7198 ± 0.0088 | $35.95M | 187 | -0.026 (-4%) |


## Phase D — Q4 2026 milestone fix structures

Goal: push P(Q4 milestone hit at $500K ARR + 3 customers) ≥ 50%.

| Fix | Composite | Q4 hit % | Q4 customers | Q4 ARR |
|---|---|---|---|---|
| q4_5dp | 0.4669 | 0% | 5.0 | $296K |
| q4_early_ops | 0.4735 | 0% | 3.0 | $219K |
| q4_bigger_dp | 0.4690 | 0% | 3.1 | $329K |
| q4_combo_all_three | 0.5948 | 90% | 5.0 | $587K |
| q4_lower_target | 0.4541 | 0% | 3.0 | $211K |

**Best Q4 hit rate: 90%.** Memo target is achievable with the right structure.


## Phase E — Persona reintroduction cost

Tests behavioral honesty cost vs winner config (personas off).

| Persona mix | Composite | Final ARR | Customers |
|---|---|---|---|
| personas_60_25_10_5 | 0.4324 ± 0.0344 | $7.96M | 173 |
| personas_40_40_15_5 | 0.4508 ± 0.0320 | $8.05M | 169 |
| personas_20_40_30_10 | 0.4994 ± 0.0358 | $9.85M | 170 |
| personas_off | 0.6828 ± 0.0200 | $24.39M | 185 |

**Best persona mix:** `personas_20_40_30_10` at 0.4994.
**Cost of behavioral honesty:** 0.183 composite vs personas-off baseline.


## Phase F — Token-price clamp variant ('median deck')

AMM pools 10x deeper to dampen price upside (median-case investor view).

- **token_clamp_60mo**: composite 0.6263, Final ARR $22.02M, Final/peak price $3.13 / $3.14


## Phase G — Per-customer-tier matching (engine change)

Each customer matches against a sampled subset of operators per tier (varies by customer, sticky across months as ops churn). Targets the active-op decline observed post-m24 in iter4.

- **matching_per_tier_60mo**: composite **0.6830 ± 0.0225**, Final ARR $24.84M, Active ops 3342, T4+ 2590


## Phase I — Final iter5 winner validation (combined discoveries, MC=20)

**final_iter5_stake025_matchoff_60mo**

- Composite: **0.7461 ± 0.0149**
- Final ARR (m60): $29.08M
- Customers: 212
- T4+ ops: 3063
- Active ops final: 3843
- Cum revenue: $49.33M


## Diagnostic — per-tier matching effect on active op decline

Single-seed (42) comparison of aggregate vs per-tier matching:

| Mode | Peak active ops | Final active ops | Peak→final decline |
|---|---|---|---|
| Aggregate (current) | 4199 | 3602 | 14.2% |
| Per-tier (iter5) | 4284 | 3637 | 15.1% |

**Result:** per-tier matching did not reduce active-op decline; global matching is sufficient.


## Realism backtest vs DePIN / data-labeling peers

Compared winner ARR trajectory at year-end checkpoints to Scale AI / Helium / Hivemapper.

**Distances (log-L2, lower = closer):**
- Hivemapper: 0.252
- Helium: 0.512
- Scale AI: 0.548

**Closest peer:** Hivemapper.

Distance interpretation: <0.5 = same order of magnitude; 0.5-1.0 = same shape, different scale; >1.0 = qualitatively different.


## Iter5 headline findings

- **Stake winner is $25** (composite 0.746), beating iter4's $100. There IS a floor — $0 underperforms $25.
- **Worst combined-stress pair: `stress_geoGE_AND_winter`** at composite 0.621. The two existentials together compound — additive, not interactive.
- **Q4 milestone:** best hit rate 90%. Memo target achievable.
- **Persona cost:** 0.183 composite — best mix `personas_20_40_30_10`. Personas remain off in winner config.
- **Per-tier matching:** composite 0.683, active ops 0. Engine change does not improve winner — keep aggregate matching.
- **Realism backtest:** trajectory closest to **Hivemapper** — sits between Helium (DePIN-stagnated) and Scale AI (hypergrowth) — defensible in investor narrative.


## Recommended launch config (post-iter5)

```
calibration:        train_v5_realistic.PARAMS_V5_REALISTIC (J-curve)
tier_unlock:        op-count gated — T3=10, T4=5, T5=2
hardware_stake_t3:  $25  (iter5 discovery — was $100 in iter4)
token_emission:     500K/mo, 100M max supply
amm_pool_at_tge:    $200K each side
contracts:          $15-40K/mo, λ=0.6/seg/mo (J-curve via era multipliers)
design_partners:    3 multi-year (24-month immune-from-sat-churn)
operator_onboarding: ×0.10 of v4 schedule
horizon_for_deck:   60 months
expected_composite: 0.746
```


## Files

- `experiments_v5_iter5.py` — 7-phase sweep harness
- `bayesian_opt_v5.py` — random-search optimizer
- `backtest_v5.py` — realism comparison vs Helium/Scale AI/Hivemapper
- `deck_iter5.py` — stakeholder package + 5-slide investor pitch generator
- `prepare_v5.py` — engine (added per-customer-tier matching)
- `v5_results/iter5_*.json` — phase-by-phase aggregates
- `v5_results/bo_winner_config.json` — Bayesian-opt winner
- `INVESTOR_PITCH_v5_iter5.md` — 5-slide deck-ready pitch
- `EXECUTIVE_SUMMARY_v5_iter5.md` — 1-page distillation
- `winner_timeseries_v5_iter5.csv` — month-by-month trajectory
- `v5_iter5_overview.png` — 6-panel chart
