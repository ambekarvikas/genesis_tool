"""
Pathway Mapping Layer
---------------------
Enriches raw R pathway score rows with human-readable system labels,
clinical impact text, symptoms, and recommended actions sourced from
config/pathway_mapping.json.
"""
from __future__ import annotations

import json
import pathlib
from functools import lru_cache

_CONFIG_DIR = pathlib.Path(__file__).parent.parent / "config"


@lru_cache(maxsize=1)
def _load_mapping() -> dict:
    mapping_file = _CONFIG_DIR / "pathway_mapping.json"
    if not mapping_file.exists():
        return {}
    with mapping_file.open(encoding="utf-8") as fh:
        return json.load(fh)


def _match_pathway(pathway_name: str, mapping: dict) -> dict | None:
    """
    Try exact match first, then case-insensitive substring scan.
    Returns the mapping entry or None.
    """
    if pathway_name in mapping:
        return mapping[pathway_name]

    norm = pathway_name.lower()
    for key, entry in mapping.items():
        if key.lower() in norm or norm in key.lower():
            return entry

    return None


def enrich_pathways(pathway_rows: list[dict]) -> list[dict]:
    """
    Attach `symptoms`, `impact`, `actions` and `label` to each pathway row
    where a match exists in pathway_mapping.json.
    Returns the same list (mutated in-place) for convenience.
    """
    mapping = _load_mapping()
    for row in pathway_rows:
        name = str(row.get("pathway") or "")
        entry = _match_pathway(name, mapping)
        if entry:
            row["mapped_label"] = entry.get("label")
            row["mapped_impact"] = entry.get("impact")
            row["mapped_symptoms"] = entry.get("symptoms", [])
            row["mapped_actions"] = entry.get("actions", [])
        else:
            row["mapped_label"] = None
            row["mapped_impact"] = None
            row["mapped_symptoms"] = []
            row["mapped_actions"] = []
    return pathway_rows


def get_pathway_entry(pathway_name: str) -> dict | None:
    """Lookup a single pathway by name."""
    return _match_pathway(pathway_name, _load_mapping())
