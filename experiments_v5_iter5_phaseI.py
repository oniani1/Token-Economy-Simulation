"""
Phase I — final iter5 winner validation
========================================
Combines iter5 discoveries:
  - Best stake from Phase A (read from iter5_phasea_results.json)
  - Per-customer-tier matching (if Phase G shows it helps)
  - 60mo horizon
  MC=20 validation

Usage:
  python experiments_v5_iter5_phaseI.py
"""

import json
import os
import sys
import copy
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, List, Tuple

import prepare_v5
from prepare_v5 import run_simulation_v5, RANDOM_SEED
from train_v5_realistic import PARAMS_V5_REALISTIC, evaluate_realism

OUT_DIR = "v5_results"
N_WORKERS = max(1, (os.cpu_count() or 4) - 1)


def discover_winner_stake() -> int:
    p = os.path.join(OUT_DIR, "iter5_phasea_results.json")
    if not os.path.exists(p):
        print("WARNING: phaseA results not found, using $100")
        return 100
    with open(p) as f:
        results = json.load(f)
    best = max(((int(k.split("_")[1]), v.get("score_mean", 0)) for k, v in results.items() if k.startswith("stake_")),
               key=lambda x: x[1])
    return best[0]


def per_tier_helps() -> bool:
    pg_path = os.path.join(OUT_DIR, "iter5_phaseg_results.json")
    pa_path = os.path.join(OUT_DIR, "iter5_phasea_results.json")
    if not (os.path.exists(pg_path) and os.path.exists(pa_path)):
        return False
    with open(pg_path) as f:
        pg = json.load(f)
    with open(pa_path) as f:
        pa = json.load(f)
    pg_score = next(iter(pg.values())).get("score_mean", 0)
    # Compare to stake_100 from phaseA (Phase G uses stake $100 + matching)
    pa_stake_100 = pa.get("stake_100", {}).get("score_mean", 0)
    return pg_score > pa_stake_100 + 0.005


def build_final_config():
    p = copy.deepcopy(PARAMS_V5_REALISTIC)
    p["tier_unlock"]["rules"] = {
        3: {"op_count_at_prev_tier": 10},
        4: {"op_count_at_prev_tier": 5},
        6: {"op_count_at_prev_tier": 2},
    }
    p["hardware"]["stake_required_t3_usd"] = discover_winner_stake()
    if per_tier_helps():
        p.setdefault("customers", {}).setdefault("matching", {})["per_customer_tier_pool"] = True
        p["customers"]["matching"]["pool_size_per_tier"] = 25
        print(f"  Including per-tier matching (Phase G > Phase A stake_100)")
    else:
        print(f"  Skipping per-tier matching (no clear Phase G improvement)")
    return p


def _run_one(args):
    seed, params, sim_months = args
    prepare_v5.SIMULATION_MONTHS = sim_months
    history, customers = run_simulation_v5(params, seed=seed)
    return seed, evaluate_realism(history, customers)


def main():
    mc = 20
    if len(sys.argv) >= 2:
        try:
            mc = int(sys.argv[1])
        except ValueError:
            pass

    stake = discover_winner_stake()
    print(f"\nPhase I — final iter5 winner validation")
    print(f"  Discovered winner stake: ${stake}")
    print(f"  MC: {mc}")

    params = build_final_config()
    matching_on = per_tier_helps()
    cell_name = f"final_iter5_stake{stake:03d}_match{'on' if matching_on else 'off'}_60mo"

    tasks = [(RANDOM_SEED + i, params, 60) for i in range(mc)]
    print(f"  Running {len(tasks)} runs on {N_WORKERS} workers...")

    t_start = time.time()
    results = []
    with ProcessPoolExecutor(max_workers=N_WORKERS) as ex:
        futs = [ex.submit(_run_one, t) for t in tasks]
        for fut in as_completed(futs):
            seed, r = fut.result()
            results.append(r)

    n = len(results)
    keys = set().union(*(r.keys() for r in results))
    agg = {"n_runs": n}
    for k in keys:
        vals = [r.get(k, 0) for r in results if isinstance(r.get(k), (int, float))]
        if vals:
            mean = sum(vals) / n
            std = (sum((v - mean) ** 2 for v in vals) / n) ** 0.5
            agg[k + "_mean"] = round(mean, 4)
            agg[k + "_std"] = round(std, 4)
        bool_vals = [r.get(k) for r in results if isinstance(r.get(k), bool)]
        if bool_vals:
            agg[k + "_pct_true"] = round(sum(bool_vals) / len(bool_vals), 4)

    elapsed = time.time() - t_start
    print(f"\n--- {cell_name} ---")
    print(f"  composite:          {agg.get('score_mean', 0):.4f} ± {agg.get('score_std', 0):.4f}")
    print(f"  final ARR:          ${agg.get('realism_final_arr_usd_mean', 0):,.0f}")
    print(f"  customers:          {agg.get('realism_final_customer_count_mean', 0):.0f}")
    print(f"  T4+ ops:            {agg.get('t4_plus_operators_mean', 0):.0f}")
    print(f"  active ops final:   {agg.get('active_operators_final_mean', 0):.0f}")
    print(f"  cum revenue:        ${agg.get('cumulative_revenue_mean', 0):,.0f}")
    print(f"\nDone in {elapsed:.1f}s.")

    out = {cell_name: agg}
    with open(os.path.join(OUT_DIR, "iter5_phaseI_results.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(f"Wrote {OUT_DIR}/iter5_phaseI_results.json")


if __name__ == "__main__":
    main()
