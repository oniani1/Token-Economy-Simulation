"""
CrowdBrain v5 — iteration 3: REALISTIC parameter sweeps
========================================================
Uses PARAMS_V5_REALISTIC (calibrated customer model + token economy + onboarding)
to find the optimal v5 config under realistic, defensible-vs-real-world conditions.

All cells start from PARAMS_V5_REALISTIC and override individual axes.

Phases:
  1. Realistic baseline + diagnostic (3 cells)
  2. Realistic unlock policy sweep (5 cells)
  3. Realistic emission + stake fine-tuning (6 cells)
  4. 60-month long horizon (2 cells)
  5. Q4 2026 milestone probability (1 cell, 50 MC for confidence)

Total: 17 cells. ~50 min wall time at MC=20 on 23 cores.

Usage:
  python experiments_v5_iter3.py phase1            # baseline + combo (3 cells)
  python experiments_v5_iter3.py phase2            # unlock sweep (5 cells)
  python experiments_v5_iter3.py phase3            # emission + stake sweep (6 cells)
  python experiments_v5_iter3.py phase4            # 60mo horizon (2 cells)
  python experiments_v5_iter3.py milestone         # Q4 2026 probability at MC=50
  python experiments_v5_iter3.py all [MC]          # all phases + milestone; MC default 20
"""

import sys
import json
import time
import copy
import os
from typing import Dict, List, Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed

import prepare_v5
from prepare_v5 import run_simulation_v5, evaluate_v5, RANDOM_SEED
from train_v5_realistic import PARAMS_V5_REALISTIC, evaluate_realism


DEFAULT_MC = 20
N_WORKERS = max(1, (os.cpu_count() or 4) - 1)
OUT_DIR = "v5_results"
os.makedirs(OUT_DIR, exist_ok=True)


# ─── WORKER ───────────────────────────────────────────────────────────────
def _run_one(args: Tuple[str, Dict, int, int]) -> Tuple[str, int, Dict, Dict]:
    cell_name, params, seed, sim_months = args
    # Override SIMULATION_MONTHS for long-horizon runs
    prepare_v5.SIMULATION_MONTHS = sim_months
    history, customers = run_simulation_v5(params, seed=seed)
    result = evaluate_realism(history, customers)
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
        # Numeric fields → mean+std
        vals = [r.get(k, 0) for r in results if isinstance(r.get(k), (int, float))]
        if vals:
            mean = sum(vals) / len(vals)
            std = (sum((v - mean) ** 2 for v in vals) / len(vals)) ** 0.5
            agg[k + "_mean"] = round(mean, 4)
            agg[k + "_std"] = round(std, 4)
        # Boolean fields → fraction True (probability)
        bool_vals = [r.get(k) for r in results if isinstance(r.get(k), bool)]
        if bool_vals:
            agg[k + "_pct_true"] = round(sum(bool_vals) / len(bool_vals), 4)
    return agg


