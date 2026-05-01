"""Outcome prediction engine.

Predicts expected score improvement, timeline, and observable clinical signs
based on a system's current health score and priority band.
"""
from __future__ import annotations

# Observable signs per system — shown as "what the patient will actually notice"
_OBSERVABLE_SIGNS: dict[str, dict[str, list[str]]] = {
    "Energy": {
        "critical":  ["Significant reduction in daily fatigue", "Able to sustain activity without crashing", "Improved sleep quality"],
        "high":      ["Fewer afternoon energy dips", "Better post-exercise recovery", "More consistent wakefulness"],
        "moderate":  ["Mild improvement in sustained energy", "Reduced reliance on stimulants"],
        "low":       ["Energy levels remain stable"],
    },
    "Inflammation": {
        "critical":  ["Reduced joint stiffness on waking", "Less soreness after activity", "Improved recovery rate"],
        "high":      ["Lower baseline ache level", "Faster tissue recovery", "Better sleep quality"],
        "moderate":  ["Minor reduction in chronic soreness"],
        "low":       ["Inflammatory markers remain stable"],
    },
    "Detox": {
        "critical":  ["Reduced headache frequency", "Less sensitivity to environmental toxins", "Improved mental clarity"],
        "high":      ["Better tolerance to chemical exposures", "Reduced fatigue after meals"],
        "moderate":  ["Minor improvement in general wellbeing"],
        "low":       ["Detox function remains stable"],
    },
    "Brain": {
        "critical":  ["Noticeably clearer thinking", "Improved mood stability", "Better stress tolerance"],
        "high":      ["Improved focus under pressure", "Reduced brain fog episodes", "More consistent mood"],
        "moderate":  ["Slightly sharper cognition", "Fewer low-focus periods"],
        "low":       ["Cognitive function remains stable"],
    },
    "Recovery": {
        "critical":  ["Significantly faster muscle recovery", "Reduced injury susceptibility", "Better adaptation to training"],
        "high":      ["Less delayed-onset soreness", "Improved training consistency", "Better sleep-driven repair"],
        "moderate":  ["Slightly improved post-activity recovery"],
        "low":       ["Recovery capacity remains stable"],
    },
}

_DEFAULT_SIGNS = {
    "critical": ["Noticeable functional improvement", "Reduced symptom burden"],
    "high":     ["Moderate functional improvement"],
    "moderate": ["Mild improvement over baseline"],
    "low":      ["No change expected — system stable"],
}


def predict_outcome(system: str, score: int | float) -> dict:
    """
    Return a structured outcome prediction with:
    - expected_change: score delta range as a string
    - timeline: realistic improvement window
    - observable_signs: what the patient/clinician will actually see
    - note: interpretation context
    """
    s = float(score)

    signs_map = _OBSERVABLE_SIGNS.get(system, _DEFAULT_SIGNS)

    if s < 35:
        return {
            "expected_change": "+15 to +25",
            "timeline": "6–8 weeks with consistent intervention",
            "observable_signs": signs_map.get("critical", _DEFAULT_SIGNS["critical"]),
            "note": "Critical deficit — sustained improvement requires lifestyle + clinical intervention in parallel.",
        }
    if s < 50:
        return {
            "expected_change": "+8 to +15",
            "timeline": "4–6 weeks",
            "observable_signs": signs_map.get("high", _DEFAULT_SIGNS["high"]),
            "note": "Significant room for improvement with targeted nutritional and lifestyle changes.",
        }
    if s < 65:
        return {
            "expected_change": "+5 to +10",
            "timeline": "4–6 weeks",
            "observable_signs": signs_map.get("moderate", _DEFAULT_SIGNS["moderate"]),
            "note": "System is sub-optimal but not critical — corrective measures should prevent further decline.",
        }
    return {
        "expected_change": "Maintain ±5",
        "timeline": "Ongoing",
        "observable_signs": signs_map.get("low", _DEFAULT_SIGNS["low"]),
        "note": "System is within optimal range. Focus on maintenance.",
    }
