"""
CrowdBrain v5 — Bayesian-style random-search optimization
==========================================================
Random search over the unified v5 parameter space to discover unexpected
interactions that grid sweeps miss.

Search space (open-ended ranges per user directive):
  hardware_stake_t3       : [0, 400] USD
  lambda_max_per_segment  : [0.30, 1.50]
  onboarding_multiplier   : [0.05, 0.50]
  era_maturity_mult       : [2.0, 6.0]   (customer_arrival in maturity era)
  era_growth_threshold_mo : [12, 24]
  dp_size_multiplier      : [0.5, 2.0]   (uniform multiplier on all DP sizes)

Strategy:
  Stage 1 — 80 random configs × MC=10 (faster screening, ~15-20 min)
  Stage 2 — top 5 configs × MC=20 (~5 min)

Output:
  v5_results/bo_stage1_results.json
  v5_results/bo_stage2_top5.json
  v5_results/bo_winner_config.json
"""

import sys
import json
import time
import copy
import os
import random
from typing import Dict, List, Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed

import prepare_v5
from prepare_v5 import run_simulation_v5, RANDOM_SEED
from train_v5_realistic import PARAMS_V5_REALISTIC, evaluate_realism


N_WORKERS = max(1, (os.cpu_count() or 4) - 1)
OUT_DIR = "v5_results"
os.makedirs(OUT_DIR, exist_ok=True)
SIM_MONTHS = 60


# ─── SEARCH SPACE ─────────────────────────────────────────────────────────
SEARCH_SPACE = {
    "hardware_stake_t3":       (0, 400),
    "lambda_max_per_segment":  (0.30, 1.50),
    "onboarding_multiplier":   (0.05, 0.50),
    "era_maturity_mult":       (2.0, 6.0),
    "era_growth_threshold_mo": (12, 24),
    "dp_size_multiplier":      (0.5, 2.0),
}


def sample_config(rng: random.Random) -> Dict:
    cfg = {}
    for name, (lo, hi) in SEARCH_SPACE.items():
        if name == "era_growth_threshold_mo" or name == "hardware_stake_t3":
            cfg[name] = rng.randint(int(lo), int(hi))
        else:
            cfg[name] = round(lo + rng.random() * (hi - lo), 4)
    return cfg


def apply_config(base_params: Dict, cfg: Dict) -> Dict:
    """Returns a deep-copy of base_params with cfg applied."""
    p = copy.deepcopy(base_params)

    # Tier-unlock op_count winners (10/5/2) — keep iter4 best
    p["tier_unlock"]["rules"] = {
        3: {"op_count_at_prev_tier": 10},
        4: {"op_count_at_prev_tier": 5},
        6: {"op_count_at_prev_tier": 2},
    }

    p["hardware"]["stake_required_t3_usd"] = cfg["hardware_stake_t3"]
    p["customers"]["arrival"]["lambda_max_per_segment"] = cfg["lambda_max_per_segment"]
    p["task_model"]["onboarding_multiplier"] = cfg["onboarding_multiplier"]
    p["macro"]["era"]["era_multipliers"]["maturity"]["customer_arrival"] = cfg["era_maturity_mult"]
    p["macro"]["era"]["growth_month_threshold"] = cfg["era_growth_threshold_mo"]

    # Maturity threshold should always be >= growth+12 to keep era ordering sensible
    p["macro"]["era"]["maturity_month_threshold"] = max(
        p["macro"]["era"].get("maturity_month_threshold", 30),
        cfg["era_growth_threshold_mo"] + 12,
    )

    # Apply DP size multiplier
    dp_mult = cfg["dp_size_multiplier"]
    p["customers"]["arrival"]["design_partners"] = [
        (seg, int(size * dp_mult))
        for seg, size in p["customers"]["arrival"]["design_partners"]
    ]

    return p


# ─── RUNNERS ──────────────────────────────────────────────────────────────
def _run_single(args: Tuple[int, Dict, int, int]) -> Tuple[int, int, Dict]:
    cfg_idx, params, seed, sim_months = args
    prepare_v5.SIMULATION_MONTHS = sim_months
    history, customers = run_simulation_v5(params, seed=seed)
    result = evaluate_realism(history, customers)
    return (cfg_idx, seed, result)


def _aggregate(results: List[Dict]) -> Dict:
    if not results:
        return {"n_runs": 0}
    agg = {"n_runs": len(results)}
    keys = set().union(*(r.keys() for r in results))
    for k in keys:
        vals = [r.get(k, 0) for r in results if isinstance(r.get(k), (int, float))]
        if vals:
            mean = sum(vals) / len(vals)
            std = (sum((v - mean) ** 2 for v in vals) / len(vals)) ** 0.5
            agg[k + "_mean"] = round(mean, 4)
            agg[k + "_std"] = round(std, 4)
        bool_vals = [r.get(k) for r in results if isinstance(r.get(k), bool)]
        if bool_vals:
            agg[k + "_pct_true"] = round(sum(bool_vals) / len(bool_vals), 4)
    return agg