def run_phase(cells: List[Tuple[str, Dict, int]], mc: int, label: str) -> Dict:
    """cells: list of (cell_name, params, sim_months)"""
    print(f"\n{'='*78}")
    print(f"PHASE: {label}  |  cells={len(cells)}  MC={mc}  workers={N_WORKERS}")
    print(f"{'='*78}\n")

    tasks = []
    for cell_name, params, sim_months in cells:
        for i in range(mc):
            tasks.append((cell_name, params, RANDOM_SEED + i, sim_months))
    print(f"Total runs: {len(tasks)}  (estimated wall time ~{len(tasks) * 220 / N_WORKERS / 60:.0f} min)")

    by_cell: Dict[str, List[Dict]] = {name: [] for name, _, _ in cells}

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
            arr = result.get("realism_final_arr_usd", 0)
            print(f"  [{completed}/{len(tasks)}] {cell_name} seed={seed} "
                  f"score={result.get('score', 0):.3f} cust={result.get('realism_final_customer_count', 0)} "
                  f"ARR=${arr/1e6:.1f}M Q4hit={result.get('realism_q4_2026_milestone_hit', False)}  "
                  f"elapsed={elapsed/60:.1f}min ETA={remaining/60:.1f}min", flush=True)

    phase_results = {}
    for cell_name, _, _ in cells:
        agg = _aggregate(by_cell[cell_name])
        phase_results[cell_name] = agg
        print(f"\n--- {cell_name} ---")
        print(f"  composite:           {agg.get('score_mean', 0):.4f} ± {agg.get('score_std', 0):.4f}")
        print(f"  cum_rev:             ${agg.get('cumulative_revenue_mean', 0):,.0f} ± ${agg.get('cumulative_revenue_std', 0):,.0f}")
        print(f"  final ARR:           ${agg.get('realism_final_arr_usd_mean', 0):,.0f}")
        print(f"  final customers:     {agg.get('realism_final_customer_count_mean', 0):.0f}")
        print(f"  T4+ ops:             {agg.get('t4_plus_operators_mean', 0):.0f}")
        print(f"  Q4 milestone hit:    {agg.get('realism_q4_2026_milestone_hit_pct_true', 0)*100:.0f}% of runs")
        print(f"  ARR in band:         {agg.get('realism_arr_in_band_pct_true', 0)*100:.0f}% of runs")
        print(f"  customers in band:   {agg.get('realism_customer_count_in_band_pct_true', 0)*100:.0f}% of runs")

    elapsed_total = time.time() - t_start
    print(f"\n{label} complete in {elapsed_total/60:.1f} min")
    return phase_results


# ─── PHASE 1: REALISTIC BASELINE + DIAGNOSTIC ─────────────────────────────
def build_phase1() -> List[Tuple[str, Dict, int]]:
    cells = []

    # Realistic baseline (PARAMS_V5_REALISTIC as-is)
    cells.append(("realistic_baseline", copy.deepcopy(PARAMS_V5_REALISTIC), 36))

    # Realistic with all v5 LAYERS off (just realistic customer/emission/onboarding)
    p = copy.deepcopy(PARAMS_V5_REALISTIC)
    p.pop("tier_unlock", None)
    p.pop("node_providers", None)
    p.pop("geography", None)
    p["points_to_token"] = {"trigger_type": "always_token"}
    p["customers"].pop("design_partner_contract_term_months", None)
    cells.append(("realistic_layers_off", p, 36))

    # Realistic with combo (best iter2 winners + Intel Library at m24)
    p = copy.deepcopy(PARAMS_V5_REALISTIC)
    p["points_to_token"] = {"trigger_type": "month", "month_index": 12}
    p.setdefault("stress", {})["intelligence_library_start_month"] = 24
    p["stress"]["intelligence_library_factor"] = 0.5
    cells.append(("realistic_winner_combo", p, 36))

    return cells


# ─── PHASE 2: REALISTIC UNLOCK POLICY SWEEP ───────────────────────────────
def build_phase2() -> List[Tuple[str, Dict, int]]:
    cells = []

    def _base():
        return copy.deepcopy(PARAMS_V5_REALISTIC)

    # Op-count thresholds (varying)
    p = _base()
    p["tier_unlock"]["rules"] = {
        3: {"op_count_at_prev_tier": 10},
        4: {"op_count_at_prev_tier": 5},
        6: {"op_count_at_prev_tier": 2},
    }
    cells.append(("realistic_op_loose", p, 36))

    # Default realistic op-count (current)
    p = _base()
    cells.append(("realistic_op_medium", p, 36))   # 25/10/5

    p = _base()
    p["tier_unlock"]["rules"] = {
        3: {"op_count_at_prev_tier": 50},
        4: {"op_count_at_prev_tier": 20},
        6: {"op_count_at_prev_tier": 10},
    }
    cells.append(("realistic_op_strict", p, 36))

    # Revenue-gated calibrated to realistic scale
    p = _base()
    p["tier_unlock"]["rules"] = {
        3: {"cumulative_revenue_usd": 100_000},
        4: {"cumulative_revenue_usd": 500_000},
        6: {"cumulative_revenue_usd": 2_000_000},
    }
    cells.append(("realistic_rev_gated", p, 36))

    # Hybrid: rev OR op-count
    p = _base()
    p["tier_unlock"]["rules"] = {
        3: {"cumulative_revenue_usd": 100_000, "op_count_at_prev_tier": 25},
        4: {"cumulative_revenue_usd": 500_000, "op_count_at_prev_tier": 10},
        6: {"cumulative_revenue_usd": 2_000_000, "op_count_at_prev_tier": 5},
    }
    cells.append(("realistic_hybrid", p, 36))

    return cells


