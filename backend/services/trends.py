"""Trend interpretation and narrative summary engine.

Replaces raw delta numbers with clinically meaningful language.
"""
from __future__ import annotations


def interpret_trend(previous: int | float | None, current: int | float) -> dict:
    """
    Convert a score delta into a clinical trend interpretation.

    Returns:
        status: one-line clinical status phrase
        interpretation: decision-driving explanation
        delta: numeric change
    """
    curr = float(current)

    if previous is None:
        return {
            "status": "Baseline — no prior data",
            "interpretation": "First assessment. Establish baseline and re-test in 6–8 weeks.",
            "delta": None,
        }

    delta = round(curr - float(previous), 1)

    if delta == 0:
        if curr < 50:
            return {
                "status": "Stable but below optimal",
                "interpretation": "No improvement despite low score — intervention is overdue. Current approach is not working.",
                "delta": 0,
            }
        if curr < 65:
            return {
                "status": "Stable but sub-optimal",
                "interpretation": "Holding steady below peak — corrective measures should continue to push score above 65.",
                "delta": 0,
            }
        return {
            "status": "Stable within optimal range",
            "interpretation": "System is holding well — maintain current protocols.",
            "delta": 0,
        }

    if delta > 0:
        if delta >= 10:
            return {
                "status": "Strong improvement",
                "interpretation": f"+{delta} points — intervention is working. Continue current protocol.",
                "delta": delta,
            }
        return {
            "status": "Improving",
            "interpretation": f"+{delta} points — positive trend confirmed. Maintain and monitor.",
            "delta": delta,
        }

    # delta < 0
    if delta <= -10:
        return {
            "status": "Significant decline",
            "interpretation": f"{delta} points — active deterioration. Review intervention protocol immediately.",
            "delta": delta,
        }
    return {
        "status": "Declining",
        "interpretation": f"{delta} points — downward trend. Intensify corrective measures.",
        "delta": delta,
    }


def build_summary(system_scores: dict[str, int | float]) -> str:
    """
    Return a single, direct 3-part clinical summary sentence.

    Format: "X is [status], Y is [status], Z is [status]"
    Ranked worst-first so the most urgent information leads.
    """
    THRESHOLDS = [
        (35,  "critically underperforming — immediate intervention required"),
        (50,  "significantly underperforming"),
        (65,  "sub-optimal — corrective measures recommended"),
        (100, "stable"),
    ]

    def _label(score: float) -> str:
        for threshold, label in THRESHOLDS:
            if score < threshold:
                return label
        return "stable"

    ranked = sorted(system_scores.items(), key=lambda x: x[1])

    parts = [f"{system} is {_label(float(score))}" for system, score in ranked[:5]]

    if not parts:
        return "Insufficient data to generate summary."

    # Build sentence: first 2 joined with comma, last joined with "and"
    if len(parts) == 1:
        return parts[0].capitalize() + "."
    return (", ".join(parts[:-1]) + f", and {parts[-1]}").capitalize() + "."
