"""
Customer cohort survival analysis.

Reads v4_best_customers_final.csv and v4_baseline_customers_final.csv,
groups customers by signing month into 6mo cohorts (m0-5, m6-11, ...),
and computes:
  - Cohort survival rate at end (% still active at m36)
  - Average expansion count per cohort
  - Revenue per cohort (cumulative)
  - Avg satisfaction per cohort

Generates customer_cohort_analysis.png + writes summary table to stdout.
"""

import csv
import sys
from collections import defaultdict
from typing import Dict, List


def read_customer_csv(path: str) -> List[Dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append({
                "id": int(row["id"]),
                "segment": row["segment"],
                "signed_month": int(row["signed_month"]),
                "contract_size_usd": float(row["contract_size_usd"]),
                "demand_multiplier": float(row["demand_multiplier"]),
                "status": row["status"],
                "churn_month": int(row["churn_month"]) if row["churn_month"] else None,
                "expansion_count": int(row["expansion_count"]),
                "cumulative_revenue": float(row["cumulative_revenue"]),
                "months_active": int(row["months_active"]),
                "last_satisfaction": float(row["last_satisfaction"]),
            })
    return rows


def cohort_summary(customers: List[Dict], cohort_size: int = 6) -> List[Dict]:
    cohorts: Dict[int, List[Dict]] = defaultdict(list)
    for c in customers:
        cohort_idx = c["signed_month"] // cohort_size
        cohorts[cohort_idx].append(c)

    summary = []
    for ci in sorted(cohorts.keys()):
        cs = cohorts[ci]
        total = len(cs)
        active = sum(1 for c in cs if c["status"] == "active")
        survival = active / total if total else 0
        expansions = sum(c["expansion_count"] for c in cs)
        avg_expansions = expansions / total if total else 0
        total_rev = sum(c["cumulative_revenue"] for c in cs)
        avg_sat = sum(c["last_satisfaction"] for c in cs if c["last_satisfaction"] > 0) / max(1, sum(1 for c in cs if c["last_satisfaction"] > 0))
        starting_mrr = sum(c["contract_size_usd"] for c in cs)
        current_mrr = sum(c["contract_size_usd"] * c["demand_multiplier"] for c in cs if c["status"] == "active")
        nrr = current_mrr / starting_mrr if starting_mrr else 0

        summary.append({
            "cohort": f"m{ci*cohort_size}-{(ci+1)*cohort_size-1}",
            "signed_month_start": ci * cohort_size,
            "size": total,
            "active": active,
            "survival_pct": survival * 100,
            "avg_expansions": avg_expansions,
            "total_revenue": total_rev,
            "starting_mrr": starting_mrr,
            "current_mrr": current_mrr,
            "nrr": nrr,
            "avg_last_sat": avg_sat,
        })
    return summary


def emit_cohort_plot(best_summary: List[Dict], baseline_summary: List[Dict],
                     output_path: str = "customer_cohort_analysis.png") -> bool:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return False

    fig, ax = plt.subplots(2, 2, figsize=(14, 10))

    # Panel 1: Survival % by cohort
    cohorts = [s["cohort"] for s in best_summary]
    best_surv = [s["survival_pct"] for s in best_summary]
    base_surv = [s["survival_pct"] for s in baseline_summary[:len(best_summary)]] if baseline_summary else []

    x = range(len(cohorts))
    w = 0.35
    ax[0][0].bar([i - w/2 for i in x], best_surv, w, label="v4_no_personas (best)", color="green", alpha=0.7)
    if base_surv:
        ax[0][0].bar([i + w/2 for i in x], base_surv, w, label="v4_baseline (all 3 pillars)", color="lightcoral", alpha=0.7)
    ax[0][0].set_title("Customer Survival % by Signing Cohort", fontweight="bold")
    ax[0][0].set_xlabel("Signing month cohort")
    ax[0][0].set_ylabel("Active at m36 (%)")
    ax[0][0].set_xticks(list(x))
    ax[0][0].set_xticklabels(cohorts, rotation=30)
    ax[0][0].legend()
    ax[0][0].grid(True, alpha=0.3)

    # Panel 2: NRR by cohort
    best_nrr = [s["nrr"] for s in best_summary]
    base_nrr = [s["nrr"] for s in baseline_summary[:len(best_summary)]] if baseline_summary else []
    ax[0][1].bar([i - w/2 for i in x], best_nrr, w, label="v4_no_personas (best)", color="green", alpha=0.7)
    if base_nrr:
        ax[0][1].bar([i + w/2 for i in x], base_nrr, w, label="v4_baseline", color="lightcoral", alpha=0.7)
    ax[0][1].axhline(1.0, color="gray", linestyle="--", alpha=0.5, label="NRR=1.0 target")
    ax[0][1].set_title("Net Revenue Retention by Cohort", fontweight="bold")
    ax[0][1].set_xlabel("Signing month cohort")
    ax[0][1].set_ylabel("NRR (current MRR / starting MRR)")
    ax[0][1].set_xticks(list(x))
    ax[0][1].set_xticklabels(cohorts, rotation=30)
    ax[0][1].legend()
    ax[0][1].grid(True, alpha=0.3)

    # Panel 3: Cohort size + cumulative revenue
    sizes = [s["size"] for s in best_summary]
    revs = [s["total_revenue"] / 1e6 for s in best_summary]
    ax[1][0].bar(x, sizes, color="steelblue", alpha=0.7, label="Customers in cohort")
    ax[1][0].set_title("Cohort Size & Revenue (best config)", fontweight="bold")
    ax[1][0].set_xlabel("Signing month cohort")
    ax[1][0].set_ylabel("Customer count", color="steelblue")
    ax[1][0].set_xticks(list(x))
    ax[1][0].set_xticklabels(cohorts, rotation=30)
    ax[1][0].legend(loc="upper left")
    ax[1][0].grid(True, alpha=0.3)
    ax2 = ax[1][0].twinx()
    ax2.plot(x, revs, "darkred", marker="o", label="Cum Revenue ($M)")
    ax2.set_ylabel("Cumulative Revenue ($M)", color="darkred")

    # Panel 4: Avg expansions by cohort
    best_exp = [s["avg_expansions"] for s in best_summary]
    ax[1][1].bar(x, best_exp, color="orange", alpha=0.7)
    ax[1][1].set_title("Avg Expansions per Customer (best config)", fontweight="bold")
    ax[1][1].set_xlabel("Signing month cohort")
    ax[1][1].set_ylabel("Avg expansion events")
    ax[1][1].set_xticks(list(x))
    ax[1][1].set_xticklabels(cohorts, rotation=30)
    ax[1][1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=100)
    plt.close()
    return True


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Usage: python customer_cohort_analysis.py")
        print("Reads v4_best_customers_final.csv and v4_baseline_customers_final.csv")
        print("Writes customer_cohort_analysis.png + prints summary table")
        return

    print("Loading customer data...")
    best = read_customer_csv("v4_best_customers_final.csv")
    baseline = read_customer_csv("v4_baseline_customers_final.csv")

    print(f"\nv4_no_personas (best): {len(best)} customers ({sum(1 for c in best if c['status']=='active')} active at m36)")
    print(f"v4_baseline (all 3):   {len(baseline)} customers ({sum(1 for c in baseline if c['status']=='active')} active at m36)")
    print()

    best_summary = cohort_summary(best, cohort_size=6)
    base_summary = cohort_summary(baseline, cohort_size=6)

    print("=== v4_no_personas (best) — cohort summary ===")
    print(f"{'Cohort':10s} {'Size':>5s} {'Active':>6s} {'Survival':>10s} {'Avg Exp':>8s} {'NRR':>6s} {'Last Sat':>9s} {'Cum Rev':>11s}")
    print("-" * 78)
    for s in best_summary:
        print(f"{s['cohort']:10s} {s['size']:>5d} {s['active']:>6d} {s['survival_pct']:>9.1f}% {s['avg_expansions']:>8.2f} {s['nrr']:>6.2f} {s['avg_last_sat']:>9.3f} ${s['total_revenue']:>10,.0f}")

    print()
    print("=== v4_baseline (all 3 pillars) — cohort summary ===")
    print(f"{'Cohort':10s} {'Size':>5s} {'Active':>6s} {'Survival':>10s} {'Avg Exp':>8s} {'NRR':>6s} {'Last Sat':>9s} {'Cum Rev':>11s}")
    print("-" * 78)
    for s in base_summary:
        print(f"{s['cohort']:10s} {s['size']:>5d} {s['active']:>6d} {s['survival_pct']:>9.1f}% {s['avg_expansions']:>8.2f} {s['nrr']:>6.2f} {s['avg_last_sat']:>9.3f} ${s['total_revenue']:>10,.0f}")

    print()
    plotted = emit_cohort_plot(best_summary, base_summary)
    if plotted:
        print("Saved -> customer_cohort_analysis.png")
    else:
        print("matplotlib not available; skipped plot")


if __name__ == "__main__":
    main()
