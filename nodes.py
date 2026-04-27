"""
Nodes — DePIN node network for CrowdTrain v3 simulation.

Each Node = a regional facility with N robot arms hosting sync-tier work
(T2 browser teleop, T4 VR teleop, T5 live deployment).

Ownership: partner-operated (universities, hardware companies, regional partners).
CrowdTrain provides software + routing + QA standards. Partners earn revenue
share for hosting.

Spawn rule: when active_operators / nodes > target_ops_per_node, spawn a new
node. (Bootstrap: always spawn the first node — Alpha Node Tbilisi.)

Capacity: each arm provides hours_per_arm_per_month × max_concurrent_ops_per_arm
sync-tier hours per month. (Time-shared across operators.)
"""

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional


HOURS_PER_ARM_PER_MONTH = 720  # 24h × 30 days


@dataclass
class Node:
    id: int
    region: str = "global"
    arm_count: int = 4
    capex_usd: float = 50_000.0
    partner_owner_id: int = 0
    online_month: int = 0
    cumulative_revenue_usd: float = 0.0
    cumulative_partner_payouts_usd: float = 0.0
    monthly_utilization_history: List[float] = field(default_factory=list)


def maybe_spawn_node(
    active_op_count: int,
    existing_nodes: List[Node],
    ops_per_node_target: int,
    current_month: int,
    arms_per_node: int = 4,
    capex_per_node: float = 50_000.0,
) -> Optional[Node]:
    """
    Spawn a new node if active_ops / nodes > target.
    Bootstrap: always spawn the first node (Alpha Node Tbilisi).
    """
    if not existing_nodes:
        return Node(
            id=0,
            region="tbilisi",
            arm_count=arms_per_node,
            capex_usd=capex_per_node,
            partner_owner_id=0,
            online_month=current_month,
        )

    ratio = active_op_count / len(existing_nodes)
    if ratio > ops_per_node_target:
        regions = ["manila", "nairobi", "lagos", "buenos_aires", "warsaw",
                   "ho_chi_minh", "lisbon", "cape_town", "lima", "tashkent"]
        region = regions[len(existing_nodes) % len(regions)]
        return Node(
            id=len(existing_nodes),
            region=region,
            arm_count=arms_per_node,
            capex_usd=capex_per_node,
            partner_owner_id=len(existing_nodes),
            online_month=current_month,
        )
    return None


def total_arm_hours_available(
    nodes: List[Node],
    hours_per_arm_per_month: int = HOURS_PER_ARM_PER_MONTH,
    max_concurrent_ops_per_arm: int = 2,
) -> float:
    """Total sync-tier hours all arms can host this month (time-sharing accounted for)."""
    total_arms = sum(n.arm_count for n in nodes)
    return total_arms * hours_per_arm_per_month * max_concurrent_ops_per_arm


def cap_sync_tier_supply(
    sync_tier_demand_hours: Dict[int, float],
    total_arm_hours: float,
) -> Dict[int, float]:
    """
    Cap sync-tier (T2 / T4 / T5) demand at total arm capacity.
    Higher tiers prioritized: T5 > T4 > T2 (customer-facing live work first).
    Returns {tier: hours_actually_supplied}.
    """
    supplied = {}
    remaining = total_arm_hours
    for tier in [5, 4, 2]:  # priority order
        demand = sync_tier_demand_hours.get(tier, 0.0)
        h = min(demand, max(0.0, remaining))
        supplied[tier] = h
        remaining -= h
    return supplied


def compute_node_utilization(
    nodes: List[Node],
    total_sync_hours_supplied: float,
    hours_per_arm_per_month: int = HOURS_PER_ARM_PER_MONTH,
    max_concurrent_ops_per_arm: int = 2,
) -> float:
    """Aggregate utilization (0.0 - 1.0)."""
    if not nodes:
        return 0.0
    capacity = (
        sum(n.arm_count for n in nodes)
        * hours_per_arm_per_month
        * max_concurrent_ops_per_arm
    )
    if capacity <= 0:
        return 0.0
    util = total_sync_hours_supplied / capacity
    # Record per-node
    for n in nodes:
        n.monthly_utilization_history.append(min(1.0, util))
    return min(1.0, util)


def distribute_node_revenue(
    nodes: List[Node],
    monthly_sync_revenue_usd: float,
    partner_share_pct: float,
) -> Dict[int, float]:
    """
    Distribute monthly sync-tier revenue to node partners proportional to arm count.
    Updates each node's cumulative_revenue_usd and cumulative_partner_payouts_usd.
    Returns {partner_owner_id: total_payout_usd}.
    """
    total_arms = sum(n.arm_count for n in nodes)
    if total_arms == 0 or monthly_sync_revenue_usd <= 0:
        return {}

    payouts: Dict[int, float] = {}
    for n in nodes:
        arm_share = n.arm_count / total_arms
        node_revenue = arm_share * monthly_sync_revenue_usd
        n.cumulative_revenue_usd += node_revenue
        partner_payout = node_revenue * partner_share_pct
        n.cumulative_partner_payouts_usd += partner_payout
        payouts[n.partner_owner_id] = payouts.get(n.partner_owner_id, 0.0) + partner_payout
    return payouts


def node_roi_score(
    nodes: List[Node],
    current_month: int,
    amortization_months: int = 36,
) -> float:
    """
    Fraction of nodes (older than amortization_months) that have hit positive ROI.
    Returns 0.5 (neutral) if no nodes are old enough yet.
    """
    qualifying = [n for n in nodes if (current_month - n.online_month) >= amortization_months]
    if not qualifying:
        return 0.5
    paid_back = sum(1 for n in qualifying if n.cumulative_partner_payouts_usd >= n.capex_usd)
    return paid_back / len(qualifying)


def capacity_utilization_score(
    nodes: List[Node],
    target_low: float = 0.60,
    target_high: float = 0.80,
    idle_floor: float = 0.40,
    bottleneck_ceiling: float = 0.95,
) -> float:
    """
    Reward sync-tier utilization in [target_low, target_high].
    Penalize <idle_floor (idle waste) and >bottleneck_ceiling (unmet demand).
    Score in [0, 1].
    """
    if not nodes:
        return 0.0
    avg_util_per_node = []
    for n in nodes:
        if n.monthly_utilization_history:
            avg_util_per_node.append(
                sum(n.monthly_utilization_history) / len(n.monthly_utilization_history)
            )
    if not avg_util_per_node:
        return 0.5
    network_avg = sum(avg_util_per_node) / len(avg_util_per_node)

    if target_low <= network_avg <= target_high:
        return 1.0
    if network_avg < target_low:
        # Linear penalty below target; floor of 0.0 at idle_floor or below
        if network_avg <= idle_floor:
            return 0.0
        return (network_avg - idle_floor) / (target_low - idle_floor)
    # network_avg > target_high
    if network_avg >= bottleneck_ceiling:
        return 0.0
    return 1.0 - (network_avg - target_high) / (bottleneck_ceiling - target_high)
