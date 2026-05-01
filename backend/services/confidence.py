"""Standalone confidence scoring module.

Determines reliability of a clinical flag based on available genomic evidence.
"""
from __future__ import annotations


def calculate_confidence(n_genes: int | float | None, median_fc: float | None = None) -> str:
    """
    Return "High", "Medium", or "Low" confidence based on:
    - n_genes: number of matched genes driving the pathway score
    - median_fc: median fold-change magnitude across those genes

    Rules:
    - High   → 15+ genes AND |median_fc| > 0.5 (large signal, well-supported)
    - Medium → 8+ genes (adequate data, moderate signal)
    - Low    → insufficient genes or fold-change too small to be conclusive
    """
    genes = int(n_genes or 0)
    fc = abs(float(median_fc)) if median_fc is not None else 0.0

    if genes >= 15 and fc > 0.5:
        return "High"
    if genes >= 8:
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
