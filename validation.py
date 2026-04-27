"""
Validation — multi-witness consensus peer review for CrowdTrain v3 simulation.

Workflow per task:
1. Producer's hour of work generates a Task with raw_quality_score
2. Risk-weighted sampling decides whether the task gets reviewed
3. Sampled tasks get k validators (each with tier >= producer.tier + min_offset)
4. Each validator independently judges; consensus requires >=2 agreement
5. Disagreement -> escalate to single T6 audit
6. Consensus = "fail" -> graduated slashing (10/25/50% / ban)
7. Slashed tokens 50% to validators / 50% burned
8. Within validators: 70% to "fail" voters / 30% to "pass" voters
9. Validator base fee (10% of task value) paid to each validator
10. Bootstrap months 1-3: T0/T1 tasks auto-pass (no validator pool yet)
"""

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


PASS_THRESHOLD = 0.50  # raw_quality_score >= 0.50 is the "true" pass label


@dataclass
class Task:
    id: int
    producer_id: int
    tier: int
    hours: float = 1.0
    value_usd: float = 0.0
    value_tokens: float = 0.0
    raw_quality_score: float = 0.7
    sampled_for_review: bool = False
    validator_ids: List[int] = field(default_factory=list)
    validator_verdicts: Dict[int, str] = field(default_factory=dict)
    consensus_verdict: Optional[str] = None
    escalated: bool = False
    final_verdict: Optional[str] = None  # "pass" | "fail" | "auto_pass"
    final_quality: float = 0.7


def generate_task_pool(
    active_ops: List,
    tier_hours_actual: Dict[int, float],
    hourly_rates_usd: Dict[int, float],
    current_token_price: float,
    sim_trained_quality_bonus: float,
    next_task_id: int,
) -> Tuple[List[Task], int, Dict[int, float]]:
    """
    Generate task pool from operator-hours produced this month.

    Returns:
        (tasks, next_task_id_after, hours_per_op {op_id: hours})
    """
    tasks: List[Task] = []
    hours_per_op: Dict[int, float] = {}

    ops_by_tier: Dict[int, List] = {}
    for op in active_ops:
        if getattr(op, "is_banned", False):
            continue
        if getattr(op, "cooldown_until_month", None) is not None:
            continue
        ops_by_tier.setdefault(op.tier, []).append(op)

    for tier, hours_in_tier in tier_hours_actual.items():
        ops = ops_by_tier.get(tier, [])
        if not ops or hours_in_tier <= 0:
            continue

        # Distribute hours equally across operators in this tier
        # (capped per-op at the tier's nominal hours/month — set by caller via op.tier_hours_cap if present)
        per_op = hours_in_tier / len(ops)

        value_usd = hourly_rates_usd.get(tier, 0.0)
        value_tokens = value_usd / max(0.0001, current_token_price)

        for op in ops:
            cap = getattr(op, "tier_hours_cap", per_op)
            op_hours = min(per_op, cap)
            hours_per_op[op.id] = hours_per_op.get(op.id, 0.0) + op_hours

            # Each integer hour = 1 task; fractional hour rolls probabilistically
            num_tasks = int(op_hours)
            if (op_hours - num_tasks) > random.random():
                num_tasks += 1

            for _ in range(num_tasks):
                base = 0.65
                tier_bonus = tier * 0.05
                skill_factor = (op.skill - 0.5) * 0.20
                noise = random.gauss(0.0, 0.10)
                raw_q = max(0.0, min(1.0, base + tier_bonus + sim_trained_quality_bonus + skill_factor + noise))
                t = Task(
                    id=next_task_id,
                    producer_id=op.id,
                    tier=tier,
                    hours=1.0,
                    value_usd=value_usd,
                    value_tokens=value_tokens,
                    raw_quality_score=raw_q,
                )
                tasks.append(t)
                op.tasks_produced += 1
                op.time_budget_used_this_month += 1.0
                next_task_id += 1

    return tasks, next_task_id, hours_per_op


