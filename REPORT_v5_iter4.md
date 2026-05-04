# CrowdBrain v5 — Iteration 4 Report (J-curve realistic + stakeholder package)

**Goal:** validate iter3 winners under a refined J-curve calibration that better matches real-world teleop/Physical-AI adoption (slow start years 1 + first half year 2, mild pickup mid year 2 → mid year 3, take off mid year 3+).

**4 phases + Q4 milestone validation. ~28 cells × MC=20. Realistic-mode runs are 5–10x faster than prior iters because the economy is smaller (~2K active ops vs ~30K).**

**Calibration changes from iter3:**
- Customer arrival λ_max: 0.6/seg/mo (was 1.0)
- Customer arrival midpoint: m24 (was m13) — pushes growth out
- Era thresholds: bootstrap → growth at m18, growth → maturity at m30 (was m36)
- Era multipliers: bootstrap×0.6, growth×1.4, maturity×4.0 (J-curve shape)
- Operator onboarding mult: 0.10 (was 0.35) — memo-aligned
- Smaller contracts: $15–40K/mo (was $22–55K)

## Phase A — Combined winners on J-curve baseline

Tests whether iter3's individual winners (op_loose unlock + stake_100) compose constructively on the J-curve baseline at both 36mo and 60mo horizons.

### Phase A cells

| Cell | Composite | Final ARR | Cust @ end | T4+ ops | Active ops | Cum revenue |
|---|---|---|---|---|---|---|
| `jcurve_combined_60mo` | 0.683 ± 0.020 | $24.39M | 185 | 2,582 | 0 | $40.04M |
| `jcurve_baseline_60mo` | 0.485 ± 0.014 | $8.11M | 129 | 1,155 | 0 | $12.23M |
| `jcurve_combined_36mo` | 0.454 ± 0.015 | $7.75M | 75 | 1,783 | 0 | $5.61M |
| `jcurve_baseline_36mo` | 0.352 ± 0.021 | $892K | 73 | 9 | 0 | $1.29M |

**Combined-winners boost at 60mo**: 0.485 → 0.683 (++0.197). The op_loose unlock + $100 stake combination unlocks the operator pipeline early enough to support the J-curve customer take-off.

## Phase B — Q4 milestone fix candidates

Memo Q4 2026 target: 3+ paying customers, $500K+ ARR by month 8. Under the J-curve calibration the customer count target is consistently met (design partners are 3) but the ARR threshold is hard to hit because the slow start is a deliberate model feature.

Phase B tests three candidate fixes plus combinations.

### Phase B cells

| Cell | Composite | Final ARR | Cust @ end | T4+ ops | Active ops | Cum revenue |
|---|---|---|---|---|---|---|
| `jcurve_q4_combo_60mo` | 0.658 ± 0.129 | $21.82M | 179 | 3,760 | 0 | $33.11M |
| `jcurve_q4_combo` | 0.425 ± 0.054 | $5.02M | 69 | 1,431 | 0 | $4.08M |
| `jcurve_bigger_dp` | 0.375 ± 0.024 | $2.71M | 73 | 467 | 0 | $2.62M |
| `jcurve_fast_ramp` | 0.352 ± 0.027 | $928K | 64 | 59 | 0 | $1.39M |
| `jcurve_4dp` | 0.348 ± 0.027 | $762K | 62 | 7 | 0 | $1.32M |

**Q4 milestone hit rates** (P of hitting both targets at MC=20):

- `jcurve_4dp`: 0% hit; mean ARR @ m8 = $235K
- `jcurve_bigger_dp`: 0% hit; mean ARR @ m8 = $283K
- `jcurve_fast_ramp`: 0% hit; mean ARR @ m8 = $206K
- `jcurve_q4_combo`: 0% hit; mean ARR @ m8 = $389K
- `jcurve_q4_combo_60mo`: 0% hit; mean ARR @ m8 = $389K

## Phase C — Realistic-mode stress tests (60mo)

Six scenarios run on the J-curve baseline at 60-month horizon. The deck risk slide should be informed by these numbers, not iter1's unrealistic-mode stress findings.

### Phase C cells

| Cell | Composite | Final ARR | Cust @ end | T4+ ops | Active ops | Cum revenue |
|---|---|---|---|---|---|---|
| `stress_intel_library` | 0.514 ± 0.016 | $13.99M | 129 | 1,155 | 0 | $19.30M |
| `stress_baseline_60mo` | 0.485 ± 0.014 | $8.11M | 129 | 1,155 | 0 | $12.23M |
| `stress_tesla_hiring` | 0.483 ± 0.022 | $8.53M | 144 | 1,142 | 0 | $12.32M |
| `stress_geo_GE` | 0.478 ± 0.021 | $8.24M | 135 | 1,138 | 0 | $12.00M |
| `stress_funding_winter` | 0.339 ± 0.032 | $2.57M | 35 | 341 | 0 | $3.55M |
| `stress_mvp_slip` | 0.256 ± 0.007 | $289K | 3 | 3 | 0 | $1.74M |

