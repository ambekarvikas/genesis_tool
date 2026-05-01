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
from services.mapping import enrich_pathways, get_pathway_entry
from services.rule_engine import evaluate_rules, get_priority, get_severity_and_urgency, calculate_confidence
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

SYSTEM_FOCUS_GOALS = {
    "Energy":       "Improve mitochondrial function and daily energy stability",
    "Inflammation": "Reduce chronic inflammatory burden below baseline threshold",
    "Detox":        "Strengthen detoxification and antioxidant defence",
    "Brain":        "Support cognitive resilience and neurotransmitter balance",
    "Recovery":     "Enhance cellular repair, hormonal balance and training recovery",
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


def _build_insights(system_scores: dict[str, int], pathway_rows: list[dict]) -> list[dict]:
    rule_insights = evaluate_rules(system_scores)
    insights: list[dict] = []
    seen_systems: set[str] = set()

    for row in rule_insights:
        seen_systems.add(row["system"])
        insights.append({
            "issue": row["issue"],
            "impact": row["impact"],
            "symptoms": row.get("symptoms", []),
            "action": row["actions"],
            "recommended_actions": row["actions"],
            "expected_outcome": row.get("expected_outcome", ""),
            "priority": row["priority"],
            "severity": row["severity"],
            "urgency": row["urgency"],
            "confidence": "High",
            "clinical_label": row["issue"],
            "focus_area": SYSTEM_FOCUS_GOALS.get(row["system"], ""),
            "goal": row.get("goal", ""),
            "system": row["system"],
            "score": row["score"],
            "rank": row.get("rank", 99),
            "pathway": None,
            "n_genes": None,
        })

    low_pathways = [r for r in pathway_rows if r.get("n_genes", 0) and r.get("score", 50) < 40]
    low_pathways = sorted(low_pathways, key=lambda r: r.get("score", 50))[:3]

    for row in low_pathways:
        system = SYSTEM_BY_CATEGORY.get(row.get("category") or "", "Recovery")
        entry = get_pathway_entry(str(row.get("pathway") or ""))
        n_genes = int(row.get("n_genes") or 0)
        score = float(row.get("score", 50))
        severity, urgency = get_severity_and_urgency(score)
        confidence = calculate_confidence(n_genes)
        if entry:
            label    = entry.get("label", f"{system} system resilience")
            impact   = entry.get("impact", "Pathway activity suggests reduced system resilience.")
            actions  = entry.get("actions", ["Correlate with symptoms", "Reassess lifestyle factors"])
            symptoms = entry.get("symptoms", [])
        else:
            label    = f"{system} pathway strain"
            impact   = "System-level pathway activity suggests reduced resilience that may increase symptom variability."
            actions  = ["Correlate with symptoms", "Reassess nutrition, sleep and training load"]
            symptoms = []
        target = 55
        goal = f"Improve pathway score from {round(score)} to {target}+"
        insights.append({
            "issue": f"{label} - pathway suppression detected",
            "impact": impact,
            "symptoms": symptoms,
            "action": actions,
            "recommended_actions": actions,
            "expected_outcome": f"Pathway score should recover toward {target}+ with consistent protocol.",
            "priority": get_priority(score),
            "severity": severity,
            "urgency": urgency,
            "confidence": confidence,
            "clinical_label": label,
            "focus_area": SYSTEM_FOCUS_GOALS.get(system, ""),
            "goal": goal,
            "system": system,
            "score": round(score),
            "rank": 99,
            "pathway": row.get("pathway"),
            "n_genes": n_genes,
        })

    _SEVERITY_RANK = {"Critical": 0, "High": 1, "Moderate": 2, "Low": 3}
    insights.sort(key=lambda r: (_SEVERITY_RANK.get(r.get("severity", "Low"), 9), r.get("score", 50)))

    seen: set[str] = set()
    deduped: list[dict] = []
    for item in insights:
        key = f"{item['system']}::{item['issue'][:40]}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    for idx, item in enumerate(deduped, start=1):
        item["rank"] = idx

    return deduped


def _build_focus_areas(insights: list[dict], systems: dict[str, int]) -> list[dict]:
    areas: list[dict] = []
    seen: set[str] = set()

    for row in insights:
        system = row.get("system", "")
        if system in seen:
            continue
        seen.add(system)
        score = systems.get(system, 50)
        high_is_bad = system == "Inflammation"
        target = row.get("target_score") or (
            max(50, score - 15) if high_is_bad else min(75, score + 15)
        )
        goal = row.get("goal") or (
            f"Reduce {system} score from {score} to {target}"
            if high_is_bad
            else f"Increase {system} score from {score} to {target}"
        )
        areas.append({
            "title": SYSTEM_FOCUS_GOALS.get(system, f"Improve {system} resilience"),
            "reason": row.get("impact", ""),
            "system": system,
            "urgency": row.get("urgency", "Medium"),
            "goal": goal,
            "current_score": score,
            "target_score": target,
        })
        if len(areas) >= 3:
            break

    if len(areas) < 2:
        for system, score in sorted(systems.items(), key=lambda x: x[1]):
            if system in seen:
                continue
            seen.add(system)
            high_is_bad = system == "Inflammation"
            target = max(50, score - 10) if high_is_bad else min(70, score + 15)
            areas.append({
                "title": SYSTEM_FOCUS_GOALS.get(system, f"Improve {system} resilience"),
                "reason": f"{system} score is {score}. Sustained lifestyle support is recommended over the next 30 days.",
                "system": system,
                "urgency": "Medium",
                "goal": f"Increase {system} score from {score} to {target}",
                "current_score": score,
                "target_score": target,
            })
            if len(areas) >= 2:
                break

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
    pathway       = generate_pathway(normalized_df)
    pathway_rows  = pathway.get("scores", [])

    enrich_pathways(pathway_rows)

    categories  = _group_by_category(pathway_rows)
    systems     = _aggregate_system_scores(pathway_rows)
    insights    = _build_insights(systems, pathway_rows)
    top_issues  = insights[:3]
    focus_areas = _build_focus_areas(insights, systems)

    report = _persist_report(
        db=db,
        patient_id=patient_id,
        systems=systems,
        pathways=pathway_rows,
        insights=insights,
    )

    return {
        "patient_id":    patient_id,
        "report_id":     report.id,
        "created_at":    report.created_at.isoformat(),
        "systems":       systems,
        "top_issues":    top_issues,
        "insights":      insights,
        "focus_areas":   focus_areas,
        "pathways":      pathway_rows,
        "pathway_genes": pathway.get("gene_details", {}),
        "pathway": {
            "status":            pathway.get("status"),
            "runner":            pathway.get("runner"),
            "output_file":       pathway.get("output_file"),
            "genes_output_file": pathway.get("genes_output_file"),
            "categories":        categories,
            "scores":            pathway_rows,
        },
        "scores": {
            "source_column": base_scores.get("source_column"),
            "rows_total":    base_scores.get("rows_total"),
            "rows_used":     base_scores.get("rows_used"),
        },
    }
