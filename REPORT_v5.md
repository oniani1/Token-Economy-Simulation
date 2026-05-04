# CrowdBrain v5 Token Economy — Simulation Report
**Source memo**: `crowdbrain-memo-v5.docx` (replaces `crowdtrain-memo-v12.docx`)
**Baseline**: v4_no_personas winner config + v5 layers (tier_unlock, node_providers, geography, points_to_token) + v5 customer extension (multi-year design partner contracts)
**Horizon**: 36 months
**Workers**: parallel MC across CPU cores

## TL;DR — Track-by-track headline findings

- **Track 1 — Tier-unlock policy** (6 cells × MC=10): winner = `unlock_revenue_gated` (score 0.535), worst = `unlock_op_gated` (0.484), spread = 0.051
- **Track 2 — Points-to-tokens transition** (4 cells × MC=10): winner = `transition_m12` (score 0.511), worst = `points_only` (0.395), spread = 0.116
- **Track 3 — Three-stakeholder loop** (6 cells × MC=10): winner = `nodes_low_bond` (score 0.535), worst = `nodes_community_heavy` (0.468), spread = 0.067
- **Track 4 — Macro stress + milestone path** (8 cells × MC=10): winner = `intelligence_library` (score 0.574), worst = `mvp_slip` (0.259), spread = 0.315

## Track 1 — Tier-unlock policy

v5 memo says T0–T2 launch immediately and T3–T5 unlock conditionally with scale, but doesn't specify thresholds. This sweep tests 6 different gating rules.

| Cell | Composite | Cum revenue | T4+ ops | NRR | Active customers |
|---|---|---|---|---|---|
| unlock_revenue_gated | 0.535 ± 0.039 | $26.3M | 6,936 | 0.162 ± 0.057 | 286 |
| unlock_time_gated | 0.529 ± 0.035 | $24.3M | 6,520 | 0.146 ± 0.038 | 282 |
| unlock_strict | 0.517 ± 0.053 | $24.3M | 6,234 | 0.150 ± 0.035 | 303 |
| unlock_baseline | 0.496 ± 0.088 | $22.7M | 5,813 | 0.147 ± 0.062 | 264 |
| unlock_demand_gated | 0.496 ± 0.088 | $22.7M | 5,813 | 0.147 ± 0.062 | 264 |
| unlock_op_gated | 0.484 ± 0.082 | $21.6M | 5,559 | 0.141 ± 0.046 | 254 |

**Track 1 winner**: `unlock_revenue_gated`
- Composite 0.5350 ± 0.0390
- Cumulative revenue $26.3M
- T4+ operators: 6936
- NRR: 0.162


## Track 2 — Points → Tokens Transition

v5 memo: 'Operators begin with points and transition to tokens later.' Tests when the cutover should happen. All cells use 1:1 conversion at cutover.

| Cell | Composite | Cum revenue | T4+ ops | NRR |
|---|---|---|---|---|
| transition_m12 | 0.511 ± 0.046 | $22.4M | 6,069 | 0.136 ± 0.043 |
| transition_m18 | 0.492 ± 0.084 | $21.8M | 5,269 | 0.152 ± 0.028 |
| transition_revenue_1m | 0.483 ± 0.087 | $20.8M | 4,822 | 0.148 ± 0.035 |
| points_only | 0.395 ± 0.064 | $12.6M | 1,698 | 0.145 ± 0.031 |

## Track 3 — Three-Stakeholder Loop (Bonded Node Providers)

v5 elevates node-providers to first-class economic actors with bonded stakes, operator reporting, and dispute resolution. Tests bond size + facility/community split.

| Cell | Composite | Cum revenue | T4+ ops | NRR |
|---|---|---|---|---|
| nodes_low_bond | 0.535 ± 0.039 | $26.3M | 6,936 | 0.162 ± 0.057 |
| nodes_med_bond | 0.535 ± 0.039 | $26.3M | 6,936 | 0.162 ± 0.057 |
| nodes_high_bond | 0.535 ± 0.039 | $26.3M | 6,936 | 0.162 ± 0.057 |
| nodes_baseline | 0.500 ± 0.084 | $23.4M | 5,762 | 0.140 ± 0.050 |
| nodes_community_only | 0.478 ± 0.097 | $20.9M | 5,044 | 0.149 ± 0.044 |
| nodes_community_heavy | 0.468 ± 0.083 | $20.0M | 4,738 | 0.128 ± 0.055 |