def select_validators(
    task: Task,
    eligible_pool: List,
    k: int = 3,
    min_offset: int = 1,
    audit_tier: int = 6,
) -> List:
    """
    Pick k validators for a task. Validator must:
    - tier >= task.tier + min_offset
    - not be the producer
    - not be banned / in cooldown
    - have spare review capacity (review_capacity_remaining > 0)
    Falls back to T6 audit pool if too few candidates.
    """
    candidates = [
        op for op in eligible_pool
        if op.tier >= task.tier + min_offset
        and op.id != task.producer_id
        and not getattr(op, "is_banned", False)
        and getattr(op, "cooldown_until_month", None) is None
        and getattr(op, "review_capacity_remaining", 0.0) > 0
    ]

    if len(candidates) >= k:
        return random.sample(candidates, k)

    # Fallback: T6 audit pool can validate any tier
    t6_pool = [
        op for op in eligible_pool
        if op.tier == audit_tier
        and op.id != task.producer_id
        and not getattr(op, "is_banned", False)
        and getattr(op, "cooldown_until_month", None) is None
        and getattr(op, "review_capacity_remaining", 0.0) > 0
    ]
    if len(t6_pool) >= k:
        return random.sample(t6_pool, k)

    # Combine; return whatever we have
    combined = list({c.id: c for c in (candidates + t6_pool)}.values())
    return combined[:k]


def validator_judgement(validator, task: Task) -> str:
    """
    Validator independently judges. Returns "pass" or "fail".
    Validator accuracy correlates with their own quality_score:
    accuracy = 0.60 + quality_score * 0.35  -> [0.60, 0.95]
    """
    true_pass = task.raw_quality_score >= PASS_THRESHOLD
    accuracy = 0.60 + getattr(validator, "quality_score", 0.7) * 0.35
    if random.random() < accuracy:
        return "pass" if true_pass else "fail"
    return "fail" if true_pass else "pass"


def run_consensus(
    task: Task,
    validators: List,
    current_month: int,
    bootstrap_months: int,
) -> Optional[str]:
    """
    Each validator independently judges. >=2 of 3 agree -> consensus verdict.
    During bootstrap_months: T0 / T1 tasks auto-pass.
    """
    if current_month <= bootstrap_months and task.tier <= 1:
        task.final_verdict = "auto_pass"
        task.final_quality = task.raw_quality_score
        return "auto_pass"

    if len(validators) < 2:
        # Insufficient validators -> auto-pass (treated as missed sample)
        task.final_verdict = "auto_pass"
        task.final_quality = task.raw_quality_score
        return "auto_pass"

    verdicts = []
    for v in validators:
        verdict = validator_judgement(v, task)
        task.validator_verdicts[v.id] = verdict
        task.validator_ids.append(v.id)
        v.tasks_reviewed += 1
        v.review_capacity_remaining = max(0.0, v.review_capacity_remaining - 0.25)
        verdicts.append(verdict)

    pass_count = verdicts.count("pass")
    fail_count = verdicts.count("fail")

    if pass_count >= 2:
        task.consensus_verdict = "pass"
        task.final_verdict = "pass"
    elif fail_count >= 2:
        task.consensus_verdict = "fail"
        task.final_verdict = "fail"
    else:
        # 1 pass, 1 fail (only with k=2) -> escalate
        task.consensus_verdict = None
        task.escalated = True
        task.final_verdict = None

    task.final_quality = task.raw_quality_score
    return task.final_verdict


def escalate_to_audit(task: Task, t6_pool: List) -> str:
    """Single T6 auditor breaks consensus tie."""
    eligible = [
        op for op in t6_pool
        if op.id != task.producer_id
        and op.id not in task.validator_ids
        and not getattr(op, "is_banned", False)
        and getattr(op, "review_capacity_remaining", 0.0) > 0
    ]
    if not eligible:
        task.final_verdict = "pass"
        return "pass"
    auditor = random.choice(eligible)
    verdict = validator_judgement(auditor, task)
    task.final_verdict = verdict
    auditor.tasks_reviewed += 1
    auditor.review_capacity_remaining = max(0.0, auditor.review_capacity_remaining - 0.5)
    return verdict


