"""
CrowdBrain v5 — iteration 4: J-curve REALISTIC sweep + stakeholder package
==========================================================================
Uses the J-curve calibration (slow start + rapid late acceleration as teleop
market wakes up) from train_v5_realistic.PARAMS_V5_REALISTIC.

Five phases addressing the user's iter4 requests:
  Phase A — Combined winners (op_loose + stake_100) at 36mo and 60mo
  Phase B — Q4 milestone fix candidates (4 design partners / bigger DPs / faster ramp)
  Phase C — Realistic-mode stress tests
  Phase D — Sensitivity (±20% on key params)
  Phase E — Q4 milestone probability at MC=50 on winner

Total: ~28 cells. ~10 min wall time at MC=20 on 23 cores
(realistic-mode is 5-10x faster than unrealistic-mode runs).

Usage:
  python experiments_v5_iter4.py phaseA            # Combined winners (4 cells)
  python experiments_v5_iter4.py phaseB            # Q4 fix candidates (5 cells)
  python experiments_v5_iter4.py phaseC            # Stress tests (6 cells)
  python experiments_v5_iter4.py phaseD            # Sensitivity (8 cells)
  python experiments_v5_iter4.py milestone         # Q4 milestone at MC=50
  python experiments_v5_iter4.py all [MC]          # all phases + milestone; MC default 20
"""

import sys
import json
import time
import copy
import os
from typing import Dict, List, Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed

import prepare_v5
from prepare_v5 import run_simulation_v5, RANDOM_SEED
from train_v5_realistic import PARAMS_V5_REALISTIC, evaluate_realism


DEFAULT_MC = 20
N_WORKERS = max(1, (os.cpu_count() or 4) - 1)
OUT_DIR = "v5_results"
os.makedirs(OUT_DIR, exist_ok=True)


def _run_one(args: Tuple[str, Dict, int, int]) -> Tuple[str, int, Dict, Dict]:
    cell_name, params, seed, sim_months = args
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


def run_phase(cells: List[Tuple[str, Dict, int]], mc: int, label: str) -> Dict:
    print(f"\n{'='*78}")
    print(f"PHASE: {label}  |  cells={len(cells)}  MC={mc}  workers={N_WORKERS}")
    print(f"{'='*78}\n")

    tasks = []
    for cell_name, params, sim_months in cells:
        for i in range(mc):
            tasks.append((cell_name, params, RANDOM_SEED + i, sim_months))
    print(f"Total runs: {len(tasks)}")

    by_cell: Dict[str, List[Dict]] = {name: [] for name, _, _ in cells}
    t_start = time.time()
    completed = 0
    with ProcessPoolExecutor(max_workers=N_WORKERS) as ex:
        futs = {ex.submit(_run_one, t): t for t in tasks}
        for fut in as_completed(futs):
            cell_name, seed, result, final = fut.result()
            by_cell[cell_name].append(result)
            completed += 1
            if completed % 20 == 0 or completed == len(tasks):
                elapsed = time.time() - t_start
                print(f"  [{completed}/{len(tasks)}] elapsed={elapsed:.1f}s  "
                      f"latest: {cell_name} score={result.get('score', 0):.3f} "
                      f"ARR=${result.get('realism_final_arr_usd', 0)/1e6:.1f}M", flush=True)

    phase_results = {}
    for cell_name, _, _ in cells:
        agg = _aggregate(by_cell[cell_name])
        phase_results[cell_name] = agg
        print(f"\n--- {cell_name} ---")
        print(f"  composite:           {agg.get('score_mean', 0):.4f} ± {agg.get('score_std', 0):.4f}")
        print(f"  cum_rev:             ${agg.get('cumulative_revenue_mean', 0):,.0f}")
        print(f"  final ARR:           ${agg.get('realism_final_arr_usd_mean', 0):,.0f}")
        print(f"  final customers:     {agg.get('realism_final_customer_count_mean', 0):.0f}")
        print(f"  T4+ ops:             {agg.get('t4_plus_operators_mean', 0):.0f}")
        print(f"  active ops:          {agg.get('active_operators_mean', 0):.0f}")
        print(f"  Q4 milestone hit:    {agg.get('realism_q4_2026_milestone_hit_pct_true', 0)*100:.0f}% of runs")

    elapsed_total = time.time() - t_start
    print(f"\n{label} complete in {elapsed_total/60:.1f} min")
    return phase_results


