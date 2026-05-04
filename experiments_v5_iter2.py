"""
CrowdBrain v5 — iteration 2 sweeps (composite + revenue Pareto)
================================================================
Targets the 3 biggest sub-score drags identified in REPORT_v5.md:
  - Revenue (-0.095): tier-unlock thresholds may be too strict
  - Retention (-0.084): hardware stake may be over-tuned
  - Capacity util (-0.036): nodes likely over-provisioned

Three phases, 18 cells total, MC=20 default. Wall time ~57 min on 23 cores.

Usage:
  python experiments_v5_iter2.py phase1            # combo + diagnostic (3 cells)
  python experiments_v5_iter2.py phase2            # revenue threshold sweep (6 cells)
  python experiments_v5_iter2.py phase3            # hardware stake + nodes sweep (9 cells)
  python experiments_v5_iter2.py all [MC]          # all 3 phases; MC default 20
"""

import sys
import json
import time
import copy
import os
from typing import Dict, List, Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed

from prepare_v5 import run_simulation_v5, evaluate_v5, RANDOM_SEED
from train_v5 import PARAMS_V5
import tier_unlock as TU
import node_providers as NP
import points_to_token as PT


DEFAULT_MC = 20
N_WORKERS = max(1, (os.cpu_count() or 4) - 1)
OUT_DIR = "v5_results"
os.makedirs(OUT_DIR, exist_ok=True)


# ─── WORKER ───────────────────────────────────────────────────────────────
def _run_one(args: Tuple[str, Dict, int]) -> Tuple[str, int, Dict, Dict]:
    cell_name, params, seed = args
    history, customers = run_simulation_v5(params, seed=seed)
    result = evaluate_v5(history, customers)
    final = history[-1] if history else {}
    return (cell_name, seed, result, final)


def _aggregate(results: List[Dict]) -> Dict:
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


def run_phase(cells: List[Tuple[str, Dict]], mc: int, label: str) -> Dict:
    print(f"\n{'='*78}")
    print(f"PHASE: {label}  |  cells={len(cells)}  MC={mc}  workers={N_WORKERS}")
    print(f"{'='*78}\n")

    tasks = []
    for cell_name, params in cells:
        for i in range(mc):
            tasks.append((cell_name, params, RANDOM_SEED + i))
    print(f"Total runs: {len(tasks)}  (estimated wall time ~{len(tasks) * 220 / N_WORKERS / 60:.0f} min)")

    by_cell: Dict[str, List[Dict]] = {name: [] for name, _ in cells}

    t_start = time.time()
    completed = 0
    with ProcessPoolExecutor(max_workers=N_WORKERS) as ex:
        futs = {ex.submit(_run_one, t): t for t in tasks}
        for fut in as_completed(futs):
            cell_name, seed, result, final = fut.result()
            by_cell[cell_name].append(result)
            completed += 1
            elapsed = time.time() - t_start
            avg_per = elapsed / completed
            remaining = avg_per * (len(tasks) - completed)
            print(f"  [{completed}/{len(tasks)}] {cell_name} seed={seed} "
                  f"score={result.get('score', 0):.3f} rev=${result.get('cumulative_revenue', 0)/1e6:.1f}M  "
                  f"elapsed={elapsed/60:.1f}min ETA={remaining/60:.1f}min", flush=True)

    phase_results = {}
    for cell_name, _ in cells:
        agg = _aggregate(by_cell[cell_name])
        phase_results[cell_name] = agg
        print(f"\n--- {cell_name} ---")
        print(f"  composite: {agg.get('score_mean', 0):.4f} ± {agg.get('score_std', 0):.4f}")
        print(f"  cum_rev:   ${agg.get('cumulative_revenue_mean', 0):,.0f} ± ${agg.get('cumulative_revenue_std', 0):,.0f}")
        print(f"  T4+ ops:   {agg.get('t4_plus_operators_mean', 0):.0f}")
        print(f"  retention: {agg.get('retention_score_mean', 0):.3f}  "
              f"stability: {agg.get('stability_score_mean', 0):.3f}  "
              f"cap_util:  {agg.get('capacity_utilization_score_mean', 0):.3f}")

    elapsed_total = time.time() - t_start
    print(f"\n{label} complete in {elapsed_total/60:.1f} min")
    return phase_results


# ─── PHASE 1: COMBO + DIAGNOSTIC ──────────────────────────────────────────
def build_phase1() -> List[Tuple[str, Dict]]:
    cells = []

    # v5_winner_combo: all 4 track winners stacked
    p = copy.deepcopy(PARAMS_V5)
    # Track 1 winner: revenue-gated (already the train_v5 default)
    # Track 2 winner: transition_m12
    p["points_to_token"] = {"trigger_type": "month", "month_index": 12}
    # Track 3 winner: nodes_med_bond ($5K, 50/50) — already the default in train_v5
    # Track 4 winner: intelligence_library at m24
    p.setdefault("stress", {})["intelligence_library_start_month"] = 24
    p["stress"]["intelligence_library_factor"] = 0.5
    cells.append(("v5_winner_combo", p))

    # v5_combo_no_intel: same minus Intel Library
    p2 = copy.deepcopy(PARAMS_V5)
    p2["points_to_token"] = {"trigger_type": "month", "month_index": 12}
    cells.append(("v5_combo_no_intel", p2))

    # v5_layers_off: closest match to v4_no_personas (turn off all v5 layers)
    p3 = copy.deepcopy(PARAMS_V5)
    p3.pop("tier_unlock", None)
    p3.pop("node_providers", None)
    p3.pop("geography", None)
    p3["points_to_token"] = {"trigger_type": "always_token"}
    p3["customers"].pop("design_partner_contract_term_months", None)
    p3["hardware"]["stake_required_t3_usd"] = 100   # v4 default
    cells.append(("v5_layers_off", p3))

    return cells


