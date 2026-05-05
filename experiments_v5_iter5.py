"""
CrowdBrain v5 — iteration 5: full open-ended discovery sweep
============================================================
User directive: "Let model discover" — open-ended ranges on all axes.
Builds on iter4's `jcurve_combined_60mo` standing winner (composite 0.683 ± 0.020).

Phases:
  A — Stake sweep open-ended ($0/$10/$25/$50/$100/$200) × 60mo
      Sensitivity flagged stake as #1 lever; iter4 winner @ $100, sensitivity says go lower.
  B — MC=50 winner validation: rerun jcurve_combined_60mo to halve CIs
  C — Combined-stress pairs (4 cells × 60mo): defenses for "what if X AND Y"
  D — Q4 milestone fix structures (5 cells × 36mo): try to push P(milestone) ≥ 50%
  E — Persona reintroduction (4 mix cells × 60mo): test cost of behavioral honesty
  F — Token-price clamp variant (1 cell × 60mo): "median deck" view
  G — Per-customer-tier matching enabled (1 cell × 60mo) — engine change required first

Total cells: 22  (Phase G adds 1 once engine change lands)
Compute estimate: ~25-35 min wall time at MC=20 + ~5 min for MC=50.

Usage:
  python experiments_v5_iter5.py phaseA              # Stake sweep
  python experiments_v5_iter5.py phaseB              # MC=50 validation
  python experiments_v5_iter5.py phaseC              # Combined stress
  python experiments_v5_iter5.py phaseD              # Q4 fixes
  python experiments_v5_iter5.py phaseE              # Personas
  python experiments_v5_iter5.py phaseF              # Token clamp
  python experiments_v5_iter5.py phaseG              # Per-tier matching (after engine change)
  python experiments_v5_iter5.py all [MC]            # all phases; MC default 20
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


# ─── COMMON: APPLY ITER4 WINNERS (op_loose 10/5/2 + stake $100) ──────────
def winner_base() -> Dict:
    """Returns deep-copy of jcurve_combined_60mo standing-winner config."""
    p = copy.deepcopy(PARAMS_V5_REALISTIC)
    p["tier_unlock"]["rules"] = {
        3: {"op_count_at_prev_tier": 10},
        4: {"op_count_at_prev_tier": 5},
        6: {"op_count_at_prev_tier": 2},
    }
    p["hardware"]["stake_required_t3_usd"] = 100
    return p


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


# ─── PHASE A: STAKE SWEEP (open-ended) ─────────────────────────────────────
def build_phaseA() -> List[Tuple[str, Dict, int]]:
    """
    Open-ended stake discovery: $0 to $200.
    Sensitivity in iter4 said going lower than $100 should help. Test if there's
    a floor where stake near zero stops working (operator quality collapse?).
    """
    cells = []
    for stake in [0, 10, 25, 50, 100, 200]:
        p = winner_base()
        p["hardware"]["stake_required_t3_usd"] = stake
        cells.append((f"stake_{stake:03d}", p, 60))
    return cells


# ─── PHASE B: MC=50 WINNER VALIDATION ──────────────────────────────────────
def build_phaseB() -> List[Tuple[str, Dict, int]]:
    """Tight MC=50 rerun on the standing winner — halves CI for investor presentation."""
    return [("jcurve_combined_60mo_mc50", winner_base(), 60)]


# ─── PHASE C: COMBINED STRESS PAIRS ────────────────────────────────────────
def build_phaseC() -> List[Tuple[str, Dict, int]]:
    """
    Pairs of stress scenarios — defends "what if X AND Y" investor questions.
    Single-axis stress in iter4 said funding_winter -30% and mvp_slip -47% are
    existential. Combined effects test whether they're additive or interact.
    """
    cells = []

    def _w():
        return winner_base()

    # funding_winter + mvp_slip (the two existentials together — should be catastrophic)
    p = _w()
    p.setdefault("stress", {})["customer_arrival_multiplier"] = 0.25
    p["stress"]["customer_arrival_start_month"] = 6
    p["stress"]["mvp_start_month"] = 3
    cells.append(("stress_winter_AND_slip", p, 60))

    # funding_winter + tesla_hiring (recession + talent drain)
    p = _w()
    p.setdefault("stress", {})["customer_arrival_multiplier"] = 0.25
    p["stress"]["customer_arrival_start_month"] = 6
    p["geography"]["tesla_stress"] = {
        "fraction_of_t3plus_with_alt_offer": 0.30,
        "alt_wage_usd": 48.0,
        "wage_gap_churn_multiplier_per_dollar": 0.005,
    }
    cells.append(("stress_winter_AND_tesla", p, 60))

    # geo_GE shock + funding_winter (Georgia capacity hit + capital crunch)
    p = _w()
    p["geography"]["geo_shock"] = {
        "region": "georgia",
        "start_month": 18,
        "duration": 6,
        "capacity_factor": 0.30,
    }
    p.setdefault("stress", {})["customer_arrival_multiplier"] = 0.25
    p["stress"]["customer_arrival_start_month"] = 6
    cells.append(("stress_geoGE_AND_winter", p, 60))

    # mvp_slip + intel_library (slow start partially offset by data licensing upside)
    p = _w()
    p.setdefault("stress", {})["mvp_start_month"] = 3
    p["stress"]["intelligence_library_start_month"] = 24
    p["stress"]["intelligence_library_factor"] = 0.5
    cells.append(("stress_slip_AND_intel", p, 60))

    return cells


# ─── PHASE D: Q4 MILESTONE FIX STRUCTURES ──────────────────────────────────
def build_phaseD() -> List[Tuple[str, Dict, int]]:
    """
    Push Q4 2026 milestone hit rate ≥ 50% if possible. iter4 found 0% under
    pure J-curve, so we test 5 deliberate fixes that don't break realism.
    """
    cells = []

    # q4_5dp: 5 design partners signed at TGE (vs current 3)
    p = winner_base()
    p["customers"]["arrival"]["design_partners"] = [
        ("manufacturing",  20_000),
        ("warehouse",      15_000),
        ("healthcare",     35_000),
        ("robotics_oem",   25_000),
        ("manufacturing",  20_000),    # 2nd manufacturing DP
    ]
    cells.append(("q4_5dp", p, 36))

    # q4_early_ops: accelerated onboarding ×0.30 in m1-6, decay back to ×0.10 after
    # We don't have time-varying onboarding directly — approximate with
    # higher overall mult ×0.20 (covers the ramp). Real time-vary requires engine work.
    p = winner_base()
    p["task_model"]["onboarding_multiplier"] = 0.20
    cells.append(("q4_early_ops", p, 36))

    # q4_bigger_dp: DPs at $40K/$30K/$60K (vs $20K/$15K/$35K)
    p = winner_base()
    p["customers"]["arrival"]["design_partners"] = [
        ("manufacturing",  40_000),
        ("warehouse",      30_000),
        ("healthcare",     60_000),
    ]
    cells.append(("q4_bigger_dp", p, 36))

    # q4_combo_all_three: 5 DPs + bigger contracts + accelerated ramp
    p = winner_base()
    p["customers"]["arrival"]["design_partners"] = [
        ("manufacturing",  40_000),
        ("warehouse",      30_000),
        ("healthcare",     60_000),
        ("robotics_oem",   45_000),
        ("manufacturing",  40_000),
    ]
    p["task_model"]["onboarding_multiplier"] = 0.20
    cells.append(("q4_combo_all_three", p, 36))

    # q4_lower_target: just measure baseline at relaxed target ($300K ARR + 3 customers)
    # The realism_q4_2026 fields are computed on $500K target; we still record raw m8 fields
    # so analysis can apply its own threshold. Same baseline winner.
    cells.append(("q4_lower_target", winner_base(), 36))

    return cells


# ─── PHASE E: PERSONA REINTRODUCTION ───────────────────────────────────────
# v4 personas were OFF in winner. Test whether reintroducing them under
# realistic params has a smaller cost than the -0.24 hit observed under
# unrealistic params.
DEFAULT_PERSONA_DEFS = {
    "casual": {
        "share":              0.60,
        "time_per_month":     40,
        "base_sell":          0.55,
        "stake_aggro":        0.05,
        "tier_speed":         1.30,
        "quality_focus":      0.80,
        "validator_share":    0.0,
        "front_load_stake":   0.0,
    },
    "pro_earner": {
        "share":              0.25,
        "time_per_month":     160,
        "base_sell":          0.30,
        "stake_aggro":        0.40,
        "tier_speed":         0.70,
        "quality_focus":      1.10,
        "validator_share":    0.0,
        "front_load_stake":   0.0,
    },
    "validator": {
        "share":              0.10,
        "time_per_month":     120,
        "base_sell":          0.20,
        "stake_aggro":        0.40,
        "tier_speed":         1.00,
        "quality_focus":      1.20,
        "validator_share":    0.50,
        "front_load_stake":   0.0,
    },
    "hw_investor": {
        "share":              0.05,
        "time_per_month":     80,
        "base_sell":          0.15,
        "stake_aggro":        0.80,
        "tier_speed":         1.00,
        "quality_focus":      1.00,
        "validator_share":    0.0,
        "front_load_stake":   0.30,
    },
}


def _personas_with_shares(casual, pro, val, hw) -> Dict:
    p = copy.deepcopy(DEFAULT_PERSONA_DEFS)
    p["casual"]["share"] = casual
    p["pro_earner"]["share"] = pro
    p["validator"]["share"] = val
    p["hw_investor"]["share"] = hw
    return p


def _operators_block(personas: Dict) -> Dict:
    return {
        "personas": personas,
        "learning":  {"alpha": 0.10, "cap": 0.30},
        "referrals": {"base_rate_per_op": 0.02, "persona_inheritance_prob": 0.30},
    }


def build_phaseE() -> List[Tuple[str, Dict, int]]:
    cells = []

    # 60/25/10/5 — v4 default mix
    p = winner_base()
    p["operators"] = _operators_block(_personas_with_shares(0.60, 0.25, 0.10, 0.05))
    cells.append(("personas_60_25_10_5", p, 60))

    # 40/40/15/5 — pro-heavier
    p = winner_base()
    p["operators"] = _operators_block(_personas_with_shares(0.40, 0.40, 0.15, 0.05))
    cells.append(("personas_40_40_15_5", p, 60))

    # 20/40/30/10 — validator-heavy (memo v5 favors validators for quality)
    p = winner_base()
    p["operators"] = _operators_block(_personas_with_shares(0.20, 0.40, 0.30, 0.10))
    cells.append(("personas_20_40_30_10", p, 60))

    # off (control = standing winner with no personas pillar)
    cells.append(("personas_off", winner_base(), 60))

    return cells


# ─── PHASE F: TOKEN-PRICE CLAMP VARIANT ────────────────────────────────────
def build_phaseF() -> List[Tuple[str, Dict, int]]:
    """
    Cap token price at $20 via large AMM (10x bigger pools = 100x harder to price-pump).
    Produces "median deck" trajectory where price stays in conservative band.
    """
    p = winner_base()
    p["macro"]["amm"]["initial_token_pool"] = 2_000_000      # 10x deeper
    p["macro"]["amm"]["initial_usd_pool"]   = 2_000_000      # 10x deeper
    return [("token_clamp_60mo", p, 60)]


# ─── PHASE G: PER-CUSTOMER-TIER MATCHING ENABLED ───────────────────────────
def build_phaseG() -> List[Tuple[str, Dict, int]]:
    """
    Re-run winner with new per-customer-tier matching enabled.
    Engine change toggles via `customers.matching.per_customer_tier_pool: True`.
    Should reduce active-op decline post-m24 (3K → 1.8K observed in iter4).
    """
    p = winner_base()
    p.setdefault("customers", {}).setdefault("matching", {})["per_customer_tier_pool"] = True
    p["customers"]["matching"]["pool_size_per_tier"] = 25      # each cust matches against 25 ops/tier
    return [("matching_per_tier_60mo", p, 60)]


# ─── ORCHESTRATION ────────────────────────────────────────────────────────
PHASES = {
    "phasea": (build_phaseA, "Phase A — Stake sweep open-ended"),
    "phaseb": (build_phaseB, "Phase B — MC=50 winner validation"),
    "phasec": (build_phaseC, "Phase C — Combined stress pairs"),
    "phased": (build_phaseD, "Phase D — Q4 milestone fix structures"),
    "phasee": (build_phaseE, "Phase E — Persona reintroduction"),
    "phasef": (build_phaseF, "Phase F — Token-price clamp variant"),
    "phaseg": (build_phaseG, "Phase G — Per-customer-tier matching enabled"),
}


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

    if cmd == "all":
        # Run all phases. Phase B uses MC=50 hardcoded.
        for key, (builder, label) in PHASES.items():
            phase_mc = 50 if key == "phaseb" else mc
            cells = builder()
            results = run_phase(cells, phase_mc, label)
            all_results[key] = results
            with open(os.path.join(OUT_DIR, f"iter5_{key}_results.json"), "w") as f:
                json.dump(results, f, indent=2)
        with open(os.path.join(OUT_DIR, "iter5_all_results.json"), "w") as f:
            json.dump(all_results, f, indent=2)
    elif cmd in PHASES:
        builder, label = PHASES[cmd]
        # Phase B uses MC=50 by default (pass override via CLI)
        if cmd == "phaseb" and mc == DEFAULT_MC:
            mc = 50
        cells = builder()
        results = run_phase(cells, mc, label)
        all_results[cmd] = results
        with open(os.path.join(OUT_DIR, f"iter5_{cmd}_results.json"), "w") as f:
            json.dump(results, f, indent=2)
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)

    elapsed = time.time() - overall_start
    print(f"\n{'='*78}")
    print(f"DONE — total wall time {elapsed/60:.1f} min")
    print(f"Results in: {OUT_DIR}/iter5_*.json")
    print(f"{'='*78}")


if __name__ == "__main__":
    main()