# ─── PHASE 3: EMISSION + STAKE SWEEP ──────────────────────────────────────
def build_phase3() -> List[Tuple[str, Dict, int]]:
    cells = []

    # Token emission rate (3 levels)
    for emission_rate, label in [(250_000, "emission_250k"), (500_000, "emission_500k"), (1_000_000, "emission_1m")]:
        p = copy.deepcopy(PARAMS_V5_REALISTIC)
        p["supply"]["monthly_emission_rate"] = emission_rate
        cells.append((label, p, 36))

    # Hardware stake (3 levels)
    for t3_stake, label in [(100, "stake_100"), (200, "stake_200"), (300, "stake_300")]:
        p = copy.deepcopy(PARAMS_V5_REALISTIC)
        p["hardware"]["stake_required_t3_usd"] = t3_stake
        cells.append((label, p, 36))

    return cells


# ─── PHASE 4: 60-MONTH LONG HORIZON ───────────────────────────────────────
def build_phase4() -> List[Tuple[str, Dict, int]]:
    cells = []

    # Realistic baseline at 60mo
    cells.append(("realistic_baseline_60mo", copy.deepcopy(PARAMS_V5_REALISTIC), 60))

    # Realistic with combo at 60mo
    p = copy.deepcopy(PARAMS_V5_REALISTIC)
    p["points_to_token"] = {"trigger_type": "month", "month_index": 12}
    p.setdefault("stress", {})["intelligence_library_start_month"] = 24
    p["stress"]["intelligence_library_factor"] = 0.5
    cells.append(("realistic_combo_60mo", p, 60))

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
        results = run_phase(cells, mc, "Phase 1 — Realistic baseline + diagnostic")
        all_results["phase1"] = results
        with open(os.path.join(OUT_DIR, "iter3_phase1_results.json"), "w") as f:
            json.dump(results, f, indent=2)

    if cmd in ("phase2", "all"):
        cells = build_phase2()
        results = run_phase(cells, mc, "Phase 2 — Realistic unlock policy sweep")
        all_results["phase2"] = results
        with open(os.path.join(OUT_DIR, "iter3_phase2_results.json"), "w") as f:
            json.dump(results, f, indent=2)

    if cmd in ("phase3", "all"):
        cells = build_phase3()
        results = run_phase(cells, mc, "Phase 3 — Emission + stake fine-tuning")
        all_results["phase3"] = results
        with open(os.path.join(OUT_DIR, "iter3_phase3_results.json"), "w") as f:
            json.dump(results, f, indent=2)

    if cmd in ("phase4", "all"):
        cells = build_phase4()
        results = run_phase(cells, mc, "Phase 4 — 60-month long horizon")
        all_results["phase4"] = results
        with open(os.path.join(OUT_DIR, "iter3_phase4_results.json"), "w") as f:
            json.dump(results, f, indent=2)

    if cmd in ("milestone", "all"):
        # MC=50 for confidence on Q4 milestone probability
        milestone_mc = max(50, mc)
        cells = [("realistic_baseline_milestone", copy.deepcopy(PARAMS_V5_REALISTIC), 36)]
        results = run_phase(cells, milestone_mc, f"Milestone — Q4 2026 probability at MC={milestone_mc}")
        all_results["milestone"] = results
        with open(os.path.join(OUT_DIR, "iter3_milestone_results.json"), "w") as f:
            json.dump(results, f, indent=2)

    if cmd == "all":
        with open(os.path.join(OUT_DIR, "iter3_all_results.json"), "w") as f:
            json.dump(all_results, f, indent=2)

    elapsed = time.time() - overall_start
    print(f"\n{'='*78}")
    print(f"DONE — total wall time {elapsed/60:.1f} min ({elapsed/3600:.2f} hrs)")
    print(f"Results in: {OUT_DIR}/iter3_*.json")
    print(f"{'='*78}")


if __name__ == "__main__":
    main()
