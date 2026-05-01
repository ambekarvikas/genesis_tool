"""
comparison_engine.py
~~~~~~~~~~~~~~~~~~~~
Compare baseline vs follow-up system scores and produce a human-readable
verdict for each body system.
"""
from __future__ import annotations

SYSTEMS = ["Energy", "Inflammation", "Detox", "Brain", "Recovery"]

# ── thresholds ───────────────────────────────────────────────────────────────
STRONG_IMPROVEMENT = 15
IMPROVEMENT = 5
STRONG_DECLINE = -15
DECLINE = -5


def _interpret(delta: float, system: str) -> str:
    """Return a one-line clinical interpretation string."""
    if delta >= STRONG_IMPROVEMENT:
        return f"Strong improvement in {system} function"
    if delta >= IMPROVEMENT:
        return f"Moderate improvement in {system} function"
    if delta <= STRONG_DECLINE:
        return f"Significant decline in {system} — urgent review required"
    if delta <= DECLINE:
        return f"Slight decline in {system} — monitor closely"
    return f"{system} function stable"


def _status(delta: float) -> str:
    if delta > IMPROVEMENT:
        return "improved"
    if delta < DECLINE:
        return "worse"
    return "same"


def compare_reports(
    baseline_scores: dict[str, float],
    followup_scores: dict[str, float],
    interventions: list[dict] | None = None,
) -> list[dict]:
    """
    Compare two score snapshots and return per-system comparison rows.

    Parameters
    ----------
    baseline_scores : dict  {system: score}
    followup_scores : dict  {system: score}
    interventions   : list of intervention dicts linked to this patient
                      (used to surface the action label in the result)

    Returns
    -------
    list of dicts, one per system, e.g.:
        {
          "system": "Detox",
          "baseline": 32,
          "followup": 48,
          "delta": 16,
          "status": "improved",
          "interpretation": "Strong improvement in Detox function",
          "intervention": "NAC, Glutathione"   # if available
        }
    """
    # Build a quick lookup: system → comma-separated intervention labels
    intervention_map: dict[str, str] = {}
    if interventions:
        for inv in interventions:
            sys = inv.get("system", "")
            items = inv.get("interventions") or []
            if isinstance(items, list):
                label = ", ".join(str(i) for i in items)
            else:
                label = str(items)
            if sys and label:
                # Append if multiple intervention records per system
                if sys in intervention_map:
                    intervention_map[sys] += f"; {label}"
                else:
                    intervention_map[sys] = label

    all_systems = set(list(baseline_scores.keys()) + list(followup_scores.keys()))
    # Maintain canonical order
    ordered = [s for s in SYSTEMS if s in all_systems] + [
        s for s in sorted(all_systems) if s not in SYSTEMS
    ]

    results = []
    for system in ordered:
        baseline = baseline_scores.get(system)
        followup = followup_scores.get(system)

        if baseline is None and followup is None:
            continue

        b = float(baseline) if baseline is not None else float(followup)  # type: ignore[arg-type]
        f = float(followup) if followup is not None else float(baseline)  # type: ignore[arg-type]
        delta = round(f - b, 1)

        results.append(
            {
                "system": system,
                "baseline": round(b),
                "followup": round(f),
                "delta": delta,
                "delta_pct": round((delta / b * 100) if b else 0, 1),
                "status": _status(delta),
                "interpretation": _interpret(delta, system),
                "intervention": intervention_map.get(system),
            }
        )

    return results


def comparison_summary(comparison_rows: list[dict]) -> dict:
    """Return aggregate stats across all systems."""
    if not comparison_rows:
        return {"overall_status": "no_data", "improved": 0, "same": 0, "worse": 0}
    improved = sum(1 for r in comparison_rows if r["status"] == "improved")
    worse = sum(1 for r in comparison_rows if r["status"] == "worse")
    same = len(comparison_rows) - improved - worse
    avg_delta = round(sum(r["delta"] for r in comparison_rows) / len(comparison_rows), 1)
    if improved > worse:
        overall = "net_improvement"
    elif worse > improved:
        overall = "net_decline"
    else:
        overall = "mixed"
    return {
        "overall_status": overall,
        "improved": improved,
        "same": same,
        "worse": worse,
        "avg_delta": avg_delta,
        "systems_total": len(comparison_rows),
    }