# ─── PHASE A: COMBINED WINNERS ────────────────────────────────────────────
def build_phaseA() -> List[Tuple[str, Dict, int]]:
    """Apply iter3 winners (op_loose unlock + stake_100) to J-curve baseline."""
    cells = []

    # Baseline references
    cells.append(("jcurve_baseline_36mo", copy.deepcopy(PARAMS_V5_REALISTIC), 36))
    cells.append(("jcurve_baseline_60mo", copy.deepcopy(PARAMS_V5_REALISTIC), 60))

    # Combined winners: op_loose unlock (10/5/2) + stake_100
    p = copy.deepcopy(PARAMS_V5_REALISTIC)
    p["tier_unlock"]["rules"] = {
        3: {"op_count_at_prev_tier": 10},
        4: {"op_count_at_prev_tier": 5},
        6: {"op_count_at_prev_tier": 2},
    }
    p["hardware"]["stake_required_t3_usd"] = 100
    cells.append(("jcurve_combined_36mo", p, 36))
    cells.append(("jcurve_combined_60mo", copy.deepcopy(p), 60))

    return cells


# ─── PHASE B: Q4 MILESTONE FIX CANDIDATES ─────────────────────────────────
def build_phaseB() -> List[Tuple[str, Dict, int]]:
    """Test fixes to push Q4 2026 hit rate up. Note J-curve baseline likely
    won't hit memo's $500K ARR target at month 8 — also test relaxed targets."""
    cells = []

    # 4 design partners (instead of 3)
    p = copy.deepcopy(PARAMS_V5_REALISTIC)
    p["customers"]["arrival"]["design_partners"] = [
        ("manufacturing",  20_000),
        ("warehouse",      15_000),
        ("healthcare",     35_000),
        ("robotics_oem",   25_000),    # NEW 4th DP
    ]
    cells.append(("jcurve_4dp", p, 36))

    # Bigger DP contracts (~50% larger)
    p = copy.deepcopy(PARAMS_V5_REALISTIC)
    p["customers"]["arrival"]["design_partners"] = [
        ("manufacturing",  30_000),
        ("warehouse",      22_000),
        ("healthcare",     50_000),
    ]
    cells.append(("jcurve_bigger_dp", p, 36))

    # Faster operator ramp in first 12 months (mult 0.20 instead of 0.10)
    # Approximated by doubling onboarding overall (since we can't easily time-vary)
    p = copy.deepcopy(PARAMS_V5_REALISTIC)
    p["task_model"]["onboarding_multiplier"] = 0.20
    cells.append(("jcurve_fast_ramp", p, 36))

    # Combined Q4 fix: 4 DPs + bigger contracts + fast ramp
    p = copy.deepcopy(PARAMS_V5_REALISTIC)
    p["customers"]["arrival"]["design_partners"] = [
        ("manufacturing",  35_000),
        ("warehouse",      25_000),
        ("healthcare",     55_000),
        ("robotics_oem",   30_000),
    ]
    p["task_model"]["onboarding_multiplier"] = 0.20
    cells.append(("jcurve_q4_combo", p, 36))

    # Combined Q4 fix at 60mo
    cells.append(("jcurve_q4_combo_60mo", copy.deepcopy(p), 60))

    return cells


# ─── PHASE C: REALISTIC STRESS TESTS ──────────────────────────────────────
def build_phaseC() -> List[Tuple[str, Dict, int]]:
    cells = []

    def _base():
        return copy.deepcopy(PARAMS_V5_REALISTIC)

    # Baseline reference (60mo where J-curve effects are clearest)
    cells.append(("stress_baseline_60mo", _base(), 60))

    # Funding winter: customer arrivals × 0.25 from m6
    p = _base()
    p.setdefault("stress", {})["customer_arrival_multiplier"] = 0.25
    p["stress"]["customer_arrival_start_month"] = 6
    cells.append(("stress_funding_winter", p, 60))

    # Tesla/1X hiring stress
    p = _base()
    p["geography"]["tesla_stress"] = {
        "fraction_of_t3plus_with_alt_offer": 0.30,
        "alt_wage_usd": 48.0,
        "wage_gap_churn_multiplier_per_dollar": 0.005,
    }
    cells.append(("stress_tesla_hiring", p, 60))

    # Geo shock — Georgia (most load-bearing per iter1)
    p = _base()
    p["geography"]["geo_shock"] = {
        "region": "georgia",
        "start_month": 18,    # mid-J-curve
        "duration": 6,
        "capacity_factor": 0.30,
    }
    cells.append(("stress_geo_GE", p, 60))

    # MVP slip — onboarding starts at m3
    p = _base()
    p.setdefault("stress", {})["mvp_start_month"] = 3
    p["stress"]["customer_arrival_multiplier"] = 0.0
    p["stress"]["customer_arrival_start_month"] = 0
    cells.append(("stress_mvp_slip", p, 60))

    # Intelligence Library activation at m24
    p = _base()
    p.setdefault("stress", {})["intelligence_library_start_month"] = 24
    p["stress"]["intelligence_library_factor"] = 0.5
    cells.append(("stress_intel_library", p, 60))

    return cells


