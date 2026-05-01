"""Decision engine — ranks systems by clinical priority and packages top issues.

Separates ranking/selection logic from the clinical definitions in clinical_engine.py
so each module has a single responsibility.
"""
from __future__ import annotations

import math

from services.confidence import get_priority


def _priority_rank(priority: str) -> int:
    return {"Critical": 0, "High": 1, "Moderate": 2, "Low": 3}.get(priority, 9)


def build_decision_output(
    system_scores: dict[str, int | float],
    system_reasons: dict[str, dict] | None = None,
) -> list[dict]:
    """
    Rank all five systems by clinical priority score and return a ranked list.

    priority_score = (100 - health_score) * log(n_genes + 1 + 1)
    Fallback: (100 - score) * 0.5  when no gene data available.

    Args:
        system_scores:  {system: health_score} dict
        system_reasons: optional {system: {n_genes, median_fc}} for weighting

    Returns:
        List of dicts ordered by descending priority, each with rank assigned.
    """
    reasons = system_reasons or {}
    ranked: list[dict] = []

    for system, score in system_scores.items():
        s = float(score)
        priority = get_priority(s)
        reason = reasons.get(system, {})
        n_genes = int(reason.get("n_genes") or 0)
        # Weight by evidence: more genes = more reliable prioritisation
        gene_weight = math.log(n_genes + 1) if n_genes > 0 else 0.5
        priority_score = round((100 - s) * gene_weight, 3)

        ranked.append(
            {
                "system": system,
                "score": round(s),
                "priority": priority,
                "priority_score": priority_score,
            }
        )

    ranked.sort(
        key=lambda x: (_priority_rank(x["priority"]), -x["priority_score"], x["score"])
    )

    for idx, item in enumerate(ranked, start=1):
        item["rank"] = idx

    return ranked


def get_top_issues(ranked_systems: list[dict], n: int = 3) -> list[dict]:
    """Return the top N highest-priority systems."""
    return ranked_systems[:n]