## Track 4 — Macro Stress + Milestone Path Probability

Eight scenarios spanning funding-winter, wage-anchor (Tesla/1X), geographic shocks, MVP slip, and Intelligence Library activation. These feed the risk slide of the deck.

| Cell | Composite | Cum revenue | T4+ ops | NRR | Active ops |
|---|---|---|---|---|---|
| intelligence_library | 0.574 ± 0.047 | $37.1M | 6,811 | 0.161 ± 0.055 | 0 |
| path_baseline | 0.535 ± 0.039 | $26.3M | 6,936 | 0.162 ± 0.057 | 0 |
| tesla_hiring | 0.532 ± 0.077 | $26.7M | 7,062 | 0.145 ± 0.032 | 0 |
| geo_shock_kenya | 0.505 ± 0.064 | $23.4M | 5,880 | 0.151 ± 0.056 | 0 |
| geo_shock_philippines | 0.472 ± 0.085 | $20.2M | 4,931 | 0.153 ± 0.032 | 0 |
| geo_shock_georgia | 0.446 ± 0.119 | $19.5M | 4,399 | 0.144 ± 0.036 | 0 |
| funding_winter | 0.294 ± 0.007 | $3.2M | 0 | 0.162 ± 0.105 | 0 |
| mvp_slip | 0.259 ± 0.003 | $1.2M | 0 | 0.879 ± 0.189 | 0 |

**Funding winter impact**: composite 0.535 → 0.294 (Δ -0.241); revenue $26.3M → $3.2M (Δ -88%).

**Geographic shock sensitivity** (which region is most load-bearing):

- geo_shock_georgia: composite 0.446, revenue $19.5M
- geo_shock_philippines: composite 0.472, revenue $20.2M
- geo_shock_kenya: composite 0.505, revenue $23.4M


## Strategic conclusions

1. **Recommended launch tier-unlock policy**: `unlock_revenue_gated`. Highest composite among 6 gating rules tested.
2. **Path-baseline composite**: 0.535 ± 0.039 at MC=10.
3. **All v5 layers have measurable cost vs v4 baseline** — the question for each design choice is whether the realism gain is worth the composite-score drag. Use this sim to pick the layers where the realism cost is justified.
4. **Defensive posture**: weakest scenarios in Track 4 should be planned around explicitly in the GTM and treasury runway, not modeled as tail risk.

## Appendix — All cell results

