from __future__ import annotations

import json
from collections import defaultdict
from typing import Annotated

from fastapi import FastAPI, UploadFile, HTTPException, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from sqlalchemy.orm import Session

from services.scoring import calculate_scores
from services.r_integration import generate_pathway
from services.mapping import enrich_pathways
from services.clinical_engine import build_clinical_summary, build_overall_summary
from services.decision_engine import build_decision_output, get_top_issues
from services.trends import interpret_trend, build_summary as build_trend_summary
from db.database import Base, engine, get_db, SessionLocal
from models.entities import Patient, Report, Score, Pathway, PathwayScore, Insight

app = FastAPI()

SYSTEM_BY_CATEGORY = {
    "CARBOHYDRATES": "Energy",
    "FATS": "Energy",
    "LONGEVITY_PATHWAY": "Recovery",
    "MUSCLE": "Recovery",
    "HORMONES": "Recovery",
    "AQUAPORIN": "Recovery",
    "AMINO_ACIDS": "Detox",
    "DIGESTIVE_SYSTEM": "Detox",
    "MINERALS_ELECTROLYTES_VITAMINS": "Detox",
    "BRAIN": "Brain",
    "ADDICTIONS": "Brain",
    "ASTHMA": "Inflammation",
    "PROSTATE_CANCER": "Inflammation",
}

def _normalize_input_df(df: pd.DataFrame) -> pd.DataFrame:
    col_map = {col.lower(): col for col in df.columns}
    gene_col = None
    for candidate in ["gene_symbol", "genesymbol", "gene", "symbol", "hugo_symbol"]:
        if candidate in col_map:
            gene_col = col_map[candidate]
            break
    if gene_col is None:
        gene_col = df.columns[0]
    expr_col = None
    for candidate in ["expression_value", "log2fc", "logfc", "expression", "value", "score"]:
        if candidate in col_map:
            expr_col = col_map[candidate]
            break
    if expr_col is None:
        numeric_cols = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]
        if not numeric_cols:
            raise HTTPException(status_code=400, detail="Could not detect expression_value numeric column")
        expr_col = numeric_cols[0]
    normalized = pd.DataFrame({
        "gene_symbol": df[gene_col].astype(str).str.strip().str.upper(),
        "expression_value": pd.to_numeric(df[expr_col], errors="coerce"),
    })
    normalized = normalized.dropna(subset=["gene_symbol", "expression_value"])
    if normalized.empty:
        raise HTTPException(status_code=400, detail="No usable gene_symbol/expression_value rows found")
    return normalized


def _group_by_category(pw_scores: list[dict]) -> list[dict]:
    buckets: dict[str, list[dict]] = defaultdict(list)
    for row in pw_scores:
        cat = row.get("category") or "UNCATEGORISED"
        buckets[cat].append(row)
    categories = []
    for cat, rows in sorted(buckets.items()):
        scored = [r for r in rows if r.get("n_genes", 0) and r["n_genes"] > 0]
        avg = round(sum(r["score"] for r in scored) / len(scored)) if scored else 50
        categories.append({
            "category": cat,
            "avg_score": avg,
            "pathway_count": len(rows),
            "matched_count": len(scored),
            "pathways": sorted(rows, key=lambda r: r["score"], reverse=True),
        })
    return categories


def _aggregate_system_scores(pathway_rows: list[dict]) -> dict[str, int]:
    weighted: dict[str, float] = defaultdict(float)
    weight_sum: dict[str, float] = defaultdict(float)
    for row in pathway_rows:
        category = row.get("category") or "UNCATEGORISED"
        system = SYSTEM_BY_CATEGORY.get(category, "Recovery")
        row["system"] = system
        n_genes = row.get("n_genes") or 0
        if n_genes <= 0:
            continue
        pathway_weight = float(row.get("weight") or 1.0)
        effective_weight = pathway_weight * max(1, n_genes)
        weighted[system] += float(row.get("score", 50)) * effective_weight
        weight_sum[system] += effective_weight
    systems = {}
    for system in ["Energy", "Inflammation", "Detox", "Brain", "Recovery"]:
        if weight_sum[system] > 0:
            systems[system] = round(weighted[system] / weight_sum[system])
        else:
            systems[system] = 50
    return systems


