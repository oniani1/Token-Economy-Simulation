"""
CrowdBrain v5 Experiments — 4-track sweep orchestrator
========================================================
Parallelized across CPU cores (24 available). Each Monte Carlo run is its own
process; cells run sequentially within tracks but MC is parallel.

Usage:
  python experiments_v5.py track1                # Tier-unlock policy (6 cells)
  python experiments_v5.py track2                # Points-to-tokens (4 cells)
  python experiments_v5.py track3                # 3-stakeholder loop (6 cells)
  python experiments_v5.py track4                # Macro stress (8 cells)
  python experiments_v5.py all [MC]              # All tracks; MC default 10

Output: track_<N>_results.json + per-cell timeseries CSV in csv_v5/
"""

import sys
import json
import time
import copy
import os
from typing import Dict, List, Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed

from prepare_v5 import (
    run_simulation_v5, evaluate_v5, RANDOM_SEED,
)
from train_v5 import PARAMS_V5
import tier_unlock as TU
import node_providers as NP
import points_to_token as PT


# ─── DEFAULTS ─────────────────────────────────────────────────────────────
DEFAULT_MC = 10
N_WORKERS = max(1, (os.cpu_count() or 4) - 1)   # leave 1 core for OS

# Output directory
OUT_DIR = "v5_results"
os.makedirs(OUT_DIR, exist_ok=True)


# ─── WORKER ───────────────────────────────────────────────────────────────
def _run_one(args: Tuple[str, Dict, int]) -> Tuple[str, int, Dict, Dict]:
    """One MC run. Returns (cell_name, seed, evaluation_dict, final_snapshot)."""
    cell_name, params, seed = args
    history, customers = run_simulation_v5(params, seed=seed)
    result = evaluate_v5(history, customers)
    final = history[-1] if history else {}
    return (cell_name, seed, result, final)


def _aggregate(results: List[Dict]) -> Dict:
    """Mean + std across MC runs for numeric fields."""
    if not results:
        return {"n_runs": 0}
    keys = set()
    for r in results:
        keys.update(r.keys())
    agg = {"n_runs": len(results)}
    for k in keys:
        vals = [r.get(k, 0) for r in results if isinstance(r.get(k), (int, float))]
        if vals:
            mean = sum(vals) / len(vals)
            std = (sum((v - mean) ** 2 for v in vals) / len(vals)) ** 0.5
            agg[k + "_mean"] = round(mean, 4)
            agg[k + "_std"] = round(std, 4)
    return agg


def run_track(cells: List[Tuple[str, Dict]], mc: int, label: str) -> Dict:
    """
    Run a track of cells. Each cell runs MC seeds in parallel across workers.
    Returns dict: {cell_name: {agg metrics + std}}.
    """
    print(f"\n{'='*78}")
    print(f"TRACK: {label}  |  cells={len(cells)}  MC={mc}  workers={N_WORKERS}")
    print(f"{'='*78}\n")

    # Build full task list (cell × MC seeds)
    tasks = []
    for cell_name, params in cells:
        for i in range(mc):
            tasks.append((cell_name, params, RANDOM_SEED + i))

    print(f"Total runs: {len(tasks)}  (estimated wall time ~{len(tasks) * 220 / N_WORKERS / 60:.0f} min)")

    # Group results by cell
    by_cell: Dict[str, List[Dict]] = {name: [] for name, _ in cells}
    by_cell_finals: Dict[str, List[Dict]] = {name: [] for name, _ in cells}

    t_start = time.time()
    completed = 0
    with ProcessPoolExecutor(max_workers=N_WORKERS) as ex:
        futs = {ex.submit(_run_one, t): t for t in tasks}
        for fut in as_completed(futs):
            cell_name, seed, result, final = fut.result()
            by_cell[cell_name].append(result)
            by_cell_finals[cell_name].append(final)
            completed += 1
            elapsed = time.time() - t_start
            avg_per = elapsed / completed
            remaining = avg_per * (len(tasks) - completed)
            print(f"  [{completed}/{len(tasks)}] {cell_name} seed={seed} score={result.get('score', 0):.3f}  "
                  f"elapsed={elapsed/60:.1f}min  ETA={remaining/60:.1f}min", flush=True)

    # Aggregate
    track_results = {}
    for cell_name, _ in cells:
        agg = _aggregate(by_cell[cell_name])
        track_results[cell_name] = agg
        print(f"\n--- {cell_name} ---")
        score_m = agg.get("score_mean", 0)
        score_s = agg.get("score_std", 0)
        rev_m = agg.get("cumulative_revenue_mean", 0)
        t4_m = agg.get("t4_plus_operators_mean", 0)
        nrr_m = agg.get("nrr_blended_mean", 0)
        print(f"  composite: {score_m:.4f} ± {score_s:.4f}")
        print(f"  cum_rev:   ${rev_m:,.0f}")
        print(f"  T4+ ops:   {t4_m:.0f}")
        print(f"  NRR:       {nrr_m:.3f}")

    elapsed_total = time.time() - t_start
    print(f"\n{label} complete in {elapsed_total/60:.1f} min")
    return track_results


