from __future__ import annotations

import json
import math
import pathlib
from functools import lru_cache

from services.confidence import calculate_confidence, get_priority as _priority_label
from services.outcome_engine import predict_outcome

_CONFIG_PATH = pathlib.Path(__file__).parent.parent / "config" / "system_definitions.json"
_ACTIONS_PATH = pathlib.Path(__file__).parent.parent / "config" / "system_actions.json"
_PRIORITY_RANK = {"Critical": 0, "High": 1, "Moderate": 2, "Low": 3}


@lru_cache(maxsize=1)
def _load_system_defs() -> dict:
    if not _CONFIG_PATH.exists():
        return {}
    with _CONFIG_PATH.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def _load_system_actions() -> dict:
    if not _ACTIONS_PATH.exists():
        return {}
    with _ACTIONS_PATH.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def _get_actions(system: str, priority: str, band_actions: dict | list) -> dict:
    """Return priority-specific actions from system_actions.json, falling back to band actions."""
    actions_config = _load_system_actions()
    system_actions = actions_config.get(system, {})
    priority_actions = system_actions.get(priority)
    if priority_actions and isinstance(priority_actions, dict):
        return priority_actions
    # Fall back to band definition actions
    if isinstance(band_actions, dict):
        return band_actions
    return {"lifestyle": [], "nutrition": [], "clinical": []}


def _confidence(n_genes: int | float | None, median_fc: float | None = None) -> str:
    return calculate_confidence(n_genes, median_fc)


def _health_score(raw_score: float, high_is_worse: bool) -> float:
    return 100 - raw_score if high_is_worse else raw_score


def _pick_band(health_score: float, bands: list[dict]) -> dict:
    for band in bands:
        if float(band.get("min", 0)) <= health_score <= float(band.get("max", 100)):
            return band
    return bands[-1] if bands else {}


def _reason_for_system(system: str, pathway_rows: list[dict]) -> dict:
    rows = [r for r in pathway_rows if r.get("system") == system and (r.get("n_genes") or 0) > 0]
    if not rows:
        return {"n_genes": 0, "median_fc": None}

    total_genes = int(sum(int(r.get("n_genes") or 0) for r in rows))
    weighted_fc_num = 0.0
    weighted_fc_den = 0.0
    for row in rows:
        n_genes = float(row.get("n_genes") or 0)
        median_fc = row.get("median_fc")
        if median_fc is None:
            continue
        weighted_fc_num += float(median_fc) * n_genes
        weighted_fc_den += n_genes

    median_fc = round(weighted_fc_num / weighted_fc_den, 4) if weighted_fc_den > 0 else None
    return {"n_genes": total_genes, "median_fc": median_fc}


def _trend_status(health_score: float, priority: str, n_genes: int) -> dict:
    """Return a clinical trend interpretation — not just a raw value."""
    if priority in {"Critical", "High"}:
        if n_genes == 0:
            return {
                "status": "Flagged — insufficient genomic data to confirm",
                "interpretation": "Score is low but no matched genes found — validate input data or expand panel",
            }
        return {
            "status": f"Below threshold — intervention required",
            "interpretation": f"Score of {round(health_score)} with {n_genes} matched genes confirms active pathway disruption",
        }
    if priority == "Moderate":
        return {
            "status": "Stable but below optimal",
            "interpretation": "No immediate clinical action required — monitor and maintain corrective measures",
        }
    return {
        "status": "Within optimal range",
        "interpretation": "No pathway disruption detected — maintain current protocols",
    }


def build_clinical_summary(pathway_rows: list[dict], system_scores: dict[str, int | float]) -> list[dict]:
    defs = _load_system_defs()
    summary: list[dict] = []

    for system, raw_score in system_scores.items():
        definition = defs.get(system, {})
        bands = definition.get("bands", [])
        high_is_worse = bool(definition.get("high_is_worse", False))
        health = _health_score(float(raw_score), high_is_worse)
        band = _pick_band(health, bands)

        reason = _reason_for_system(system, pathway_rows)
        confidence = _confidence(reason.get("n_genes"), reason.get("median_fc"))
        weight = float(definition.get("system_weight", 1.0))
        n_genes_factor = math.log(float(reason.get("n_genes") or 0) + 1)
        priority_score = round((100 - health) * weight * max(n_genes_factor, 0.5), 2)
        band_priority = band.get("priority", "Moderate")
        actions = _get_actions(system, band_priority, band.get("actions", {}))
        outcome = predict_outcome(system, float(raw_score))

        summary.append(
            {
                "system": system,
                "label": definition.get("label", f"{system} System"),
                "score": round(float(raw_score)),
                "priority": band_priority,
                "priority_score": priority_score,
                "issue": band.get("issue", f"{system} requires clinical attention"),
                "impact": band.get("impact", ""),
                "symptoms": band.get("symptoms", definition.get("default_symptoms", [])),
                "actions": actions,
                "expected_outcome": band.get("expected_outcome", ""),
                "outcome_prediction": outcome,
                "confidence": confidence,
                "reason": {**reason, "score": round(float(raw_score))},
                "trend": _trend_status(health, band_priority, int(reason.get("n_genes") or 0)),
                "high_is_worse": high_is_worse,
                "goal": definition.get("focus_goal", f"Improve {system} function"),
                "severity": band_priority,
                "urgency": {
                    "Critical": "Immediate",
                    "High": "High",
                    "Moderate": "Medium",
                    "Low": "Low",
                }.get(band_priority, "Medium"),
            }
        )

    summary.sort(
        key=lambda item: (
            _PRIORITY_RANK.get(item.get("priority", "Low"), 9),
            -float(item.get("priority_score", 0)),
            float(item.get("score", 50)),
        )
    )

    for idx, item in enumerate(summary, start=1):
        item["rank"] = idx

    return summary


def build_overall_summary(systems: list[dict]) -> str:
    critical = [s for s in systems if s.get("priority") == "Critical"]
    high = [s for s in systems if s.get("priority") == "High"]
    urgent = critical + high
    if not urgent:
        moderate = [s for s in systems if s.get("priority") == "Moderate"]
        if moderate:
            names = ", ".join(s["system"] for s in moderate[:2])
            return f"{names} systems are below optimal — no immediate intervention required, but corrective measures should start now."
        return "All systems are within optimal range. Maintain current protocols and schedule next assessment in 8 weeks."
    if critical:
        names = ", ".join(s["system"] for s in critical[:2])
        suffix = f" — {', '.join(s['system'] for s in high[:1])} also requires attention." if high else "."
        return f"{names} require immediate clinical intervention{suffix}"
    names = " and ".join(s["system"] for s in high[:2])
    return f"{names} systems are underperforming. Prioritize intervention in the next clinical cycle."
