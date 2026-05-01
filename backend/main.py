from __future__ import annotations

import json
from collections import defaultdict
from typing import Annotated

from fastapi import FastAPI, UploadFile, HTTPException, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from pydantic import BaseModel
from sqlalchemy.orm import Session

from services.scoring import calculate_scores
from services.r_integration import generate_pathway
from services.mapping import enrich_pathways
from services.clinical_engine import build_clinical_summary_with_interactions, boost_confidence_from_history
from services.decision_engine import build_decision_output, get_top_issues
from services.trends import interpret_trend, build_summary as build_trend_summary
from db.database import Base, engine, get_db, SessionLocal
from models.entities import Patient, Report, Score, Pathway, PathwayScore, Insight, Intervention, ProtocolPerformance
from services.outcome_validation import (
    validate_outcome,
    get_intervention_history,
    assess_intervention_effectiveness,
    build_adaptive_recommendation,
)
from services.evidence_engine import (
    get_evidence_for_system,
    get_evidence_priority_modifier,
    refresh_protocol_performance,
)
from services.comparison_engine import compare_reports as _compare_reports, comparison_summary

app = FastAPI()


class InterventionCreate(BaseModel):
    patient_id: int
    system: str
    interventions: list[str]
    adherence: str = "unknown"
    notes: str | None = None
    report_id: int | None = None


class PatientCreate(BaseModel):
    name: str
    age: int = 0
    gender: str = "Unknown"


class ReportLabelUpdate(BaseModel):
    report_type: str  # 'baseline' | 'followup'
    label: str | None = None


class OutcomeValidationRequest(BaseModel):
    patient_id: int
    system: str
    previous_score: float
    current_score: float
    expected_min: float = 5.0
    expected_max: float = 25.0

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
    report_type: str = "followup",
    label: str | None = None,
) -> Report:
    report = Report(patient_id=patient_id, report_type=report_type, label=label)
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
    report_type: Annotated[str, Form()] = "followup",
    label: Annotated[str | None, Form()] = None,
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
    clinical_systems, system_interactions, reality_check_flags = build_clinical_summary_with_interactions(
        pathway_rows,
        system_scores,
    )

    prior_reports = (
        db.query(Report)
        .filter(Report.patient_id == patient_id)
        .order_by(Report.created_at.desc())
        .limit(5)
        .all()
    )
    prior_scores: dict[str, int] | None = None
    prior_history: list[dict] = []
    if prior_reports:
        prior_score_rows = db.query(Score).filter(Score.report_id == prior_reports[0].id).all()
        prior_scores = {r.system: round(r.score) for r in prior_score_rows}
        for prior_report in prior_reports:
            score_rows = db.query(Score).filter(Score.report_id == prior_report.id).all()
            for score_row in score_rows:
                prior_history.append(
                    {
                        "system": score_row.system,
                        "priority": "High" if score_row.score < 50 else "Low",
                        "created_at": prior_report.created_at.isoformat(),
                    }
                )

    for item in clinical_systems:
        system = item.get("system")
        item["confidence"] = boost_confidence_from_history(system, prior_history, item.get("confidence", "Medium"))
        effectiveness = assess_intervention_effectiveness(db, patient_id, system)
        item["intervention_effectiveness"] = effectiveness
        item["adaptive_recommendation"] = build_adaptive_recommendation(
            system,
            float(item.get("score") or 0),
            0.75,
            effectiveness,
            system_interactions,
        )

        # --- Evidence layer ---
        raw_actions = item.get("actions", {})
        action_items = []
        if isinstance(raw_actions, dict):
            for cat in ("lifestyle", "nutrition", "clinical"):
                action_items.extend(raw_actions.get(cat) or [])
        elif isinstance(raw_actions, list):
            action_items = raw_actions
        evidence = get_evidence_for_system(db, system, action_items or None)
        item["evidence"] = evidence

        # Evidence-based priority modifier
        ev_modifier = get_evidence_priority_modifier(evidence.get("success_rate_raw"))
        item["evidence_priority_modifier"] = ev_modifier
        if ev_modifier == "boost":
            item["evidence_note"] = (
                f"Evidence supports this protocol: {evidence['success_rate']} success rate "
                f"across {evidence['similar_cases']} similar cases"
            )
        elif ev_modifier == "lower":
            item["evidence_note"] = (
                f"Protocol underperforms historically: {evidence['success_rate']} success rate "
                f"across {evidence['similar_cases']} cases — consider alternative"
            )
        else:
            item["evidence_note"] = None

        # Actual outcome for this system since last report
        actual_outcome = None
        if prior_scores and system in prior_scores:
            delta = (system_scores.get(system) or 0) - prior_scores[system]
            actual_outcome = {
                "previous_score": prior_scores[system],
                "current_score": system_scores.get(system),
                "delta": round(delta, 1),
                "direction": "improved" if delta > 0 else ("declined" if delta < 0 else "unchanged"),
            }
        item["actual_outcome"] = actual_outcome

        # Risk flag: incorporate evidence
        if item.get("confidence") == "Low":
            item["risk_flag"] = "Low confidence — validate with lab biomarkers"
        elif effectiveness.get("recommendation") == "escalate":
            item["risk_flag"] = "Previous protocol underperformed — validate progression with biomarkers and clinical review"
        elif ev_modifier == "lower" and evidence["similar_cases"] >= 5:
            item["risk_flag"] = f"Evidence shows <50% success rate for this protocol ({evidence['similar_cases']} cases) — consider escalation"
        else:
            item["risk_flag"] = None

    insights = _systems_to_insights(clinical_systems)
    top_issues = insights[:3]
    focus_areas = _build_focus_areas(clinical_systems, system_scores)
    system_reasons = {s.get("system"): s.get("reason", {}) for s in clinical_systems}
    decision_ranked = build_decision_output(system_scores, system_reasons)
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
                "risk_flag": row.get("risk_flag"),
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
        report_type=report_type,
        label=label,
    )

    return {
        "patient_id": patient_id,
        "report_id": report.id,
        "report_type": report.report_type,
        "label": report.label,
        "created_at": report.created_at.isoformat(),
        "summary": summary,
        "systems": clinical_systems,
        "system_scores": system_scores,
        "top_issues": top_issues,
        "decision": decision_ranked,
        "trends": trends,
        "insights": insights,
        "focus_areas": focus_areas,
        "system_interactions": system_interactions,
        "reality_check_flags": reality_check_flags,
        "pathways": pathway_rows,
        "pathway_genes": pathway.get("gene_details", {}),
        "pathway": {
            "status": pathway.get("status"),
            "runner": pathway.get("runner"),
            "categories": categories,
        },
        "scores": {
            "source_column": base_scores.get("source_column"),
            "rows_total": base_scores.get("rows_total"),
            "rows_used": base_scores.get("rows_used"),
        },
    }


