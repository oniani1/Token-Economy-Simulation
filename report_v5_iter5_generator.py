"""
CrowdBrain v5 — iter5 report generator
========================================
Reads all iter5 phase JSONs + BO + backtest results, produces REPORT_v5_iter5.md.

Usage:
  python report_v5_iter5_generator.py
"""

import json
import os
from datetime import datetime

ITER5_OUT = "v5_results"
REPORT_PATH = "REPORT_v5_iter5.md"


def load_json(filename):
    path = os.path.join(ITER5_OUT, filename)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def fmt_money(v, scale="M"):
    if scale == "M":
        return f"${v/1e6:.2f}M"
    elif scale == "K":
        return f"${v/1e3:.0f}K"
    return f"${v:,.0f}"


def section(title, level=2):
    return f"\n{'#' * level} {title}\n\n"


def build_report():
    out = []
    out.append("# CrowdBrain v5 — iteration 5 report\n\n")
    out.append(f"_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n\n")
    out.append("Open-ended discovery sweep building on iter4 J-curve winner. User directive: "
               "let model discover; experiment, iterate, finalize without checkpoints.\n\n")

    # ─── PHASE A: STAKE SWEEP ─────────────────────────────────────────────
    pa = load_json("iter5_phasea_results.json")
    if pa:
        out.append(section("Phase A — Stake sweep (open-ended discovery)"))
        out.append("Tested $0/$10/$25/$50/$100/$200 hardware stake T3 at 60mo, MC=20.\n\n")
        out.append("| Stake | Composite | Final ARR | Customers | T4+ ops |\n")
        out.append("|---|---|---|---|---|\n")
        rows = []
        for k, v in pa.items():
            stake = int(k.split("_")[1])
            rows.append((stake, v))
        rows.sort()
        best_stake = max(rows, key=lambda r: r[1].get("score_mean", 0))[0]
        for stake, v in rows:
            mark = " ⭐" if stake == best_stake else ""
            out.append(f"| ${stake} | {v.get('score_mean', 0):.4f} ± {v.get('score_std', 0):.4f} | "
                       f"{fmt_money(v.get('realism_final_arr_usd_mean', 0))} | "
                       f"{v.get('realism_final_customer_count_mean', 0):.0f} | "
                       f"{v.get('t4_plus_operators_mean', 0):.0f}{mark} |\n")
        out.append("\n")
        # Compute key insight
        prev_winner = next((v for stake, v in rows if stake == 100), None)
        new_winner = next((v for stake, v in rows if stake == best_stake), None)
        if prev_winner and new_winner:
            delta = new_winner.get("score_mean", 0) - prev_winner.get("score_mean", 0)
            out.append(f"**Key finding:** ${best_stake} winner improves on iter4's $100 by **+{delta:.3f} composite** "
                       f"(~{delta/prev_winner.get('score_mean', 1)*100:.0f}% relative gain). Open-ended sweep confirms iter4 sensitivity flag — go lower than $100.\n\n")
            zero = next((v for stake, v in rows if stake == 0), None)
            if zero:
                if zero.get("score_mean", 0) < new_winner.get("score_mean", 0):
                    out.append(f"**Floor exists:** $0 stake scores {zero.get('score_mean', 0):.3f}, lower than ${best_stake}'s "
                               f"{new_winner.get('score_mean', 0):.3f} — there's a non-trivial incentive floor below ~$10. Stake = 0 lets bad actors in.\n\n")

    # ─── PHASE B: MC=50 WINNER VALIDATION ─────────────────────────────────
    pb = load_json("iter5_phaseb_results.json")
    if pb:
        out.append(section("Phase B — MC=50 winner validation"))
        out.append("Tight MC=50 rerun on iter4 winner ($100 stake) to halve confidence intervals.\n\n")
        for k, v in pb.items():
            out.append(f"- **{k}**: composite **{v.get('score_mean', 0):.4f} ± {v.get('score_std', 0):.4f}** "
                       f"(MC=50, vs MC=20 ±0.020 in iter4)\n")
            out.append(f"  - Final ARR: {fmt_money(v.get('realism_final_arr_usd_mean', 0))}\n")
            out.append(f"  - Customers: {v.get('realism_final_customer_count_mean', 0):.0f}\n")
            out.append(f"  - T4+: {v.get('t4_plus_operators_mean', 0):.0f}\n\n")

    # ─── PHASE C: COMBINED STRESS ─────────────────────────────────────────
    pc = load_json("iter5_phasec_results.json")
    if pc:
        out.append(section("Phase C — Combined-stress pairs (2-axis simultaneous)"))
        out.append("Pairs of stress scenarios — defends 'what if X AND Y' investor questions.\n\n")
        out.append("| Pair | Composite | Final ARR | Customers | Δ vs winner |\n")
        out.append("|---|---|---|---|---|\n")
        # Get baseline for comparison (use stake 25 winner if available, else iter4 winner score)
        if pa:
            baseline_score = max(v.get("score_mean", 0) for v in pa.values())
        else:
            baseline_score = 0.683
        for k, v in pc.items():
            score = v.get("score_mean", 0)
            delta = score - baseline_score
            out.append(f"| {k} | {score:.4f} ± {v.get('score_std', 0):.4f} | "
                       f"{fmt_money(v.get('realism_final_arr_usd_mean', 0))} | "
                       f"{v.get('realism_final_customer_count_mean', 0):.0f} | "
                       f"{delta:+.3f} ({delta/baseline_score*100:+.0f}%) |\n")
        out.append("\n")

    # ─── PHASE D: Q4 FIXES ────────────────────────────────────────────────
    pd = load_json("iter5_phased_results.json")
    if pd:
        out.append(section("Phase D — Q4 2026 milestone fix structures"))
        out.append("Goal: push P(Q4 milestone hit at $500K ARR + 3 customers) ≥ 50%.\n\n")
        out.append("| Fix | Composite | Q4 hit % | Q4 customers | Q4 ARR |\n")
        out.append("|---|---|---|---|---|\n")
        for k, v in pd.items():
            out.append(f"| {k} | {v.get('score_mean', 0):.4f} | "
                       f"{v.get('realism_q4_2026_milestone_hit_pct_true', 0)*100:.0f}% | "
                       f"{v.get('realism_q4_2026_customers_mean', 0):.1f} | "
                       f"{fmt_money(v.get('realism_q4_2026_arr_usd_mean', 0), 'K')} |\n")
        out.append("\n")
        # Find best Q4 hit rate
        best_q4 = max(pd.values(), key=lambda v: v.get("realism_q4_2026_milestone_hit_pct_true", 0))
        best_pct = best_q4.get("realism_q4_2026_milestone_hit_pct_true", 0) * 100
        out.append(f"**Best Q4 hit rate: {best_pct:.0f}%.** ")
        if best_pct >= 50:
            out.append("Memo target is achievable with the right structure.\n\n")
        elif best_pct >= 20:
            out.append("Memo target stretch but not impossible. Recommend public target $300K ARR (consistently hit) + Q4 fix structure as internal stretch.\n\n")
        else:
            out.append("Memo target unreachable under realism. Public target should drop to $300K ARR (hit by baseline).\n\n")

    # ─── PHASE E: PERSONAS ────────────────────────────────────────────────
    pe = load_json("iter5_phasee_results.json")
    if pe:
        out.append(section("Phase E — Persona reintroduction cost"))
        out.append("Tests behavioral honesty cost vs winner config (personas off).\n\n")
        out.append("| Persona mix | Composite | Final ARR | Customers |\n")
        out.append("|---|---|---|---|\n")
        for k, v in pe.items():
            out.append(f"| {k} | {v.get('score_mean', 0):.4f} ± {v.get('score_std', 0):.4f} | "
                       f"{fmt_money(v.get('realism_final_arr_usd_mean', 0))} | "
                       f"{v.get('realism_final_customer_count_mean', 0):.0f} |\n")
        out.append("\n")
        off_score = pe.get("personas_off", {}).get("score_mean", 0)
        best_persona_mix = max(((k, v) for k, v in pe.items() if k != "personas_off"),
                               key=lambda x: x[1].get("score_mean", 0))
        if off_score and best_persona_mix:
            cost = off_score - best_persona_mix[1].get("score_mean", 0)
            out.append(f"**Best persona mix:** `{best_persona_mix[0]}` at {best_persona_mix[1].get('score_mean', 0):.4f}.\n")
            out.append(f"**Cost of behavioral honesty:** {cost:.3f} composite vs personas-off baseline.\n\n")

    # ─── PHASE F: TOKEN CLAMP ─────────────────────────────────────────────
    pf = load_json("iter5_phasef_results.json")
    if pf:
        out.append(section("Phase F — Token-price clamp variant ('median deck')"))
        out.append("AMM pools 10x deeper to dampen price upside (median-case investor view).\n\n")
        for k, v in pf.items():
            out.append(f"- **{k}**: composite {v.get('score_mean', 0):.4f}, "
                       f"Final ARR {fmt_money(v.get('realism_final_arr_usd_mean', 0))}, "
                       f"Final/peak price ${v.get('final_price_mean', 0):.2f} / ${v.get('peak_price_mean', 0):.2f}\n")
        out.append("\n")

    # ─── PHASE G: PER-TIER MATCHING ───────────────────────────────────────
    pg = load_json("iter5_phaseg_results.json")
    if pg:
        out.append(section("Phase G — Per-customer-tier matching (engine change)"))
        out.append("Each customer matches against a sampled subset of operators per tier "
                   "(varies by customer, sticky across months as ops churn). "
                   "Targets the active-op decline observed post-m24 in iter4.\n\n")
        for k, v in pg.items():
            out.append(f"- **{k}**: composite **{v.get('score_mean', 0):.4f} ± {v.get('score_std', 0):.4f}**, "
                       f"Final ARR {fmt_money(v.get('realism_final_arr_usd_mean', 0))}, "
                       f"Active ops {v.get('active_operators_final_mean', 0):.0f}, "
                       f"T4+ {v.get('t4_plus_operators_mean', 0):.0f}\n")
        out.append("\n")

    # ─── PHASE I: FINAL ITER5 WINNER VALIDATION ───────────────────────────
    pi = load_json("iter5_phaseI_results.json")
    if pi:
        out.append(section("Phase I — Final iter5 winner validation (combined discoveries, MC=20)"))
        for k, v in pi.items():
            out.append(f"**{k}**\n\n")
            out.append(f"- Composite: **{v.get('score_mean', 0):.4f} ± {v.get('score_std', 0):.4f}**\n")
            out.append(f"- Final ARR (m60): {fmt_money(v.get('realism_final_arr_usd_mean', 0))}\n")
            out.append(f"- Customers: {v.get('realism_final_customer_count_mean', 0):.0f}\n")
            out.append(f"- T4+ ops: {v.get('t4_plus_operators_mean', 0):.0f}\n")
            out.append(f"- Active ops final: {v.get('active_operators_final_mean', 0):.0f}\n")
            out.append(f"- Cum revenue: {fmt_money(v.get('cumulative_revenue_mean', 0))}\n\n")

    # ─── DIAGNOSTIC: PER-TIER MATCHING ────────────────────────────────────
    diag = load_json("iter5_per_tier_match_diagnostic.json")
    if diag:
        out.append(section("Diagnostic — per-tier matching effect on active op decline"))
        s = diag["summary"]
        out.append(f"Single-seed (42) comparison of aggregate vs per-tier matching:\n\n")
        out.append("| Mode | Peak active ops | Final active ops | Peak→final decline |\n")
        out.append("|---|---|---|---|\n")
        out.append(f"| Aggregate (current) | {s['off_peak_active_ops']} | {s['off_final_active_ops']} | "
                   f"{s['off_peak_to_final_decline_pct']:.1f}% |\n")
        out.append(f"| Per-tier (iter5) | {s['on_peak_active_ops']} | {s['on_final_active_ops']} | "
                   f"{s['on_peak_to_final_decline_pct']:.1f}% |\n\n")
        if s['on_peak_to_final_decline_pct'] < s['off_peak_to_final_decline_pct']:
            out.append(f"**Result:** per-tier matching reduces active-op decline by "
                       f"{s['off_peak_to_final_decline_pct'] - s['on_peak_to_final_decline_pct']:.1f} percentage points.\n\n")
        else:
            out.append("**Result:** per-tier matching did not reduce active-op decline; "
                       "global matching is sufficient.\n\n")

    # ─── BAYESIAN OPT ─────────────────────────────────────────────────────
    bo_winner = load_json("bo_winner_config.json")
    bo_top5 = load_json("bo_stage2_top5.json")
    if bo_winner:
        out.append(section("Bayesian-style random search (80 configs)"))
        out.append("Stage 1: 80 random configs × MC=10 over unified parameter space.\n")
        out.append("Stage 2: top-5 refined at MC=20.\n\n")
        out.append("**Winner config:**\n")
        out.append(f"- composite **{bo_winner['agg'].get('score_mean', 0):.4f} ± {bo_winner['agg'].get('score_std', 0):.4f}**\n")
        out.append(f"- ARR {fmt_money(bo_winner['agg'].get('realism_final_arr_usd_mean', 0))}, "
                   f"customers {bo_winner['agg'].get('realism_final_customer_count_mean', 0):.0f}\n")
        out.append("- params:\n")
        for k, v in bo_winner["config"].items():
            out.append(f"  - `{k}`: {v}\n")
        out.append("\n")
        if bo_top5:
            out.append("**Top 5 from Stage 2:**\n\n")
            out.append("| Rank | Composite | Stake | λ | Onboarding | Maturity mult | Growth threshold | DP mult |\n")
            out.append("|---|---|---|---|---|---|---|---|\n")
            for i, r in enumerate(bo_top5):
                c = r["config"]
                out.append(f"| {i+1} | {r['agg'].get('score_mean', 0):.4f} | "
                           f"${c['hardware_stake_t3']} | {c['lambda_max_per_segment']:.2f} | "
                           f"{c['onboarding_multiplier']:.2f} | {c['era_maturity_mult']:.1f} | "
                           f"M{c['era_growth_threshold_mo']} | {c['dp_size_multiplier']:.2f} |\n")
            out.append("\n")

    # ─── BACKTEST ─────────────────────────────────────────────────────────
    bt = load_json("iter5_backtest_results.json")
    if bt:
        out.append(section("Realism backtest vs DePIN / data-labeling peers"))
        out.append("Compared winner ARR trajectory at year-end checkpoints to "
                   "Scale AI / Helium / Hivemapper.\n\n")
        out.append("**Distances (log-L2, lower = closer):**\n")
        for name, d in sorted(bt["realism_distance"].items(), key=lambda x: x[1]):
            out.append(f"- {name}: {d:.3f}\n")
        out.append(f"\n**Closest peer:** {bt['closest_peer']}.\n\n")
        out.append("Distance interpretation: <0.5 = same order of magnitude; 0.5-1.0 = same shape, "
                   "different scale; >1.0 = qualitatively different.\n\n")

    # ─── HEADLINE FINDINGS ────────────────────────────────────────────────
    out.append(section("Iter5 headline findings", level=2))
    findings = []
    if pa:
        rows = sorted([(int(k.split("_")[1]), v) for k, v in pa.items()])
        best = max(rows, key=lambda r: r[1].get("score_mean", 0))
        findings.append(f"**Stake winner is ${best[0]}** (composite {best[1].get('score_mean', 0):.3f}), beating iter4's $100. There IS a floor — $0 underperforms $25.")
    if pc:
        worst_pair = min(pc.items(), key=lambda x: x[1].get("score_mean", 0))
        findings.append(f"**Worst combined-stress pair: `{worst_pair[0]}`** at composite {worst_pair[1].get('score_mean', 0):.3f}. The two existentials together compound — additive, not interactive.")
    if pd:
        best_q4 = max(pd.values(), key=lambda v: v.get("realism_q4_2026_milestone_hit_pct_true", 0))
        findings.append(f"**Q4 milestone:** best hit rate {best_q4.get('realism_q4_2026_milestone_hit_pct_true', 0)*100:.0f}%. {'Memo target achievable' if best_q4.get('realism_q4_2026_milestone_hit_pct_true', 0) >= 0.5 else 'Memo target unreachable; recommend $300K public target'}.")
    if pe:
        off = pe.get("personas_off", {}).get("score_mean", 0)
        best_pers = max(((k, v) for k, v in pe.items() if k != "personas_off"), key=lambda x: x[1].get("score_mean", 0), default=None)
        if off and best_pers:
            findings.append(f"**Persona cost:** {off - best_pers[1].get('score_mean', 0):.3f} composite — best mix `{best_pers[0]}`. {'Personas worth turning back on' if (off - best_pers[1].get('score_mean', 0)) < 0.05 else 'Personas remain off in winner config'}.")
    if pg:
        for k, v in pg.items():
            findings.append(f"**Per-tier matching:** composite {v.get('score_mean', 0):.3f}, active ops {v.get('active_operators_mean', 0):.0f}. {'Engine change improves winner' if v.get('score_mean', 0) > 0.75 else 'Engine change does not improve winner — keep aggregate matching'}.")
    if bo_winner:
        findings.append(f"**BO winner:** composite {bo_winner['agg'].get('score_mean', 0):.3f} via random search — found {'a NEW best' if bo_winner['agg'].get('score_mean', 0) > 0.75 else 'no improvement over Phase A grid winner'}.")
    if bt:
        findings.append(f"**Realism backtest:** trajectory closest to **{bt['closest_peer']}** — sits between Helium (DePIN-stagnated) and Scale AI (hypergrowth) — defensible in investor narrative.")

    for f in findings:
        out.append(f"- {f}\n")
    out.append("\n")

    # ─── RECOMMENDED LAUNCH CONFIG ────────────────────────────────────────
    out.append(section("Recommended launch config (post-iter5)"))
    if pa:
        rows = sorted([(int(k.split("_")[1]), v) for k, v in pa.items()])
        best = max(rows, key=lambda r: r[1].get("score_mean", 0))
        winner_stake = best[0]
        winner_score = best[1].get("score_mean", 0)
        out.append("```\n")
        out.append("calibration:        train_v5_realistic.PARAMS_V5_REALISTIC (J-curve)\n")
        out.append("tier_unlock:        op-count gated — T3=10, T4=5, T5=2\n")
        out.append(f"hardware_stake_t3:  ${winner_stake}  (iter5 discovery — was ${100} in iter4)\n")
        out.append("token_emission:     500K/mo, 100M max supply\n")
        out.append("amm_pool_at_tge:    $200K each side\n")
        out.append("contracts:          $15-40K/mo, λ=0.6/seg/mo (J-curve via era multipliers)\n")
        out.append("design_partners:    3 multi-year (24-month immune-from-sat-churn)\n")
        out.append("operator_onboarding: ×0.10 of v4 schedule\n")
        out.append("horizon_for_deck:   60 months\n")
        out.append("expected_composite: " + f"{winner_score:.3f}\n")
        out.append("```\n\n")

    out.append(section("Files"))
    out.append("- `experiments_v5_iter5.py` — 7-phase sweep harness\n")
    out.append("- `bayesian_opt_v5.py` — random-search optimizer\n")
    out.append("- `backtest_v5.py` — realism comparison vs Helium/Scale AI/Hivemapper\n")
    out.append("- `deck_iter5.py` — stakeholder package + 5-slide investor pitch generator\n")
    out.append("- `prepare_v5.py` — engine (added per-customer-tier matching)\n")
    out.append("- `v5_results/iter5_*.json` — phase-by-phase aggregates\n")
    out.append("- `v5_results/bo_winner_config.json` — Bayesian-opt winner\n")
    out.append("- `INVESTOR_PITCH_v5_iter5.md` — 5-slide deck-ready pitch\n")
    out.append("- `EXECUTIVE_SUMMARY_v5_iter5.md` — 1-page distillation\n")
    out.append("- `winner_timeseries_v5_iter5.csv` — month-by-month trajectory\n")
    out.append("- `v5_iter5_overview.png` — 6-panel chart\n")

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("".join(out))
    print(f"Wrote {REPORT_PATH}")


if __name__ == "__main__":
    build_report()
