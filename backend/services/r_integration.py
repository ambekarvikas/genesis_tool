import subprocess
import shutil
from pathlib import Path

import pandas as pd

RSCRIPT_WINDOWS_EXE = "Rscript.exe"
RSCRIPT_COMMANDS = ("Rscript", RSCRIPT_WINDOWS_EXE)


def _resolve_rscript_path() -> str | None:
    from os import environ

    rscript_from_env = environ.get("RSCRIPT_PATH")
    if rscript_from_env and Path(rscript_from_env).exists():
        return rscript_from_env

    for command in RSCRIPT_COMMANDS:
        resolved = shutil.which(command)
        if resolved:
            return resolved

    common_paths = [
        Path("C:/Program Files/R"),
        Path("C:/Program Files (x86)/R"),
    ]

    candidates: list[Path] = []
    for root in common_paths:
        if not root.exists():
            continue

        version_dirs = sorted(
            [child for child in root.iterdir() if child.is_dir() and child.name.lower().startswith("r-")],
            reverse=True,
        )
        for version_dir in version_dirs:
            candidates.append(version_dir / "bin" / RSCRIPT_WINDOWS_EXE)
            candidates.append(version_dir / "bin" / "x64" / RSCRIPT_WINDOWS_EXE)

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    return None


def _read_pathway_scores(output_file: Path) -> list[dict]:
    if not output_file.exists():
        return []

    try:
        pathway_df = pd.read_csv(output_file)
    except Exception:
        return []

    records: list[dict] = []
    for row in pathway_df.to_dict(orient="records"):
        records.append(
            {
                "pathway":   row.get("pathway"),
                "category":  row.get("category"),
                "kegg_id":   row.get("kegg_id"),
                "score":     int(row["score"]) if pd.notna(row.get("score")) else 50,
                "n_genes":   int(row["n_genes"]) if "n_genes" in row and pd.notna(row["n_genes"]) else None,
                "median_fc": float(round(row["median_fc"], 4)) if "median_fc" in row and pd.notna(row["median_fc"]) else None,
            }
        )

    return records


def _read_pathway_gene_details(genes_output_file: Path) -> dict[str, list[dict]]:
    if not genes_output_file.exists():
        return {}

    try:
        genes_df = pd.read_csv(genes_output_file)
    except Exception:
        return {}

    details: dict[str, list[dict]] = {}
    for row in genes_df.to_dict(orient="records"):
        kegg_id = str(row.get("kegg_id") or "")
        if not kegg_id:
            continue
        details.setdefault(kegg_id, []).append(
            {
                "gene_symbol": row.get("gene_symbol"),
                "expression_value": float(round(row["expression_value"], 4))
                if pd.notna(row.get("expression_value"))
                else None,
            }
        )

    return details


def generate_pathway(df: pd.DataFrame):
    rscript_path = _resolve_rscript_path()
    script_path = Path(__file__).resolve().parents[2] / "r-service" / "generate_pathway.R"
    workspace_root = script_path.parents[1]
    input_file = workspace_root / "data" / "uploaded_gene_data.csv"
    output_file = workspace_root / "data" / "pathway_scores.csv"
    genes_output_file = workspace_root / "data" / "pathway_gene_details.csv"
    cache_dir   = workspace_root / "data" / "kegg_cache"

    if rscript_path is None:
        return {
            "status": "skipped",
            "scores": [],
        }

    input_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(input_file, index=False)

    try:
        result = subprocess.run(
            [rscript_path, str(script_path), str(input_file), str(output_file), str(cache_dir), str(genes_output_file)],
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
            cwd=str(workspace_root),
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"R script exited with code {result.returncode}. "
                f"stderr: {result.stderr.strip()[:500]}"
            )

        pathway_scores = _read_pathway_scores(output_file)
        pathway_gene_details = _read_pathway_gene_details(genes_output_file)
        return {
            "status": "ok",
            "runner": rscript_path,
            "scores": pathway_scores,
            "gene_details": pathway_gene_details,
        }
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("R script timed out after 120 seconds.") from exc
    except FileNotFoundError:
        return {
            "status": "skipped",
            "scores": [],
        }
