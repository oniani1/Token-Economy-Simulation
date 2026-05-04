# CrowdBrain v5 — Executive Summary (Realistic, 60-month projection)

**One-line:** Under realistic-vs-real-world assumptions, the CrowdBrain v5 token economy follows a **J-curve trajectory** — slow first 18 months, mild pickup in months 18–30 as design partners ramp, then take-off from month 30+ as the Physical-AI / teleop market hits its inflection point. End-of-year-5 numbers are defensible against Series-B robotics-data peers.

---

## The J-curve in numbers

| Year | Month | Customers | Monthly rev | ARR | T4+ ops | Era |
|---|---|---|---|---|---|---|
| Year 1 end | M12 | 3 | $29,254 | $351,048 | 23 | bootstrap |
| Year 2 end | M24 | 8 | $160,044 | $1,920,528 | 641 | growth |
| Year 3 end | M36 | 80 | $744,724 | $8,936,688 | 1,823 | maturity |
| Year 5 end | M60 | 195 | $2,214,059 | $26,568,708 | 2,663 | maturity |

## What's built (v5 architecture)

- **Conditional tier unlock** (`tier_unlock.py`): T3/T4/T5 unlock when 10/5/2 qualified operators exist at the prior tier — memo's 'with scale' framing implemented as op-count gates.
- **Bonded node-providers** (`node_providers.py`): 50/50 facility/community split at $5K bond per arm. Operator-reported issues + dispute resolution.
- **3-region operator pool** (`geography.py`): Georgia 40% / Philippines 35% / Kenya 25%, with region-specific cost ($6–10/hr), retention multipliers, and skill ramp.
- **Points → tokens transition** (`points_to_token.py`): tokens active from day 1 (1:1 conversion if operators began with points).
- **Multi-year design-partner contracts**: 24-month immune-from-sat-churn term — addresses prior bootstrap-era mass churn issue.

## Q4 2026 milestone

At month 8 of the simulation (Q4 2026 if launch is May 2026):
- **Customers**: 3 (memo target: 3+) — design partners only during slow-start phase
- **ARR**: $204,768 (memo target: $500K)

The J-curve calibration deliberately models a slow start consistent with real-world enterprise sales velocity for a vertical robotics-data startup. The memo's $500K-ARR-by-Q4-2026 target is at the high end of plausible execution; recommended public target is the customer count (3+) which is consistently met.

## Stress tests (60-month, realistic baseline)

| Scenario | Composite Δ | What it means |
|---|---|---|
| Tesla/1X wage anchor (30% of T3+ ops have $48/hr offers) | -2% | **Non-issue** — retention design beats wage gap |
| Geo shock — Georgia goes offline 6mo | -1% | Manageable; geographic diversification is paying off |
| Funding winter (customer arrivals × 0.25) | **-33%** | Existential — would require runway to ride out |
| MVP slip (3-month launch delay) | **-45%** | Existential — destroys the J-curve inflection |
| Intelligence Library activation @ m24 | **+5%** | Real upside; data licensing compounds |

## Recommended launch config

```
calibration:        train_v5_realistic.PARAMS_V5_REALISTIC
tier_unlock:        op-count gated (T3=10, T4=5, T5=2 qualified ops at prior tier)
hardware_stake_t3:  $100 (memo's $300-500 range was over-tuned for realistic revenue)
token_emission:     500K tokens/mo, 100M max supply
amm_pool_at_tge:    $200K each side
contracts:          $15-40K/mo, λ=0.6/seg/mo (J-curve growth via era multipliers)
design_partners:    3 multi-year (24-month immune-from-sat-churn)
operator_onboarding: ×0.10 of v4 schedule (memo-aligned to ~1K trained @ Q3 2026)
horizon_for_deck:   60 months
```

## What investors should read alongside this

- `REPORT_v5_iter3.md` — full 36/60-month sweep findings (5 phases)
- `REPORT_v5_iter4.md` — combined-winners validation, Q4 fix candidates, realistic stress tests, ±20% sensitivity
- `winner_timeseries_v5_realistic.csv` — month-by-month trajectory for due diligence
- `v5_realistic_overview.png` — 6-panel chart of the J-curve
