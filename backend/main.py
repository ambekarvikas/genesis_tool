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


INSIGHT_RULES = [
    {
        "system": "Energy",
        "predicate": lambda score: score < 50,
        "issue": "Low mitochondrial function",
        "impact": "Reduced ATP production may increase fatigue and slower recovery.",
        "action": ["CoQ10", "Sleep optimization"],
    },
    {
        "system": "Inflammation",
        "predicate": lambda score: score > 65,
        "issue": "Chronic inflammation tendency",
        "impact": "Persistent inflammatory signaling may increase tissue stress and recovery burden.",
        "action": ["Omega-3", "Anti-inflammatory diet"],
    },
    {
        "system": "Brain",
        "predicate": lambda score: score < 45,
        "issue": "Neurological pathway suppression",
        "impact": "Neurotransmission and cognitive resilience pathways appear reduced.",
        "action": ["Stress load reduction", "Sleep consistency"],
    },
    {
        "system": "Detox",
        "predicate": lambda score: score < 45,
        "issue": "Detoxification pathway weakness",
        "impact": "Lower xenobiotic and redox pathway activity may reduce metabolic clearance resilience.",
        "action": ["Hydration", "Micronutrient support"],
    },
]


IMPACT_TRANSLATION_RULES = [
    {
        "keywords": ["D_AMINO", "GABA", "GLUTAM", "SEROTON", "DOPAMIN", "NEURO"],
        "clinical_label": "Neurotransmitter balance",
        "impact": "Neurochemical signaling may be less stable, contributing to low mood, focus variability, or stress intolerance.",
        "actions": ["Sleep consistency (7-8h)", "Protein timing across meals", "Stress load reduction plan"],
        "focus_area": "Stabilize neurotransmitter balance",
    },
    {
        "keywords": ["SULFUR", "GLUTATHIONE", "XENOBIOTIC", "CYTOCHROME"],
        "clinical_label": "Detox function",
        "impact": "Detox efficiency may be reduced, increasing risk of sluggish recovery and toxin handling burden.",
        "actions": ["Hydration target 2-2.5L/day", "Cruciferous vegetables daily", "Review environmental toxin load"],
        "focus_area": "Improve detoxification resilience",
    },
    {
        "keywords": ["STARCH", "SUCROSE", "GLYCOLYSIS", "DIABETES", "FRUCTOSE", "GALACTOSE"],
        "clinical_label": "Glucose regulation",
        "impact": "Glucose handling pathways look stressed, which may contribute to energy crashes and cravings.",
        "actions": ["Post-meal walks (10-15 min)", "Prioritize fiber + protein at meals", "Reduce refined sugar intake"],
        "focus_area": "Improve glycemic stability",
    },
    {
        "keywords": ["FATTY_ACID", "MITOCHON", "TCA", "AMPK", "THERMOGENESIS"],
        "clinical_label": "Mitochondrial energy production",
        "impact": "Cellular energy output may be reduced, increasing fatigue and slower physical recovery.",
        "actions": ["CoQ10 100-200 mg/day", "Progressive resistance training 3x/week", "Sleep window regularization"],
        "focus_area": "Restore mitochondrial performance",
    },
    {
        "keywords": ["INFLAM", "TNF", "CYTOKINE", "ASTHMA"],
        "clinical_label": "Inflammatory load control",
        "impact": "Inflammation signaling may remain elevated, increasing symptom burden and delaying tissue repair.",
        "actions": ["Omega-3 rich nutrition", "Anti-inflammatory meal pattern", "Check stress + sleep debt"],
        "focus_area": "Lower inflammatory burden",
    },
]


SYSTEM_FOCUS_AREAS = {
    "Energy": "Improve mitochondrial function and daily energy stability",
    "Inflammation": "Reduce chronic inflammatory burden",
    "Detox": "Strengthen detoxification and redox support",
    "Brain": "Support cognitive resilience and neurotransmission",
    "Recovery": "Enhance repair, hormonal, and training recovery",
}


def _priority_label(score: float) -> str:
    if score < 35:
        return "Critical"
    if score < 40:
        return "High"
    if score <= 55:
        return "Moderate"
    return "Low"


def _confidence_label(n_genes: int | None) -> str:
    genes = int(n_genes or 0)
    if genes >= 30:
        return "High"
    if genes >= 10:
        return "Medium"
    return "Low"


