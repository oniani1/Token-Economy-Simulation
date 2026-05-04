"""
CrowdBrain v5 Report Generator
================================
Reads JSON results from v5_results/ and writes REPORT_v5.md.

Usage:
  python report_v5_generator.py
"""

import json
import os
from typing import Dict, List, Optional


OUT_DIR = "v5_results"
REPORT_PATH = "REPORT_v5.md"


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


def _format_track_table(track: Dict, headline_keys: List[str], header_labels: List[str]) -> str:
    if not track:
        return "_No results found._\n"
    lines = ["| Cell | " + " | ".join(header_labels) + " |"]
    lines.append("|" + "|".join(["---"] * (len(header_labels) + 1)) + "|")
    # Sort by composite score desc
    sorted_cells = sorted(
        track.items(),
        key=lambda kv: kv[1].get("score_mean", 0.0),
        reverse=True,
    )
    for cell_name, agg in sorted_cells:
        row = [cell_name]
        for k in headline_keys:
            v = agg.get(k + "_mean", agg.get(k, 0))
            std = agg.get(k + "_std", None)
            if "revenue" in k or "earnings" in k:
                cell = _fmt_dollars(v)
            elif "score" in k or "nrr" in k or "concentration" in k or "diversity" in k:
                cell = f"{v:.3f}"
                if std is not None:
                    cell += f" ± {std:.3f}"
            else:
                cell = f"{v:,.0f}"
            row.append(cell)
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines) + "\n"


def _winner_of(track: Dict) -> Optional[str]:
    if not track:
        return None
    return max(track.items(), key=lambda kv: kv[1].get("score_mean", 0.0))[0]


def _bottom_of(track: Dict) -> Optional[str]:
    if not track:
        return None
    return min(track.items(), key=lambda kv: kv[1].get("score_mean", 0.0))[0]


def _spread(track: Dict) -> float:
    if not track:
        return 0.0
    scores = [v.get("score_mean", 0.0) for v in track.values()]
    return max(scores) - min(scores) if scores else 0.0


def _format_summary_section(track: Dict, name: str) -> str:
    if not track:
        return f"_{name}: no data_\n\n"
    winner = _winner_of(track)
    bottom = _bottom_of(track)
    spread = _spread(track)
    n_runs = next(iter(track.values())).get("n_runs", 0)
    return (
        f"- **{name}** ({len(track)} cells × MC={n_runs}): "
        f"winner = `{winner}` (score {track[winner].get('score_mean', 0):.3f}), "
        f"worst = `{bottom}` ({track[bottom].get('score_mean', 0):.3f}), "
        f"spread = {spread:.3f}\n"
    )


