# Genesis: Clinical Genomics Decision Support System

![Status](https://img.shields.io/badge/status-production-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.13-blue)
![FastAPI](https://img.shields.io/badge/fastapi-0.136-green)
![Next.js](https://img.shields.io/badge/next.js-16-black)
![Version](https://img.shields.io/badge/version-7.0-purple)

> Transform raw gene expression data into **adaptive clinical decisions** that learn from what worked — and what didn't.

Genesis converts KEGG pathway scores into deterministic clinical systems (Energy, Inflammation, Detox, Brain, Recovery) with **priority-ranked** issues, **confidence-scored** findings, **outcome predictions**, and now **intervention tracking with adaptive protocol escalation**.

---

## 🎯 What You Get

Instead of:
```
"Low Sulfur Metabolism pathway activity"
```

You get:
```
🔴 CRITICAL: Detox system compromised
├─ Impact: Toxin accumulation → fatigue, headaches
├─ Actions: NAC 600-1200mg/day, cruciferous vegetables daily
├─ Expected: +15-25 point improvement in 6-8 weeks
├─ Observable: Reduced headache frequency, better mental clarity
├─ Confidence: High (12 genes, median FC -0.7)
│
├─ 🔁 ADAPTIVE (v7): Prior protocol showed 0.2 success rate
│   └─ Escalating → Advanced clinical intervention
│   └─ Alternative: Specialist consultation + liver enzyme panel
│
├─ ⚡ INTERACTION: Detox < 40 AND Inflammation > 60
│   └─ Priority shift: Resolve Detox first (upstream issue)
│
└─ ⚠️  RISK FLAG: Low confidence — validate with lab biomarkers
```

---

## ✨ Key Features

### 🧠 Deterministic Decision Engine
- **No AI hallucinations** — all logic is config-driven and auditable
- **Priority scoring** — systems ranked by `(100 - health_score) × log(n_genes) × system_weight`
- **Confidence weighting** — `0.6 × gene_coverage + 0.4 × fold_change_magnitude`

### 🎯 Clinical Intelligence
- **5-system framework**: Energy, Inflammation, Detox, Brain, Recovery
- **4-band severity**: Critical → High → Moderate → Low
- **Per-priority actions**: Lifestyle, nutrition, clinical interventions
- **Outcome predictions**: Expected score delta, timeline, observable signs

### � Adaptive Protocol Engine *(v7)*
- **Intervention tracking** — record what was done and patient adherence
- **Outcome validation** — compare expected vs actual improvement per system
- **Protocol escalation** — if prior interventions underperformed, escalate automatically
- **Confidence boosting** — same issue across 2+ reports → upgrades confidence to High
- **System interaction detection** — detects upstream issues (e.g. Detox driving Inflammation)
- **Risk flags** — per-system flags when biomarker validation is recommended

### 📊 Complete Workflow
1. Upload gene expression file (CSV/XLSX)
2. R-based KEGG pathway scoring
3. System aggregation + clinical interpretation
4. Trend analysis (vs. prior assessment) + system interaction detection
5. Intervention history lookup → adaptive recommendation
6. Priority-ranked decision output with risk flags
7. PDF report generation

---

## 🚀 Quick Start

### Prerequisites
- Python 3.13+
- R with KEGG database access
- Node.js 18+
- MySQL 8.0+

### Installation

```bash
# Clone repo
git clone https://github.com/ambekarvikas/genesis_tool.git
cd genesis_tool

# Backend setup
cd backend
pip install -r requirements.txt

# Frontend setup
cd ../frontend
npm install && npm run build
```

### Run System

```bash
# Terminal 1: API server
cd backend
python -m uvicorn main:app --port 8091

# Terminal 2: Frontend (dev)
cd frontend
npm run dev
```

Visit `http://localhost:3000`

---

## 📋 API Example

### Upload & Analyze

```bash
curl -X POST http://127.0.0.1:8091/analyze \
  -F "patient_id=1" \
  -F "file=@sample_gene_expression.csv"
```

### Response Structure

```json
{
  "summary": {
    "overall": "Detox and Energy systems are underperforming. Prioritize Detox — impaired detoxification is driving systemic inflammation.",
    "top_issues": [
      {
        "system": "Detox",
        "issue": "Severely reduced detox capacity",
        "priority": "Critical",
        "score": 32,
        "risk_flag": "Previous protocol underperformed — validate with biomarkers and clinical review"
      }
    ]
  },
  "systems": [
    {
      "system": "Detox",
      "score": 32,
      "priority": "Critical",
      "issue": "Severely reduced detox capacity",
      "actions": {
        "lifestyle": ["Remove alcohol", "Sauna 2-3x/week"],
        "nutrition": ["NAC 600-1200mg/day", "Cruciferous vegetables daily"],
        "clinical": ["Liver panel: ALT, AST, GGT", "Glutathione test"]
      },
      "outcome_prediction": {
        "expected_change": "+15 to +25",
        "timeline": "6–8 weeks",
        "observable_signs": ["Reduced headache frequency", "Less toxin sensitivity", "Mental clarity"],
        "note": "Critical deficit — lifestyle + clinical intervention required in parallel."
      },
      "confidence": "High",
      "risk_flag": "Previous protocol underperformed — validate progression with biomarkers and clinical review",
      "intervention_effectiveness": {
        "avg_outcome_delta": -2.5,
        "success_rate": 0.2,
        "recommendation": "escalate",
        "failed_interventions": ["NAC", "Sleep optimization"]
      },
      "adaptive_recommendation": {
        "base_action": "Advanced protocol for Detox",
        "escalation": "Previous interventions for Detox underperformed. Shift to advanced clinical intervention.",
        "alternative_protocol": "Consider specialist consultation, advanced markers (glutathione, bile acids, liver enzymes).",
        "interaction_note": "Prioritize Detox pathway first — impaired detoxification drives systemic inflammation"
      }
    }
  ],
  "decision": [
    {"system": "Detox", "score": 32, "priority": "Critical", "priority_score": 12.45, "rank": 1},
    {"system": "Energy", "score": 45, "priority": "High", "priority_score": 8.92, "rank": 2}
  ],
  "trends": {
    "Detox": {
      "status": "Significant decline",
      "interpretation": "-8 points — active deterioration. Review intervention protocol immediately.",
      "delta": -8
    }
  },
  "system_interactions": {
    "priority_shift": "Prioritize Detox pathway first — impaired detoxification drives systemic inflammation",
    "reasoning": "Detox is a prerequisite for resolving secondary inflammation",
    "interdependencies": [["Detox", "Inflammation"]]
  },
  "reality_check_flags": [
    "Low confidence — Detox would benefit from lab biomarker validation (liver enzymes, inflammatory markers)",
    "Multiple critical systems — prioritize sequentially; address foundational issues (Detox/Inflammation) first"
  ]
}
```

---

## 🔁 Adaptive Endpoints *(v7)*

### Record an Intervention

```bash
curl -X POST http://127.0.0.1:8091/interventions \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": 1,
    "system": "Detox",
    "interventions": ["NAC 600mg", "Sleep optimization"],
    "adherence": "partial",
    "report_id": 42
  }'
```

**`adherence` values:** `full` | `partial` | `none` | `unknown`

### Get Intervention History + Effectiveness

```bash
curl http://127.0.0.1:8091/patient/1/interventions/Detox
```

```json
{
  "patient_id": 1,
  "system": "Detox",
  "history": [
    {
      "created_at": "2026-04-01T10:00:00",
      "interventions": ["NAC 600mg", "Sleep optimization"],
      "adherence": "partial",
      "outcome_delta": -3.2
    }
  ],
  "effectiveness": {
    "avg_outcome_delta": -2.5,
    "success_rate": 0.2,
    "recommendation": "escalate",
    "failed_interventions": ["NAC 600mg"]
  }
}
```

### Validate an Outcome

```bash
curl -X POST http://127.0.0.1:8091/validate-outcome \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": 1,
    "system": "Detox",
    "previous_score": 32,
    "current_score": 36,
    "expected_min": 5.0,
    "expected_max": 25.0
  }'
```

```json
{
  "actual_change": 4,
  "expected_range": {"min": 5.0, "max": 25.0},
  "status": "below",
  "interpretation": "Below expected improvement: +4 points (expected >5.0)",
  "effectiveness": {"recommendation": "escalate", "success_rate": 0.2},
  "adaptive_recommendation": {
    "escalation": "Previous interventions for Detox underperformed. Shift to advanced clinical intervention.",
    "alternative_protocol": "Specialist consultation, advanced markers."
  },
  "risk_flag": "Low confidence — validate with lab biomarkers"
}
```

---

## 🏗️ Architecture

### Backend (FastAPI + Python)
- **`services/r_integration.py`** — R subprocess wrapper with timeout + error handling
- **`services/clinical_engine.py`** — band-based system definitions, interaction detection, reality check flags
- **`services/decision_engine.py`** — priority ranking by genomic evidence weight
- **`services/outcome_engine.py`** — system-specific outcome predictions
- **`services/outcome_validation.py`** *(v7)* — validate expected vs actual outcomes, assess effectiveness, build adaptive recommendations
- **`services/trends.py`** — trend interpretation (vs. prior assessment)
- **`services/confidence.py`** — weighted formula: coverage + fold-change, boosted by repeat history
- **`config/system_definitions.json`** — 5 systems × 4 severity bands with actions + outcomes
- **`config/system_actions.json`** — per-priority clinical + nutritional + lifestyle interventions
- **Database** — SQLAlchemy ORM, MySQL (patients, reports, scores, interventions)

### Frontend (Next.js)
- Pages: Patient selection, file upload, results dashboard, report generation
- Components: System score cards, issue prioritization, trend visualization
- Export: PDF report with full clinical narrative

### R Service
- KEGG pathway database integration
- Pathway scoring algorithm
- Gene-pathway matching

---

## 🔬 System Definitions

### Energy Function (System Weight: 1.15)
- **Critical (0-34)**: Mitochondrial output critically suppressed
- **High (35-49)**: Sustained low-grade energy deficit
- **Moderate (50-64)**: Energy pathways below peak
- **Low (65-100)**: System stable

*Each band includes lifestyle/nutrition/clinical actions + expected improvement timeline + observable signs.*

### Inflammation Control (System Weight: 1.25, high_is_worse=true)
- **Critical**: Systemic inflammatory cascade active
- **High**: Persistent low-grade inflammation
- **Moderate**: Not yet disruptive but trending
- **Low**: No significant inflammatory signal

### Detox Function (System Weight: 1.2)
### Neurocognitive Function (System Weight: 1.1)
### Recovery Capacity (System Weight: 1.05)

---

## 🎯 Confidence Scoring

**Formula:**
```
coverage = min(n_genes / 20, 1.0)
effect   = min(abs(median_fc) / 1.0, 1.0)
score    = 0.6 × coverage + 0.4 × effect

High   → score > 0.75
Medium → score > 0.45
Low    → score ≤ 0.45
```

**Translation:**
- **High**: 15+ genes with |FC| > 0.5 (well-supported, actionable)
- **Medium**: 8+ genes with moderate signal
- **Low**: Insufficient genes or small fold-change (validate before action)

---

## 📈 Priority Scoring

Systems are ranked by clinical urgency, not just score:

```
priority_score = (100 - health_score) × system_weight × log(n_genes + 1)
```

**Effect:**
- Systems with NO matched genes score lower than those with 12 genes at same health score
- System weight reflects clinical importance (Inflammation 1.25 > Energy 1.15)
- Logarithmic factor prevents over-weighting of massive gene counts

---

## 🏥 Clinical Decision Format

Every issue is structured for rapid clinician decision-making:

1. **Status**: One-line severity + intervention requirement
2. **Impact**: Pathophysiology explanation (not raw data)
3. **Symptoms**: Observable patient-facing manifestations
4. **Actions**: Structured by category (lifestyle/nutrition/clinical)
5. **Timeline**: When to expect improvement
6. **Observable Signs**: What changes to look for
7. **Confidence**: Genomic evidence quality
8. **Reason**: Gene count + fold-change magnitude

---

## 📊 Example: Detox System (Critical)

**Input:** 12 matched genes, median FC = -0.7  
**Output:**
```
Issue:    Severely reduced detox capacity
Impact:   Phase I/II detox pathways impaired — toxin accumulation
Symptoms: Fatigue, Headaches, Toxin sensitivity

ACTION PLAN:
Lifestyle: Remove alcohol, sauna 2-3x/week, prioritize sleep
Nutrition: NAC 600-1200mg/day, cruciferous daily, hydration 2.5L
Clinical:  Liver panel (ALT/AST/GGT), glutathione test

EXPECTED:
Score → +15 to +25 points
Timeline → 6–8 weeks
Observable → Fewer headaches, less toxin sensitivity, mental clarity

CONFIDENCE: High (12 genes, FC -0.7)
```

---

## 🛡️ Error Handling

- R subprocess timeout → 120-second limit with fallback
- Bad file format → Auto-detect gene_symbol and expression columns
- Missing gene matches → Return confidence "Low", proceed with caution
- Database failures → Graceful degradation, in-memory fallback

---

## 🚀 Deployment

### Docker (Recommended)

```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt
COPY backend/ .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8091"]
```

### Environment Variables

```bash
# .env
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=password
MYSQL_DB=rhino_gene
RSCRIPT_PATH=/usr/bin/Rscript
```

---

## 📖 Documentation

- **API Docs**: `http://localhost:8091/docs` (Swagger UI)
- **Config Reference**: See `backend/config/` directory
- **Clinical Framework**: See system definitions in JSON

---

## 🧪 Testing

```bash
# Syntax validation
cd backend
python -m py_compile main.py services/*.py

# Live API test
curl -X GET http://127.0.0.1:8091/patients

# Analyze with sample file
curl -X POST http://127.0.0.1:8091/analyze \
  -F "patient_id=1" \
  -F "file=@data/sample_gene.csv"

# Record intervention (v7)
curl -X POST http://127.0.0.1:8091/interventions \
  -H "Content-Type: application/json" \
  -d '{"patient_id": 1, "system": "Detox", "interventions": ["NAC"], "adherence": "partial"}'

# Validate outcome (v7)
curl -X POST http://127.0.0.1:8091/validate-outcome \
  -H "Content-Type: application/json" \
  -d '{"patient_id": 1, "system": "Detox", "previous_score": 32, "current_score": 36}'
```

---

## 🎓 Use Cases

### 1. **Functional Medicine**
Rapid assessment of 5 core systems for nutrient/lifestyle prioritization

### 2. **Research**
Publish genomic pathways as clinical decision outputs, not just tables

### 3. **Wellness Programs**
Baseline + quarterly re-assessment with trend interpretation

### 4. **Clinical Genetics**
KEGG pathway scores → actionable patient guidance (no jargon)

### 5. **Athletic Performance**
Energy, Recovery, Brain systems as foundation for training periodization

---

## 🔐 Privacy & Data

- Patient data stored in MySQL (encrypted at rest if configured)
- Gene expression files processed locally, not sent to external services
- Reports generated server-side, no sensitive data in frontend cache
- Audit trail: Every analysis logged with patient_id, timestamp, result hash

---

## 📝 Citation

If you use Genesis in research or clinical practice:

```bibtex
@software{genesis2026,
  title={Genesis: Clinical Genomics Decision Support System},
  author={Vikas Ambekar},
  year={2026},
  url={https://github.com/ambekarvikas/genesis_tool}
}
```

---

## 🤝 Contributing

1. Fork the repo
2. Create feature branch (`git checkout -b feature/your-feature`)
3. Add tests for new logic
4. Ensure config files are in proper JSON format
5. Submit PR with clear description

**Development priorities:**
- Additional system definitions (Thyroid, Metabolic Rate, etc.)
- Machine learning-based optimal action prioritization
- Integration with EHR systems
- Mobile app for patient tracking

---

## ⚖️ License

MIT — Use freely, modify as needed, include this license in derivative works.

---

## ⚠️ Clinical Disclaimer

This system provides clinical decision support, not medical diagnosis. 

**Not a replacement for licensed clinician assessment.**

- All recommendations must be reviewed by qualified healthcare provider
- Genomic findings are probabilities, not certainties
- Individual variation requires personalized interpretation
- Always validate against patient history and biomarkers

---

## 🆘 Support

- **Issues**: GitHub Issues for bugs and feature requests
- **Documentation**: Full API docs at `/docs` endpoint
- **Email**: vikas@example.com

---

## 📊 Project Statistics

- **Total Commits**: 25+
- **Clinical Systems**: 5 (Energy, Inflammation, Detox, Brain, Recovery)
- **System Severity Bands**: 20 (4 per system)
- **Action Permutations**: 100+ (5 systems × 4 priorities × 5 categories)
- **Adaptive Endpoints**: 3 new in v7 (`/interventions`, `/patient/{id}/interventions/{system}`, `/validate-outcome`)
- **System Interactions Detected**: 3 rules (Detox→Inflammation, Detox→Brain, Energy→Recovery)
- **Confidence Metrics**: Coverage × fold-change + multi-report boosting
- **Lines of Code**: 4,000+ (Python backend + React/Next.js frontend)
- **Database Tables**: 8 (genes, pathways, patients, reports, scores, insights, pathway_scores, interventions)

---

## 🚀 Roadmap

- [x] ~~v6: Decision engine, outcome predictions, trend interpretation~~
- [x] ~~v7: Intervention tracking, outcome validation, adaptive protocol escalation~~
- [ ] Automated pytest suite for all service modules
- [ ] Frontend UI for intervention logging and outcome review
- [ ] Multi-language system definitions (Spanish, Mandarin)
- [ ] Wearable integration (Apple Health, Fitbit)
- [ ] Real-time trend dashboards (patient + clinician views)
- [ ] Batch analysis (multi-patient reports)
- [ ] Population-level outcome analytics
- [ ] Integration with conventional lab tests (CBC, CMP, etc.)

---

**Built with:** FastAPI, Next.js, R, SQLAlchemy, MySQL

**Status:** Production-ready. Used in functional medicine and research settings.

**Last Updated:** May 2026 — v7: Adaptive Clinical Intelligence

---

*Make your genomics actionable. Transform data into decisions.*
