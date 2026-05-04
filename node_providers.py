"""
CrowdBrain v5 — Node providers as first-class bonded stakeholders
==================================================================
v5 memo treats node-providers as a separate economic actor (not just an
internal node-spawn process). Each provider stakes per-arm; slashable on
uptime/latency/quality failures; earns revenue share. Operators report bad
nodes; higher-tier reviewers verify disputes; auto-checks for routine.

Distinct from v4's `nodes.py` (which models capacity only). v5 layer adds:
- Bonded provider entity (separate from CrowdBrain-owned facility nodes)
- Stake at risk
- Quality monitoring (uptime, latency, calibration, data-quality)
- Operator reporting + dispute resolution
- Revenue routing (provider share + protocol fee)

Provider types:
- 'facility': CrowdBrain-owned (Alpha Node + replicas). No bond. Implicit quality.
- 'community': Third-party. Bonded. Slashable. Higher revenue share for risk.

The facility/community split is parameterized for sweep (Track 3).
"""

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ─── DEFAULTS ─────────────────────────────────────────────────────────────────
DEFAULT_PROVIDER_PARAMS = {
    "bond_per_arm_usd": 5_000,
    "facility_share":   1.0,       # 1.0 = all facility, 0.0 = all community
    "community_revenue_share":  0.20,   # community providers get 20% of task revenue routed through them
    "facility_revenue_share":   0.0,    # facility owned by CB; revenue stays with CB
    "protocol_fee_pct":         0.10,
    "report_audit_threshold":   3,      # 3 reports in a rolling 6mo window triggers audit
    "auto_check_failure_pct":   0.02,   # 2% of months: random auto-check failure baseline
    "slash_severities": {
        "uptime":      0.10,   # 10% of bond
        "latency":     0.10,
        "calibration": 0.15,
        "safety":      0.30,   # severe
        "data_quality":0.15,
        "audit_fail":  0.50,   # confirmed dispute via audit
    },
    "ban_after_full_slash":     True,   # provider banned when bond is depleted
    "report_false_positive_pct": 0.10,  # 10% of operator reports are bad-faith / wrong
}

PRESET_POLICIES = {
    "nodes_baseline": {
        "bond_per_arm_usd": 5_000,
        "facility_share":   1.0,    # 100% facility (matches v4)
        "report_audit_threshold": 3,
    },
    "nodes_low_bond": {
        "bond_per_arm_usd": 1_000,
        "facility_share":   0.5,    # 50/50
        "report_audit_threshold": 3,
    },
    "nodes_med_bond": {
        "bond_per_arm_usd": 5_000,
        "facility_share":   0.5,
        "report_audit_threshold": 3,
    },
    "nodes_high_bond": {
        "bond_per_arm_usd": 20_000,
        "facility_share":   0.5,
        "report_audit_threshold": 5,
    },
    "nodes_community_heavy": {
        "bond_per_arm_usd": 5_000,
        "facility_share":   0.2,    # 20/80 (community-heavy)
        "report_audit_threshold": 3,
    },
    "nodes_community_only": {
        "bond_per_arm_usd": 5_000,
        "facility_share":   0.0,    # 100% community
        "report_audit_threshold": 3,
    },
}


@dataclass
class NodeProvider:
    id: int
    kind: str              # "facility" or "community"
    arms: int              # number of arms hosted
    bond_usd: float        # current bond in USD
    initial_bond_usd: float
    join_month: int
    quality_score: float = 0.85   # rolling quality (0-1)
    uptime_pct: float = 0.95
    reports_received: List[int] = field(default_factory=list)   # list of months a report was filed
    audits_open: int = 0
    is_banned: bool = False
    cumulative_earnings_usd: float = 0.0
    months_active: int = 0


def init_providers_for_arms(
    total_arms: int,
    params: Dict,
    month: int,
) -> List[NodeProvider]:
    """
    Allocate the current arm pool to facility vs community providers.
    Facility provider is always one big node (CB-owned).
    Community providers are smaller (1-3 arms each typically).
    """
    facility_share = params.get("facility_share", 1.0)
    bond_per_arm = params.get("bond_per_arm_usd", 5_000)

    facility_arms = int(round(total_arms * facility_share))
    community_arms = total_arms - facility_arms

    providers: List[NodeProvider] = []

    if facility_arms > 0:
        providers.append(NodeProvider(
            id=0,
            kind="facility",
            arms=facility_arms,
            bond_usd=0.0,             # facility has no slashable bond
            initial_bond_usd=0.0,
            join_month=0,
            quality_score=0.92,        # facility quality higher than community baseline
            uptime_pct=0.98,
        ))

    # Community providers: split into individual provider entities
    # Each owns 1-3 arms (Pareto-ish; mostly 1-arm hobbyists)
    if community_arms > 0:
        provider_id = 1
        remaining = community_arms
        while remaining > 0:
            arms_for_this = min(remaining, random.choices([1, 2, 3], weights=[0.6, 0.3, 0.1])[0])
            bond = bond_per_arm * arms_for_this
            providers.append(NodeProvider(
                id=provider_id,
                kind="community",
                arms=arms_for_this,
                bond_usd=bond,
                initial_bond_usd=bond,
                join_month=month,
            ))
            provider_id += 1
            remaining -= arms_for_this

    return providers


def total_arms_active(providers: List[NodeProvider]) -> int:
    return sum(p.arms for p in providers if not p.is_banned)