def evaluate_configs(configs: List[Dict], mc: int, label: str) -> List[Dict]:
    """Run each config × MC seeds in parallel. Returns list of {cfg, agg} dicts."""
    print(f"\n{'='*78}")
    print(f"BO {label}: {len(configs)} configs x MC={mc}  workers={N_WORKERS}")
    print(f"{'='*78}\n")

    tasks = []
    for idx, cfg in enumerate(configs):
        params = apply_config(PARAMS_V5_REALISTIC, cfg)
        for i in range(mc):
            tasks.append((idx, params, RANDOM_SEED + i, SIM_MONTHS))

    print(f"Total runs: {len(tasks)}")
    by_cfg: Dict[int, List[Dict]] = {i: [] for i in range(len(configs))}

    t_start = time.time()
    completed = 0
    with ProcessPoolExecutor(max_workers=N_WORKERS) as ex:
        futs = {ex.submit(_run_single, t): t for t in tasks}
        for fut in as_completed(futs):
            cfg_idx, seed, result = fut.result()
            by_cfg[cfg_idx].append(result)
            completed += 1
            if completed % 40 == 0 or completed == len(tasks):
                elapsed = time.time() - t_start
                print(f"  [{completed}/{len(tasks)}] elapsed={elapsed:.1f}s", flush=True)

    out = []
    for idx, cfg in enumerate(configs):
        agg = _aggregate(by_cfg[idx])
        out.append({"cfg_idx": idx, "config": cfg, "agg": agg})

    elapsed_total = time.time() - t_start
    print(f"\n{label} complete in {elapsed_total/60:.1f} min")
    return out


def main():
    n_configs = 80
    if len(sys.argv) >= 2:
        try:
            n_configs = int(sys.argv[1])
        except ValueError:
            pass

    rng = random.Random(RANDOM_SEED)
    configs = [sample_config(rng) for _ in range(n_configs)]

    overall_start = time.time()

    # Stage 1: random search at MC=10
    stage1 = evaluate_configs(configs, mc=10, label="Stage 1 (broad search MC=10)")

    # Sort by composite score
    stage1.sort(key=lambda r: r["agg"].get("score_mean", 0), reverse=True)

    # Save BEFORE printing - print failures (encoding etc) won't lose data.
    with open(os.path.join(OUT_DIR, "bo_stage1_results.json"), "w") as f:
        json.dump(stage1, f, indent=2)

    try:
        print("\nTop 10 from Stage 1:")
        for r in stage1[:10]:
            c = r["config"]
            print(f"  cfg{r['cfg_idx']:>3d} score={r['agg'].get('score_mean', 0):.4f}  "
                  f"stake=${c['hardware_stake_t3']:>3d} lambda={c['lambda_max_per_segment']:.2f} "
                  f"onb={c['onboarding_multiplier']:.2f} mat_mult={c['era_maturity_mult']:.1f} "
                  f"grow_mo={c['era_growth_threshold_mo']:>2d} dp_mult={c['dp_size_multiplier']:.2f}")
    except (UnicodeEncodeError, Exception) as e:
        print(f"  (skipped pretty-print due to {type(e).__name__})")

    # Stage 2: top 5 at MC=20
    top5_configs = [r["config"] for r in stage1[:5]]
    stage2 = evaluate_configs(top5_configs, mc=20, label="Stage 2 (top-5 refinement MC=20)")

    stage2.sort(key=lambda r: r["agg"].get("score_mean", 0), reverse=True)

    # Save BEFORE printing.
    with open(os.path.join(OUT_DIR, "bo_stage2_top5.json"), "w") as f:
        json.dump(stage2, f, indent=2)

    try:
        print("\nStage 2 final ranking:")
        for r in stage2:
            c = r["config"]
            print(f"  score={r['agg'].get('score_mean', 0):.4f} +- {r['agg'].get('score_std', 0):.4f} "
                  f"ARR=${r['agg'].get('realism_final_arr_usd_mean', 0)/1e6:.1f}M "
                  f"stake=${c['hardware_stake_t3']:>3d} lambda={c['lambda_max_per_segment']:.2f} "
                  f"onb={c['onboarding_multiplier']:.2f}")
    except (UnicodeEncodeError, Exception) as e:
        print(f"  (skipped pretty-print due to {type(e).__name__})")

    if stage2:
        winner = stage2[0]
        with open(os.path.join(OUT_DIR, "bo_winner_config.json"), "w") as f:
            json.dump(winner, f, indent=2)

    elapsed = time.time() - overall_start
    print(f"\n{'='*78}")
    print(f"BO complete - total wall time {elapsed/60:.1f} min")
    print(f"{'='*78}")


if __name__ == "__main__":
    main()