# ─── TRACK 1: TIER UNLOCK ─────────────────────────────────────────────────
def build_track1() -> List[Tuple[str, Dict]]:
    cells = []
    for cell_name, rules in TU.PRESET_POLICIES.items():
        p = copy.deepcopy(PARAMS_V5)
        p["tier_unlock"]["rules"] = rules
        cells.append((cell_name, p))
    return cells


# ─── TRACK 2: POINTS → TOKENS ─────────────────────────────────────────────
def build_track2() -> List[Tuple[str, Dict]]:
    cells = []
    for cell_name, policy in PT.PRESET_POLICIES.items():
        p = copy.deepcopy(PARAMS_V5)
        p["points_to_token"] = dict(policy)
        cells.append((cell_name, p))
    return cells


# ─── TRACK 3: 3-STAKEHOLDER LOOP ──────────────────────────────────────────
def build_track3() -> List[Tuple[str, Dict]]:
    cells = []
    for cell_name, np_params in NP.PRESET_POLICIES.items():
        p = copy.deepcopy(PARAMS_V5)
        p["node_providers"]["params"] = {**NP.DEFAULT_PROVIDER_PARAMS, **np_params}
        cells.append((cell_name, p))
    return cells


# ─── TRACK 4: MACRO STRESS + MILESTONE PROBABILITY ────────────────────────
def build_track4() -> List[Tuple[str, Dict]]:
    cells = []
    base = copy.deepcopy(PARAMS_V5)

    # path_baseline — high-MC for milestone probability (handled separately)
    cells.append(("path_baseline", copy.deepcopy(base)))

    # funding_winter
    p = copy.deepcopy(base)
    p.setdefault("stress", {})["customer_arrival_multiplier"] = 0.25
    p["stress"]["customer_arrival_start_month"] = 6
    cells.append(("funding_winter", p))

    # tesla_hiring
    p = copy.deepcopy(base)
    p["geography"]["tesla_stress"] = {
        "fraction_of_t3plus_with_alt_offer": 0.30,
        "alt_wage_usd": 48.0,
        "wage_gap_churn_multiplier_per_dollar": 0.005,
    }
    cells.append(("tesla_hiring", p))

    # geo_shock_GE / PH / KE
    for region in ("georgia", "philippines", "kenya"):
        p = copy.deepcopy(base)
        p["geography"]["geo_shock"] = {
            "region": region,
            "start_month": 12,
            "duration": 6,
            "capacity_factor": 0.30,
        }
        cells.append((f"geo_shock_{region}", p))

    # mvp_slip — onboarding starts at m3 instead of m0 (modeled by a 3-month-delay
    # customer arrival multiplier of 0.0 for m0-2)
    p = copy.deepcopy(base)
    p.setdefault("stress", {})["customer_arrival_multiplier"] = 0.0
    p["stress"]["customer_arrival_start_month"] = 0
    # Manually unset the multiplier after m3 — we model this by another field
    p["stress"]["mvp_start_month"] = 3
    cells.append(("mvp_slip", p))

    # intelligence_library — additional revenue line from m24
    p = copy.deepcopy(base)
    p.setdefault("stress", {})["intelligence_library_start_month"] = 24
    p["stress"]["intelligence_library_factor"] = 0.5    # $0.50 per cumulative op-hour per month
    cells.append(("intelligence_library", p))

    return cells


# ─── ORCHESTRATION ────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1].lower()
    mc = DEFAULT_MC
    if len(sys.argv) >= 3:
        try:
            mc = int(sys.argv[2])
        except ValueError:
            pass

    overall_start = time.time()
    all_results = {}

    if cmd in ("track1", "all"):
        cells = build_track1()
        track_results = run_track(cells, mc, "Track 1 — Tier-unlock policy")
        all_results["track1"] = track_results
        with open(os.path.join(OUT_DIR, "track1_results.json"), "w") as f:
            json.dump(track_results, f, indent=2)

    if cmd in ("track3", "all"):   # priority order: T1, T3, T4, T2 (T2 last per user)
        cells = build_track3()
        track_results = run_track(cells, mc, "Track 3 — 3-stakeholder loop")
        all_results["track3"] = track_results
        with open(os.path.join(OUT_DIR, "track3_results.json"), "w") as f:
            json.dump(track_results, f, indent=2)

    if cmd in ("track4", "all"):
        cells = build_track4()
        track_results = run_track(cells, mc, "Track 4 — Macro stress + milestones")
        all_results["track4"] = track_results
        with open(os.path.join(OUT_DIR, "track4_results.json"), "w") as f:
            json.dump(track_results, f, indent=2)

    if cmd in ("track2", "all"):
        cells = build_track2()
        track_results = run_track(cells, mc, "Track 2 — Points-to-tokens")
        all_results["track2"] = track_results
        with open(os.path.join(OUT_DIR, "track2_results.json"), "w") as f:
            json.dump(track_results, f, indent=2)

    if cmd == "all":
        with open(os.path.join(OUT_DIR, "all_results.json"), "w") as f:
            json.dump(all_results, f, indent=2)

    elapsed = time.time() - overall_start
    print(f"\n{'='*78}")
    print(f"DONE — total wall time {elapsed/60:.1f} min ({elapsed/3600:.2f} hrs)")
    print(f"Results in: {OUT_DIR}/")
    print(f"{'='*78}")


if __name__ == "__main__":
    main()