**Stress sensitivities** (composite Δ vs baseline):

- `stress_intel_library`: +0.028 → composite 0.514, ARR $13.99M
- `stress_tesla_hiring`: -0.002 → composite 0.483, ARR $8.53M
- `stress_geo_GE`: -0.008 → composite 0.478, ARR $8.24M
- `stress_funding_winter`: -0.146 → composite 0.339, ARR $2.57M
- `stress_mvp_slip`: -0.229 → composite 0.256, ARR $289K

## Phase D — Sensitivity (±20%)

Tests how the headline composite responds to ±20% perturbation on 4 key params: customer arrival λ, contract size, hardware stake, onboarding multiplier. All cells run at 60mo to capture the J-curve effect.

### Phase D cells

| Cell | Composite | Final ARR | Cust @ end | T4+ ops | Active ops | Cum revenue |
|---|---|---|---|---|---|---|
| `sens_stake_m20` | 0.531 ± 0.062 | $12.50M | 141 | 1,549 | 0 | $18.40M |
| `sens_lambda_p20` | 0.499 ± 0.017 | $9.33M | 159 | 1,262 | 0 | $14.29M |
| `sens_contract_p20` | 0.494 ± 0.020 | $9.23M | 130 | 1,208 | 0 | $13.95M |
| `sens_onboarding_p20` | 0.492 ± 0.021 | $9.02M | 127 | 1,285 | 0 | $12.93M |
| `sens_stake_p20` | 0.488 ± 0.020 | $8.05M | 124 | 1,173 | 0 | $12.28M |
| `sens_lambda_m20` | 0.473 ± 0.018 | $7.14M | 106 | 1,091 | 0 | $10.45M |
| `sens_onboarding_m20` | 0.469 ± 0.016 | $7.51M | 139 | 894 | 0 | $11.77M |
| `sens_contract_m20` | 0.467 ± 0.014 | $6.82M | 131 | 1,049 | 0 | $9.66M |

**Sensitivity** (Δ composite vs J-curve baseline 0.485):

- **contract**: +20% → 0.494, -20% → 0.467  (spread 0.027)
- **lambda**: +20% → 0.499, -20% → 0.473  (spread 0.026)
- **onboarding**: +20% → 0.492, -20% → 0.469  (spread 0.023)
- **stake**: +20% → 0.488, -20% → 0.531  (spread 0.043)

## Q4 2026 Milestone Probability (MC=50, best Q4-fix combo)

- **P(hit milestone)**: 2%
- Mean Q4 customers: **4.1** (target ≥3)
- Mean Q4 ARR: **$400K** (target ≥$500K)

**Recommendation:** Set the public Q4 2026 target as `3+ customers + $300K ARR` (higher hit probability) and frame the $500K+ ARR as the upside scenario. Alternatively, accelerate the design-partner ramp to push fulfillment in months 4–8.

## Strategic conclusion — recommended launch config

Use **`jcurve_combined_60mo`** as the standing recommended config:

- Calibration: `train_v5_realistic.PARAMS_V5_REALISTIC` (J-curve realistic)
- Tier unlock: op-count gated (T3=10 / T4=5 / T5=2 qualified ops at prior tier)
- Hardware stake T3: $100
- Horizon for stakeholder reporting: 60 months

The J-curve trajectory tells a clean Series-A → B → C story aligned with how teleop / Physical-AI markets actually mature: slow first 18 months while operators train and design partners ramp; mild pickup as second-wave customers arrive; take-off from month 30 onwards as Physical-AI hits its data-hunger inflection point.

## Appendix — All cell results

