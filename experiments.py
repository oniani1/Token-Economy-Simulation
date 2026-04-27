"""
Experiments — sweep, ablation, stress tests, output for CrowdTrain v3.

This is the "let the sim breathe" layer. Provides:
- parameter_sweep: Cartesian-product runner over a grid of axes
- ablation_test: turn off one new mechanic at a time to attribute contribution
- stress_test_*: collusion, token crash, node bottleneck, demand shocks
- pareto_frontier: identify non-dominated configs across axes
- emit_csv_timeseries / emit_plots: persist results for further analysis

Designed to be runnable as a script with subcommands, OR imported and called.
"""

import copy
import csv
import itertools
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import prepare
from prepare import run_simulation, evaluate, run_monte_carlo


def deep_set(d: Dict, dot_path: str, value: Any) -> None:
    """Set a nested dict value via dot path: deep_set(p, 'supply.initial_supply', 25M)."""
    keys = dot_path.split(".")
    cur = d
    for k in keys[:-1]:
        if k not in cur or not isinstance(cur[k], dict):
            cur[k] = {}
        cur = cur[k]
    cur[keys[-1]] = value


def deep_get(d: Dict, dot_path: str, default: Any = None) -> Any:
    cur = d
    for k in dot_path.split("."):
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


def short_label(axis_values: Dict[str, Any]) -> str:
    """Human-readable label like 'init=25M_emit=10M_burn=0.50'."""
    parts = []
    for k, v in axis_values.items():
        short_k = k.split(".")[-1].replace("_", "")[:8]
        if isinstance(v, (int, float)):
            if v >= 1_000_000:
                vs = f"{v/1_000_000:.0f}M"
            elif v >= 1000:
                vs = f"{v/1000:.0f}k"
            elif isinstance(v, float):
                vs = f"{v:.2f}"
            else:
                vs = str(v)
        else:
            vs = str(v)
        parts.append(f"{short_k}={vs}")
    return "_".join(parts)


def parameter_sweep(
    base_params: Dict,
    sweep_grid: Dict[str, List[Any]],
    n_runs_per_config: int = 5,
    sim_months: int = 36,
    verbose: bool = True,
) -> List[Dict]:
    """
    Cartesian-product runner.

    sweep_grid example:
        {
            "supply.initial_supply": [10_000_000, 25_000_000, 50_000_000],
            "supply.monthly_emission_rate": [2_000_000, 5_000_000, 10_000_000],
            "burn.burn_pct_of_revenue": [0.30, 0.50, 0.70],
        }

    Returns list of dicts: {config_label, params, metrics (Monte Carlo aggregated)}.
    """
    prepare.SIMULATION_MONTHS = sim_months
    axes = list(sweep_grid.keys())
    value_lists = [sweep_grid[a] for a in axes]
    configs = list(itertools.product(*value_lists))

    if verbose:
        print(f"Sweep: {len(configs)} configs × {n_runs_per_config} MC runs = {len(configs)*n_runs_per_config} sims")
        est_per_sim = 30  # seconds, rough
        print(f"Estimated time: ~{(len(configs)*n_runs_per_config*est_per_sim)/60:.1f} min")

    results = []
    for i, cfg in enumerate(configs):
        params = copy.deepcopy(base_params)
        axis_values = dict(zip(axes, cfg))
        for axis, val in axis_values.items():
            deep_set(params, axis, val)
        label = short_label(axis_values)

        t0 = time.time()
        metrics = run_monte_carlo(params, n_runs=n_runs_per_config)
        elapsed = time.time() - t0

        if verbose:
            score = metrics.get("score_mean", 0)
            std = metrics.get("score_std", 0)
            print(f"  [{i+1}/{len(configs)}] {label[:60]:60s}  score={score:.4f}±{std:.3f}  ({elapsed:.0f}s)")

        results.append({
            "config_label": label,
            "axis_values": axis_values,
            "metrics": metrics,
            "elapsed_seconds": elapsed,
        })

    return sorted(results, key=lambda r: -r["metrics"].get("score_mean", 0))