### track1
```json
{
  "unlock_baseline": {
    "n_runs": 10,
    "gini_score_mean": 0.5713,
    "gini_score_std": 0.0578,
    "revenue_score_mean": 0.4543,
    "revenue_score_std": 0.1555,
    "sentiment_resilience_mean": 2.9485,
    "sentiment_resilience_std": 3.7303,
    "amm_usd_pool_final_mean": 4385315.9,
    "amm_usd_pool_final_std": 1473249.8632,
    "gini_mean": 0.2572,
    "gini_std": 0.0347,
    "validator_integrity_score_mean": 0.6241,
    "validator_integrity_score_std": 0.0238,
    "active_operators_final_mean": 30504.5,
    "active_operators_final_std": 4306.6878,
    "retention_pct_mean": 24.7,
    "retention_pct_std": 2.7148,
    "stability_score_mean": 0.0285,
    "stability_score_std": 0.0572,
    "total_operators_ever_mean": 123153.7,
    "total_operators_ever_std": 5492.7809,
    "nrr_blended_mean": 0.147,
    "nrr_blended_std": 0.0616,
    "customer_count_active_mean": 263.7,
    "customer_count_active_std": 39.588,
    "t4_plus_operators_mean": 5812.6,
    "t4_plus_operators_std": 2799.9016,
    "capacity_utilization_score_mean": 0.0,
    "capacity_utilization_score_std": 0.0,
    "slash_rate_mean": 0.0334,
    "slash_rate_std": 0.0026,
    "peak_price_mean": 21.4015,
    "peak_price_std": 12.8071,
    "final_price_mean": 21.4015,
    "final_price_std": 12.8071,
    "qualified_score_mean": 0.8451,
    "qualified_score_std": 0.283,
    "top_3_concentration_pct_mean": 7.29,
    "top_3_concentration_pct_std": 1.6275,
    "quality_score_mean": 0.8328,
    "quality_score_std": 0.0131,
    "retention_score_mean": 0.4489,
    "retention_score_std": 0.0495,
    "customer_count_total_mean": 427.4,
    "customer_count_total_std": 47.9983,
    "amm_token_pool_final_mean": 267594.6,
    "amm_token_pool_final_std": 130034.047,
    "cumulative_referrals_mean": 0.0,
    "cumulative_referrals_std": 0.0,
    "persona_diversity_index_mean": 0.0,
    "persona_diversity_index_std": 0.0,
    "false_positive_rate_mean": 0.0376,
    "false_positive_rate_std": 0.0024,
    "cumulative_revenue_mean": 22713466.0,
    "cumulative_revenue_std": 7776424.8052,
    "node_roi_score_mean": 0.5,
    "node_roi_score_std": 0.0,
    "score_mean": 0.4964,
    "score_std": 0.0883
  },
  "unlock_op_gated": {
    "n_runs": 10,
    "gini_score_mean": 0.5552,
    "gini_score_std": 0.066,
    "revenue_score_mean": 0.4314,
    "revenue_score_std": 0.1323,
    "sentiment_resilience_mean": 1.2704,
    "sentiment_resilience_std": 0.9946,
    "amm_usd_pool_final_mean": 4243327.9,
    "amm_usd_pool_final_std": 1398910.6741,
    "gini_mean": 0.2669,
    "gini_std": 0.0396,
    "validator_integrity_score_mean": 0.6245,
    "validator_integrity_score_std": 0.0099,
    "active_operators_final_mean": 29739.1,
    "active_operators_final_std": 5118.4464,
    "retention_pct_mean": 24.34,
    "retention_pct_std": 2.7343,
    "stability_score_mean": 0.0092,
    "stability_score_std": 0.0276,
    "total_operators_ever_mean": 121338.5,
    "total_operators_ever_std": 8600.7007,
    "nrr_blended_mean": 0.1415,
    "nrr_blended_std": 0.0459,
    "customer_count_active_mean": 253.8,
    "customer_count_active_std": 48.1265,
    "t4_plus_operators_mean": 5559.3,
    "t4_plus_operators_std": 2604.6234,
    "capacity_utilization_score_mean": 0.0444,
    "capacity_utilization_score_std": 0.0648,
    "slash_rate_mean": 0.0343,
    "slash_rate_std": 0.0027,
    "peak_price_mean": 19.9628,
    "peak_price_std": 11.0402,
    "final_price_mean": 19.9628,
    "final_price_std": 11.0402,
    "qualified_score_mean": 0.8117,
    "qualified_score_std": 0.2934,
    "top_3_concentration_pct_mean": 8.5,
    "top_3_concentration_pct_std": 1.816,
    "quality_score_mean": 0.8284,
    "quality_score_std": 0.0135,
    "retention_score_mean": 0.4427,
    "retention_score_std": 0.0492,
    "customer_count_total_mean": 415.7,
    "customer_count_total_std": 59.0187,
    "amm_token_pool_final_mean": 274693.1,
    "amm_token_pool_final_std": 124325.7753,
    "cumulative_referrals_mean": 0.0,
    "cumulative_referrals_std": 0.0,
    "persona_diversity_index_mean": 0.0,
    "persona_diversity_index_std": 0.0,
    "false_positive_rate_mean": 0.0376,
    "false_positive_rate_std": 0.001,
    "cumulative_revenue_mean": 21571916.9,
    "cumulative_revenue_std": 6613808.5746,
    "node_roi_score_mean": 0.5,
    "node_roi_score_std": 0.0,
    "score_mean": 0.4841,
    "score_std": 0.0821
  },
  "unlock_revenue_gated": {
    "n_runs": 10,
    "gini_score_mean": 0.5883,
    "gini_score_std": 0.0217,
    "revenue_score_mean": 0.5266,
    "revenue_score_std": 0.0955,
    "sentiment_resilience_mean": 1.6413,
    "sentiment_resilience_std": 1.6015,
    "amm_usd_pool_final_mean": 5288206.0,
    "amm_usd_pool_final_std": 858784.5583,
    "gini_mean": 0.247,
    "gini_std": 0.013,
    "validator_integrity_score_mean": 0.6186,
    "validator_integrity_score_std": 0.0132,
    "active_operators_final_mean": 32924.6,
    "active_operators_final_std": 3207.7509,
    "retention_pct_mean": 26.09,
    "retention_pct_
```