def apply_slashing(
    producer,
    task: Task,
    validators: List,
    strike_severities: List[float],
    slash_split: Dict[str, float],
    catch_bonus_split: Dict[str, float],
    ban_on_strike: int,
    cooldown_months_after_3rd: int,
    current_month: int,
) -> Dict:
    """
    Apply graduated slashing on a "fail" verdict.
    Returns dict with: slash_amount, validator_payout_total, burn_amount,
                       catcher_payouts {validator_id: amount},
                       strike_count, cooldown_set, banned
    """
    result = {
        "slash_amount": 0.0,
        "validator_payout_total": 0.0,
        "burn_amount": 0.0,
        "catcher_payouts": {},
        "strike_count": producer.strikes,
        "cooldown_set": False,
        "banned": False,
        "false_positive_validator_ids": [],
    }
    if task.final_verdict != "fail":
        return result

    producer.strikes += 1
    producer.clean_hours_since_last_strike = 0.0

    if producer.strikes >= ban_on_strike:
        producer.is_banned = True
        slash_pct = 1.0
        result["banned"] = True
    elif (producer.strikes - 1) < len(strike_severities):
        slash_pct = strike_severities[producer.strikes - 1]
    else:
        slash_pct = strike_severities[-1]

    if producer.strikes == 3 and cooldown_months_after_3rd > 0:
        producer.cooldown_until_month = current_month + cooldown_months_after_3rd
        result["cooldown_set"] = True

    available_stake = max(0.0, producer.tokens_staked)
    slash_amount = available_stake * slash_pct
    producer.tokens_staked = max(0.0, producer.tokens_staked - slash_amount)

    validator_payout_total = slash_amount * slash_split["validators"]
    burn_amount = slash_amount * slash_split["burn"]

    fail_voters = [v for v in validators if task.validator_verdicts.get(v.id) == "fail"]
    pass_voters = [v for v in validators if task.validator_verdicts.get(v.id) == "pass"]

    catcher_payouts: Dict[int, float] = {}

    fail_pool = validator_payout_total * catch_bonus_split["fail_voters"]
    pass_pool = validator_payout_total * catch_bonus_split["pass_voters"]

    if fail_voters:
        per = fail_pool / len(fail_voters)
        for v in fail_voters:
            catcher_payouts[v.id] = per
            v.tokens_held += per
    else:
        burn_amount += fail_pool

    if pass_voters:
        per = pass_pool / len(pass_voters)
        for v in pass_voters:
            catcher_payouts[v.id] = catcher_payouts.get(v.id, 0.0) + per
            v.tokens_held += per
            # pass-vote on a consensus-fail = false positive (missed bad work)
            v.false_positive_count += 1
            result["false_positive_validator_ids"].append(v.id)
    else:
        burn_amount += pass_pool

    result["slash_amount"] = slash_amount
    result["validator_payout_total"] = validator_payout_total
    result["burn_amount"] = burn_amount
    result["catcher_payouts"] = catcher_payouts
    result["strike_count"] = producer.strikes
    return result


def update_strikes_and_clean_streak(
    operators: List,
    monthly_qualified_hours: Dict[int, float],
    clean_hours_per_reset: int = 100,
    quality_threshold: float = 0.65,
) -> int:
    """
    Increment clean_hours for ops with quality >= threshold.
    Remove 1 strike per `clean_hours_per_reset` accumulated.
    Returns count of strikes removed this month.
    """
    removed = 0
    for op in operators:
        if op.strikes <= 0:
            continue
        if op.quality_score >= quality_threshold:
            h = monthly_qualified_hours.get(op.id, 0.0)
            op.clean_hours_since_last_strike += h
            while (
                op.clean_hours_since_last_strike >= clean_hours_per_reset
                and op.strikes > 0
            ):
                op.strikes -= 1
                op.clean_hours_since_last_strike -= clean_hours_per_reset
                removed += 1
    return removed