def ablation_test(
    base_params: Dict,
    n_runs_per_config: int = 5,
    sim_months: int = 36,
    verbose: bool = True,
) -> Dict[str, Dict]:
    """
    Turn OFF each new mechanic individually and measure score impact vs full enabled.

    Returns:
        {mechanic_name: {metrics, delta_vs_baseline}}
    """
    prepare.SIMULATION_MONTHS = sim_months
    out = {}

    if verbose:
        print(f"Ablation: baseline + {6} mechanic toggles × {n_runs_per_config} MC runs")
        print()

    # Baseline (all mechanics enabled, default params)
    print("Baseline (all mechanics enabled)...")
    t0 = time.time()
    baseline_metrics = run_monte_carlo(base_params, n_runs=n_runs_per_config)
    baseline_score = baseline_metrics.get("score_mean", 0)
    print(f"  Baseline score: {baseline_score:.4f}  ({time.time()-t0:.0f}s)")
    out["baseline"] = {"metrics": baseline_metrics, "delta": 0.0}
    print()

    # 1. Disable validation (all sample rates -> 0 = nothing reviewed = quality drift)
    print("Disable validation (sample_rate=0 across all tiers)...")
    p = copy.deepcopy(base_params)
    p["validation"]["sample_rate_by_tier"] = {t: 0.0 for t in range(7)}
    t0 = time.time()
    m = run_monte_carlo(p, n_runs=n_runs_per_config)
    delta = m.get("score_mean", 0) - baseline_score
    print(f"  Score: {m.get('score_mean', 0):.4f} (delta={delta:+.4f})  ({time.time()-t0:.0f}s)")
    out["no_validation"] = {"metrics": m, "delta": delta}

    # 2. Disable fiat ramp (always pure tokens)
    print("Disable fiat ramp (pure tokens always)...")
    p = copy.deepcopy(base_params)
    p["earnings"]["phase_revenue_ladder_arr_to_fiat_ratio"] = [(0, 0.0), (1_000_000_000, 0.0)]
    t0 = time.time()
    m = run_monte_carlo(p, n_runs=n_runs_per_config)
    delta = m.get("score_mean", 0) - baseline_score
    print(f"  Score: {m.get('score_mean', 0):.4f} (delta={delta:+.4f})  ({time.time()-t0:.0f}s)")
    out["no_fiat_ramp"] = {"metrics": m, "delta": delta}

    # 3. Disable nodes (ops_per_node huge so few nodes spawn, and remove sync cap effectively)
    print("Disable node modeling (huge ops_per_node)...")
    p = copy.deepcopy(base_params)
    p["nodes"]["ops_per_node_target"] = 1_000_000
    p["nodes"]["arms_per_node"] = 100_000  # essentially infinite capacity per node
    t0 = time.time()
    m = run_monte_carlo(p, n_runs=n_runs_per_config)
    delta = m.get("score_mean", 0) - baseline_score
    print(f"  Score: {m.get('score_mean', 0):.4f} (delta={delta:+.4f})  ({time.time()-t0:.0f}s)")
    out["no_node_constraint"] = {"metrics": m, "delta": delta}

    # 4. Disable hardware-stake gates (no stake required)
    print("Disable hardware-stake gates...")
    p = copy.deepcopy(base_params)
    p["hardware"]["stake_required_t3_usd"] = 0
    p["hardware"]["stake_required_t4_usd"] = 0
    p["hardware"]["stake_required_t6_usd"] = 0
    t0 = time.time()
    m = run_monte_carlo(p, n_runs=n_runs_per_config)
    delta = m.get("score_mean", 0) - baseline_score
    print(f"  Score: {m.get('score_mean', 0):.4f} (delta={delta:+.4f})  ({time.time()-t0:.0f}s)")
    out["no_hardware_stake"] = {"metrics": m, "delta": delta}

    # 5. Disable strike resets (permanent strikes)
    print("Disable strike resets (permanent strikes)...")
    p = copy.deepcopy(base_params)
    p["slashing"]["clean_hours_per_strike_reset"] = 1_000_000_000
    t0 = time.time()
    m = run_monte_carlo(p, n_runs=n_runs_per_config)
    delta = m.get("score_mean", 0) - baseline_score
    print(f"  Score: {m.get('score_mean', 0):.4f} (delta={delta:+.4f})  ({time.time()-t0:.0f}s)")
    out["no_strike_reset"] = {"metrics": m, "delta": delta}

    # 6. Disable burn loop
    print("Disable burn loop (0% burn)...")
    p = copy.deepcopy(base_params)
    p["burn"]["burn_pct_of_revenue"] = 0.0
    t0 = time.time()
    m = run_monte_carlo(p, n_runs=n_runs_per_config)
    delta = m.get("score_mean", 0) - baseline_score
    print(f"  Score: {m.get('score_mean', 0):.4f} (delta={delta:+.4f})  ({time.time()-t0:.0f}s)")
    out["no_burn"] = {"metrics": m, "delta": delta}

    return out


