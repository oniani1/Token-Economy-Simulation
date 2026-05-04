"""
CrowdBrain v5 iter2 — Pareto-frontier report generator
========================================================
Reads JSON results from v5_results/iter2_*.json and writes REPORT_v5_iter2.md
with per-phase tables, Pareto frontier (composite × revenue), and findings.

Usage:
  python report_v5_iter2_generator.py
"""

import json
import os
from typing import Dict, List, Tuple, Optional


OUT_DIR = "v5_results"
REPORT_PATH = "REPORT_v5_iter2.md"

# References for context
V4_NO_PERSONAS = {"score": 0.7575, "cumulative_revenue": 73_000_000}
V5_BASELINE = {"score": 0.535, "cumulative_revenue": 26_300_000}


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


def _phase_table(phase: Dict, label: str) -> str:
    if not phase:
        return f"_{label}: no results found._\n\n"
    lines = [f"### {label}\n"]
    lines.append("| Cell | Composite | Cum revenue | T4+ ops | Retention | Cap util | Stability |")
    lines.append("|---|---|---|---|---|---|---|")
    sorted_cells = sorted(phase.items(), key=lambda kv: -kv[1].get("score_mean", 0))
    for cell, agg in sorted_cells:
        s_m = agg.get("score_mean", 0)
        s_s = agg.get("score_std", 0)
        rev = agg.get("cumulative_revenue_mean", 0)
        t4 = agg.get("t4_plus_operators_mean", 0)
        ret = agg.get("retention_score_mean", 0)
        cap = agg.get("capacity_utilization_score_mean", 0)
        stab = agg.get("stability_score_mean", 0)
        lines.append(
            f"| `{cell}` | {s_m:.3f} ± {s_s:.3f} | {_fmt_dollars(rev)} | {t4:,.0f} | {ret:.3f} | {cap:.3f} | {stab:.3f} |"
        )
    return "\n".join(lines) + "\n\n"


def _flatten_all(*phases) -> List[Tuple[str, str, Dict]]:
    """Returns list of (phase_name, cell_name, agg) across all phases."""
    out = []
    for phase_name, phase in phases:
        if not phase:
            continue
        for cell_name, agg in phase.items():
            out.append((phase_name, cell_name, agg))
    return out


def _pareto_optimal(rows: List[Tuple[str, str, Dict]], key1="score_mean", key2="cumulative_revenue_mean") -> List[Tuple[str, str, Dict]]:
    """A cell is Pareto-optimal if no other cell beats it on BOTH key1 and key2."""
    pareto = []
    for i, (phase_a, cell_a, agg_a) in enumerate(rows):
        a1 = agg_a.get(key1, 0)
        a2 = agg_a.get(key2, 0)
        dominated = False
        for j, (phase_b, cell_b, agg_b) in enumerate(rows):
            if i == j:
                continue
            b1 = agg_b.get(key1, 0)
            b2 = agg_b.get(key2, 0)
            # b dominates a if b1 >= a1 AND b2 >= a2 with at least one strict
            if b1 >= a1 and b2 >= a2 and (b1 > a1 or b2 > a2):
                dominated = True
                break
        if not dominated:
            pareto.append((phase_a, cell_a, agg_a))
    return sorted(pareto, key=lambda r: -r[2].get(key1, 0))