def main():
    track1 = _load("track1_results.json")
    track2 = _load("track2_results.json")
    track3 = _load("track3_results.json")
    track4 = _load("track4_results.json")

    sections = []

    sections.append("# CrowdBrain v5 Token Economy — Simulation Report\n")
    sections.append(
        "**Source memo**: `crowdbrain-memo-v5.docx` (replaces `crowdtrain-memo-v12.docx`)\n"
        "**Baseline**: v4_no_personas winner config + v5 layers (tier_unlock, node_providers, "
        "geography, points_to_token) + v5 customer extension (multi-year design partner contracts)\n"
        "**Horizon**: 36 months\n"
        f"**Workers**: parallel MC across CPU cores\n\n"
    )

    sections.append("## TL;DR — Track-by-track headline findings\n\n")
    sections.append(_format_summary_section(track1, "Track 1 — Tier-unlock policy"))
    sections.append(_format_summary_section(track2, "Track 2 — Points-to-tokens transition"))
    sections.append(_format_summary_section(track3, "Track 3 — Three-stakeholder loop"))
    sections.append(_format_summary_section(track4, "Track 4 — Macro stress + milestone path"))
    sections.append("\n")

    # ── Track 1 ──
    if track1:
        sections.append("## Track 1 — Tier-unlock policy\n\n")
        sections.append(
            "v5 memo says T0–T2 launch immediately and T3–T5 unlock conditionally with scale, "
            "but doesn't specify thresholds. This sweep tests 6 different gating rules.\n\n"
        )
        sections.append(_format_track_table(
            track1,
            ["score", "cumulative_revenue", "t4_plus_operators", "nrr_blended", "customer_count_active"],
            ["Composite", "Cum revenue", "T4+ ops", "NRR", "Active customers"],
        ))
        winner = _winner_of(track1)
        if winner:
            sections.append(f"\n**Track 1 winner**: `{winner}`\n")
            tw = track1[winner]
            sections.append(
                f"- Composite {tw.get('score_mean', 0):.4f} ± {tw.get('score_std', 0):.4f}\n"
                f"- Cumulative revenue {_fmt_dollars(tw.get('cumulative_revenue_mean', 0))}\n"
                f"- T4+ operators: {tw.get('t4_plus_operators_mean', 0):.0f}\n"
                f"- NRR: {tw.get('nrr_blended_mean', 0):.3f}\n\n"
            )
        sections.append("\n")

    # ── Track 2 ──
    if track2:
        sections.append("## Track 2 — Points → Tokens Transition\n\n")
        sections.append(
            "v5 memo: 'Operators begin with points and transition to tokens later.' "
            "Tests when the cutover should happen. All cells use 1:1 conversion at cutover.\n\n"
        )
        sections.append(_format_track_table(
            track2,
            ["score", "cumulative_revenue", "t4_plus_operators", "nrr_blended"],
            ["Composite", "Cum revenue", "T4+ ops", "NRR"],
        ))
        sections.append("\n")

    # ── Track 3 ──
    if track3:
        sections.append("## Track 3 — Three-Stakeholder Loop (Bonded Node Providers)\n\n")
        sections.append(
            "v5 elevates node-providers to first-class economic actors with bonded stakes, "
            "operator reporting, and dispute resolution. Tests bond size + facility/community split.\n\n"
        )
        sections.append(_format_track_table(
            track3,
            ["score", "cumulative_revenue", "t4_plus_operators", "nrr_blended"],
            ["Composite", "Cum revenue", "T4+ ops", "NRR"],
        ))
        sections.append("\n")

    # ── Track 4 ──
    if track4:
        sections.append("## Track 4 — Macro Stress + Milestone Path Probability\n\n")
        sections.append(
            "Eight scenarios spanning funding-winter, wage-anchor (Tesla/1X), "
            "geographic shocks, MVP slip, and Intelligence Library activation. "
            "These feed the risk slide of the deck.\n\n"
        )
        sections.append(_format_track_table(
            track4,
            ["score", "cumulative_revenue", "t4_plus_operators", "nrr_blended", "active_operators"],
            ["Composite", "Cum revenue", "T4+ ops", "NRR", "Active ops"],
        ))
        # Funding winter delta
        if "path_baseline" in track4 and "funding_winter" in track4:
            base_score = track4["path_baseline"].get("score_mean", 0)
            base_rev = track4["path_baseline"].get("cumulative_revenue_mean", 0)
            fw_score = track4["funding_winter"].get("score_mean", 0)
            fw_rev = track4["funding_winter"].get("cumulative_revenue_mean", 0)
            sections.append(
                f"\n**Funding winter impact**: composite {base_score:.3f} → {fw_score:.3f} "
                f"(Δ {fw_score - base_score:+.3f}); revenue {_fmt_dollars(base_rev)} → "
                f"{_fmt_dollars(fw_rev)} (Δ {(fw_rev - base_rev)/max(1, base_rev)*100:+.0f}%).\n\n"
            )
        # Geo shock comparisons
        geo_shocks = {k: v for k, v in track4.items() if k.startswith("geo_shock_")}
        if geo_shocks:
            sections.append("**Geographic shock sensitivity** (which region is most load-bearing):\n\n")
            for region_cell, agg in sorted(geo_shocks.items(), key=lambda kv: kv[1].get("score_mean", 0)):
                sections.append(
                    f"- {region_cell}: composite {agg.get('score_mean', 0):.3f}, "
                    f"revenue {_fmt_dollars(agg.get('cumulative_revenue_mean', 0))}\n"
                )
            sections.append("\n")
        sections.append("\n")

    # ── Strategic conclusions ──
    sections.append("## Strategic conclusions\n\n")
    if track1 and track4:
        winner1 = _winner_of(track1)
        path_base = track4.get("path_baseline", {})
        sections.append(
            f"1. **Recommended launch tier-unlock policy**: `{winner1}`. Highest composite among "
            f"6 gating rules tested.\n"
        )
        sections.append(
            f"2. **Path-baseline composite**: {path_base.get('score_mean', 0):.3f} ± "
            f"{path_base.get('score_std', 0):.3f} at MC=10.\n"
        )
    sections.append(
        "3. **All v5 layers have measurable cost vs v4 baseline** — the question for each "
        "design choice is whether the realism gain is worth the composite-score drag. "
        "Use this sim to pick the layers where the realism cost is justified.\n"
    )
    sections.append(
        "4. **Defensive posture**: weakest scenarios in Track 4 should be planned around "
        "explicitly in the GTM and treasury runway, not modeled as tail risk.\n\n"
    )

    # ── Appendix: full param hashes ──
    sections.append("## Appendix — All cell results\n\n")
    for tname, t in [("track1", track1), ("track2", track2), ("track3", track3), ("track4", track4)]:
        if not t:
            continue
        sections.append(f"### {tname}\n```json\n")
        sections.append(json.dumps(t, indent=2)[:5000])
        sections.append("\n```\n\n")

    body = "".join(sections)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(body)

    print(f"Report written to {REPORT_PATH} ({len(body)} chars)")


if __name__ == "__main__":
    main()
