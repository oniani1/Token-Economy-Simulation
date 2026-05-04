# CrowdBrain v5 — Iteration 2 Report (Pareto frontier sweep)

**Goal:** close the 0.34 composite gap between v5 baseline (0.535) and v4_no_personas (0.7575) by tuning the 3 biggest sub-score drags identified in REPORT_v5.md.

**Three phases, 18 cells total, MC=20.**

**Reference points:**
- v4_no_personas: composite **0.7575**, cum revenue **$73.0M** @ 36mo
- v5 baseline (unlock_revenue_gated, current winner): composite **0.5350**, cum revenue **$26.3M** @ 36mo

## Phase 1 — Combo + Diagnostic

Tests whether the 4 v5 track winners compose constructively when stacked, and confirms how much of the v5 gap is structural vs. tunable.

### Phase 1 cells

| Cell | Composite | Cum revenue | T4+ ops | Retention | Cap util | Stability |
|---|---|---|---|---|---|---|
| `v5_layers_off` | 0.772 ± 0.009 | $83.9M | 21,968 | 0.849 | 0.004 | 0.532 |
| `v5_winner_combo` | 0.560 ± 0.065 | $34.7M | 6,457 | 0.460 | 0.046 | 0.022 |
| `v5_combo_no_intel` | 0.520 ± 0.058 | $24.2M | 6,447 | 0.458 | 0.046 | 0.023 |

**Composability:** combo composite 0.5599 vs single-track winners 0.535–0.574. Layers-off composite 0.7723 (matches v4_no_personas reference).

## Phase 2 — Revenue threshold sweep

The biggest single sub-score drag (-0.095 from revenue). The current winner uses $250K / $1M / $5M ARR thresholds; this phase tests both looser (faster unlock = more revenue) and tighter (more quality = less revenue but higher score density).

### Phase 2 cells

| Cell | Composite | Cum revenue | T4+ ops | Retention | Cap util | Stability |
|---|---|---|---|---|---|---|
| `unlock_revenue_gated_ref` | 0.560 ± 0.065 | $34.7M | 6,457 | 0.460 | 0.046 | 0.022 |
| `unlock_hybrid` | 0.527 ± 0.106 | $31.6M | 5,501 | 0.444 | 0.049 | 0.057 |
| `unlock_very_loose` | 0.524 ± 0.104 | $31.3M | 5,443 | 0.444 | 0.049 | 0.049 |
| `unlock_op_low` | 0.519 ± 0.099 | $31.2M | 5,447 | 0.440 | 0.068 | 0.015 |
| `unlock_loose` | 0.513 ± 0.101 | $30.2M | 4,999 | 0.432 | 0.039 | 0.065 |
| `unlock_tight` | 0.512 ± 0.098 | $30.1M | 5,128 | 0.435 | 0.056 | 0.061 |

## Phase 3 — Hardware stake + node provisioning

