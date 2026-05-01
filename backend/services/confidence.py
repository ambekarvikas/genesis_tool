"""Standalone confidence scoring module.

Determines reliability of a clinical flag based on available genomic evidence.
"""
from __future__ import annotations


def calculate_confidence(
    n_genes: int | float | None,
    median_fc: float | None = None,
    expected_genes: int = 20,
) -> str:
    """
    Return "High", "Medium", or "Low" using a weighted coverage × effect formula.

    coverage = n_genes / expected_genes  (capped at 1.0)
    effect   = |median_fc| / 1.0        (capped at 1.0)
    score    = 0.6 * coverage + 0.4 * effect

    Thresholds:
    - High   → score > 0.75
    - Medium → score > 0.45
    - Low    → score ≤ 0.45
    """
    genes = int(n_genes or 0)
    fc = abs(float(median_fc)) if median_fc is not None else 0.0

    coverage = min(genes / expected_genes, 1.0)
    effect = min(fc / 1.0, 1.0)
    score = 0.6 * coverage + 0.4 * effect

    if score > 0.75:
        return "High"
    if score > 0.45:
        return "Medium"
    return "Low"


def get_priority(score: int | float) -> str:
    """Map a health score to a clinical priority label."""
    s = float(score)
    if s < 35:
        return "Critical"
    if s < 50:
        return "High"
    if s < 65:
        return "Moderate"
    return "Low"