def stress_test_token_crash(base_params: Dict, n_runs: int = 5, sim_months: int = 36) -> Dict:
    """Token launches at $1, crashes 80% in month 6."""
    prepare.SIMULATION_MONTHS = sim_months
    p = copy.deepcopy(base_params)
    p["supply"]["initial_token_price"] = 1.0
    # We can't easily inject mid-sim crash without code changes; emulate via lower initial
    p["supply"]["initial_token_price"] = 0.20  # crashed launch
    return run_monte_carlo(p, n_runs=n_runs)


def stress_test_node_bottleneck(base_params: Dict, n_runs: int = 5, sim_months: int = 36) -> Dict:
    """Cap node spawn rate to 50% by halving ops_per_node target (more nodes needed but capacity smaller)."""
    prepare.SIMULATION_MONTHS = sim_months
    p = copy.deepcopy(base_params)
    p["nodes"]["arms_per_node"] = 2  # cut arms in half
    p["nodes"]["ops_per_node_target"] = 2_000  # spawn fewer nodes
    return run_monte_carlo(p, n_runs=n_runs)


def stress_test_demand_shock(base_params: Dict, multiplier: float, n_runs: int = 5, sim_months: int = 36) -> Dict:
    """Scale per-customer hours by multiplier (e.g., 0.5 = pessimistic, 1.5 = optimistic)."""
    prepare.SIMULATION_MONTHS = sim_months
    p = copy.deepcopy(base_params)
    base_per = p["demand"]["per_customer_hours_per_tier"]
    p["demand"]["per_customer_hours_per_tier"] = {t: int(h * multiplier) for t, h in base_per.items()}
    return run_monte_carlo(p, n_runs=n_runs)


def pareto_frontier(results: List[Dict], axes: List[str]) -> List[Dict]:
    """
    Identify Pareto-optimal results across the named score axes
    (each axis is a metric key, e.g. 'score_mean', 'revenue_score_mean').
    """
    def dominates(a: Dict, b: Dict) -> bool:
        a_vals = [a["metrics"].get(ax + "_mean", a["metrics"].get(ax, 0)) for ax in axes]
        b_vals = [b["metrics"].get(ax + "_mean", b["metrics"].get(ax, 0)) for ax in axes]
        any_better = any(av > bv for av, bv in zip(a_vals, b_vals))
        all_geq = all(av >= bv for av, bv in zip(a_vals, b_vals))
        return any_better and all_geq

    frontier = []
    for r in results:
        if not any(dominates(other, r) for other in results if other is not r):
            frontier.append(r)
    return frontier