### phaseA
```json
{
  "jcurve_baseline_36mo": {
    "n_runs": 20,
    "amm_usd_pool_final_mean": 111414.6,
    "amm_usd_pool_final_std": 14853.6174,
    "quality_score_mean": 0.83,
    "quality_score_std": 0.0265,
    "gini_score_mean": 0.0053,
    "gini_score_std": 0.0127,
    "total_operators_ever_mean": 12195.3,
    "total_operators_ever_std": 707.8354,
    "realism_final_arr_usd_mean": 892114.8,
    "realism_final_arr_usd_std": 163313.1256,
    "realism_customer_count_in_band_mean": 1.0,
    "realism_customer_count_in_band_std": 0.0,
    "realism_customer_count_in_band_pct_true": 1.0,
    "revenue_score_mean": 0.0258,
    "revenue_score_std": 0.0022,
    "sentiment_resilience_mean": 1.0906,
    "sentiment_resilience_std": 0.4482,
    "realism_q4_2026_customers_mean": 3.05,
    "realism_q4_2026_customers_std": 0.2179,
    "persona_diversity_index_mean": 0.0,
    "persona_diversity_index_std": 0.0,
    "amm_token_pool_final_mean": 366001.8,
    "amm_token_pool_final_std": 52796.9368,
    "final_price_mean": 0.3159,
    "final_price_std": 0.0807,
    "cumulative_revenue_mean": 1287679.1,
    "cumulative_revenue_std": 112383.762,
    "active_operators_final_mean": 2541.7,
    "active_operators_final_std": 135.8956,
    "qualified_score_mean": 0.0017,
    "qualified_score_std": 0.0006,
    "gini_mean": 0.6279,
    "gini_std": 0.0287,
    "retention_pct_mean": 20.865,
    "retention_pct_std": 0.7945,
    "false_positive_rate_mean": 0.0169,
    "false_positive_rate_std": 0.0017,
    "slash_rate_mean": 0.034,
    "slash_rate_std": 0.0053,
    "realism_q4_2026_milestone_hit_mean": 0.0,
    "realism_q4_2026_milestone_hit_std": 0.0,
    "realism_q4_2026_milestone_hit_pct_true": 0.0,
    "nrr_blended_mean": 0.2212,
    "nrr_blended_std": 0.1886,
    "peak_price_mean": 1.0072,
    "peak_price_std": 0.0057,
    "customer_count_active_mean": 73.0,
    "customer_count_active_std": 11.3842,
    "retention_score_mean": 0.3793,
    "retention_score_std": 0.0144,
    "realism_q4_2026_arr_usd_mean": 204138.6,
    "realism_q4_2026_arr_usd_std": 8560.5038,
    "realism_final_customer_count_mean": 73.0,
    "realism_final_customer_count_std": 11.3842,
    "node_roi_score_mean": 0.5,
    "node_roi_score_std": 0.0,
    "customer_count_total_mean": 79.1,
    "customer_count_total_std": 12.4214,
    "cumulative_referrals_mean": 0.0,
    "cumulative_referrals_std": 0.0,
    "t4_plus_operators_mean": 8.65,
    "t4_plus_operators_std": 3.0704,
    "validator_integrity_score_mean": 0.8312,
    "validator_integrity_score_std": 0.0175,
    "stability_score_mean": 0.7099,
    "stability_score_std": 0.2095,
    "top_3_concentration_pct_mean": 20.48,
    "top_3_concentration_pct_std": 5.2086,
    "score_mean": 0.352,
    "score_std": 0.0211,
    "realism_arr_in_band_mean": 0.35,
    "realism_arr_in_band_std": 0.477,
    "realism_arr_in_band_pct_true": 0.35,
    "capacity_utilization_score_mean": 0.9913,
    "capacity_utilization_score_std": 0.0262
  },
  "jcurve_baseline_60mo": {
    "n_runs": 20,
    "amm_usd_pool_final_mean": 1228808.75,
    "amm_usd_pool_final_std": 124214.0103,
    "quality_score_mean": 0.9226,
    "quality_score_std": 0.0065,
    "gini_score_mean": 0.6441,
    "gini_score_std": 0.0153,
    "total_operators_ever_mean": 13350.0,
    "total_operators_ever_std": 677.6543,
    "realism_final_arr_usd_mean": 8109162.6,
    "realism_final_arr_usd_std": 869451.7895,
    "realism_customer_count_in_band_mean": 0.15,
    "realism_customer_count_in_band_std": 0.3571,
    "realism_customer_count_in_band_pct_true": 0.15,
    "revenue_score_mean": 0.2446,
    "revenue_score_std": 0.0257,
    "sentiment_resilience_mean": 1.8107,
    "sentiment_resilience_std": 2.0673,
    "realism_q4_2026_customers_mean": 3.05,
    "realism_q4_2026_customers_std": 0.2179,
    "persona_diversity_index_mean": 0.0,
    "persona_diversity_index_std": 0.0,
    "amm_token_pool_final_mean": 32940.05,
    "amm_token_pool_final_std": 3895.3418,
    "final_price_mean": 38.135,
    "final_price_std": 7.2447,
    "cumulative_revenue_mean": 12229495.05,
    "cumulative_revenue_std": 1286456.9417,
    "active_operators_final_mean": 1780.1,
    "active_operators_final_std": 152.5064,
    "qualified_score_mean": 0.231,
    "qualified_score_std": 0.0257,
    "gini_mean": 0.2136,
    "gini_std": 0.0092,
    "retention_pct_mean": 13.34,
    "retention_pct_std": 0.9452,
    "false_positive_rate_mean": 0.0214,
    "false_positive_rate_std": 0.0008,
    "slash_rate_mean": 0.0155,
    "slash_rate_std": 0.0013,
    "realism_q4_2026_milestone_hit_mean": 0.0,
    "realism_q4_2026_milestone_hit_std": 0.0,
    "realism_q4_2026_milestone_hit_pct_true": 0.0,
    "nrr_blended_mean": 0.0956,
    "nrr_blended_std": 0.0273,
    "peak_price_mean": 38.135,
    "peak_price_std": 7.2447,
    "customer_count_active_mean": 129.0,
    "customer_count_active_std": 22.2036,
    "retention_score_mean": 0.2425,
    "retention_score_std": 0.0172,
    "realism_q4_2026_arr_usd_mean": 204138.6,
    "realism_q4_2026_a
```

