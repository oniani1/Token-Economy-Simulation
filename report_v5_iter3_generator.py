"""
CrowdBrain v5 iter3 — Realistic-mode report generator
======================================================
Reads JSON results from v5_results/iter3_*.json and writes REPORT_v5_iter3.md
with realistic-mode findings, Q4 2026 milestone probability, and recommended
launch config.

Usage:
  python report_v5_iter3_generator.py
"""

import json
import os
from typing import Dict, List, Tuple, Optional


OUT_DIR = "v5_results"
REPORT_PATH = "REPORT_v5_iter3.md"

# Reference points
V4_NO_PERSONAS = {"score": 0.7575, "cumulative_revenue": 73_000_000}
V5_UNREALISTIC = {"score": 0.535, "cumulative_revenue": 26_300_000}


def _load(filename: str) -> Optional[Dict]:
    p = os.path.join(OUT_DIR, filename)
    if not os.path.exists(p):
        return None
    with open(p) as f:
        return json.load(f)


def _fmt_dollars(x: float) -> str:
    if x >= 1e9:
        return f"${x/1e9:.2f}B"
    if x >= 1e6:
        return f"${x/1e6:.1f}M"
    if x >= 1e3:
        return f"${x/1e3:.0f}K"
    return f"${x:,.0f}"


def _phase_table_realistic(phase: Dict, label: str) -> str:
    if not phase:
        return f"_{label}: no results found._\n\n"
    lines = [f"### {label}\n"]
    lines.append("| Cell | Composite | Final ARR | Cust @ m36 | T4+ ops | Q4 hit | ARR in band |")
    lines.append("|---|---|---|---|---|---|---|")
    sorted_cells = sorted(phase.items(), key=lambda kv: -kv[1].get("score_mean", 0))
    for cell, agg in sorted_cells:
        s_m = agg.get("score_mean", 0)
        s_s = agg.get("score_std", 0)
        arr = agg.get("realism_final_arr_usd_mean", 0)
        cust = agg.get("realism_final_customer_count_mean", 0)
        t4 = agg.get("t4_plus_operators_mean", 0)
        q4 = agg.get("realism_q4_2026_milestone_hit_pct_true", 0)
        arr_band = agg.get("realism_arr_in_band_pct_true", 0)
        lines.append(
            f"| `{cell}` | {s_m:.3f} ± {s_s:.3f} | {_fmt_dollars(arr)} | "
            f"{cust:.0f} | {t4:,.0f} | {q4*100:.0f}% | {arr_band*100:.0f}% |"
        )
    return "\n".join(lines) + "\n\n"