def _flatten_actions(actions) -> list:
    """Flatten structured {lifestyle,nutrition,clinical} or pass-through flat list."""
    if isinstance(actions, dict):
        flat = []
        for category in ("lifestyle", "nutrition", "clinical"):
            flat.extend(actions.get(category) or [])
        return flat
    return actions if isinstance(actions, list) else []


def _systems_to_insights(clinical_systems: list[dict]) -> list[dict]:
    insights: list[dict] = []
    for item in clinical_systems:
        raw_actions = item.get("actions", {})
        flat_actions = _flatten_actions(raw_actions)
        insights.append(
            {
                "issue": item.get("issue"),
                "impact": item.get("impact") or item.get("issue"),
                "symptoms": item.get("symptoms", []),
                "action": flat_actions,
                "recommended_actions": flat_actions,
                "actions_structured": raw_actions if isinstance(raw_actions, dict) else {},
                "expected_outcome": item.get("expected_outcome", ""),
                "priority": item.get("priority", "Moderate"),
                "severity": item.get("severity", item.get("priority", "Moderate")),
                "urgency": item.get("urgency", "Medium"),
                "confidence": item.get("confidence", "Medium"),
                "clinical_label": item.get("label") or item.get("system"),
                "focus_area": item.get("goal") or f"Improve {item.get('system')} function",
                "goal": item.get("goal"),
                "system": item.get("system"),
                "score": item.get("score"),
                "rank": item.get("rank"),
                "trend": item.get("trend"),
                "outcome_prediction": item.get("outcome_prediction"),
                "pathway": None,
                "n_genes": item.get("reason", {}).get("n_genes"),
            }
        )
    return insights


def _build_focus_areas(clinical_systems: list[dict], system_scores: dict[str, int]) -> list[dict]:
    areas: list[dict] = []
    for row in clinical_systems[:3]:
        system = row.get("system", "")
        areas.append(
            {
                "title": row.get("label", f"{system} Function"),
                "reason": row.get("issue", ""),
                "system": system,
                "urgency": row.get("urgency", "Medium"),
                "goal": row.get("goal") or f"Improve {system} function",
                "current_score": row.get("score", system_scores.get(system, 50)),
                "target_score": None,
            }
        )

    return areas


def _get_or_create_pathway(db: Session, row: dict) -> Pathway:
    kegg_id  = row.get("kegg_id") or "unknown"
    name     = row.get("pathway") or "Unknown_Pathway"
    category = row.get("category") or "UNCATEGORISED"
    system   = SYSTEM_BY_CATEGORY.get(category, "Recovery")
    existing = db.query(Pathway).filter(Pathway.kegg_id == kegg_id, Pathway.name == name).first()
    if existing:
        if existing.category != category or existing.system != system:
            existing.category = category
            existing.system   = system
        return existing
    pathway = Pathway(kegg_id=kegg_id, name=name, category=category, system=system, weight=1.0)
    db.add(pathway)
    db.flush()
    return pathway


def _persist_report(
    db: Session,
    patient_id: int,
    systems: dict[str, int],
    pathways: list[dict],
    insights: list[dict],
) -> Report:
    report = Report(patient_id=patient_id)
    db.add(report)
    db.flush()
    for system, value in systems.items():
        db.add(Score(report_id=report.id, system=system, score=float(value)))
    for row in pathways:
        pathway = _get_or_create_pathway(db, row)
        db.add(PathwayScore(
            report_id=report.id,
            pathway_id=pathway.id,
            score=float(row.get("score", 50)),
            n_genes=int(row.get("n_genes") or 0),
            median_fc=float(row.get("median_fc") or 0.0),
        ))
    for item in insights:
        db.add(Insight(
            report_id=report.id,
            issue=item["issue"],
            impact=item["impact"],
            action_json=json.dumps(item["action"]),
            priority=item["priority"],
        ))
    db.commit()
    db.refresh(report)
    return report


def _ensure_seed_patients(db: Session) -> None:
    if db.query(Patient).count() > 0:
        return
    db.add_all([
        Patient(name="Demo Patient 1", age=35, gender="Female"),
        Patient(name="Demo Patient 2", age=42, gender="Male"),
    ])
    db.commit()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {"status": "running"}


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        _ensure_seed_patients(db)