### track2
```json
{
  "points_only": {
    "n_runs": 10,
    "gini_score_mean": 0.5663,
    "gini_score_std": 0.0412,
    "revenue_score_mean": 0.2528,
    "revenue_score_std": 0.1071,
    "sentiment_resilience_mean": 1.55,
    "sentiment_resilience_std": 0.9887,
    "amm_usd_pool_final_mean": 2179448.4,
    "amm_usd_pool_final_std": 1540432.1062,
    "gini_mean": 0.2602,
    "gini_std": 0.0247,
    "validator_integrity_score_mean": 0.5468,
    "validator_integrity_score_std": 0.0403,
    "active_operators_final_mean": 25507.0,
    "active_operators_final_std": 3244.7274,
    "retention_pct_mean": 20.69,
    "retention_pct_std": 2.207,
    "stability_score_mean": 0.4064,
    "stability_score_std": 0.3977,
    "total_operators_ever_mean": 123141.5,
    "total_operators_ever_std": 5736.3429,
    "nrr_blended_mean": 0.1448,
    "nrr_blended_std": 0.031,
    "customer_count_active_mean": 260.8,
    "customer_count_active_std": 49.6665,
    "t4_plus_operators_mean": 1698.1,
    "t4_plus_operators_std": 2054.1233,
    "capacity_utilization_score_mean": 0.0508,
    "capacity_utilization_score_std": 0.0916,
    "slash_rate_mean": 0.0435,
    "slash_rate_std": 0.0133,
    "peak_price_mean": 7.3206,
    "peak_price_std": 7.3699,
    "final_price_mean": 7.1229,
    "final_price_std": 7.5403,
    "qualified_score_mean": 0.3396,
    "qualified_score_std": 0.4108,
    "top_3_concentration_pct_mean": 9.49,
    "top_3_concentration_pct_std": 3.207,
    "quality_score_mean": 0.7823,
    "quality_score_std": 0.0666,
    "retention_score_mean": 0.3761,
    "retention_score_std": 0.0399,
    "customer_count_total_mean": 425.9,
    "customer_count_total_std": 52.5765,
    "amm_token_pool_final_mean": 802228.4,
    "amm_token_pool_final_std": 504242.4611,
    "cumulative_referrals_mean": 0.0,
    "cumulative_referrals_std": 0.0,
    "persona_diversity_index_mean": 0.0,
    "persona_diversity_index_std": 0.0,
    "false_positive_rate_mean": 0.0453,
    "false_positive_rate_std": 0.004,
    "cumulative_revenue_mean": 12639890.6,
    "cumulative_revenue_std": 5356977.3122,
    "node_roi_score_mean": 0.5,
    "node_roi_score_std": 0.0,
    "score_mean": 0.3953,
    "score_std": 0.0643
  },
  "transition_m12": {
    "n_runs": 10,
    "gini_score_mean": 0.5968,
    "gini_score_std": 0.02,
    "revenue_score_mean": 0.4486,
    "revenue_score_std": 0.0921,
    "sentiment_resilience_mean": 3.9084,
    "sentiment_resilience_std": 3.2908,
    "amm_usd_pool_final_mean": 4476841.4,
    "amm_usd_pool_final_std": 960841.2041,
    "gini_mean": 0.2419,
    "gini_std": 0.012,
    "validator_integrity_score_mean": 0.6146,
    "validator_integrity_score_std": 0.02,
    "active_operators_final_mean": 30312.4,
    "active_operators_final_std": 2676.27,
    "retention_pct_mean": 24.45,
    "retention_pct_std": 2.2151,
    "stability_score_mean": 0.0,
    "stability_score_std": 0.0,
    "total_operators_ever_mean": 124106.5,
    "total_operators_ever_std": 4931.8835,
    "nrr_blended_mean": 0.1356,
    "nrr_blended_std": 0.0434,
    "customer_count_active_mean": 249.7,
    "customer_count_active_std": 44.549,
    "t4_plus_operators_mean": 6068.7,
    "t4_plus_operators_std": 1462.9453,
    "capacity_utilization_score_mean": 0.0471,
    "capacity_utilization_score_std": 0.082,
    "slash_rate_mean": 0.0344,
    "slash_rate_std": 0.0034,
    "peak_price_mean": 20.9653,
    "peak_price_std": 8.469,
    "final_price_mean": 20.9653,
    "final_price_std": 8.469,
    "qualified_score_mean": 0.9521,
    "qualified_score_std": 0.1438,
    "top_3_concentration_pct_mean": 7.61,
    "top_3_concentration_pct_std": 1.7369,
    "quality_score_mean": 0.828,
    "quality_score_std": 0.0168,
    "retention_score_mean": 0.4445,
    "retention_score_std": 0.04,
    "customer_count_total_mean": 419.8,
    "customer_count_total_std": 48.28,
    "amm_token_pool_final_mean": 235206.8,
    "amm_token_pool_final_std": 56327.3179,
    "cumulative_referrals_mean": 0.0,
    "cumulative_referrals_std": 0.0,
    "persona_diversity_index_mean": 0.0,
    "persona_diversity_index_std": 0.0,
    "false_positive_rate_mean": 0.0385,
    "false_positive_rate_std": 0.002,
    "cumulative_revenue_mean": 22426898.6,
    "cumulative_revenue_std": 4606330.4616,
    "node_roi_score_mean": 0.5,
    "node_roi_score_std": 0.0,
    "score_mean": 0.5113,
    "score_std": 0.0457
  },
  "transition_m18": {
    "n_runs": 10,
    "gini_score_mean": 0.5721,
    "gini_score_std": 0.0526,
    "revenue_score_mean": 0.436,
    "revenue_score_std": 0.1371,
    "sentiment_resilience_mean": 1.4591,
    "sentiment_resilience_std": 1.3174,
    "amm_usd_pool_final_mean": 4399518.8,
    "amm_usd_pool_final_std": 1507703.6097,
    "gini_mean": 0.2568,
    "gini_std": 0.0315,
    "validator_integrity_score_mean": 0.6013,
    "validator_integrity_score_std": 0.0303,
    "active_operators_final_mean": 30232.9,
    "active_operators_final_std": 4023.3622,
    "retention_pct_mean": 24.35,
    "retention_pct_std": 3.1832,
    "stability_sc
```