### phaseB
```json
{
  "jcurve_4dp": {
    "n_runs": 20,
    "amm_usd_pool_final_mean": 101082.05,
    "amm_usd_pool_final_std": 17088.7802,
    "quality_score_mean": 0.8318,
    "quality_score_std": 0.0253,
    "gini_score_mean": 0.0039,
    "gini_score_std": 0.0098,
    "total_operators_ever_mean": 12026.6,
    "total_operators_ever_std": 512.5674,
    "realism_final_arr_usd_mean": 761689.2,
    "realism_final_arr_usd_std": 206558.0061,
    "realism_customer_count_in_band_mean": 1.0,
    "realism_customer_count_in_band_std": 0.0,
    "realism_customer_count_in_band_pct_true": 1.0,
    "revenue_score_mean": 0.0265,
    "revenue_score_std": 0.0019,
    "sentiment_resilience_mean": 1.1004,
    "sentiment_resilience_std": 0.4118,
    "realism_q4_2026_customers_mean": 4.0,
    "realism_q4_2026_customers_std": 0.0,
    "persona_diversity_index_mean": 0.0,
    "persona_diversity_index_std": 0.0,
    "amm_token_pool_final_mean": 405937.4,
    "amm_token_pool_final_std": 62912.0593,
    "final_price_mean": 0.2627,
    "final_price_std": 0.0971,
    "cumulative_revenue_mean": 1323738.2,
    "cumulative_revenue_std": 93866.7383,
    "active_operators_final_mean": 2492.3,
    "active_operators_final_std": 129.7702,
    "qualified_score_mean": 0.0014,
    "qualified_score_std": 0.0006,
    "gini_mean": 0.6256,
    "gini_std": 0.0271,
    "retention_pct_mean": 20.735,
    "retention_pct_std": 0.778,
    "false_positive_rate_mean": 0.0166,
    "false_positive_rate_std": 0.0018,
    "slash_rate_mean": 0.0336,
    "slash_rate_std": 0.0051,
    "realism_q4_2026_milestone_hit_mean": 0.0,
    "realism_q4_2026_milestone_hit_std": 0.0,
    "realism_q4_2026_milestone_hit_pct_true": 0.0,
    "nrr_blended_mean": 0.1626,
    "nrr_blended_std": 0.1,
    "peak_price_mean": 1.006,
    "peak_price_std": 0.0041,
    "customer_count_active_mean": 62.05,
    "customer_count_active_std": 10.4904,
    "retention_score_mean": 0.3769,
    "retention_score_std": 0.0141,
    "realism_q4_2026_arr_usd_mean": 235374.6,
    "realism_q4_2026_arr_usd_std": 16798.2438,
    "realism_final_customer_count_mean": 62.05,
    "realism_final_customer_count_std": 10.4904,
    "node_roi_score_mean": 0.5,
    "node_roi_score_std": 0.0,
    "customer_count_total_mean": 69.3,
    "customer_count_total_std": 11.0368,
    "cumulative_referrals_mean": 0.0,
    "cumulative_referrals_std": 0.0,
    "t4_plus_operators_mean": 7.25,
    "t4_plus_operators_std": 2.9133,
    "validator_integrity_score_mean": 0.8337,
    "validator_integrity_score_std": 0.0181,
    "stability_score_mean": 0.7465,
    "stability_score_std": 0.227,
    "top_3_concentration_pct_mean": 24.83,
    "top_3_concentration_pct_std": 4.2769,
    "score_mean": 0.3484,
    "score_std": 0.0266,
    "realism_arr_in_band_mean": 0.1,
    "realism_arr_in_band_std": 0.3,
    "realism_arr_in_band_pct_true": 0.1,
    "capacity_utilization_score_mean": 0.8505,
    "capacity_utilization_score_std": 0.1236
  },
  "jcurve_bigger_dp": {
    "n_runs": 20,
    "amm_usd_pool_final_mean": 331403.15,
    "amm_usd_pool_final_std": 262111.8655,
    "quality_score_mean": 0.8631,
    "quality_score_std": 0.0333,
    "gini_score_mean": 0.1674,
    "gini_score_std": 0.1726,
    "total_operators_ever_mean": 12230.35,
    "total_operators_ever_std": 528.5057,
    "realism_final_arr_usd_mean": 2709321.6,
    "realism_final_arr_usd_std": 2248140.0968,
    "realism_customer_count_in_band_mean": 1.0,
    "realism_customer_count_in_band_std": 0.0,
    "realism_customer_count_in_band_pct_true": 1.0,
    "revenue_score_mean": 0.0524,
    "revenue_score_std": 0.0243,
    "sentiment_resilience_mean": 1.0254,
    "sentiment_resilience_std": 0.774,
    "realism_q4_2026_customers_mean": 3.0,
    "realism_q4_2026_customers_std": 0.0,
    "persona_diversity_index_mean": 0.0,
    "persona_diversity_index_std": 0.0,
    "amm_token_pool_final_mean": 227618.8,
    "amm_token_pool_final_std": 141112.3251,
    "final_price_mean": 4.4633,
    "final_price_std": 5.2728,
    "cumulative_revenue_mean": 2622450.55,
    "cumulative_revenue_std": 1216843.4196,
    "active_operators_final_mean": 2890.5,
    "active_operators_final_std": 402.2441,
    "qualified_score_mean": 0.0935,
    "qualified_score_std": 0.1173,
    "gini_mean": 0.5023,
    "gini_std": 0.1065,
    "retention_pct_mean": 23.64,
    "retention_pct_std": 3.1668,
    "false_positive_rate_mean": 0.017,
    "false_positive_rate_std": 0.0012,
    "slash_rate_mean": 0.0274,
    "slash_rate_std": 0.0067,
    "realism_q4_2026_milestone_hit_mean": 0.0,
    "realism_q4_2026_milestone_hit_std": 0.0,
    "realism_q4_2026_milestone_hit_pct_true": 0.0,
    "nrr_blended_mean": 0.352,
    "nrr_blended_std": 0.2145,
    "peak_price_mean": 4.8342,
    "peak_price_std": 4.9853,
    "customer_count_active_mean": 72.95,
    "customer_count_active_std": 11.8215,
    "retention_score_mean": 0.4298,
    "retention_score_std": 0.0577,
    "realism_q4_2026_arr_usd_mean": 282943.2,
    "realism_q4_2026_arr_usd_std": 19734.0416,
    
```

