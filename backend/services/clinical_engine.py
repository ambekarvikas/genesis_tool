from __future__ import annotations

import json
import pathlib
from functools import lru_cache

_CONFIG_PATH = pathlib.Path(__file__).parent.parent / "config" / "system_definitions.json"
_PRIORITY_RANK = {"Critical": 0, "High": 1, "Moderate": 2, "Low": 3}


@lru_cache(maxsize=1)
def _load_system_defs() -> dict:
    if not _CONFIG_PATH.exists():
        return {}
    with _CONFIG_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def _confidence(n_genes: int | float | None, _median_fc: float | None = None) -> str:
    genes = int(n_genes or 0)
    if genes >= 15:
        return "High"
    if genes >= 8:
        return "Medium"
    return "Low"


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
        priority_score = round((100 - health) * weight, 2)

        summary.append(
            {
                "system": system,
                "label": definition.get("label", f"{system} System"),
                "score": round(float(raw_score)),
                "priority": band.get("priority", "Moderate"),
                "priority_score": priority_score,
                "issue": band.get("issue", f"{system} requires clinical attention"),
                "impact": band.get("issue", f"{system} requires clinical attention"),
                "symptoms": band.get("symptoms", definition.get("default_symptoms", [])),
                "actions": band.get("actions", []),
                "expected_outcome": band.get("expected_outcome", ""),
                "confidence": confidence,
                "reason": reason,
                "high_is_worse": high_is_worse,
                "goal": definition.get("focus_goal", f"Improve {system} function"),
                "severity": band.get("priority", "Moderate"),
                "urgency": {
                    "Critical": "Immediate",
                    "High": "High",
                    "Moderate": "Medium",
                    "Low": "Low",
                }.get(band.get("priority", "Moderate"), "Medium"),
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
    critical = [s for s in systems if s.get("priority") in {"Critical", "High"}]
    if not critical:
        return "All systems are in stable range with no high-priority clinical flags."

    focus = critical[:2]
    names = " and ".join(s.get("system", "Unknown") for s in focus)
    return f"{names} systems are underperforming and should be prioritized in the next intervention cycle."