# ─── PHASE 2: REVENUE THRESHOLD SWEEP ─────────────────────────────────────
def build_phase2() -> List[Tuple[str, Dict]]:
    cells = []

    # All cells inherit v5_winner_combo (best single-track winners minus tier_unlock)
    def _base():
        p = copy.deepcopy(PARAMS_V5)
        p["points_to_token"] = {"trigger_type": "month", "month_index": 12}
        p.setdefault("stress", {})["intelligence_library_start_month"] = 24
        p["stress"]["intelligence_library_factor"] = 0.5
        return p

    # unlock_very_loose
    p = _base()
    p["tier_unlock"]["rules"] = {
        3: {"cumulative_revenue_usd": 50_000},
        4: {"cumulative_revenue_usd": 250_000},
        6: {"cumulative_revenue_usd": 1_000_000},
    }
    cells.append(("unlock_very_loose", p))

    # unlock_loose
    p = _base()
    p["tier_unlock"]["rules"] = {
        3: {"cumulative_revenue_usd": 100_000},
        4: {"cumulative_revenue_usd": 500_000},
        6: {"cumulative_revenue_usd": 2_000_000},
    }
    cells.append(("unlock_loose", p))

    # unlock_revenue_gated_ref (current winner)
    p = _base()
    p["tier_unlock"]["rules"] = {
        3: {"cumulative_revenue_usd": 250_000},
        4: {"cumulative_revenue_usd": 1_000_000},
        6: {"cumulative_revenue_usd": 5_000_000},
    }
    cells.append(("unlock_revenue_gated_ref", p))

    # unlock_tight
    p = _base()
    p["tier_unlock"]["rules"] = {
        3: {"cumulative_revenue_usd": 500_000},
        4: {"cumulative_revenue_usd": 2_000_000},
        6: {"cumulative_revenue_usd": 10_000_000},
    }
    cells.append(("unlock_tight", p))

    # unlock_op_low (small op-count thresholds)
    p = _base()
    p["tier_unlock"]["rules"] = {
        3: {"op_count_at_prev_tier": 25},
        4: {"op_count_at_prev_tier": 10},
        6: {"op_count_at_prev_tier": 5},
    }
    cells.append(("unlock_op_low", p))

    # unlock_hybrid: OR-trigger (revenue OR op-count) — both must NOT have _require_all
    p = _base()
    p["tier_unlock"]["rules"] = {
        3: {"cumulative_revenue_usd": 100_000, "op_count_at_prev_tier": 50},
        4: {"cumulative_revenue_usd": 500_000, "op_count_at_prev_tier": 25},
        6: {"cumulative_revenue_usd": 2_000_000, "op_count_at_prev_tier": 10},
    }
    cells.append(("unlock_hybrid", p))

    return cells


# ─── PHASE 3: HARDWARE STAKE + NODE PROVISIONING ──────────────────────────
def build_phase3() -> List[Tuple[str, Dict]]:
    cells = []

    # Use phase 2's revenue_gated_ref as the base (Phase 1 result will tell us
    # if we should pivot, but at iter2 design time, revenue_gated is the known winner)
    def _base():
        p = copy.deepcopy(PARAMS_V5)
        p["points_to_token"] = {"trigger_type": "month", "month_index": 12}
        p.setdefault("stress", {})["intelligence_library_start_month"] = 24
        p["stress"]["intelligence_library_factor"] = 0.5
        return p

    # Hardware stake sweep ($300-$500 in $50 steps)
    for stake in (300, 350, 400, 450, 500):
        p = _base()
        p["hardware"]["stake_required_t3_usd"] = stake
        cells.append((f"stake_{stake}", p))

    # Node provisioning (ops_per_node_target)
    for target in (2000, 4000, 8000, 12000):
        p = _base()
        p["nodes"]["ops_per_node_target"] = target
        cells.append((f"nodes_{target//1000}k", p))

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

    if cmd in ("phase1", "all"):
        cells = build_phase1()
        results = run_phase(cells, mc, "Phase 1 — Combo + Diagnostic")
        all_results["phase1"] = results
        with open(os.path.join(OUT_DIR, "iter2_phase1_results.json"), "w") as f:
            json.dump(results, f, indent=2)

    if cmd in ("phase2", "all"):
        cells = build_phase2()
        results = run_phase(cells, mc, "Phase 2 — Revenue threshold sweep")
        all_results["phase2"] = results
        with open(os.path.join(OUT_DIR, "iter2_phase2_results.json"), "w") as f:
            json.dump(results, f, indent=2)

    if cmd in ("phase3", "all"):
        cells = build_phase3()
        results = run_phase(cells, mc, "Phase 3 — Hardware stake + node provisioning")
        all_results["phase3"] = results
        with open(os.path.join(OUT_DIR, "iter2_phase3_results.json"), "w") as f:
            json.dump(results, f, indent=2)

    if cmd == "all":
        with open(os.path.join(OUT_DIR, "iter2_all_results.json"), "w") as f:
            json.dump(all_results, f, indent=2)

    elapsed = time.time() - overall_start
    print(f"\n{'='*78}")
    print(f"DONE — total wall time {elapsed/60:.1f} min ({elapsed/3600:.2f} hrs)")
    print(f"Results in: {OUT_DIR}/iter2_*.json")
    print(f"{'='*78}")


if __name__ == "__main__":
    main()