def emit_csv_results(results: List[Dict], path: str) -> None:
    """Write sweep results to CSV. Each row = one config × Monte-Carlo aggregate."""
    if not results:
        return
    fieldnames = ["config_label"] + sorted(set().union(*[r["axis_values"].keys() for r in results]))
    metric_keys = sorted(set().union(*[r["metrics"].keys() for r in results]))
    fieldnames += metric_keys
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in results:
            row = {"config_label": r["config_label"]}
            row.update(r["axis_values"])
            row.update(r["metrics"])
            w.writerow(row)


def emit_csv_timeseries(history: List[Dict], path: str) -> None:
    """Write per-month time series for a single simulation."""
    if not history:
        return
    fieldnames = sorted(set().union(*[set(h.keys()) for h in history]))
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for h in history:
            row = {k: (json.dumps(v) if isinstance(v, dict) else v) for k, v in h.items()}
            w.writerow(row)


def emit_plots(history: List[Dict], output_dir: str, prefix: str = "v3") -> bool:
    """Generate matplotlib plots if available. Returns True if plots were created."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return False

    os.makedirs(output_dir, exist_ok=True)
    months = [h["month"] for h in history]

    fig, ax = plt.subplots(2, 2, figsize=(14, 10))

    ax[0][0].plot(months, [h["token_price"] for h in history], "b-")
    ax[0][0].set_title("Token Price (USD)")
    ax[0][0].set_xlabel("Month")
    ax[0][0].grid(True)

    ax[0][1].plot(months, [h["monthly_revenue"] for h in history], "g-")
    ax[0][1].set_title("Monthly Revenue (USD)")
    ax[0][1].set_xlabel("Month")
    ax[0][1].grid(True)

    ax[1][0].plot(months, [h["active_operators"] for h in history], "k-", label="Active")
    ax[1][0].plot(months, [h["operators_t4_plus"] for h in history], "r--", label="T4+")
    ax[1][0].set_title("Operator Population")
    ax[1][0].set_xlabel("Month")
    ax[1][0].legend()
    ax[1][0].grid(True)

    ax[1][1].plot(months, [h["fiat_paid_ratio"] for h in history], "m-", label="Fiat ratio")
    ax[1][1].plot(months, [h["false_positive_rate"] for h in history], "c--", label="False-positive rate")
    ax[1][1].plot(months, [h["slash_rate"] for h in history], "y:", label="Slash rate")
    ax[1][1].set_title("Validation & Earnings Mix")
    ax[1][1].set_xlabel("Month")
    ax[1][1].legend()
    ax[1][1].grid(True)

    plt.tight_layout()
    out = os.path.join(output_dir, f"{prefix}_overview.png")
    plt.savefig(out, dpi=100)
    plt.close()
    return True


def print_top_n(results: List[Dict], n: int = 10):
    print()
    print(f"Top {n} configs by composite score:")
    print(f"  {'Rank':<5} {'Score':<10} {'±Std':<8} {'Config'}")
    print("  " + "-" * 100)
    for i, r in enumerate(results[:n]):
        score = r["metrics"].get("score_mean", 0)
        std = r["metrics"].get("score_std", 0)
        print(f"  {i+1:<5} {score:<10.4f} {std:<8.3f} {r['config_label']}")
    print()


# ─── CLI ENTRY POINT ──────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("Usage: python experiments.py <command> [args]")
        print("Commands: ablation | small_sweep | full_sweep | stress | timeseries | plots")
        return

    cmd = sys.argv[1]
    from train import PARAMS

    if cmd == "ablation":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        out = ablation_test(PARAMS, n_runs_per_config=n)
        print()
        print("=== Ablation Summary ===")
        print(f"{'Mechanic':30s}  {'Score':>10s}  {'Δ':>10s}  {'Interpretation'}")
        print("-" * 90)
        baseline = out["baseline"]["metrics"].get("score_mean", 0)
        for name, data in out.items():
            s = data["metrics"].get("score_mean", 0)
            d = data["delta"]
            interp = "(reference)" if name == "baseline" else (
                "MECHANIC HELPS" if d < 0 else "MECHANIC HURTS" if d > 0 else "no effect"
            )
            print(f"{name:30s}  {s:>10.4f}  {d:>+10.4f}  {interp}")
        # Save
        with open("ablation_results.json", "w") as f:
            json.dump({k: {"metrics": v["metrics"], "delta": v["delta"]} for k, v in out.items()}, f, indent=2)
        print()
        print("Saved -> ablation_results.json")

    elif cmd == "small_sweep":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 2
        # Focused 3-axis grid based on ablation insights (hardware stakes too high in default):
        # 2x3x2 = 12 configs; at ~70s × n MC runs
        grid = {
            "task_model.base_emission_per_active_op_per_month": [25.0, 45.0],
            "hardware.stake_required_t4_usd": [50, 150, 400],
            "supply.monthly_emission_rate": [3_000_000, 8_000_000],
        }
        results = parameter_sweep(PARAMS, grid, n_runs_per_config=n)
        print_top_n(results, n=10)
        emit_csv_results(results, "sweep_small_results.csv")
        print("Saved -> sweep_small_results.csv")
        # Pareto on (composite, revenue, fairness)
        front = pareto_frontier(results, ["score_mean", "revenue_score_mean", "gini_score_mean"])
        print(f"Pareto frontier: {len(front)} configs")
        for r in front:
            print(f"  {r['config_label']}: score={r['metrics'].get('score_mean',0):.4f}")

    elif cmd == "full_sweep":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 3
        # 6-axis grid (3 levels each = 729 configs)
        grid = {
            "supply.initial_supply": [10_000_000, 25_000_000, 50_000_000],
            "supply.monthly_emission_rate": [2_000_000, 5_000_000, 10_000_000],
            "supply.halving_interval_months": [12, 18, 24],
            "burn.burn_pct_of_revenue": [0.30, 0.50, 0.70],
            "validation.validator_base_fee_pct": [0.05, 0.10, 0.15],
            "task_model.base_emission_per_active_op_per_month": [10.0, 20.0, 35.0],
        }
        results = parameter_sweep(PARAMS, grid, n_runs_per_config=n)
        print_top_n(results, n=20)
        emit_csv_results(results, "sweep_full_results.csv")
        print("Saved -> sweep_full_results.csv")

    elif cmd == "stress":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        print("Stress: token crash...")
        c = stress_test_token_crash(PARAMS, n_runs=n)
        print(f"  Token crash score: {c.get('score_mean', 0):.4f}")
        print("Stress: node bottleneck...")
        c = stress_test_node_bottleneck(PARAMS, n_runs=n)
        print(f"  Node bottleneck score: {c.get('score_mean', 0):.4f}")
        print("Stress: demand shock pessimistic (×0.5)...")
        c = stress_test_demand_shock(PARAMS, 0.5, n_runs=n)
        print(f"  Pessimistic demand score: {c.get('score_mean', 0):.4f}")
        print("Stress: demand shock optimistic (×2.0)...")
        c = stress_test_demand_shock(PARAMS, 2.0, n_runs=n)
        print(f"  Optimistic demand score: {c.get('score_mean', 0):.4f}")

    elif cmd == "timeseries":
        prepare.SIMULATION_MONTHS = 36
        history = run_simulation(PARAMS, seed=42)
        emit_csv_timeseries(history, "v3_timeseries.csv")
        print("Saved -> v3_timeseries.csv")
        if emit_plots(history, ".", "v3"):
            print("Saved -> v3_overview.png")
        else:
            print("matplotlib not available — skipping plots")

    elif cmd == "plots":
        prepare.SIMULATION_MONTHS = 36
        history = run_simulation(PARAMS, seed=42)
        ok = emit_plots(history, ".", "v3")
        print("Plotted!" if ok else "matplotlib not installed (pip install matplotlib)")

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
