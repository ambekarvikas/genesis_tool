import pandas as pd


def _find_expression_column(df: pd.DataFrame) -> str | None:
    normalized = {str(column).strip().lower(): column for column in df.columns}
    preferred_names = [
        "expression",
        "expr",
        "logfc",
        "log2fc",
        "fold_change",
        "foldchange",
        "value",
        "score",
    ]

    for name in preferred_names:
        if name in normalized:
            return normalized[name]

    numeric_columns = df.select_dtypes(include="number").columns.tolist()
    return numeric_columns[0] if numeric_columns else None


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def calculate_scores(df: pd.DataFrame):
    source_column = _find_expression_column(df)
    if source_column is None:
        return {
            "Energy": 0,
            "Recovery": 0,
            "Inflammation": 0,
            "note": "No numeric expression-like column found",
        }

    values = pd.to_numeric(df[source_column], errors="coerce").dropna()
    if values.empty:
        return {
            "Energy": 0,
            "Recovery": 0,
            "Inflammation": 0,
            "note": f"Column '{source_column}' has no usable numeric values",
            "source_column": str(source_column),
            "rows_total": int(len(df.index)),
            "rows_used": 0,
        }

    avg = float(values.mean())
    avg_abs = float(values.abs().mean())
    up_ratio = float((values > 0).mean())

    deg_like_columns = {"logfc", "log2fc", "fold_change", "foldchange"}
    is_deg_like = str(source_column).strip().lower() in deg_like_columns

    if is_deg_like:
        magnitude_norm = _clamp01(avg_abs / 2.5)
        up_norm = _clamp01(up_ratio)
        down_norm = 1.0 - up_norm

        energy = int(_clamp01((0.65 * magnitude_norm) + (0.35 * up_norm)) * 100)
        recovery = int(_clamp01((0.60 * (1.0 - magnitude_norm)) + (0.40 * (1.0 - abs(up_norm - 0.5) * 2.0))) * 100)
        inflammation = int(_clamp01((0.70 * magnitude_norm) + (0.30 * down_norm)) * 100)
    else:
        centered = _clamp01((avg + 1.5) / 3.0)
        magnitude_norm = _clamp01(avg_abs / 2.0)

        energy = int(_clamp01((0.55 * centered) + (0.45 * magnitude_norm)) * 100)
        recovery = int(_clamp01((0.65 * (1.0 - magnitude_norm)) + (0.35 * centered)) * 100)
        inflammation = int(_clamp01((0.60 * magnitude_norm) + (0.40 * (1.0 - centered))) * 100)

    return {
        "Energy": energy,
        "Recovery": recovery,
        "Inflammation": inflammation,
        "source_column": str(source_column),
        "rows_total": int(len(df.index)),
        "rows_used": int(len(values.index)),
        "mean": round(avg, 6),
        "mean_abs": round(avg_abs, 6),
        "positive_ratio": round(up_ratio, 6),
    }


def merge_pathway_scores(base_scores: dict, pathway_scores: list[dict]) -> dict:
    merged_scores = dict(base_scores)

    for item in pathway_scores:
        pathway_name = str(item.get("pathway", "")).strip().lower()
        score_value = item.get("score")
        if score_value is None:
            continue

        try:
            normalized_score = max(0, min(100, int(float(score_value))))
        except (TypeError, ValueError):
            continue

        if pathway_name == "energy":
            merged_scores["Energy"] = normalized_score
        elif pathway_name == "recovery":
            merged_scores["Recovery"] = normalized_score
        elif pathway_name == "inflammation":
            merged_scores["Inflammation"] = normalized_score

    return merged_scores