### phaseC
```json
{
  "stress_baseline_60mo": {
    "n_runs": 20,
    "amm_usd_pool_final_mean": 1228808.75,
    "amm_usd_pool_final_std": 124214.0103,
    "quality_score_mean": 0.9226,
    "quality_score_std": 0.0065,
    "gini_score_mean": 0.6441,
    "gini_score_std": 0.0153,
    "total_operators_ever_mean": 13350.0,
    "total_operators_ever_std": 677.6543,
    "realism_final_arr_usd_mean": 8109162.6,
    "realism_final_arr_usd_std": 869451.7895,
    "realism_customer_count_in_band_mean": 0.15,
    "realism_customer_count_in_band_std": 0.3571,
    "realism_customer_count_in_band_pct_true": 0.15,
    "revenue_score_mean": 0.2446,
    "revenue_score_std": 0.0257,
    "sentiment_resilience_mean": 1.8107,
    "sentiment_resilience_std": 2.0673,
    "realism_q4_2026_customers_mean": 3.05,
    "realism_q4_2026_customers_std": 0.2179,
    "persona_diversity_index_mean": 0.0,
    "persona_diversity_index_std": 0.0,
    "amm_token_pool_final_mean": 32940.05,
    "amm_token_pool_final_std": 3895.3418,
    "final_price_mean": 38.135,
    "final_price_std": 7.2447,
    "cumulative_revenue_mean": 12229495.05,
    "cumulative_revenue_std": 1286456.9417,
    "active_operators_final_mean": 1780.1,
    "active_operators_final_std": 152.5064,
    "qualified_score_mean": 0.231,
    "qualified_score_std": 0.0257,
    "gini_mean": 0.2136,
    "gini_std": 0.0092,
    "retention_pct_mean": 13.34,
    "retention_pct_std": 0.9452,
    "false_positive_rate_mean": 0.0214,
    "false_positive_rate_std": 0.0008,
    "slash_rate_mean": 0.0155,
    "slash_rate_std": 0.0013,
    "realism_q4_2026_milestone_hit_mean": 0.0,
    "realism_q4_2026_milestone_hit_std": 0.0,
    "realism_q4_2026_milestone_hit_pct_true": 0.0,
    "nrr_blended_mean": 0.0956,
    "nrr_blended_std": 0.0273,
    "peak_price_mean": 38.135,
    "peak_price_std": 7.2447,
    "customer_count_active_mean": 129.0,
    "customer_count_active_std": 22.2036,
    "retention_score_mean": 0.2425,
    "retention_score_std": 0.0172,
    "realism_q4_2026_arr_usd_mean": 204138.6,
    "realism_q4_2026_arr_usd_std": 8560.5038,
    "realism_final_customer_count_mean": 129.0,
    "realism_final_customer_count_std": 22.2036,
    "node_roi_score_mean": 1.0,
    "node_roi_score_std": 0.0,
    "customer_count_total_mean": 299.9,
    "customer_count_total_std": 36.625,
    "cumulative_referrals_mean": 0.0,
    "cumulative_referrals_std": 0.0,
    "t4_plus_operators_mean": 1154.75,
    "t4_plus_operators_std": 128.3347,
    "validator_integrity_score_mean": 0.7858,
    "validator_integrity_score_std": 0.0082,
    "stability_score_mean": 0.7957,
    "stability_score_std": 0.0656,
    "top_3_concentration_pct_mean": 10.82,
    "top_3_concentration_pct_std": 2.5075,
    "score_mean": 0.4853,
    "score_std": 0.014,
    "realism_arr_in_band_mean": 1.0,
    "realism_arr_in_band_std": 0.0,
    "realism_arr_in_band_pct_true": 1.0,
    "capacity_utilization_score_mean": 0.6916,
    "capacity_utilization_score_std": 0.1762
  },
  "stress_funding_winter": {
    "n_runs": 20,
    "amm_usd_pool_final_mean": 350444.05,
    "amm_usd_pool_final_std": 118840.913,
    "quality_score_mean": 0.9026,
    "quality_score_std": 0.0102,
    "gini_score_mean": 0.1422,
    "gini_score_std": 0.1678,
    "total_operators_ever_mean": 13337.4,
    "total_operators_ever_std": 594.0379,
    "realism_final_arr_usd_mean": 2573599.8,
    "realism_final_arr_usd_std": 808843.6021,
    "realism_customer_count_in_band_mean": 1.0,
    "realism_customer_count_in_band_std": 0.0,
    "realism_customer_count_in_band_pct_true": 1.0,
    "revenue_score_mean": 0.071,
    "revenue_score_std": 0.0164,
    "sentiment_resilience_mean": 1.2235,
    "sentiment_resilience_std": 0.8566,
    "realism_q4_2026_customers_mean": 3.0,
    "realism_q4_2026_customers_std": 0.0,
    "persona_diversity_index_mean": 0.0,
    "persona_diversity_index_std": 0.0,
    "amm_token_pool_final_mean": 126482.2,
    "amm_token_pool_final_std": 39139.9636,
    "final_price_mean": 3.4234,
    "final_price_std": 2.4747,
    "cumulative_revenue_mean": 3548118.7,
    "cumulative_revenue_std": 821012.4375,
    "active_operators_final_mean": 1122.7,
    "active_operators_final_std": 150.0574,
    "qualified_score_mean": 0.0681,
    "qualified_score_std": 0.0421,
    "gini_mean": 0.5411,
    "gini_std": 0.1287,
    "retention_pct_mean": 8.42,
    "retention_pct_std": 1.0745,
    "false_positive_rate_mean": 0.0177,
    "false_positive_rate_std": 0.0017,
    "slash_rate_mean": 0.0195,
    "slash_rate_std": 0.002,
    "realism_q4_2026_milestone_hit_mean": 0.0,
    "realism_q4_2026_milestone_hit_std": 0.0,
    "realism_q4_2026_milestone_hit_pct_true": 0.0,
    "nrr_blended_mean": 0.1585,
    "nrr_blended_std": 0.0718,
    "peak_price_mean": 3.4278,
    "peak_price_std": 2.4703,
    "customer_count_active_mean": 35.25,
    "customer_count_active_std": 5.8981,
    "retention_score_mean": 0.1531,
    "retention_score_std": 0.0193,
    "realism_q4_2026_arr_usd_mean": 202634.4,
    "realism_q4_2026_
```