def monthly_node_quality_check(
    providers: List[NodeProvider],
    params: Dict,
    month: int,
    rng: Optional[random.Random] = None,
) -> Dict:
    """
    For each non-banned provider:
    - Roll auto-check failures (uptime/latency/calibration)
    - Roll operator-reported issues
    - Apply slashing if bond depleted -> ban (if community)
    Returns metrics: total_slashed_usd, providers_slashed, providers_banned, audits_resolved.
    """
    if rng is None:
        rng = random
    auto_fail_pct = params.get("auto_check_failure_pct", 0.02)
    severities = params.get("slash_severities", DEFAULT_PROVIDER_PARAMS["slash_severities"])
    ban_after_zero = params.get("ban_after_full_slash", True)
    report_audit_threshold = params.get("report_audit_threshold", 3)
    fp_pct = params.get("report_false_positive_pct", 0.10)

    total_slashed = 0.0
    providers_slashed = 0
    providers_banned = 0
    audits_resolved = 0

    for p in providers:
        if p.is_banned:
            continue
        p.months_active += 1

        # Facility never slashed (CB-owned, monitored internally)
        if p.kind == "facility":
            continue

        # Auto-check: each arm-month rolls for a routine failure
        # Quality drift: nudge quality_score by gaussian
        p.quality_score = max(0.3, min(1.0, p.quality_score + rng.gauss(0, 0.02)))
        p.uptime_pct = max(0.5, min(1.0, p.uptime_pct + rng.gauss(0, 0.01)))

        slash_event = None
        if rng.random() < auto_fail_pct * p.arms:
            # Pick a failure type weighted by severity (rare ones rarer)
            slash_event = rng.choices(
                list(severities.keys()),
                weights=[1, 1, 0.5, 0.2, 0.7, 0.5],   # safety + audit are rare
                k=1,
            )[0]
        # Operator-reported issues: trigger audit when threshold hit in rolling 6mo window
        recent_reports = [m for m in p.reports_received if month - m <= 6]
        if len(recent_reports) >= report_audit_threshold:
            audits_resolved += 1
            # Audit confirms ~70% of reports (fp_pct false positive rate on the bundle)
            if rng.random() > fp_pct:
                slash_event = "audit_fail"
            # Reset report window after audit
            p.reports_received = [m for m in p.reports_received if month - m <= 1]

        if slash_event:
            severity = severities[slash_event]
            slash_amt = p.bond_usd * severity
            p.bond_usd -= slash_amt
            total_slashed += slash_amt
            providers_slashed += 1

            # Quality drops on confirmed slash
            p.quality_score = max(0.3, p.quality_score - 0.10)

            if p.bond_usd <= 0 and ban_after_zero:
                p.is_banned = True
                providers_banned += 1

    return {
        "total_slashed_usd": total_slashed,
        "providers_slashed": providers_slashed,
        "providers_banned": providers_banned,
        "audits_resolved": audits_resolved,
    }


def simulate_operator_reports(
    providers: List[NodeProvider],
    n_active_operators: int,
    month: int,
    rng: Optional[random.Random] = None,
) -> int:
    """
    Each month, some operators may file reports against community nodes if quality
    is degrading. Returns total reports filed this month.
    """
    if rng is None:
        rng = random
    if n_active_operators <= 0:
        return 0
    total_reports = 0
    for p in providers:
        if p.kind != "community" or p.is_banned:
            continue
        # Probability of report per arm proportional to (1 - quality_score)
        report_prob_per_arm = max(0.0, (1.0 - p.quality_score) * 0.03)
        n_reports = sum(1 for _ in range(p.arms) if rng.random() < report_prob_per_arm)
        for _ in range(n_reports):
            p.reports_received.append(month)
            total_reports += 1
    return total_reports


def average_node_quality(providers: List[NodeProvider]) -> float:
    if not providers:
        return 0.85
    active = [p for p in providers if not p.is_banned]
    if not active:
        return 0.0
    weights = [p.arms for p in active]
    weighted_sum = sum(p.quality_score * p.arms for p in active)
    return weighted_sum / max(1, sum(weights))


def distribute_provider_revenue(
    providers: List[NodeProvider],
    sync_revenue_usd: float,
    params: Dict,
) -> Dict[str, float]:
    """
    Route sync-tier revenue to providers based on arm count and kind.
    Facility revenue stays with CrowdBrain (treasury).
    Community providers get community_revenue_share of routed revenue.
    Returns split: {treasury_usd, community_usd, protocol_fee_usd}.
    """
    if not providers or sync_revenue_usd <= 0:
        return {"treasury_usd": sync_revenue_usd, "community_usd": 0.0, "protocol_fee_usd": 0.0}

    protocol_fee = sync_revenue_usd * params.get("protocol_fee_pct", 0.10)
    after_fee = sync_revenue_usd - protocol_fee

    facility_arms = sum(p.arms for p in providers if p.kind == "facility" and not p.is_banned)
    community_arms = sum(p.arms for p in providers if p.kind == "community" and not p.is_banned)
    total_arms = facility_arms + community_arms

    if total_arms == 0:
        return {"treasury_usd": sync_revenue_usd, "community_usd": 0.0, "protocol_fee_usd": 0.0}

    community_share_rate = params.get("community_revenue_share", 0.20)
    facility_share_rate = params.get("facility_revenue_share", 0.0)

    # Facility revenue routes to treasury directly (CB-owned)
    facility_revenue = after_fee * (facility_arms / total_arms)
    community_revenue = after_fee * (community_arms / total_arms)

    # Community providers get community_share_rate; rest goes to treasury
    community_paid = community_revenue * community_share_rate
    treasury_residual = facility_revenue + community_revenue * (1 - community_share_rate)

    # Distribute community pay across community providers proportional to arms
    if community_arms > 0:
        per_arm = community_paid / community_arms
        for p in providers:
            if p.kind == "community" and not p.is_banned:
                pay = per_arm * p.arms
                p.cumulative_earnings_usd += pay

    return {
        "treasury_usd":     treasury_residual,
        "community_usd":    community_paid,
        "protocol_fee_usd": protocol_fee,
    }
