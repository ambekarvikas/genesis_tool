"""
Evidence Engine

Aggregates intervention outcomes across all patients to build protocol-level
performance statistics. Answers: Has this worked before? How often? What delta?

Used to evolve the system from rule-based to evidence-backed recommendations.
"""

from __future__ import annotations

import statistics
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models.entities import Intervention, Score, Report, ProtocolPerformance


# Minimum improvement (points) to count a case as "successful"
SUCCESS_THRESHOLD = 5.0


def _get_outcome_delta(
    db: Session,
    patient_id: int,
    report_id: int,
    system: str,
) -> float | None:
    """
    Find the score delta for a system between the given report and the
    immediately following report for the same patient.
    """
    this_score = (
        db.query(Score)
        .filter(Score.report_id == report_id, Score.system == system)
        .first()
    )
    if not this_score:
        return None

    next_report = (
        db.query(Report)
        .filter(Report.patient_id == patient_id, Report.id > report_id)
        .order_by(Report.created_at.asc())
        .first()
    )
    if not next_report:
        return None

    next_score = (
        db.query(Score)
        .filter(Score.report_id == next_report.id, Score.system == system)
        .first()
    )
    if not next_score:
        return None

    return next_score.score - this_score.score


def compute_protocol_performance(db: Session) -> dict[tuple[str, str], dict]:
    """
    Scan all interventions that have a linked report, compute outcome deltas,
    group by (system, protocol_item), and return aggregated stats.

    Returns:
        {
            ("Detox", "NAC"): {
                "system": "Detox",
                "protocol": "NAC",
                "cases": 14,
                "avg_delta": 8.2,
                "median_delta": 7.5,
                "success_rate": 0.71,
            },
            ...
        }
    """
    all_interventions = (
        db.query(Intervention)
        .filter(Intervention.report_id.isnot(None))
        .all()
    )

    # Group deltas by (system, protocol_item)
    grouped: dict[tuple[str, str], list[float]] = {}

    for inter in all_interventions:
        delta = _get_outcome_delta(db, inter.patient_id, inter.report_id, inter.system)
        if delta is None:
            continue

        items = inter.interventions or []
        if isinstance(items, str):
            items = [items]

        for item in items:
            key = (inter.system, str(item))
            grouped.setdefault(key, []).append(delta)

    results = {}
    for (system, protocol), deltas in grouped.items():
        n = len(deltas)
        avg = round(sum(deltas) / n, 2) if n else 0.0
        med = round(statistics.median(deltas), 2) if n else 0.0
        successes = sum(1 for d in deltas if d >= SUCCESS_THRESHOLD)
        success_rate = round(successes / n, 4) if n else 0.0

        results[(system, protocol)] = {
            "system": system,
            "protocol": protocol,
            "cases": n,
            "avg_delta": avg,
            "median_delta": med,
            "success_rate": success_rate,
        }

    return results


def refresh_protocol_performance(db: Session) -> int:
    """
    Recompute all protocol performance statistics and upsert into the
    `protocol_performance` table.

    Returns the number of rows written.
    """
    stats = compute_protocol_performance(db)
    now = datetime.now(tz=timezone.utc)
    written = 0

    for (system, protocol), data in stats.items():
        existing = (
            db.query(ProtocolPerformance)
            .filter(
                ProtocolPerformance.system == system,
                ProtocolPerformance.protocol == protocol,
            )
            .first()
        )
        if existing:
            existing.cases = data["cases"]
            existing.avg_delta = data["avg_delta"]
            existing.median_delta = data["median_delta"]
            existing.success_rate = data["success_rate"]
            existing.last_updated = now
        else:
            db.add(
                ProtocolPerformance(
                    system=system,
                    protocol=protocol,
                    cases=data["cases"],
                    avg_delta=data["avg_delta"],
                    median_delta=data["median_delta"],
                    success_rate=data["success_rate"],
                    last_updated=now,
                )
            )
        written += 1

    db.commit()
    return written


def get_evidence_for_system(
    db: Session,
    system: str,
    protocols: list[str] | None = None,
) -> dict:
    """
    Retrieve aggregated evidence for a given system and optional list of
    specific protocols (action items).

    If protocols is None, aggregate across all protocols for the system.

    Returns:
        {
            "similar_cases": int,
            "avg_improvement": str  (e.g. "+8.2"),
            "median_improvement": str,
            "success_rate": str  (e.g. "71%"),
            "success_rate_raw": float,
            "best_protocol": str | None,
            "worst_protocol": str | None,
            "evidence_quality": "Strong" | "Moderate" | "Limited",
        }
    """
    query = db.query(ProtocolPerformance).filter(ProtocolPerformance.system == system)

    if protocols:
        query = query.filter(ProtocolPerformance.protocol.in_(protocols))

    rows = query.all()

    if not rows:
        return _empty_evidence()

    total_cases = sum(r.cases for r in rows)
    # Weighted average delta
    weighted_avg = sum(r.avg_delta * r.cases for r in rows) / total_cases if total_cases else 0.0
    weighted_success = sum(r.success_rate * r.cases for r in rows) / total_cases if total_cases else 0.0

    # Find best and worst performing protocols
    best = max(rows, key=lambda r: r.success_rate)
    worst = min(rows, key=lambda r: r.success_rate)

    if total_cases >= 20:
        evidence_quality = "Strong"
    elif total_cases >= 8:
        evidence_quality = "Moderate"
    else:
        evidence_quality = "Limited"

    avg_str = f"+{round(weighted_avg, 1)}" if weighted_avg >= 0 else str(round(weighted_avg, 1))

    # Weighted median: approximate from weighted average as best we can without raw data
    all_medians = [r.median_delta for r in rows]
    approx_median = statistics.median(all_medians) if all_medians else 0.0
    median_str = f"+{round(approx_median, 1)}" if approx_median >= 0 else str(round(approx_median, 1))

    return {
        "similar_cases": total_cases,
        "avg_improvement": avg_str,
        "median_improvement": median_str,
        "success_rate": f"{round(weighted_success * 100)}%",
        "success_rate_raw": round(weighted_success, 4),
        "best_protocol": best.protocol if best.success_rate > 0 else None,
        "worst_protocol": worst.protocol if len(rows) > 1 else None,
        "evidence_quality": evidence_quality,
    }


def _empty_evidence() -> dict:
    return {
        "similar_cases": 0,
        "avg_improvement": "N/A",
        "median_improvement": "N/A",
        "success_rate": "N/A",
        "success_rate_raw": None,
        "best_protocol": None,
        "worst_protocol": None,
        "evidence_quality": "None",
    }


def get_evidence_priority_modifier(success_rate_raw: float | None) -> str:
    """
    Determine whether to boost, lower, or keep recommendation priority
    based on protocol evidence.

    Returns:
        "boost"  — success_rate > 70%: evidence strongly supports this protocol
        "lower"  — success_rate < 50%: protocol underperforms historically
        "neutral" — 50-70% or no data
    """
    if success_rate_raw is None:
        return "neutral"
    if success_rate_raw > 0.70:
        return "boost"
    if success_rate_raw < 0.50:
        return "lower"
    return "neutral"