### phaseD
```json
{
  "sens_lambda_p20": {
    "n_runs": 20,
    "amm_usd_pool_final_mean": 1408478.95,
    "amm_usd_pool_final_std": 143465.8728,
    "quality_score_mean": 0.9245,
    "quality_score_std": 0.0051,
    "gini_score_mean": 0.6484,
    "gini_score_std": 0.0117,
    "total_operators_ever_mean": 13395.95,
    "total_operators_ever_std": 823.6461,
    "realism_final_arr_usd_mean": 9331997.4,
    "realism_final_arr_usd_std": 924188.8473,
    "realism_customer_count_in_band_mean": 0.0,
    "realism_customer_count_in_band_std": 0.0,
    "realism_customer_count_in_band_pct_true": 0.0,
    "revenue_score_mean": 0.2857,
    "revenue_score_std": 0.0313,
    "sentiment_resilience_mean": 1.4937,
    "sentiment_resilience_std": 1.0264,
    "realism_q4_2026_customers_mean": 3.05,
    "realism_q4_2026_customers_std": 0.2179,
    "persona_diversity_index_mean": 0.0,
    "persona_diversity_index_std": 0.0,
    "amm_token_pool_final_mean": 28709.5,
    "amm_token_pool_final_std": 3069.0498,
    "final_price_mean": 50.1099,
    "final_price_std": 9.9987,
    "cumulative_revenue_mean": 14286550.55,
    "cumulative_revenue_std": 1564400.5201,
    "active_operators_final_mean": 1903.15,
    "active_operators_final_std": 188.3532,
    "qualified_score_mean": 0.2523,
    "qualified_score_std": 0.0291,
    "gini_mean": 0.211,
    "gini_std": 0.007,
    "retention_pct_mean": 14.19,
    "retention_pct_std": 0.9544,
    "false_positive_rate_mean": 0.0213,
    "false_positive_rate_std": 0.0008,
    "slash_rate_mean": 0.0151,
    "slash_rate_std": 0.001,
    "realism_q4_2026_milestone_hit_mean": 0.0,
    "realism_q4_2026_milestone_hit_std": 0.0,
    "realism_q4_2026_milestone_hit_pct_true": 0.0,
    "nrr_blended_mean": 0.094,
    "nrr_blended_std": 0.033,
    "peak_price_mean": 50.1099,
    "peak_price_std": 9.9987,
    "customer_count_active_mean": 158.7,
    "customer_count_active_std": 22.3743,
    "retention_score_mean": 0.258,
    "retention_score_std": 0.0174,
    "realism_q4_2026_arr_usd_mean": 204138.6,
    "realism_q4_2026_arr_usd_std": 8560.5038,
    "realism_final_customer_count_mean": 158.7,
    "realism_final_customer_count_std": 22.3743,
    "node_roi_score_mean": 1.0,
    "node_roi_score_std": 0.0,
    "customer_count_total_mean": 367.55,
    "customer_count_total_std": 32.225,
    "cumulative_referrals_mean": 0.0,
    "cumulative_referrals_std": 0.0,
    "t4_plus_operators_mean": 1261.5,
    "t4_plus_operators_std": 145.5086,
    "validator_integrity_score_mean": 0.787,
    "validator_integrity_score_std": 0.0079,
    "stability_score_mean": 0.801,
    "stability_score_std": 0.0531,
    "top_3_concentration_pct_mean": 9.02,
    "top_3_concentration_pct_std": 1.7189,
    "score_mean": 0.4995,
    "score_std": 0.017,
    "realism_arr_in_band_mean": 1.0,
    "realism_arr_in_band_std": 0.0,
    "realism_arr_in_band_pct_true": 1.0,
    "capacity_utilization_score_mean": 0.6601,
    "capacity_utilization_score_std": 0.1689
  },
  "sens_lambda_m20": {
    "n_runs": 20,
    "amm_usd_pool_final_mean": 1074269.1,
    "amm_usd_pool_final_std": 95961.38,
    "quality_score_mean": 0.9199,
    "quality_score_std": 0.0089,
    "gini_score_mean": 0.6469,
    "gini_score_std": 0.011,
    "total_operators_ever_mean": 13397.55,
    "total_operators_ever_std": 719.1436,
    "realism_final_arr_usd_mean": 7142942.4,
    "realism_final_arr_usd_std": 672973.9913,
    "realism_customer_count_in_band_mean": 0.3,
    "realism_customer_count_in_band_std": 0.4583,
    "realism_customer_count_in_band_pct_true": 0.3,
    "revenue_score_mean": 0.209,
    "revenue_score_std": 0.0189,
    "sentiment_resilience_mean": 1.6402,
    "sentiment_resilience_std": 1.5338,
    "realism_q4_2026_customers_mean": 3.05,
    "realism_q4_2026_customers_std": 0.2179,
    "persona_diversity_index_mean": 0.0,
    "persona_diversity_index_std": 0.0,
    "amm_token_pool_final_mean": 37587.75,
    "amm_token_pool_final_std": 3991.9692,
    "final_price_mean": 29.0816,
    "final_price_std": 4.8214,
    "cumulative_revenue_mean": 10449011.85,
    "cumulative_revenue_std": 944391.8504,
    "active_operators_final_mean": 1704.25,
    "active_operators_final_std": 137.7526,
    "qualified_score_mean": 0.2182,
    "qualified_score_std": 0.0219,
    "gini_mean": 0.2118,
    "gini_std": 0.0066,
    "retention_pct_mean": 12.715,
    "retention_pct_std": 0.8374,
    "false_positive_rate_mean": 0.0216,
    "false_positive_rate_std": 0.0005,
    "slash_rate_mean": 0.016,
    "slash_rate_std": 0.0018,
    "realism_q4_2026_milestone_hit_mean": 0.0,
    "realism_q4_2026_milestone_hit_std": 0.0,
    "realism_q4_2026_milestone_hit_pct_true": 0.0,
    "nrr_blended_mean": 0.0944,
    "nrr_blended_std": 0.0298,
    "peak_price_mean": 29.0816,
    "peak_price_std": 4.8214,
    "customer_count_active_mean": 106.1,
    "customer_count_active_std": 16.667,
    "retention_score_mean": 0.2313,
    "retention_score_std": 0.0152,
    "realism_q4_2026_arr_usd_mean": 204138.6,
    "realism_q4_2026_arr_usd_st
```

