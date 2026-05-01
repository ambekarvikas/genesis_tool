"""
Rule Engine
-----------
Deterministic rule evaluation against system scores.
Rules are loaded from config/rules.json.
Each rule's condition is evaluated with the system score as the only
variable — no dynamic eval, just safe comparisons parsed here.
"""
from __future__ import annotations

import json
import pathlib
import re
from functools import lru_cache

_CONFIG_DIR = pathlib.Path(__file__).parent.parent / "config"

# ─── Priority & confidence helpers ────────────────────────────────────────────

def get_priority(score: float, high_is_bad: bool = False) -> str:
    if high_is_bad:
        if score >= 75:
            return "Critical"
        if score >= 65:
            return "High"
        if score >= 55:
            return "Moderate"
        return "Low"
    if score < 35:
        return "Critical"
    if score < 50:
        return "High"
    if score < 65:
        return "Moderate"
    return "Low"


def get_severity_and_urgency(score: float, high_is_bad: bool = False) -> tuple[str, str]:
    priority = get_priority(score, high_is_bad)
    urgency_map = {
        "Critical": "Immediate",
        "High": "High",
        "Moderate": "Medium",
        "Low": "Low",
    }
    return priority, urgency_map[priority]


def calculate_confidence(n_genes: int | float | None) -> str:
    genes = int(n_genes or 0)
    if genes >= 15:
        return "High"
    if genes >= 8:
        return "Medium"
    return "Low"


# ─── Condition evaluator ──────────────────────────────────────────────────────

_CONDITION_RE = re.compile(
    r"^(?:score\s*([<>]=?|==)\s*([\d.]+))"
    r"(?:\s+and\s+score\s*([<>]=?|==)\s*([\d.]+))?$"
)


def _eval_condition(condition: str, score: float) -> bool:
    """
    Safely evaluate conditions of the form:
      'score < 50'
      'score >= 35 and score < 50'
    Returns True when the condition is satisfied.
    """
    m = _CONDITION_RE.match(condition.strip())
    if not m:
        return False

    op1, val1, op2, val2 = m.groups()
    val1 = float(val1)

    def _cmp(s: float, op: str, v: float) -> bool:
        return {
            "<":  s < v,
            "<=": s <= v,
            ">":  s > v,
            ">=": s >= v,
            "==": s == v,
        }.get(op, False)

    result = _cmp(score, op1, val1)
    if op2 and val2 is not None:
        result = result and _cmp(score, op2, float(val2))
    return result


# ─── Rule loader ──────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _load_rules() -> list[dict]:
    rules_file = _CONFIG_DIR / "rules.json"
    if not rules_file.exists():
        return []
    with rules_file.open(encoding="utf-8") as fh:
        return json.load(fh)


# ─── Public API ───────────────────────────────────────────────────────────────

def evaluate_rules(system_scores: dict[str, int | float]) -> list[dict]:
    """
    Evaluate all rules against the provided system scores.
    Returns a list of triggered rule results sorted by severity.
    """
    rules = _load_rules()
    results: list[dict] = []

    for rule in rules:
        system = rule.get("system", "")
        score = system_scores.get(system)
        if score is None:
            continue

        high_is_bad = system == "Inflammation"
        condition = rule.get("condition", "")
        if not _eval_condition(condition, float(score)):
            continue

        severity, urgency = get_severity_and_urgency(float(score), high_is_bad)
        target = rule.get("target_score")
        goal = (
            f"Increase {system} score from {round(score)} → {target}"
            if (target and not high_is_bad)
            else f"Reduce {system} score from {round(score)} → {target}"
            if (target and high_is_bad)
            else f"Improve {system} system resilience"
        )

        results.append({
            "system": system,
            "score": round(float(score)),
            "issue": rule["issue"],
            "impact": rule["impact"],
            "symptoms": rule.get("symptoms", []),
            "actions": rule.get("actions", []),
            "expected_outcome": rule.get("expected_outcome", ""),
            "priority": rule.get("priority", severity),
            "severity": severity,
            "urgency": urgency,
            "goal": goal,
            "target_score": target,
            # keep action key for backward-compat with DB persist
            "action": rule.get("actions", []),
        })

    _SEVERITY_RANK = {"Critical": 0, "High": 1, "Moderate": 2, "Low": 3}
    results.sort(key=lambda r: (_SEVERITY_RANK.get(r["severity"], 9), r["score"]))

    for idx, item in enumerate(results, start=1):
        item["rank"] = idx

    return results