### track3
```json
{
  "nodes_baseline": {
    "n_runs": 10,
    "gini_score_mean": 0.5637,
    "gini_score_std": 0.0292,
    "revenue_score_mean": 0.4685,
    "revenue_score_std": 0.1697,
    "sentiment_resilience_mean": 1.7524,
    "sentiment_resilience_std": 1.8377,
    "amm_usd_pool_final_mean": 4668420.0,
    "amm_usd_pool_final_std": 1712179.0232,
    "gini_mean": 0.2618,
    "gini_std": 0.0175,
    "validator_integrity_score_mean": 0.6079,
    "validator_integrity_score_std": 0.0234,
    "active_operators_final_mean": 30424.8,
    "active_operators_final_std": 5241.8121,
    "retention_pct_mean": 24.96,
    "retention_pct_std": 3.3037,
    "stability_score_mean": 0.0234,
    "stability_score_std": 0.0524,
    "total_operators_ever_mean": 121290.3,
    "total_operators_ever_std": 8534.7609,
    "nrr_blended_mean": 0.1404,
    "nrr_blended_std": 0.05,
    "customer_count_active_mean": 269.7,
    "customer_count_active_std": 53.3218,
    "t4_plus_operators_mean": 5761.5,
    "t4_plus_operators_std": 2446.3312,
    "capacity_utilization_score_mean": 0.1036,
    "capacity_utilization_score_std": 0.1277,
    "slash_rate_mean": 0.0344,
    "slash_rate_std": 0.0028,
    "peak_price_mean": 24.7257,
    "peak_price_std": 14.7039,
    "final_price_mean": 24.7257,
    "final_price_std": 14.7039,
    "qualified_score_mean": 0.8326,
    "qualified_score_std": 0.2566,
    "top_3_concentration_pct_mean": 7.58,
    "top_3_concentration_pct_std": 2.4742,
    "quality_score_mean": 0.8281,
    "quality_score_std": 0.0141,
    "retention_score_mean": 0.4539,
    "retention_score_std": 0.0603,
    "customer_count_total_mean": 437.6,
    "customer_count_total_std": 67.8634,
    "amm_token_pool_final_mean": 258521.3,
    "amm_token_pool_final_std": 124954.1488,
    "cumulative_referrals_mean": 0.0,
    "cumulative_referrals_std": 0.0,
    "persona_diversity_index_mean": 0.0,
    "persona_diversity_index_std": 0.0,
    "false_positive_rate_mean": 0.0392,
    "false_positive_rate_std": 0.0023,
    "cumulative_revenue_mean": 23427071.3,
    "cumulative_revenue_std": 8488203.0663,
    "node_roi_score_mean": 0.5,
    "node_roi_score_std": 0.0,
    "score_mean": 0.5005,
    "score_std": 0.0844
  },
  "nodes_low_bond": {
    "n_runs": 10,
    "gini_score_mean": 0.5883,
    "gini_score_std": 0.0217,
    "revenue_score_mean": 0.5266,
    "revenue_score_std": 0.0955,
    "sentiment_resilience_mean": 1.6413,
    "sentiment_resilience_std": 1.6015,
    "amm_usd_pool_final_mean": 5288206.0,
    "amm_usd_pool_final_std": 858784.5583,
    "gini_mean": 0.247,
    "gini_std": 0.013,
    "validator_integrity_score_mean": 0.6186,
    "validator_integrity_score_std": 0.0132,
    "active_operators_final_mean": 32924.6,
    "active_operators_final_std": 3207.7509,
    "retention_pct_mean": 26.09,
    "retention_pct_std": 1.8849,
    "stability_score_mean": 0.0115,
    "stability_score_std": 0.0222,
    "total_operators_ever_mean": 125961.7,
    "total_operators_ever_std": 5379.8602,
    "nrr_blended_mean": 0.1618,
    "nrr_blended_std": 0.0568,
    "customer_count_active_mean": 285.8,
    "customer_count_active_std": 20.7836,
    "t4_plus_operators_mean": 6935.7,
    "t4_plus_operators_std": 1538.2584,
    "capacity_utilization_score_mean": 0.0239,
    "capacity_utilization_score_std": 0.0442,
    "slash_rate_mean": 0.0341,
    "slash_rate_std": 0.002,
    "peak_price_mean": 28.7026,
    "peak_price_std": 8.3056,
    "final_price_mean": 28.7026,
    "final_price_std": 8.3056,
    "qualified_score_mean": 0.9681,
    "qualified_score_std": 0.0869,
    "top_3_concentration_pct_mean": 6.39,
    "top_3_concentration_pct_std": 0.667,
    "quality_score_mean": 0.8296,
    "quality_score_std": 0.0098,
    "retention_score_mean": 0.4746,
    "retention_score_std": 0.0342,
    "customer_count_total_mean": 455.1,
    "customer_count_total_std": 29.6427,
    "amm_token_pool_final_mean": 195543.8,
    "amm_token_pool_final_std": 40229.2132,
    "cumulative_referrals_mean": 0.0,
    "cumulative_referrals_std": 0.0,
    "persona_diversity_index_mean": 0.0,
    "persona_diversity_index_std": 0.0,
    "false_positive_rate_mean": 0.0381,
    "false_positive_rate_std": 0.0013,
    "cumulative_revenue_mean": 26331799.9,
    "cumulative_revenue_std": 4775549.8059,
    "node_roi_score_mean": 0.5,
    "node_roi_score_std": 0.0,
    "score_mean": 0.535,
    "score_std": 0.039
  },
  "nodes_med_bond": {
    "n_runs": 10,
    "gini_score_mean": 0.5883,
    "gini_score_std": 0.0217,
    "revenue_score_mean": 0.5266,
    "revenue_score_std": 0.0955,
    "sentiment_resilience_mean": 1.6413,
    "sentiment_resilience_std": 1.6015,
    "amm_usd_pool_final_mean": 5288206.0,
    "amm_usd_pool_final_std": 858784.5583,
    "gini_mean": 0.247,
    "gini_std": 0.013,
    "validator_integrity_score_mean": 0.6186,
    "validator_integrity_score_std": 0.0132,
    "active_operators_final_mean": 32924.6,
    "active_operators_final_std": 3207.7509,
    "retention_pct_mean": 26.09,
    "retention_pct_std":
```