### milestone
```json
{
  "jcurve_q4_combo_milestone": {
    "n_runs": 50,
    "amm_usd_pool_final_mean": 558258.92,
    "amm_usd_pool_final_std": 463458.4424,
    "quality_score_mean": 0.8682,
    "quality_score_std": 0.0446,
    "gini_score_mean": 0.306,
    "gini_score_std": 0.164,
    "total_operators_ever_mean": 24295.9,
    "total_operators_ever_std": 1456.1847,
    "realism_final_arr_usd_mean": 4519410.96,
    "realism_final_arr_usd_std": 3891219.7656,
    "realism_customer_count_in_band_mean": 1.0,
    "realism_customer_count_in_band_std": 0.0,
    "realism_customer_count_in_band_pct_true": 1.0,
    "revenue_score_mean": 0.0774,
    "revenue_score_std": 0.0446,
    "sentiment_resilience_mean": 1.8007,
    "sentiment_resilience_std": 2.1927,
    "realism_q4_2026_customers_mean": 4.12,
    "realism_q4_2026_customers_std": 0.3816,
    "persona_diversity_index_mean": 0.0,
    "persona_diversity_index_std": 0.0,
    "amm_token_pool_final_mean": 186278.34,
    "amm_token_pool_final_std": 146427.1869,
    "final_price_mean": 13.1612,
    "final_price_std": 14.6413,
    "cumulative_revenue_mean": 3869591.88,
    "cumulative_revenue_std": 2229110.7052,
    "active_operators_final_mean": 5927.66,
    "active_operators_final_std": 1061.7517,
    "qualified_score_mean": 0.2537,
    "qualified_score_std": 0.2717,
    "gini_mean": 0.4164,
    "gini_std": 0.0984,
    "retention_pct_mean": 24.426,
    "retention_pct_std": 4.2522,
    "false_positive_rate_mean": 0.018,
    "false_positive_rate_std": 0.0013,
    "slash_rate_mean": 0.0264,
    "slash_rate_std": 0.0089,
    "realism_q4_2026_milestone_hit_mean": 0.02,
    "realism_q4_2026_milestone_hit_std": 0.14,
    "realism_q4_2026_milestone_hit_pct_true": 0.02,
    "nrr_blended_mean": 0.5076,
    "nrr_blended_std": 0.3537,
    "peak_price_mean": 13.4667,
    "peak_price_std": 14.3754,
    "customer_count_active_mean": 68.6,
    "customer_count_active_std": 12.8717,
    "retention_score_mean": 0.444,
    "retention_score_std": 0.0774,
    "realism_q4_2026_arr_usd_mean": 399927.84,
    "realism_q4_2026_arr_usd_std": 31120.0772,
    "realism_final_customer_count_mean": 68.6,
    "realism_final_customer_count_std": 12.8717,
    "node_roi_score_mean": 0.5,
    "node_roi_score_std": 0.0,
    "customer_count_total_mean": 73.02,
    "customer_count_total_std": 13.2627,
    "cumulative_referrals_mean": 0.0,
    "cumulative_referrals_std": 0.0,
    "t4_plus_operators_mean": 1268.4,
    "t4_plus_operators_std": 1358.3648,
    "validator_integrity_score_mean": 0.8199,
    "validator_integrity_score_std": 0.0126,
    "stability_score_mean": 0.4844,
    "stability_score_std": 0.3827,
    "top_3_concentration_pct_mean": 32.37,
    "top_3_concentration_pct_std": 8.597,
    "score_mean": 0.4214,
    "score_std": 0.0522,
    "realism_arr_in_band_mean": 0.54,
    "realism_arr_in_band_std": 0.4984,
    "realism_arr_in_band_pct_true": 0.54,
    "capacity_utilization_score_mean": 0.9937,
    "capacity_utilization_score_std": 0.0319
  }
}
```