Two-axis sweep: hardware stake $300–500 (memo's full range) and ops_per_node_target 2K–12K (current 2K leaves capacity_utilization at 0.024).

### Phase 3 cells

| Cell | Composite | Cum revenue | T4+ ops | Retention | Cap util | Stability |
|---|---|---|---|---|---|---|
| `stake_300` | 0.597 ± 0.087 | $41.0M | 8,214 | 0.499 | 0.042 | 0.090 |
| `stake_350` | 0.585 ± 0.064 | $38.1M | 7,313 | 0.486 | 0.043 | 0.048 |
| `stake_400` | 0.560 ± 0.065 | $34.7M | 6,457 | 0.460 | 0.046 | 0.022 |
| `nodes_2k` | 0.560 ± 0.065 | $34.7M | 6,457 | 0.460 | 0.046 | 0.022 |
| `nodes_8k` | 0.533 ± 0.065 | $30.5M | 6,251 | 0.457 | 0.000 | 0.046 |
| `nodes_12k` | 0.525 ± 0.071 | $29.3M | 5,872 | 0.449 | 0.000 | 0.056 |
| `nodes_4k` | 0.520 ± 0.086 | $29.6M | 5,641 | 0.442 | 0.000 | 0.119 |
| `stake_450` | 0.517 ± 0.084 | $30.0M | 4,884 | 0.434 | 0.048 | 0.062 |
| `stake_500` | 0.475 ± 0.096 | $26.9M | 3,599 | 0.410 | 0.048 | 0.085 |

## Pareto frontier — composite vs cumulative revenue

A cell is Pareto-optimal if no other cell beats it on BOTH composite score AND cumulative revenue. Pick a cell on the frontier based on which metric matters more in the conversation you're having.

| Cell | Phase | Composite | Cum revenue | T4+ ops |
|---|---|---|---|---|
| `v5_layers_off` | phase1 | 0.772 ± 0.009 | $83.9M | 21,968 |

## Best-of-each-metric

- **Highest composite**: `v5_layers_off` (phase1) — 0.7723 ± 0.0086
- **Highest revenue**: `v5_layers_off` (phase1) — $83.9M
- vs v5 baseline (0.535 / $26.3M): composite Δ +0.2373 (+44.4%), revenue Δ $57.6M (+219%)
- vs v4_no_personas (0.7575): composite Δ +0.0148 (gap closed)

## Findings

1. **Combo composability** — `v5_winner_combo` (all 4 track winners stacked) scored 0.5599. Single-track winners alone scored 0.535–0.574 in iter1. Combo is constructive (winners stack).
2. **Revenue threshold optimum** — `unlock_revenue_gated_ref` wins Phase 2 at composite 0.5599. This confirms the iter1 winner.
3. **Hardware stake optimum** — `stake_300` is best at composite 0.5970. Memo's $300-500 range; sim picked: $300.
4. **Node provisioning optimum** — `nodes_2k` wins at composite 0.5599, capacity util 0.046 (was 0.024 in v5 baseline).

## Appendix — All cell results

### phase1
```json
{
  "v5_winner_combo": {
    "n_runs": 20,
    "retention_pct_mean": 25.295,
    "retention_pct_std": 2.5736,
    "score_mean": 0.5599,
    "score_std": 0.0646,
    "nrr_blended_mean": 0.1535,
    "nrr_blended_std": 0.0428,
    "gini_mean": 0.2576,
    "gini_std": 0.0113,
    "qualified_score_mean": 0.9337,
    "qualified_score_std": 0.1627,
    "slash_rate_mean": 0.0339,
    "slash_rate_std": 0.0032,
    "amm_token_pool_final_mean": 220368.1,
    "amm_token_pool_final_std": 62541.8499,
    "active_operators_final_mean": 31365.05,
    "active_operators_final_std": 3800.4641,
    "node_roi_score_mean": 0.5,
    "node_roi_score_std": 0.0,
    "peak_price_mean": 24.9282,
    "peak_price_std": 10.9949,
    "final_price_mean": 24.9282,
    "final_price_std": 10.9949,
    "gini_score_mean": 0.5707,
    "gini_score_std": 0.0189,
    "cumulative_referrals_mean": 0.0,
    "cumulative_referrals_std": 0.0,
    "retention_score_mean": 0.4599,
    "retention_score_std": 0.0468,
    "stability_score_mean": 0.0216,
    "stability_score_std": 0.0477,
    "sentiment_resilience_mean": 3.0071,
    "sentiment_resilience_std": 3.9098,
    "amm_usd_pool_final_mean": 4856551.75,
    "amm_usd_pool_final_std": 1158497.1377,
    "cumulative_revenue_mean": 34678875.7,
    "cumulative_revenue_std": 8257525.0531,
    "quality_score_mean": 0.8303,
    "quality_score_std": 0.016,
    "t4_plus_operators_mean": 6457.4,
    "t4_plus_operators_std": 1889.4891,
    "total_operators_ever_mean": 123869.1,
    "total_operators_ever_std": 6118.7729,
    "customer_count_total_mean": 431.45,
    "customer_count_total_std": 48.9035,
    "revenue_score_mean": 0.6908,
    "revenue_score_std": 0.1595,
    "customer_count_active_mean": 264.3,
    "customer_count_active_std": 40.6228,
    "top_3_concentration_pct_mean": 7.14,
    "top_3_concentration_pct_std": 1.5737,
    "persona_diversity_index_mean": 0.0,
    "persona_diversity_index_std": 0.0,
    "validator_integrity_score_mean": 0.6165,
    "validator_integrity_score_std": 0.0201,
    "false_positive_rate_mean": 0.0384,
    "false_positive_rate_std": 0.002,
    "capacity_utilization_score_mean": 0.0465,
    "capacity_utilization_score_std": 0.0742
  },
  "v5_combo_no_intel": {
    "n_runs": 20,
    "retention_pct_mean": 25.19,
    "retention_pct_std": 2.5209,
    "score_mean": 0.5201,
    "score_std": 0.0584,
    "nrr_blended_mean": 0.1543,
    "nrr_blended_std": 0.0428,
    "gini_mean": 0.2454,
    "gini_std": 0.0113,
    "qualified_score_mean": 0.9337,
    "qualified_score_std": 0.1627,
    "slash_rate_mean": 0.0343,
    "slash_rate_std": 0.003,
    "amm_token_pool_final_mean": 224250.35,
    "amm_token_pool_final_std": 63499.5358,
    "active_operators_final_mean": 31141.9,
    "active_operators_final_std": 3623.3294,
    "node_roi_score_mean": 0.5,
    "node_roi_score_std": 0.0,
    "peak_price_mean": 24.1364,
    "peak_price_std": 10.7096,
    "final_price_mean": 24.1364,
    "final_price_std": 10.7096,
    "gini_score_mean": 0.591,
    "gini_score_std": 0.0189,
    "cumulative_referrals_mean": 0.0,
    "cumulative_referrals_std": 0.0,
    "retention_score_mean": 0.4581,
    "retention_score_std": 0.0458,
    "stability_score_mean": 0.0232,
    "stability_score_std": 0.0517,
    "sentiment_resilience_mean": 3.461,
    "sentiment_resilience_std": 2.9631,
    "amm_usd_pool_final_mean": 4776250.15,
    "amm_usd_pool_final_std": 1150602.7369,
    "cumulative_revenue_mean": 24164721.9,
    "cumulative_revenue_std": 6294754.75,
    "quality_score_mean": 0.8286,
    "quality_score_std": 0.015,
    "t4_plus_operators_mean": 6447.0,
    "t4_plus_operators_std": 1899.5068,
    "total_operators_ever_mean": 123524.1,
    "total_operators_ever_std": 5925.8614,
    "customer_count_total_mean": 426.3,
    "customer_count_total_std": 47.4701,
    "revenue_score_mean": 0.4833,
    "revenue_score_std": 0.1259,
    "customer_count_active_mean": 259.45,
    "customer_count_active_std": 39.2358,
    "top_3_concentration_pct_mean": 7.25,
    "top_3_concentration_pct_std": 1.5174,
    "persona_diversity_index_mean": 0.0,
    "persona_diversity_index_std": 0.0,
    "validator_integrity_score_mean": 0.6159,
    "validator_integrity_score_std": 0.02,
    "false_positive_rate_mean": 0.0384,
    "false_positive_rate_std": 0.002,
    "capacity_utilization_score_mean": 0.0465,
    "capacity_utilization_score_std": 0.0742
  },
  "v5_layers_off": {
    "n_runs": 20,
    "retention_pct_mean": 46.71,
    "retention_pct_std": 1.396,
    "score_mean": 0.7723,
    "score_std": 0.0086,
    "nrr_blended_mean": 0.4511,
    "nrr_blended_std": 0.0897,
    "gini_mean": 0.2808,
    "gini_std": 0.0117,
    "qualified_score_mean": 1.0,
    "qualified_score_std": 0.0,
    "slash_rate_mean": 0.02,
    "slash_rate_std": 0.0005,
    "amm_token_pool_final_mean": 86980.4,
    "amm_token_pool_final_std": 9690.8276,
    "active_operators_final_mean": 57441.75,
    "active_operators_final_std": 4582.3795,
    "node_roi_score_mean": 0.5,
    "node_
```

### phase2
```json
{
  "unlock_very_loose": {
    "n_runs": 20,
    "retention_pct_mean": 24.39,
    "retention_pct_std": 3.0458,
    "score_mean": 0.5244,
    "score_std": 0.1044,
    "nrr_blended_mean": 0.1575,
    "nrr_blended_std": 0.0386,
    "gini_mean": 0.2764,
    "gini_std": 0.042,
    "qualified_score_mean": 0.8242,
    "qualified_score_std": 0.3482,
    "slash_rate_mean": 0.0355,
    "slash_rate_std": 0.006,
    "amm_token_pool_final_mean": 333778.35,
    "amm_token_pool_final_std": 335704.225,
    "active_operators_final_mean": 29974.35,
    "active_operators_final_std": 5211.7469,
    "node_roi_score_mean": 0.5,
    "node_roi_score_std": 0.0,
    "peak_price_mean": 21.891,
    "peak_price_std": 13.7013,
    "final_price_mean": 21.8595,
    "final_price_std": 13.7498,
    "gini_score_mean": 0.5393,
    "gini_score_std": 0.0701,
    "cumulative_referrals_mean": 0.0,
    "cumulative_referrals_std": 0.0,
    "retention_score_mean": 0.4435,
    "retention_score_std": 0.0553,
    "stability_score_mean": 0.0491,
    "stability_score_std": 0.158,
    "sentiment_resilience_mean": 1.3084,
    "sentiment_resilience_std": 2.0539,
    "amm_usd_pool_final_mean": 4350599.7,
    "amm_usd_pool_final_std": 1712253.1115,
    "cumulative_revenue_mean": 31280886.85,
    "cumulative_revenue_std": 11191647.2743,
    "quality_score_mean": 0.8223,
    "quality_score_std": 0.03,
    "t4_plus_operators_mean": 5443.4,
    "t4_plus_operators_std": 2731.0815,
    "total_operators_ever_mean": 122177.2,
    "total_operators_ever_std": 8575.849,
    "customer_count_total_mean": 432.9,
    "customer_count_total_std": 55.873,
    "revenue_score_mean": 0.619,
    "revenue_score_std": 0.2103,
    "customer_count_active_mean": 273.0,
    "customer_count_active_std": 39.2989,
    "top_3_concentration_pct_mean": 7.49,
    "top_3_concentration_pct_std": 1.9741,
    "persona_diversity_index_mean": 0.0,
    "persona_diversity_index_std": 0.0,
    "validator_integrity_score_mean": 0.6085,
    "validator_integrity_score_std": 0.0283,
    "false_positive_rate_mean": 0.0392,
    "false_positive_rate_std": 0.0028,
    "capacity_utilization_score_mean": 0.049,
    "capacity_utilization_score_std": 0.0705
  },
  "unlock_loose": {
    "n_runs": 20,
    "retention_pct_mean": 23.755,
    "retention_pct_std": 3.0956,
    "score_mean": 0.5133,
    "score_std": 0.1008,
    "nrr_blended_mean": 0.1665,
    "nrr_blended_std": 0.0486,
    "gini_mean": 0.2738,
    "gini_std": 0.0352,
    "qualified_score_mean": 0.7805,
    "qualified_score_std": 0.3574,
    "slash_rate_mean": 0.0355,
    "slash_rate_std": 0.0043,
    "amm_token_pool_final_mean": 354636.2,
    "amm_token_pool_final_std": 321654.1129,
    "active_operators_final_mean": 29216.0,
    "active_operators_final_std": 5107.9679,
    "node_roi_score_mean": 0.5,
    "node_roi_score_std": 0.0,
    "peak_price_mean": 20.4703,
    "peak_price_std": 13.2169,
    "final_price_mean": 20.4352,
    "final_price_std": 13.2689,
    "gini_score_mean": 0.5437,
    "gini_score_std": 0.0586,
    "cumulative_referrals_mean": 0.0,
    "cumulative_referrals_std": 0.0,
    "retention_score_mean": 0.4319,
    "retention_score_std": 0.0561,
    "stability_score_mean": 0.0654,
    "stability_score_std": 0.1725,
    "sentiment_resilience_mean": 2.1883,
    "sentiment_resilience_std": 4.0379,
    "amm_usd_pool_final_mean": 4170307.6,
    "amm_usd_pool_final_std": 1744644.6307,
    "cumulative_revenue_mean": 30168397.2,
    "cumulative_revenue_std": 10555782.9764,
    "quality_score_mean": 0.8224,
    "quality_score_std": 0.0215,
    "t4_plus_operators_mean": 4999.0,
    "t4_plus_operators_std": 2693.9447,
    "total_operators_ever_mean": 122310.45,
    "total_operators_ever_std": 8093.5017,
    "customer_count_total_mean": 425.7,
    "customer_count_total_std": 65.9061,
    "revenue_score_mean": 0.6034,
    "revenue_score_std": 0.2111,
    "customer_count_active_mean": 264.8,
    "customer_count_active_std": 46.629,
    "top_3_concentration_pct_mean": 8.135,
    "top_3_concentration_pct_std": 3.0968,
    "persona_diversity_index_mean": 0.0,
    "persona_diversity_index_std": 0.0,
    "validator_integrity_score_mean": 0.6024,
    "validator_integrity_score_std": 0.0299,
    "false_positive_rate_mean": 0.0398,
    "false_positive_rate_std": 0.003,
    "capacity_utilization_score_mean": 0.0387,
    "capacity_utilization_score_std": 0.0531
  },
  "unlock_revenue_gated_ref": {
    "n_runs": 20,
    "retention_pct_mean": 25.295,
    "retention_pct_std": 2.5736,
    "score_mean": 0.5599,
    "score_std": 0.0646,
    "nrr_blended_mean": 0.1535,
    "nrr_blended_std": 0.0428,
    "gini_mean": 0.2576,
    "gini_std": 0.0113,
    "qualified_score_mean": 0.9337,
    "qualified_score_std": 0.1627,
    "slash_rate_mean": 0.0339,
    "slash_rate_std": 0.0032,
    "amm_token_pool_final_mean": 220368.1,
    "amm_token_pool_final_std": 62541.8499,
    "active_operators_final_mean": 31365.05,
    "active_operators_final_std": 3800.4641,
    "node_roi_score_m
```

### phase3
```json
{
  "stake_300": {
    "n_runs": 20,
    "retention_pct_mean": 27.47,
    "retention_pct_std": 3.3215,
    "score_mean": 0.597,
    "score_std": 0.087,
    "nrr_blended_mean": 0.1889,
    "nrr_blended_std": 0.0613,
    "gini_mean": 0.2722,
    "gini_std": 0.022,
    "qualified_score_mean": 0.9348,
    "qualified_score_std": 0.186,
    "slash_rate_mean": 0.032,
    "slash_rate_std": 0.0032,
    "amm_token_pool_final_mean": 199586.65,
    "amm_token_pool_final_std": 99947.6159,
    "active_operators_final_mean": 33997.8,
    "active_operators_final_std": 5127.8186,
    "node_roi_score_mean": 0.5,
    "node_roi_score_std": 0.0,
    "peak_price_mean": 34.1239,
    "peak_price_std": 12.7555,
    "final_price_mean": 34.1239,
    "final_price_std": 12.7555,
    "gini_score_mean": 0.5463,
    "gini_score_std": 0.0366,
    "cumulative_referrals_mean": 0.0,
    "cumulative_referrals_std": 0.0,
    "retention_score_mean": 0.4995,
    "retention_score_std": 0.0603,
    "stability_score_mean": 0.0897,
    "stability_score_std": 0.1127,
    "sentiment_resilience_mean": 3.0404,
    "sentiment_resilience_std": 3.8116,
    "amm_usd_pool_final_mean": 5673847.3,
    "amm_usd_pool_final_std": 1389725.3446,
    "cumulative_revenue_mean": 40981659.75,
    "cumulative_revenue_std": 10938942.6369,
    "quality_score_mean": 0.8401,
    "quality_score_std": 0.0158,
    "t4_plus_operators_mean": 8214.0,
    "t4_plus_operators_std": 2658.6749,
    "total_operators_ever_mean": 123346.8,
    "total_operators_ever_std": 7400.2395,
    "customer_count_total_mean": 427.65,
    "customer_count_total_std": 55.378,
    "revenue_score_mean": 0.8023,
    "revenue_score_std": 0.1987,
    "customer_count_active_mean": 270.05,
    "customer_count_active_std": 46.3934,
    "top_3_concentration_pct_mean": 7.035,
    "top_3_concentration_pct_std": 1.1499,
    "persona_diversity_index_mean": 0.0,
    "persona_diversity_index_std": 0.0,
    "validator_integrity_score_mean": 0.6377,
    "validator_integrity_score_std": 0.0205,
    "false_positive_rate_mean": 0.0362,
    "false_positive_rate_std": 0.002,
    "capacity_utilization_score_mean": 0.0421,
    "capacity_utilization_score_std": 0.0718
  },
  "stake_350": {
    "n_runs": 20,
    "retention_pct_mean": 26.75,
    "retention_pct_std": 2.6768,
    "score_mean": 0.5845,
    "score_std": 0.0642,
    "nrr_blended_mean": 0.1816,
    "nrr_blended_std": 0.0592,
    "gini_mean": 0.2641,
    "gini_std": 0.0098,
    "qualified_score_mean": 0.9517,
    "qualified_score_std": 0.1036,
    "slash_rate_mean": 0.0329,
    "slash_rate_std": 0.0026,
    "amm_token_pool_final_mean": 193495.85,
    "amm_token_pool_final_std": 45934.969,
    "active_operators_final_mean": 33241.15,
    "active_operators_final_std": 4237.0436,
    "node_roi_score_mean": 0.5,
    "node_roi_score_std": 0.0,
    "peak_price_mean": 30.5272,
    "peak_price_std": 11.0841,
    "final_price_mean": 30.5272,
    "final_price_std": 11.0841,
    "gini_score_mean": 0.5598,
    "gini_score_std": 0.0164,
    "cumulative_referrals_mean": 0.0,
    "cumulative_referrals_std": 0.0,
    "retention_score_mean": 0.4865,
    "retention_score_std": 0.0486,
    "stability_score_mean": 0.048,
    "stability_score_std": 0.0597,
    "sentiment_resilience_mean": 0.9995,
    "sentiment_resilience_std": 2.0965,
    "amm_usd_pool_final_mean": 5418964.15,
    "amm_usd_pool_final_std": 1077973.6516,
    "cumulative_revenue_mean": 38072839.75,
    "cumulative_revenue_std": 9193956.2474,
    "quality_score_mean": 0.8353,
    "quality_score_std": 0.0128,
    "t4_plus_operators_mean": 7312.85,
    "t4_plus_operators_std": 2143.5409,
    "total_operators_ever_mean": 123985.1,
    "total_operators_ever_std": 6571.3179,
    "customer_count_total_mean": 452.15,
    "customer_count_total_std": 35.5222,
    "revenue_score_mean": 0.7599,
    "revenue_score_std": 0.1817,
    "customer_count_active_mean": 294.55,
    "customer_count_active_std": 22.5066,
    "top_3_concentration_pct_mean": 6.53,
    "top_3_concentration_pct_std": 0.9675,
    "persona_diversity_index_mean": 0.0,
    "persona_diversity_index_std": 0.0,
    "validator_integrity_score_mean": 0.6275,
    "validator_integrity_score_std": 0.0196,
    "false_positive_rate_mean": 0.0372,
    "false_positive_rate_std": 0.002,
    "capacity_utilization_score_mean": 0.0425,
    "capacity_utilization_score_std": 0.0704
  },
  "stake_400": {
    "n_runs": 20,
    "retention_pct_mean": 25.295,
    "retention_pct_std": 2.5736,
    "score_mean": 0.5599,
    "score_std": 0.0646,
    "nrr_blended_mean": 0.1535,
    "nrr_blended_std": 0.0428,
    "gini_mean": 0.2576,
    "gini_std": 0.0113,
    "qualified_score_mean": 0.9337,
    "qualified_score_std": 0.1627,
    "slash_rate_mean": 0.0339,
    "slash_rate_std": 0.0032,
    "amm_token_pool_final_mean": 220368.1,
    "amm_token_pool_final_std": 62541.8499,
    "active_operators_final_mean": 31365.05,
    "active_operators_final_std": 3800.4641,
    "node_roi_score_mean": 0.5,
    "node
```