### track4
```json
{
  "path_baseline": {
    "n_runs": 10,
    "gini_score_mean": 0.5883,
    "gini_score_std": 0.0217,
    "revenue_score_mean": 0.5266,
    "revenue_score_std": 0.0955,
    "sentiment_resilience_mean": 1.6413,
    "sentiment_resilience_std": 1.6015,
    "amm_usd_pool_final_mean": 5288206.0,
    "amm_usd_pool_final_std": 858784.5583,
    "gini_mean": 0.247,
    "gini_std": 0.013,
    "validator_integrity_score_mean": 0.6186,
    "validator_integrity_score_std": 0.0132,
    "active_operators_final_mean": 32924.6,
    "active_operators_final_std": 3207.7509,
    "retention_pct_mean": 26.09,
    "retention_pct_std": 1.8849,
    "stability_score_mean": 0.0115,
    "stability_score_std": 0.0222,
    "total_operators_ever_mean": 125961.7,
    "total_operators_ever_std": 5379.8602,
    "nrr_blended_mean": 0.1618,
    "nrr_blended_std": 0.0568,
    "customer_count_active_mean": 285.8,
    "customer_count_active_std": 20.7836,
    "t4_plus_operators_mean": 6935.7,
    "t4_plus_operators_std": 1538.2584,
    "capacity_utilization_score_mean": 0.0239,
    "capacity_utilization_score_std": 0.0442,
    "slash_rate_mean": 0.0341,
    "slash_rate_std": 0.002,
    "peak_price_mean": 28.7026,
    "peak_price_std": 8.3056,
    "final_price_mean": 28.7026,
    "final_price_std": 8.3056,
    "qualified_score_mean": 0.9681,
    "qualified_score_std": 0.0869,
    "top_3_concentration_pct_mean": 6.39,
    "top_3_concentration_pct_std": 0.667,
    "quality_score_mean": 0.8296,
    "quality_score_std": 0.0098,
    "retention_score_mean": 0.4746,
    "retention_score_std": 0.0342,
    "customer_count_total_mean": 455.1,
    "customer_count_total_std": 29.6427,
    "amm_token_pool_final_mean": 195543.8,
    "amm_token_pool_final_std": 40229.2132,
    "cumulative_referrals_mean": 0.0,
    "cumulative_referrals_std": 0.0,
    "persona_diversity_index_mean": 0.0,
    "persona_diversity_index_std": 0.0,
    "false_positive_rate_mean": 0.0381,
    "false_positive_rate_std": 0.0013,
    "cumulative_revenue_mean": 26331799.9,
    "cumulative_revenue_std": 4775549.8059,
    "node_roi_score_mean": 0.5,
    "node_roi_score_std": 0.0,
    "score_mean": 0.535,
    "score_std": 0.039
  },
  "funding_winter": {
    "n_runs": 10,
    "gini_score_mean": 0.3366,
    "gini_score_std": 0.0512,
    "revenue_score_mean": 0.0645,
    "revenue_score_std": 0.0085,
    "sentiment_resilience_mean": 1.1096,
    "sentiment_resilience_std": 0.3717,
    "amm_usd_pool_final_mean": 252090.3,
    "amm_usd_pool_final_std": 62155.4516,
    "gini_mean": 0.398,
    "gini_std": 0.0307,
    "validator_integrity_score_mean": 0.6706,
    "validator_integrity_score_std": 0.0402,
    "active_operators_final_mean": 22697.4,
    "active_operators_final_std": 1954.7501,
    "retention_pct_mean": 18.76,
    "retention_pct_std": 0.9002,
    "stability_score_mean": 0.2392,
    "stability_score_std": 0.0329,
    "total_operators_ever_mean": 121018.0,
    "total_operators_ever_std": 7394.1853,
    "nrr_blended_mean": 0.1618,
    "nrr_blended_std": 0.1046,
    "customer_count_active_mean": 66.2,
    "customer_count_active_std": 18.082,
    "t4_plus_operators_mean": 0.4,
    "t4_plus_operators_std": 1.2,
    "capacity_utilization_score_mean": 0.549,
    "capacity_utilization_score_std": 0.2114,
    "slash_rate_mean": 0.0565,
    "slash_rate_std": 0.0054,
    "peak_price_mean": 0.9967,
    "peak_price_std": 0.0002,
    "final_price_mean": 0.0674,
    "final_price_std": 0.0291,
    "qualified_score_mean": 0.0001,
    "qualified_score_std": 0.0002,
    "top_3_concentration_pct_mean": 24.82,
    "top_3_concentration_pct_std": 8.2749,
    "quality_score_mean": 0.7176,
    "quality_score_std": 0.0269,
    "retention_score_mean": 0.3408,
    "retention_score_std": 0.0164,
    "customer_count_total_mean": 109.9,
    "customer_count_total_std": 21.8287,
    "amm_token_pool_final_mean": 4291317.9,
    "amm_token_pool_final_std": 1345587.647,
    "cumulative_referrals_mean": 0.0,
    "cumulative_referrals_std": 0.0,
    "persona_diversity_index_mean": 0.0,
    "persona_diversity_index_std": 0.0,
    "false_positive_rate_mean": 0.0329,
    "false_positive_rate_std": 0.004,
    "cumulative_revenue_mean": 3224844.5,
    "cumulative_revenue_std": 423597.9405,
    "node_roi_score_mean": 0.5,
    "node_roi_score_std": 0.0,
    "score_mean": 0.294,
    "score_std": 0.0069
  },
  "tesla_hiring": {
    "n_runs": 10,
    "gini_score_mean": 0.5702,
    "gini_score_std": 0.0524,
    "revenue_score_mean": 0.5344,
    "revenue_score_std": 0.1587,
    "sentiment_resilience_mean": 2.0238,
    "sentiment_resilience_std": 2.9128,
    "amm_usd_pool_final_mean": 5183477.9,
    "amm_usd_pool_final_std": 1615453.3478,
    "gini_mean": 0.2579,
    "gini_std": 0.0314,
    "validator_integrity_score_mean": 0.6182,
    "validator_integrity_score_std": 0.0258,
    "active_operators_final_mean": 33209.3,
    "active_operators_final_std": 5162.4965,
    "retention_pct_mean": 26.27,
    "retention_pct_std": 2.9675,
    "stabil
```

