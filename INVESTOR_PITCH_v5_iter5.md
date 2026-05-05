# CrowdBrain — Investor Pitch (5 slides)

*All numbers from `experiments_v5_iter5.py` Monte-Carlo (MC=20–50) over realistic-mode calibration.*

---

## SLIDE 1 — The opportunity (memo v5 recap)

**Physical-AI / teleop is hitting a data wall.** Tesla, 1X, Figure, Boston Dynamics all need 10K+ hours of high-quality teleop demonstrations per skill — and they need it from operators who aren't already on payroll. CrowdBrain is a token-incentivized, peer-validated, geographically-distributed teleop labor pool that:

- Trains 1K operators by Q3 2026 (Georgia 40% / Philippines 35% / Kenya 25%)
- Uses peer validation + bonded node-providers + tier-unlock-with-scale to maintain quality
- Pays in tokens with USD on-ramp via fiat-backed treasury
- Sells data + skill packages to Physical-AI labs and robotics OEMs ($15–60K/mo per customer)

**The market window is 24 months.** Whoever solves teleop-data-labor at scale before Physical-AI mainstreams (m30+) wins the category.

---

## SLIDE 2 — The J-curve (why it's defensible)

Stakeholder-grade simulation: 60-month projection, MC=20+, fully open-source code path.

```
Year 1 end (M12)      3 customers   $   378,432 ARR      24 T4+ ops    [bootstrap era]
Year 2 mid (M18)      4 customers   $   675,972 ARR     185 T4+ ops    [growth era starts]
Year 3 mid (M30)     24 customers   $ 4,837,320 ARR    1585 T4+ ops    [maturity era — TAKE OFF]
Year 3 end (M36)     69 customers   $10,343,328 ARR    2124 T4+ ops
Year 4 end (M48)    147 customers   $19,129,968 ARR    2752 T4+ ops
Year 5 end (M60)    217 customers   $28,871,640 ARR    2813 T4+ ops
```

**The shape is the story:** slow first 18 months (operator training + design partner ramp) → mild pickup mid-year-2 → take-off at month 30 as Physical-AI mainstreams.

**Realism check:** trajectory is closest to Hivemapper (log-L2 distance 0.252). Sits between Helium (DePIN-stagnated) and Scale AI (hypergrowth). Defensible, not Scale-AI fantasy.

---

## SLIDE 3 — Recommended launch config

```
Calibration:        train_v5_realistic (J-curve, refined 2026-05-05)
Tier unlock:        op-count gated — T3 unlocks @ 10 T2 ops, T4 @ 5 T3, T5 @ 2 T4
Hardware stake T3:  $25 (iter5 open-ended discovery — sensitivity flagged 'go lower')
Token economy:      500K/mo emission, 100M max supply, $200K AMM each side at TGE
Customer model:     $15-40K/mo, λ=0.6/seg/mo, J-curve via era multipliers
Operator schedule:  ×0.10 of v4 — memo-aligned to ~1K trained @ Q3 2026
Design partners:    3 multi-year contracts (24-month immune-from-sat-churn)
Investor horizon:   60 months (where take-off is visible)
```

Composite score (MC=20): **0.746 ± 0.015** (Phase A `stake_025` cell, iter5 winner).

---

## SLIDE 4 — Stress sensitivity

**Single-axis stress (iter4):**
- Tesla wage anchor: -2% (non-issue)
- Geo-Georgia shock: -1% (manageable)
- Funding winter: **-30% (existential)** — would require cash runway to ride out
- MVP slip 3mo: **-47% (existential)** — destroys J-curve inflection
- Intel Library upside: +5% (data licensing compounds)

**Combined-stress pairs (iter5):**
- stress_winter_AND_slip: composite 0.625 (ARR $9.7M)
- stress_winter_AND_tesla: composite 0.625 (ARR $9.8M)
- stress_geoGE_AND_winter: composite 0.621 (ARR $9.9M)
- stress_slip_AND_intel: composite 0.720 (ARR $35.9M)

**The two existentials are funding winter and MVP slip.** Both are addressed by raising sufficient runway (12+ months at burn) and shipping the operator-onboarding stack on time.

---

## SLIDE 5 — Q4 2026 milestone roadmap

Memo's stated milestone: **3+ paying customers, $500K+ ARR by month 8 (Q4 2026 if launch May 2026).**

Under pure J-curve calibration, the $500K target is unreachable (0% hit rate) — slow start by design. The realistic public commitments are:

- **Customers @ Q4 2026: 3 active** (target ≥3 — met by design partners alone)
- **ARR @ Q4 2026: $204,768** (recommend public target: $300K — consistently hit)

**Acceleration options tested (iter5 Phase D):**
| Fix | Q4 hit % | Q4 customers | Composite |
|---|---|---|---|
| q4_5dp | 0% | 5.0 | 0.467 |
| q4_early_ops | 0% | 3.0 | 0.473 |
| q4_bigger_dp | 0% | 3.1 | 0.469 |
| q4_combo_all_three | 90% | 5.0 | 0.595 |
| q4_lower_target | 0% | 3.0 | 0.454 |

**Recommendation:** announce $300K-ARR + 3-customer target publicly (high-confidence). Use 5-DP + bigger contracts as internal stretch.

---

## Appendix — what the deck is built from

- 80+ Monte-Carlo cells across 7 phases (iter1 → iter5)
- 80-config Bayesian-style random search over unified parameter space
- Per-customer-tier matching engine extension (iter5)
- Backtest comparison against Helium / Scale AI / Hivemapper
- Full code path open: `prepare_v5.py` (engine) + `train_v5_realistic.py` (calibration) + `experiments_v5_iter[1-5].py` (sweeps)

All numbers reproducible with seed=42 + MC offsets.
