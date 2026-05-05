# CrowdBrain v5 iter5 — Executive Summary (Realistic, 60-month projection)

**Winner config:** J-curve calibration + op-count tier unlock (10/5/2) + hardware stake **$25** (iter5-discovered, was $100 in iter4).

**Composite score:** 0.746 ± 0.015 (MC=20)  •  **Final ARR (m60):** $28,871,640  •  **Customers:** 217  •  **T4+ ops:** 2813

---

## J-curve trajectory

| Year | Month | Customers | Monthly rev | ARR | T4+ ops | Era |
|---|---|---|---|---|---|---|
| Year 1 end | M12 | 3 | $31,536 | $378,432 | 24 | bootstrap |
| Year 2 end | M24 | 12 | $148,833 | $1,785,996 | 846 | growth |
| Year 3 end | M36 | 69 | $861,944 | $10,343,328 | 2,124 | maturity |
| Year 5 end | M60 | 217 | $2,405,970 | $28,871,640 | 2,813 | maturity |

## iter5 discoveries

### Stake sweep (open-ended discovery)

| Stake | Composite | Final ARR |
|---|---|---|
| $0 | 0.6860 | $24.1M |
| $10 | 0.7363 | $28.9M |
| $25 | 0.7461 | $29.1M |
| $50 | 0.7403 | $28.2M |
| $100 | 0.6828 | $24.4M |
| $200 | 0.4861 | $8.0M |

**Winner: $25** — iter4 used $100; sensitivity flagged 'go lower' and the open-ended sweep confirms.

### Combined-stress pairs (2-axis simultaneous)

| Pair | Composite | Final ARR |
|---|---|---|
| stress_winter_AND_slip | 0.6250 | $9.7M |
| stress_winter_AND_tesla | 0.6247 | $9.8M |
| stress_geoGE_AND_winter | 0.6214 | $9.9M |
| stress_slip_AND_intel | 0.7198 | $35.9M |

### Q4 2026 milestone fix structures

| Fix | Composite | Q4 hit % | Q4 customers | Q4 ARR |
|---|---|---|---|---|
| q4_5dp | 0.4669 | 0% | 5.0 | $295,751 |
| q4_early_ops | 0.4735 | 0% | 3.0 | $218,811 |
| q4_bigger_dp | 0.4690 | 0% | 3.1 | $328,567 |
| q4_combo_all_three | 0.5948 | 90% | 5.0 | $586,786 |
| q4_lower_target | 0.4541 | 0% | 3.0 | $211,402 |

### Persona reintroduction cost

| Persona mix | Composite |
|---|---|
| personas_60_25_10_5 | 0.4324 |
| personas_40_40_15_5 | 0.4508 |
| personas_20_40_30_10 | 0.4994 |
| personas_off | 0.6828 |

### Per-customer-tier matching (engine change)

With per-tier matching enabled: composite **0.6830 ± 0.0225**, active ops **0**.

### Bayesian-style optimization winner

Best random-search config (out of 80 random + top-5 refinement):
- composite **0.8690 ± 0.0053**
- params: hardware_stake_t3=1, lambda_max_per_segment=1.4446, onboarding_multiplier=0.4441, era_maturity_mult=3.0536, era_growth_threshold_mo=20, dp_size_multiplier=1.6429

### Realism backtest vs DePIN/data-labeling peers

Closest peer: **Hivemapper** (log-L2 distance 0.252).
All distances: Scale AI=0.548, Helium=0.512, Hivemapper=0.252