def _severity_and_urgency(score: float, high_is_bad: bool = False) -> tuple[str, str]:
    if high_is_bad:
        if score >= 75:
            return "Critical", "Immediate"
        if score >= 65:
            return "High", "High"
        if score >= 55:
            return "Moderate", "Medium"
        return "Low", "Low"

    if score <= 35:
        return "Critical", "Immediate"
    if score <= 42:
        return "High", "High"
    if score <= 50:
        return "Moderate", "Medium"
    return "Low", "Low"


def _translate_pathway(pathway_name: str, fallback_system: str) -> dict:
    normalized = pathway_name.upper()
    for rule in IMPACT_TRANSLATION_RULES:
        if any(keyword in normalized for keyword in rule["keywords"]):
            return {
                "clinical_label": rule["clinical_label"],
                "impact": rule["impact"],
                "actions": rule["actions"],
                "focus_area": rule["focus_area"],
            }

    default_label = f"{fallback_system} system resilience"
    return {
        "clinical_label": default_label,
        "impact": "System-level pathway activity suggests reduced resilience that may increase day-to-day symptom variability.",
        "actions": ["Correlate with symptoms", "Reassess nutrition/sleep/training load", "Repeat panel in follow-up"],
        "focus_area": SYSTEM_FOCUS_AREAS.get(fallback_system, "Improve overall metabolic resilience"),
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

    normalized = pd.DataFrame(
        {
            "gene_symbol": df[gene_col].astype(str).str.strip().str.upper(),
            "expression_value": pd.to_numeric(df[expr_col], errors="coerce"),
        }
    )
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
        categories.append(
            {
                "category": cat,
                "avg_score": avg,
                "pathway_count": len(rows),
                "matched_count": len(scored),
                "pathways": sorted(rows, key=lambda r: r["score"], reverse=True),
            }
        )
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


def _build_rule_insights(system_scores: dict[str, int], pathways: list[dict]) -> list[dict]:
    insights: list[dict] = []

    for rule in INSIGHT_RULES:
        score = system_scores.get(rule["system"], 50)
        if not rule["predicate"](score):
            continue
        severity, urgency = _severity_and_urgency(score, high_is_bad=(rule["system"] == "Inflammation"))
        insights.append(
            {
                "issue": rule["issue"],
                "impact": rule["impact"],
                "action": rule["action"],
                "priority": _priority_label(score),
                "system": rule["system"],
                "score": score,
                "severity": severity,
                "urgency": urgency,
                "confidence": "System",
                "clinical_label": rule["issue"],
                "recommended_actions": rule["action"],
                "focus_area": SYSTEM_FOCUS_AREAS.get(rule["system"], "Improve system resilience"),
            }
        )

    low_pathways = [row for row in pathways if row.get("n_genes", 0) and row.get("score", 50) < 40]
    low_pathways = sorted(low_pathways, key=lambda row: row.get("score", 50))[:3]
    for row in low_pathways:
        system = SYSTEM_BY_CATEGORY.get(row.get("category") or "", "Recovery")
        translation = _translate_pathway(str(row.get("pathway") or "Unknown_Pathway"), system)
        severity, urgency = _severity_and_urgency(float(row.get("score", 50)))
        confidence = _confidence_label(int(row.get("n_genes") or 0))
        insights.append(
            {
                "issue": f"{translation['clinical_label']} strain",
                "impact": translation["impact"],
                "action": translation["actions"],
                "priority": severity,
                "system": system,
                "score": row.get("score", 50),
                "severity": severity,
                "urgency": urgency,
                "confidence": confidence,
                "clinical_label": translation["clinical_label"],
                "recommended_actions": translation["actions"],
                "focus_area": translation["focus_area"],
                "pathway": row.get("pathway"),
                "n_genes": row.get("n_genes", 0),
            }
        )

    severity_rank = {"Critical": 0, "High": 1, "Moderate": 2, "Low": 3}
    insights.sort(key=lambda row: (severity_rank.get(row.get("severity") or row.get("priority"), 9), row.get("score", 50)))

    for idx, item in enumerate(insights, start=1):
        item["rank"] = idx
    return insights


def _build_focus_areas(insights: list[dict], systems: dict[str, int]) -> list[dict]:
    areas: list[dict] = []
    seen: set[str] = set()

    for row in insights:
        title = row.get("focus_area") or SYSTEM_FOCUS_AREAS.get(row.get("system", ""), "Improve system resilience")
        if title in seen:
            continue
        seen.add(title)
        areas.append(
            {
                "title": title,
                "reason": row.get("impact"),
                "system": row.get("system"),
                "urgency": row.get("urgency", "Medium"),
            }
        )
        if len(areas) >= 2:
            break

    if len(areas) < 2:
        ordered_systems = sorted(systems.items(), key=lambda item: item[1])
        for system, _score in ordered_systems:
            title = SYSTEM_FOCUS_AREAS.get(system)
            if not title or title in seen:
                continue
            seen.add(title)
            areas.append(
                {
                    "title": title,
                    "reason": f"System score suggests {system.lower()} support should be prioritized in the next 30 days.",
                    "system": system,
                    "urgency": "Medium",
                }
            )
            if len(areas) >= 2:
                break

    return areas


def _get_or_create_pathway(db: Session, row: dict) -> Pathway:
    kegg_id = row.get("kegg_id") or "unknown"
    name = row.get("pathway") or "Unknown_Pathway"
    category = row.get("category") or "UNCATEGORISED"
    system = SYSTEM_BY_CATEGORY.get(category, "Recovery")

    existing = (
        db.query(Pathway)
        .filter(Pathway.kegg_id == kegg_id)
        .filter(Pathway.name == name)
        .first()
    )
    if existing:
        if existing.category != category or existing.system != system:
            existing.category = category
            existing.system = system
        return existing

    pathway = Pathway(
        kegg_id=kegg_id,
        name=name,
        category=category,
        system=system,
        weight=1.0,
    )
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
        db.add(
            PathwayScore(
                report_id=report.id,
                pathway_id=pathway.id,
                score=float(row.get("score", 50)),
                n_genes=int(row.get("n_genes") or 0),
                median_fc=float(row.get("median_fc") or 0.0),
            )
        )

    for item in insights:
        db.add(
            Insight(
                report_id=report.id,
                issue=item["issue"],
                impact=item["impact"],
                action_json=json.dumps(item["action"]),
                priority=item["priority"],
            )
        )

    db.commit()
    db.refresh(report)
    return report


def _ensure_seed_patients(db: Session) -> None:
    if db.query(Patient).count() > 0:
        return
    db.add_all(
        [
            Patient(name="Demo Patient 1", age=35, gender="Female"),
            Patient(name="Demo Patient 2", age=42, gender="Male"),
        ]
    )
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
    return [
        {
            "id": patient.id,
            "name": patient.name,
            "age": patient.age,
            "gender": patient.gender,
        }
        for patient in patients
    ]


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
        history.append(
            {
                "date": report.created_at.isoformat(),
                "systems": {row.system: round(row.score) for row in system_scores},
            }
        )
    return history


@app.post(
    "/analyze",
    responses={
        400: {
            "description": "Bad upload request",
            "content": {
                "application/json": {
                    "example": {"detail": "Unsupported file type. Use .csv, .xlsx, or .xls"}
                }
            },
        }
    },
)
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
        elif filename.endswith(".xlsx") or filename.endswith(".xls"):
            df = pd.read_excel(file.file)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type. Use .csv, .xlsx, or .xls")
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=400, detail=f"Could not read uploaded file: {error}") from error

    normalized_df = _normalize_input_df(df)

    base_scores = calculate_scores(normalized_df.rename(columns={"expression_value": "log2FC"}))
    pathway = generate_pathway(normalized_df)
    pathway_rows = pathway.get("scores", [])
    categories = _group_by_category(pathway_rows)

    systems = _aggregate_system_scores(pathway_rows)
    insight_rows = _build_rule_insights(systems, pathway_rows)
    top_issues = insight_rows[:3]
    focus_areas = _build_focus_areas(insight_rows, systems)

    report = _persist_report(
        db=db,
        patient_id=patient_id,
        systems=systems,
        pathways=pathway_rows,
        insights=insight_rows,
    )

    return {
        "patient_id": patient_id,
        "report_id": report.id,
        "created_at": report.created_at.isoformat(),
        "systems": systems,
        "top_issues": top_issues,
        "insights": insight_rows,
        "focus_areas": focus_areas,
        "pathways": pathway_rows,
        "pathway_genes": pathway.get("gene_details", {}),
        "pathway": {
            "status": pathway.get("status"),
            "code": pathway.get("code"),
            "runner": pathway.get("runner"),
            "output_file": pathway.get("output_file"),
            "genes_output_file": pathway.get("genes_output_file"),
            "categories": categories,
            "scores": pathway_rows,
        },
        "scores": {
            "source_column": base_scores.get("source_column"),
            "rows_total": base_scores.get("rows_total"),
            "rows_used": base_scores.get("rows_used"),
        },
        "meta": {
            "deterministic": True,
            "model_generated_scoring": False,
            "max_target_seconds": 30,
        },
    }