@app.get("/patients")
def list_patients(db: Annotated[Session, Depends(get_db)]):
    patients = db.query(Patient).order_by(Patient.id.asc()).all()
    return [{"id": p.id, "name": p.name, "age": p.age, "gender": p.gender} for p in patients]


@app.get("/patient/{patient_id}/history")
def patient_history(patient_id: int, db: Annotated[Session, Depends(get_db)]):
    reports = (
        db.query(Report)
        .filter(Report.patient_id == patient_id)
        .order_by(Report.created_at.asc())
        .all()
    )
    history = []
    for report in reports:
        system_scores = db.query(Score).filter(Score.report_id == report.id).all()
        history.append({
            "date": report.created_at.isoformat(),
            "systems": {row.system: round(row.score) for row in system_scores},
        })
    return history

@app.post("/analyze")
async def analyze(
    db: Annotated[Session, Depends(get_db)],
    patient_id: Annotated[int, Form(...)],
    file: UploadFile | None = None,
):
    if file is None:
        raise HTTPException(status_code=400, detail="File is required")
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if patient is None:
        raise HTTPException(status_code=400, detail="Invalid patient_id")
    filename = (file.filename or "").lower()
    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(file.file)
        elif filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(file.file)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type. Use .csv, .xlsx, or .xls")
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=400, detail=f"Could not read uploaded file: {error}") from error

    normalized_df = _normalize_input_df(df)
    base_scores   = calculate_scores(normalized_df.rename(columns={"expression_value": "log2FC"}))
    try:
        pathway = generate_pathway(normalized_df)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    pathway_rows  = pathway.get("scores", [])

    enrich_pathways(pathway_rows)

    categories = _group_by_category(pathway_rows)
    system_scores = _aggregate_system_scores(pathway_rows)
    clinical_systems = build_clinical_summary(pathway_rows, system_scores)
    insights = _systems_to_insights(clinical_systems)
    top_issues = insights[:3]
    focus_areas = _build_focus_areas(clinical_systems, system_scores)

    # Decision engine — ranked system list with priority scores
    system_reasons = {s.get("system"): s.get("reason", {}) for s in clinical_systems}
    decision_ranked = build_decision_output(system_scores, system_reasons)

    # Trend interpretation per system (requires prior history)
    prior_reports = (
        db.query(Report)
        .filter(Report.patient_id == patient_id)
        .order_by(Report.created_at.desc())
        .limit(2)
        .all()
    )
    prior_scores: dict[str, int] | None = None
    if len(prior_reports) >= 1:
        prior_score_rows = db.query(Score).filter(Score.report_id == prior_reports[0].id).all()
        prior_scores = {r.system: round(r.score) for r in prior_score_rows}

    trends = {
        system: interpret_trend(prior_scores.get(system) if prior_scores else None, score)
        for system, score in system_scores.items()
    }

    summary = {
        "overall": build_trend_summary(system_scores),
        "top_issues": [
            {
                "system": row.get("system"),
                "issue": row.get("issue"),
                "priority": row.get("priority"),
                "score": row.get("score"),
            }
            for row in clinical_systems[:3]
        ],
    }

    report = _persist_report(
        db=db,
        patient_id=patient_id,
        systems=system_scores,
        pathways=pathway_rows,
        insights=insights,
    )

    return {
        "patient_id":    patient_id,
        "report_id":     report.id,
        "created_at":    report.created_at.isoformat(),
        "summary":       summary,
        "systems":       clinical_systems,
        "system_scores": system_scores,
        "top_issues":    top_issues,
        "decision":      decision_ranked,
        "trends":        trends,
        "insights":      insights,
        "focus_areas":   focus_areas,
        "pathways":      pathway_rows,
        "pathway_genes": pathway.get("gene_details", {}),
        "pathway": {
            "status":   pathway.get("status"),
            "runner":   pathway.get("runner"),
            "categories": categories,
        },
        "scores": {
            "source_column": base_scores.get("source_column"),
            "rows_total":    base_scores.get("rows_total"),
            "rows_used":     base_scores.get("rows_used"),
        },
    }