def main():
    p1 = _load("iter3_phase1_results.json")
    p2 = _load("iter3_phase2_results.json")
    p3 = _load("iter3_phase3_results.json")
    p4 = _load("iter3_phase4_results.json")
    milestone = _load("iter3_milestone_results.json")

    sections = []
    sections.append("# CrowdBrain v5 — Iteration 3 Report (REALISTIC parameter calibration)\n\n")
    sections.append(
        "**Goal:** find the optimal v5 config under REALISTIC, defensible-vs-real-world conditions. "
        "Prior iter1/iter2 used customer/revenue numbers (Scale-AI-fantasy: $73M cum @ 36mo) "
        "that don't match real-world Series-B robotics-data startups.\n\n"
        "**This iter recalibrates:**\n"
        "- Per-customer monthly contracts: $15-50K (was $60-150K)\n"
        "- Customer arrival λ_max: 1.0/seg/mo (was 3.0)\n"
        "- Operator onboarding: ×0.35 of v4 schedule (matches memo's 1K trained @ Q3 2026 target)\n"
        "- Token supply: 100M max, 500K/mo emission (was 500M / 3M)\n"
        "- Hardware stakes: $200/$100/$400 (was $400/$150/$800)\n\n"
        "**Reference points:**\n"
        f"- v4_no_personas (unrealistic, MC=3): composite **{V4_NO_PERSONAS['score']:.4f}**, "
        f"cum revenue **{_fmt_dollars(V4_NO_PERSONAS['cumulative_revenue'])}**\n"
        f"- v5 unrealistic baseline: composite **{V5_UNREALISTIC['score']:.4f}**, "
        f"cum revenue **{_fmt_dollars(V5_UNREALISTIC['cumulative_revenue'])}**\n"
        "- Memo Q4 2026 milestone (month 8): 3+ paying customers, $500K+ ARR\n\n"
    )

    sections.append("## Phase 1 — Realistic baseline + diagnostic\n\n")
    sections.append(
        "Tests the realistic-mode baseline + ablation (all v5 layers off) + winner combo "
        "(best iter2 winners applied on top of realistic params).\n\n"
    )
    sections.append(_phase_table_realistic(p1, "Phase 1 cells"))

    sections.append("## Phase 2 — Realistic unlock policy sweep\n\n")
    sections.append(
        "iter1 found that the central memo question (when do T3-T5 unlock?) has a 7% spread "
        "across policies. iter3 retests this under realistic revenue/customer scale.\n\n"
    )
    sections.append(_phase_table_realistic(p2, "Phase 2 cells"))

    sections.append("## Phase 3 — Emission + stake fine-tuning\n\n")
    sections.append(
        "Two independent sweeps: token emission rate (250K-1M/mo) and hardware stake "
        "($100-300 T3). Targets the supply-side balance for realistic revenue.\n\n"
    )
    sections.append(_phase_table_realistic(p3, "Phase 3 cells"))

    sections.append("## Phase 4 — 60-month long horizon\n\n")
    sections.append(
        "v4 found 60mo unlocks 5× revenue compounding. Test whether realistic v5 has the "
        "same property.\n\n"
    )
    sections.append(_phase_table_realistic(p4, "Phase 4 cells"))

    if milestone:
        sections.append("## Q4 2026 Milestone Probability (MC=50)\n\n")
        cell = next(iter(milestone.values())) if milestone else {}
        if cell:
            sections.append(
                f"**P(hit Q4 2026 milestone)** = {cell.get('realism_q4_2026_milestone_hit_pct_true', 0)*100:.0f}% "
                f"(over 50 MC seeds, realistic baseline)\n\n"
                f"**Mean Q4 2026 customers**: {cell.get('realism_q4_2026_customers_mean', 0):.1f}  "
                f"(target ≥3)\n"
                f"**Mean Q4 2026 ARR**: {_fmt_dollars(cell.get('realism_q4_2026_arr_usd_mean', 0))}  "
                f"(target ≥$500K)\n\n"
            )

    # Find best across all phases
    sections.append("## Best realistic configurations\n\n")
    all_cells = []
    for phase_name, phase in [("phase1", p1), ("phase2", p2), ("phase3", p3), ("phase4", p4)]:
        if not phase:
            continue
        for cell, agg in phase.items():
            all_cells.append((phase_name, cell, agg))

    if all_cells:
        # Best composite
        best_score = max(all_cells, key=lambda r: r[2].get("score_mean", 0))
        # Best Q4 milestone hit rate
        best_q4 = max(all_cells, key=lambda r: r[2].get("realism_q4_2026_milestone_hit_pct_true", 0))
        # Best ARR in realistic band
        best_band = max(all_cells, key=lambda r: r[2].get("realism_arr_in_band_pct_true", 0))

        sections.append(f"- **Highest composite**: `{best_score[1]}` ({best_score[0]}) — "
                        f"{best_score[2].get('score_mean', 0):.3f} ± {best_score[2].get('score_std', 0):.3f}\n")
        sections.append(f"- **Highest Q4 milestone hit rate**: `{best_q4[1]}` ({best_q4[0]}) — "
                        f"{best_q4[2].get('realism_q4_2026_milestone_hit_pct_true', 0)*100:.0f}% of MC runs\n")
        sections.append(f"- **Highest ARR-in-band**: `{best_band[1]}` ({best_band[0]}) — "
                        f"{best_band[2].get('realism_arr_in_band_pct_true', 0)*100:.0f}% of MC runs\n\n")

    sections.append("## Strategic conclusions\n\n")
    if all_cells:
        best_score = max(all_cells, key=lambda r: r[2].get("score_mean", 0))
        sections.append(f"1. **Recommended realistic launch config**: `{best_score[1]}` "
                        f"(composite {best_score[2].get('score_mean', 0):.3f}, "
                        f"final ARR {_fmt_dollars(best_score[2].get('realism_final_arr_usd_mean', 0))})\n")
    sections.append(
        "2. **Numbers in this report are defensible vs real-world Series-B robotics-data startups** "
        "(Scale AI was ~$10M ARR at year 3 with thousands of customers; CrowdBrain wedge is narrower).\n"
    )
    sections.append(
        "3. **iter1/iter2 results showed structural cost of v5 layers** under unrealistic numbers; "
        "iter3 confirms whether the same trade-offs apply at realistic scale.\n\n"
    )

    sections.append("## Appendix — All cell results\n\n")
    for phase_name, phase in [("phase1", p1), ("phase2", p2), ("phase3", p3), ("phase4", p4), ("milestone", milestone)]:
        if not phase:
            continue
        sections.append(f"### {phase_name}\n```json\n")
        sections.append(json.dumps(phase, indent=2)[:5000])
        sections.append("\n```\n\n")

    body = "".join(sections)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(body)
    print(f"Report written to {REPORT_PATH} ({len(body)} chars)")


if __name__ == "__main__":
    main()