# ─── PHASE D: SENSITIVITY ─────────────────────────────────────────────────
def build_phaseD() -> List[Tuple[str, Dict, int]]:
    """±20% sensitivity on 4 most impactful params (run at 60mo to capture J-curve)."""
    cells = []

    def _base():
        return copy.deepcopy(PARAMS_V5_REALISTIC)

    # lambda_max_per_segment (customer arrival rate)
    for direction, factor in [("p20", 1.20), ("m20", 0.80)]:
        p = _base()
        p["customers"]["arrival"]["lambda_max_per_segment"] *= factor
        cells.append((f"sens_lambda_{direction}", p, 60))

    # contract size (all 4 segments uniformly)
    for direction, factor in [("p20", 1.20), ("m20", 0.80)]:
        p = _base()
        for seg_name in p["customers"]["segments"]:
            p["customers"]["segments"][seg_name]["size_mean_usd"] = (
                p["customers"]["segments"][seg_name]["size_mean_usd"] * factor
            )
        cells.append((f"sens_contract_{direction}", p, 60))

    # hardware stake t3
    for direction, factor in [("p20", 1.20), ("m20", 0.80)]:
        p = _base()
        p["hardware"]["stake_required_t3_usd"] = int(p["hardware"]["stake_required_t3_usd"] * factor)
        cells.append((f"sens_stake_{direction}", p, 60))

    # onboarding multiplier
    for direction, factor in [("p20", 1.20), ("m20", 0.80)]:
        p = _base()
        p["task_model"]["onboarding_multiplier"] *= factor
        cells.append((f"sens_onboarding_{direction}", p, 60))

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

    if cmd in ("phasea", "all"):
        cells = build_phaseA()
        results = run_phase(cells, mc, "Phase A — Combined winners on J-curve baseline")
        all_results["phaseA"] = results
        with open(os.path.join(OUT_DIR, "iter4_phaseA_results.json"), "w") as f:
            json.dump(results, f, indent=2)

    if cmd in ("phaseb", "all"):
        cells = build_phaseB()
        results = run_phase(cells, mc, "Phase B — Q4 milestone fix candidates")
        all_results["phaseB"] = results
        with open(os.path.join(OUT_DIR, "iter4_phaseB_results.json"), "w") as f:
            json.dump(results, f, indent=2)

    if cmd in ("phasec", "all"):
        cells = build_phaseC()
        results = run_phase(cells, mc, "Phase C — Realistic-mode stress tests (60mo)")
        all_results["phaseC"] = results
        with open(os.path.join(OUT_DIR, "iter4_phaseC_results.json"), "w") as f:
            json.dump(results, f, indent=2)

    if cmd in ("phased", "all"):
        cells = build_phaseD()
        results = run_phase(cells, mc, "Phase D — Sensitivity ±20% (60mo)")
        all_results["phaseD"] = results
        with open(os.path.join(OUT_DIR, "iter4_phaseD_results.json"), "w") as f:
            json.dump(results, f, indent=2)

    if cmd in ("milestone", "all"):
        milestone_mc = max(50, mc)
        # Use the best Q4-fix combo
        p = copy.deepcopy(PARAMS_V5_REALISTIC)
        p["customers"]["arrival"]["design_partners"] = [
            ("manufacturing",  35_000),
            ("warehouse",      25_000),
            ("healthcare",     55_000),
            ("robotics_oem",   30_000),
        ]
        p["task_model"]["onboarding_multiplier"] = 0.20
        cells = [("jcurve_q4_combo_milestone", p, 36)]
        results = run_phase(cells, milestone_mc, f"Milestone — Q4 2026 probability at MC={milestone_mc}")
        all_results["milestone"] = results
        with open(os.path.join(OUT_DIR, "iter4_milestone_results.json"), "w") as f:
            json.dump(results, f, indent=2)

    if cmd == "all":
        with open(os.path.join(OUT_DIR, "iter4_all_results.json"), "w") as f:
            json.dump(all_results, f, indent=2)

    elapsed = time.time() - overall_start
    print(f"\n{'='*78}")
    print(f"DONE — total wall time {elapsed/60:.1f} min")
    print(f"Results in: {OUT_DIR}/iter4_*.json")
    print(f"{'='*78}")


if __name__ == "__main__":
    main()