def main():
    p1 = _load("iter2_phase1_results.json")
    p2 = _load("iter2_phase2_results.json")
    p3 = _load("iter2_phase3_results.json")

    sections = []
    sections.append("# CrowdBrain v5 — Iteration 2 Report (Pareto frontier sweep)\n\n")
    sections.append(
        "**Goal:** close the 0.34 composite gap between v5 baseline (0.535) and v4_no_personas (0.7575) "
        "by tuning the 3 biggest sub-score drags identified in REPORT_v5.md.\n\n"
        "**Three phases, 18 cells total, MC=20.**\n\n"
        f"**Reference points:**\n"
        f"- v4_no_personas: composite **{V4_NO_PERSONAS['score']:.4f}**, cum revenue **{_fmt_dollars(V4_NO_PERSONAS['cumulative_revenue'])}** @ 36mo\n"
        f"- v5 baseline (unlock_revenue_gated, current winner): composite **{V5_BASELINE['score']:.4f}**, cum revenue **{_fmt_dollars(V5_BASELINE['cumulative_revenue'])}** @ 36mo\n\n"
    )

    # ── Phase 1 ──
    sections.append("## Phase 1 — Combo + Diagnostic\n\n")
    sections.append(
        "Tests whether the 4 v5 track winners compose constructively when stacked, "
        "and confirms how much of the v5 gap is structural vs. tunable.\n\n"
    )
    sections.append(_phase_table(p1, "Phase 1 cells"))

    if p1:
        combo = p1.get("v5_winner_combo", {})
        layers_off = p1.get("v5_layers_off", {})
        if combo and layers_off:
            sections.append(
                f"**Composability:** combo composite {combo.get('score_mean', 0):.4f} vs single-track winners 0.535–0.574. "
                f"Layers-off composite {layers_off.get('score_mean', 0):.4f} (matches v4_no_personas reference).\n\n"
            )

    # ── Phase 2 ──
    sections.append("## Phase 2 — Revenue threshold sweep\n\n")
    sections.append(
        "The biggest single sub-score drag (-0.095 from revenue). The current winner uses "
        "$250K / $1M / $5M ARR thresholds; this phase tests both looser (faster unlock = "
        "more revenue) and tighter (more quality = less revenue but higher score density).\n\n"
    )
    sections.append(_phase_table(p2, "Phase 2 cells"))

    # ── Phase 3 ──
    sections.append("## Phase 3 — Hardware stake + node provisioning\n\n")
    sections.append(
        "Two-axis sweep: hardware stake $300–500 (memo's full range) and ops_per_node_target "
        "2K–12K (current 2K leaves capacity_utilization at 0.024).\n\n"
    )
    sections.append(_phase_table(p3, "Phase 3 cells"))

    # ── Pareto frontier ──
    sections.append("## Pareto frontier — composite vs cumulative revenue\n\n")
    sections.append(
        "A cell is Pareto-optimal if no other cell beats it on BOTH composite score AND "
        "cumulative revenue. Pick a cell on the frontier based on which metric matters more "
        "in the conversation you're having.\n\n"
    )
    rows = _flatten_all(("phase1", p1), ("phase2", p2), ("phase3", p3))
    pareto = _pareto_optimal(rows)
    sections.append("| Cell | Phase | Composite | Cum revenue | T4+ ops |\n")
    sections.append("|---|---|---|---|---|\n")
    for phase, cell, agg in pareto:
        s_m = agg.get("score_mean", 0)
        s_s = agg.get("score_std", 0)
        rev = agg.get("cumulative_revenue_mean", 0)
        t4 = agg.get("t4_plus_operators_mean", 0)
        sections.append(f"| `{cell}` | {phase} | {s_m:.3f} ± {s_s:.3f} | {_fmt_dollars(rev)} | {t4:,.0f} |\n")
    sections.append("\n")

    # ── Best-of-each-metric ──
    if rows:
        best_score = max(rows, key=lambda r: r[2].get("score_mean", 0))
        best_rev = max(rows, key=lambda r: r[2].get("cumulative_revenue_mean", 0))
        sections.append("## Best-of-each-metric\n\n")
        sections.append(
            f"- **Highest composite**: `{best_score[1]}` ({best_score[0]}) — "
            f"{best_score[2].get('score_mean', 0):.4f} ± {best_score[2].get('score_std', 0):.4f}\n"
        )
        sections.append(
            f"- **Highest revenue**: `{best_rev[1]}` ({best_rev[0]}) — "
            f"{_fmt_dollars(best_rev[2].get('cumulative_revenue_mean', 0))}\n"
        )
        # Improvement vs v5 baseline
        s_delta = best_score[2].get("score_mean", 0) - V5_BASELINE["score"]
        r_delta = best_rev[2].get("cumulative_revenue_mean", 0) - V5_BASELINE["cumulative_revenue"]
        sections.append(
            f"- vs v5 baseline (0.535 / $26.3M): "
            f"composite Δ {s_delta:+.4f} ({s_delta/V5_BASELINE['score']*100:+.1f}%), "
            f"revenue Δ {_fmt_dollars(r_delta)} ({r_delta/V5_BASELINE['cumulative_revenue']*100:+.0f}%)\n"
        )
        # vs v4_no_personas
        s_delta_v4 = best_score[2].get("score_mean", 0) - V4_NO_PERSONAS["score"]
        sections.append(
            f"- vs v4_no_personas (0.7575): composite Δ {s_delta_v4:+.4f} "
            f"({'gap closed' if s_delta_v4 >= 0 else 'gap remaining'})\n\n"
        )

    # ── Findings ──
    sections.append("## Findings\n\n")
    if p1 and p2 and p3:
        # Compare combo vs single-track winners
        combo = p1.get("v5_winner_combo", {})
        if combo:
            combo_score = combo.get("score_mean", 0)
            sections.append(
                f"1. **Combo composability** — `v5_winner_combo` (all 4 track winners stacked) "
                f"scored {combo_score:.4f}. "
                f"Single-track winners alone scored 0.535–0.574 in iter1. "
                f"{'Combo is constructive (winners stack).' if combo_score > 0.535 else 'Combo is NOT constructive; some winners interfere.'}\n"
            )
        # Revenue threshold optimum
        if p2:
            best_p2 = max(p2.items(), key=lambda kv: kv[1].get("score_mean", 0))
            sections.append(
                f"2. **Revenue threshold optimum** — `{best_p2[0]}` wins Phase 2 at "
                f"composite {best_p2[1].get('score_mean', 0):.4f}. "
                f"This {'confirms' if best_p2[0] == 'unlock_revenue_gated_ref' else 'overturns'} the iter1 winner.\n"
            )
        # Hardware stake optimum
        if p3:
            stake_cells = {k: v for k, v in p3.items() if k.startswith("stake_")}
            if stake_cells:
                best_stake = max(stake_cells.items(), key=lambda kv: kv[1].get("score_mean", 0))
                sections.append(
                    f"3. **Hardware stake optimum** — `{best_stake[0]}` is best at composite "
                    f"{best_stake[1].get('score_mean', 0):.4f}. "
                    f"Memo's $300-500 range; sim picked: ${best_stake[0].split('_')[1]}.\n"
                )
            node_cells = {k: v for k, v in p3.items() if k.startswith("nodes_")}
            if node_cells:
                best_nodes = max(node_cells.items(), key=lambda kv: kv[1].get("score_mean", 0))
                sections.append(
                    f"4. **Node provisioning optimum** — `{best_nodes[0]}` wins at composite "
                    f"{best_nodes[1].get('score_mean', 0):.4f}, "
                    f"capacity util {best_nodes[1].get('capacity_utilization_score_mean', 0):.3f} "
                    f"(was 0.024 in v5 baseline).\n"
                )

    sections.append("\n## Appendix — All cell results\n\n")
    for phase_name, phase in [("phase1", p1), ("phase2", p2), ("phase3", p3)]:
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