@app.post("/evidence/refresh")
def refresh_evidence(
    db: Annotated[Session, Depends(get_db)],
):
    """
    Recompute protocol performance statistics from all stored intervention
    + outcome data and upsert into protocol_performance table.

    Call after recording new interventions or when evidence feels stale.
    """
    written = refresh_protocol_performance(db)
    return {"status": "ok", "protocols_updated": written}


@app.get("/evidence/{system}")
def get_system_evidence(
    system: str,
    db: Annotated[Session, Depends(get_db)],
):
    """
    Return aggregated evidence for a system across all patients.

    Returns:
        {
            "system": str,
            "similar_cases": int,
            "avg_improvement": str,
            "success_rate": str,
            "evidence_quality": "Strong" | "Moderate" | "Limited" | "None",
            "best_protocol": str | None,
            "worst_protocol": str | None
        }
    """
    evidence = get_evidence_for_system(db, system)
    return {"system": system, **evidence}


@app.post("/interventions")
def record_intervention(
    payload: InterventionCreate,
    db: Annotated[Session, Depends(get_db)],
):
    """Record a clinical intervention and track adherence."""
    patient = db.query(Patient).filter(Patient.id == payload.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient {payload.patient_id} not found")

    intervention = Intervention(
        patient_id=payload.patient_id,
        report_id=payload.report_id,
        system=payload.system,
        interventions=payload.interventions,
        adherence=payload.adherence,
        notes=payload.notes,
    )
    db.add(intervention)
    db.commit()
    db.refresh(intervention)

    return {
        "intervention_id": intervention.id,
        "patient_id": intervention.patient_id,
        "system": intervention.system,
        "interventions": intervention.interventions,
        "adherence": intervention.adherence,
        "created_at": intervention.created_at.isoformat(),
    }

@app.get("/patient/{patient_id}/interventions/{system}")
def get_system_interventions(
    patient_id: int,
    system: str,
    db: Annotated[Session, Depends(get_db)],
    limit: int = 10,
):
    """Get intervention history and effectiveness for a patient system."""
    history = get_intervention_history(db, patient_id, system, limit)
    effectiveness = assess_intervention_effectiveness(db, patient_id, system)

    return {
        "patient_id": patient_id,
        "system": system,
        "history": [
            {
                "created_at": h["created_at"].isoformat(),
                "interventions": h["interventions"],
                "adherence": h["adherence"],
                "outcome_delta": h["outcome_delta"],
            }
            for h in history
        ],
        "effectiveness": effectiveness,
    }

@app.post("/validate-outcome")
def validate_clinical_outcome(
    payload: OutcomeValidationRequest,
    db: Annotated[Session, Depends(get_db)],
):
    """Validate whether observed clinical change matched the expected range."""
    outcome = validate_outcome(
        payload.previous_score,
        payload.current_score,
        {"min": payload.expected_min, "max": payload.expected_max},
    )

    effectiveness = assess_intervention_effectiveness(db, payload.patient_id, payload.system)
    adaptive_rec = build_adaptive_recommendation(
        payload.system,
        payload.current_score,
        0.75,
        effectiveness,
    )

    return {
        **outcome,
        "effectiveness": effectiveness,
        "adaptive_recommendation": adaptive_rec,
        "risk_flag": "Low confidence — validate with lab biomarkers" if outcome.get("status") == "below" else None,
    }


# ── Patient management ────────────────────────────────────────────────────────

@app.post("/patients", status_code=201)
def create_patient(
    payload: PatientCreate,
    db: Annotated[Session, Depends(get_db)],
):
    """Create a new patient record."""
    patient = Patient(name=payload.name, age=payload.age, gender=payload.gender)
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return {"id": patient.id, "name": patient.name, "age": patient.age, "gender": patient.gender}


@app.get("/patient/{patient_id}/reports")
def list_patient_reports(
    patient_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    """List all reports for a patient, newest first, with system scores."""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    reports = (
        db.query(Report)
        .filter(Report.patient_id == patient_id)
        .order_by(Report.created_at.desc())
        .all()
    )
    result = []
    for r in reports:
        scores = db.query(Score).filter(Score.report_id == r.id).all()
        result.append(
            {
                "id": r.id,
                "report_type": r.report_type,
                "label": r.label,
                "created_at": r.created_at.isoformat(),
                "system_scores": {s.system: round(s.score) for s in scores},
            }
        )
    return {"patient_id": patient_id, "reports": result}


@app.patch("/reports/{report_id}/type")
def set_report_type(
    report_id: int,
    payload: ReportLabelUpdate,
    db: Annotated[Session, Depends(get_db)],
):
    """Mark a report as 'baseline' or 'followup' and optionally set a label."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if payload.report_type not in ("baseline", "followup"):
        raise HTTPException(status_code=400, detail="report_type must be 'baseline' or 'followup'")
    report.report_type = payload.report_type
    if payload.label is not None:
        report.label = payload.label
    db.commit()
    return {"id": report.id, "report_type": report.report_type, "label": report.label}


# ── Comparison engine ─────────────────────────────────────────────────────────

@app.get("/patient/{patient_id}/compare")
def compare_patient_reports(
    patient_id: int,
    db: Annotated[Session, Depends(get_db)],
    baseline_report_id: int | None = None,
    followup_report_id: int | None = None,
):
    """
    Compare two reports for a patient.

    - If both IDs are provided, compare those specific reports.
    - If only one ID is provided, use it as baseline and the latest other report as followup.
    - If neither is provided, auto-select: oldest report = baseline, newest = followup.

    Returns per-system delta, status ('improved'/'worse'/'same'), and human
    interpretation, plus any recorded interventions between the two reports.

    Example:
        GET /patient/1/compare  →  "Detox improved by +16 after NAC"
    """
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    all_reports = (
        db.query(Report)
        .filter(Report.patient_id == patient_id)
        .order_by(Report.created_at.asc())
        .all()
    )
    if len(all_reports) < 2:
        raise HTTPException(
            status_code=400,
            detail="At least 2 reports required to compare. Upload a baseline and a follow-up report.",
        )

    # Resolve which reports to compare
    def _get_report(rid: int) -> Report:
        r = db.query(Report).filter(Report.id == rid, Report.patient_id == patient_id).first()
        if not r:
            raise HTTPException(status_code=404, detail=f"Report {rid} not found for this patient")
        return r

    if baseline_report_id and followup_report_id:
        baseline_r = _get_report(baseline_report_id)
        followup_r = _get_report(followup_report_id)
    elif baseline_report_id:
        baseline_r = _get_report(baseline_report_id)
        others = [r for r in all_reports if r.id != baseline_report_id]
        followup_r = max(others, key=lambda r: r.created_at)
    else:
        # Auto: first = baseline, last = followup
        baseline_r = all_reports[0]
        followup_r = all_reports[-1]

    # Fetch scores
    def _scores(report: Report) -> dict[str, float]:
        rows = db.query(Score).filter(Score.report_id == report.id).all()
        return {row.system: row.score for row in rows}

    baseline_scores = _scores(baseline_r)
    followup_scores = _scores(followup_r)

    # Fetch interventions recorded between the two reports
    t_start = min(baseline_r.created_at, followup_r.created_at)
    t_end = max(baseline_r.created_at, followup_r.created_at)
    interventions = (
        db.query(Intervention)
        .filter(
            Intervention.patient_id == patient_id,
            Intervention.created_at >= t_start,
            Intervention.created_at <= t_end,
        )
        .order_by(Intervention.created_at.asc())
        .all()
    )
    inv_dicts = [
        {
            "id": i.id,
            "system": i.system,
            "interventions": i.interventions,
            "adherence": i.adherence,
            "notes": i.notes,
            "created_at": i.created_at.isoformat(),
        }
        for i in interventions
    ]

    comparison_rows = _compare_reports(baseline_scores, followup_scores, inv_dicts)
    summary = comparison_summary(comparison_rows)

    return {
        "patient_id": patient_id,
        "patient_name": patient.name,
        "baseline": {
            "report_id": baseline_r.id,
            "report_type": baseline_r.report_type,
            "label": baseline_r.label,
            "date": baseline_r.created_at.isoformat(),
        },
        "followup": {
            "report_id": followup_r.id,
            "report_type": followup_r.report_type,
            "label": followup_r.label,
            "date": followup_r.created_at.isoformat(),
        },
        "summary": summary,
        "systems": comparison_rows,
        "interventions": inv_dicts,
    }

