# CrowdTrain v4 — Next Session Plan

## Where we left off (2026-04-26)

Built v4 simulation with 3 behavioral pillars (operators + customers + macro). Confirmed:
- **Customers + Macro pillars beat v3 winner** by +8% composite at 36mo, +204% revenue
- **Personas pillar costs ~0.24 composite** (60% Casual operators don't grind to T4+)
- **At 60 months, v4 baseline generates +55% more revenue than v3 winner** despite slightly lower composite — the 36mo cliff hides v4's late-stage strength
- **Early customer cohorts (m0-17) die at 0%** in both configs — event stack timing issue

Files: `REPORT_v4.md`, `EXECUTIVE_SUMMARY_v4.md`, plus 4 PNG plots and 4 CSVs.

## Recommended next iteration steps

### Priority 1: Fix early-cohort customer mortality

The single biggest weakness identified. Three approaches to test:

**A. Extend design partner grace to 24 months**
```python
# In train_v4.py
"satisfaction": {
    ...
    "grace_months_after_signing": 24,    # was 12
}
```
Run: `python experiments_v4.py 3` — see if NRR improves.

**B. Delay first event to m24+**
```python
"events": [
    {"event_type": "competitor",  "fire_month": 24, ...},  # was 18
    {"event_type": "regulation",  "fire_month": 30, ...},  # was 24
    {"event_type": "recession",   "fire_month": 36, ...},  # was 30
]
```

**C. Per-segment grace** (advanced)
- Healthcare/Robotics_OEM (high-tier dependent) get 24mo
- Manufacturing/Warehouse (low-tier) get 12mo

Hypothesis: B is the cleanest fix; A is a sledgehammer; C is realistic but more code.

### Priority 2: Consolidate the v4 baseline config

After fixing early-cohort mortality, lock in the baseline:
- Rerun the 8-cell pillar ablation + stress sweep with corrected grace
- Pick the headline config (likely v4_no_personas with corrected grace)

### Priority 3: Finish iter3 60mo sweep

Last cell `v4_no_personas_60mo` takes ~60-90 min at MC=2 (slow because no_personas + 60mo = many T4+ ops generating tasks). Either:
- Wait it out
- Reduce to MC=1 and accept higher variance
- Compare the available 2 cells and infer

### Priority 4: Re-derive sentiment_resilience metric

Currently can blow up to 11+ when sim is mostly bear (formula: bear_revenue / bull_revenue averaged). Re-derive as:
```
weighted_score = (months_in_bull * score_in_bull + months_in_bear * score_in_bear) / total_months
sentiment_resilience = score_in_bear / score_in_bull   # cap at [0, 1]
```

### Priority 5: AMM depth sweep

Three cells: $500K (shallow) / $1M (current) / $5M (deep) initial pool. Measures shock sensitivity. ~30 min.

### Priority 6: Customer × persona affinity

Healthcare prefers Validator-type ops for T6 audit. Robotics OEM prefers HW Investors. Currently aggregate quality. To model:
- Each customer has segment-preferred personas
- Quality calc weights by preference
- Affects satisfaction → churn

This is a structural change (~200 lines). Defer to dedicated session.

### Priority 7: Bayesian optimization

Replace grid sweeps with Gaussian Process optimization in continuous parameter space. 50 runs gets what 729-config grid would. Tools: `scikit-optimize` or `Ax-platform`. Defer to dedicated methodology session.

## Quick commands

```bash
# Smoke test v4 (single seed, ~2 min)
python train_v4.py

# Full 8-cell ablation + stress sweep (~50 min @ MC=3)
python experiments_v4.py 3

# Tuned-persona iteration (~30 min @ MC=2)
python experiments_v4_iter2.py 2

# 60mo long-horizon (~60-90 min @ MC=2)
python experiments_v4_iter3.py 2

# Regenerate report from JSON results
python report_v4_generator.py

# Customer cohort analysis (uses CSVs)
python customer_cohort_analysis.py

# v3 winner reference (untouched)
python train.py
```

## What v3 vs v4 gives you

| Use case | Best config | Why |
|---|---|---|
| Investor headline numbers | v4_no_personas | +8% composite, $73M revenue, top-3 conc 7.5% |
| Realistic stress modeling | v4_baseline | All 3 pillars, behavioral richness, defensible to skeptics |
| Long-horizon storytelling | v4_baseline @ 60mo | $122M revenue, captures late-stage compounding |
| Methodological clarity | v3_winner | Simple, direct, untouched yesterday's result |

## Open issues to track

1. NRR low (0.14-0.37) — early-cohort mortality, addressed by Priority 1
2. T4+ count drop (-87% with personas) — accept the realism trade-off OR drop personas
3. sentiment_resilience metric unstable — Priority 4
4. Validator persona behavior — verify Validator Specialists actually concentrate in T4+ as designed
5. AMM depth — only tested at $1M, sweep recommended
6. Per-customer task assignment — currently aggregate; explicit matching would improve quality attribution
