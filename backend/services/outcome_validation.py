"""
Outcome Validation Engine

Compares expected vs actual clinical outcomes based on intervention adherence
and historical performance. Provides feedback for adaptive recommendations.
"""

from __future__ import annotations

from typing import Literal

from sqlalchemy.orm import Session
from models.entities import Score, Report, Intervention, Patient


def validate_outcome(
    previous_score: float,
    current_score: float,
    expected_range: dict[str, float],
) -> dict:
    """
    Validate whether current outcome matches expected improvement range.

    Args:
        previous_score: Prior system score (0-100)
        current_score: Current system score (0-100)
        expected_range: {"min": X, "max": Y} expected improvement in points

    Returns:
        {
            "actual_change": delta,
            "expected_range": expected_range,
            "status": "met" | "below" | "exceeded",
            "interpretation": str
        }
    """
    delta = current_score - previous_score

    if delta >= expected_range.get("min", 0):
        status: Literal["met", "below", "exceeded"] = "met"
        interpretation = f"Improvement met expectation: +{delta} points"
    elif delta < expected_range.get("min", 0):
        status = "below"
        interpretation = f"Below expected improvement: +{delta} points (expected >{expected_range.get('min', 0)})"
    else:
        status = "met"
        interpretation = f"Expected improvement achieved: +{delta} points"

    if delta > expected_range.get("max", 100):
        status = "exceeded"
        interpretation = f"Exceeded expectations: +{delta} points (expected <{expected_range.get('max', 100)})"

    return {
        "actual_change": delta,
        "expected_range": expected_range,
        "status": status,
        "interpretation": interpretation,
    }


def get_intervention_history(
    db: Session,
    patient_id: int,
    system: str,
    limit: int = 5,
) -> list[dict]:
    """
    Retrieve recent interventions for a patient's system.

    Returns:
        [{"created_at", "interventions", "adherence", "outcome_delta"}, ...]
    """
    interventions = (
        db.query(Intervention)
        .filter(Intervention.patient_id == patient_id, Intervention.system == system)
        .order_by(Intervention.created_at.desc())
        .limit(limit)
        .all()
    )

    history = []
    for inter in interventions:
        # Calculate delta between this intervention's report and the next (if exists)
        if inter.report_id:
            current_report = db.query(Report).filter(Report.id == inter.report_id).first()
            next_report = (
                db.query(Report)
                .filter(Report.patient_id == patient_id, Report.id > inter.report_id)
                .order_by(Report.created_at.asc())
                .first()
            )

            current_score = (
                db.query(Score)
                .filter(Score.report_id == inter.report_id, Score.system == system)
                .first()
            )
            next_score = None
            outcome_delta = 0.0

            if next_report and current_score:
                next_score = (
                    db.query(Score)
                    .filter(Score.report_id == next_report.id, Score.system == system)
                    .first()
                )
                if next_score:
                    outcome_delta = next_score.score - current_score.score

            history.append(
                {
                    "created_at": inter.created_at,
                    "interventions": inter.interventions,
                    "adherence": inter.adherence,
                    "outcome_delta": outcome_delta,
                }
            )

    return history


def assess_intervention_effectiveness(
    db: Session,
    patient_id: int,
    system: str,
) -> dict:
    """
    Assess whether interventions for this system have been effective historically.

    Returns:
        {
            "avg_outcome_delta": float,
            "success_rate": 0.0-1.0,
            "recommendation": "escalate" | "continue" | "optimize",
            "failed_interventions": [str] list of interventions that haven't worked
        }
    """
    history = get_intervention_history(db, patient_id, system, limit=10)

    if not history:
        return {
            "avg_outcome_delta": 0.0,
            "success_rate": 0.0,
            "recommendation": "continue",
            "failed_interventions": [],
        }

    deltas = [h["outcome_delta"] for h in history]
    successful = sum(1 for d in deltas if d > 0)
    avg_delta = sum(deltas) / len(deltas) if deltas else 0.0
    success_rate = successful / len(deltas) if deltas else 0.0

    # Failed interventions: positive adherence but negative outcome
    failed_interventions = [
        h["interventions"]
        for h in history
        if h["adherence"] in ["full", "partial"] and h["outcome_delta"] < -5
    ]

    # Flatten list of intervention lists
    failed_flat = []
    for inter_list in failed_interventions:
        if isinstance(inter_list, (list, tuple)):
            failed_flat.extend(inter_list)
        else:
            failed_flat.append(inter_list)

    if success_rate < 0.3 and avg_delta < -2:
        recommendation = "escalate"
    elif success_rate > 0.7 and avg_delta > 5:
        recommendation = "continue"
    else:
        recommendation = "optimize"

    return {
        "avg_outcome_delta": round(avg_delta, 2),
        "success_rate": round(success_rate, 2),
        "recommendation": recommendation,
        "failed_interventions": list(set(failed_flat)),  # Unique failed interventions
    }


def build_adaptive_recommendation(
    system: str,
    current_score: float,
    confidence: float,
    effectiveness: dict,
    system_interactions: dict | None = None,
) -> dict:
    """
    Build adaptive recommendation based on intervention history and current state.

    Escalates recommendation if previous interventions failed.
    Adjusts priority if system interactions detected.

    Returns:
        {
            "base_action": str,
            "escalation": str or None,
            "alternative_protocol": str or None,
            "interaction_note": str or None,
        }
    """
    result = {
        "base_action": "",
        "escalation": None,
        "alternative_protocol": None,
        "interaction_note": None,
    }

    if effectiveness["recommendation"] == "escalate":
        result["escalation"] = f"Previous interventions for {system} underperformed. Shift to advanced clinical intervention."
        result["alternative_protocol"] = "Consider specialist consultation, advanced markers (glutathione, bile acids, liver enzymes)."

    elif effectiveness["recommendation"] == "optimize":
        result["escalation"] = f"Previous interventions for {system} showed mixed results. Optimize protocol with dosage/timing adjustments."
        result["alternative_protocol"] = "Increase adherence support, combine therapies, add lifestyle modifications."

    if system_interactions and system_interactions.get("priority_shift"):
        result["interaction_note"] = system_interactions["priority_shift"]

    result["base_action"] = f"{'Advanced' if effectiveness['recommendation'] == 'escalate' else 'Standard'} protocol for {system}"

    return result
