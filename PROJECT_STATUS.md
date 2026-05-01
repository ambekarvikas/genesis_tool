# Project Status — Rhino Gene Pathway Analysis

_Last updated: 2026-04-30_

## 1) Current Goal
The project ingests uploaded gene expression files (`.csv`, `.xlsx`, `.xls`), scores KEGG pathways, groups them by biological category, and shows results in a web dashboard with insights.

## 2) Current Architecture

### Backend (FastAPI)
- Entry point: `backend/main.py`
- Endpoint: `POST /analyze`
- Responsibilities:
  - Read uploaded file
  - Run Python-side base scoring
  - Call R service for pathway scoring
  - Group pathways by category
  - Return insights + structured payload for UI

### R Service (KEGG scoring)
- Script: `r-service/generate_pathway.R`
- Responsibilities:
  - Detect gene symbol + expression columns
  - Score configured KEGG pathways
  - Use local cache directory (`data/kegg_cache`) for KEGG gene lists
  - Write output CSV (`data/pathway_scores.csv`)

### Frontend (Next.js)
- Main view: `frontend/app/page.tsx`
- Responsibilities:
  - Upload file and call API
  - Show summary + insights
  - Show category cards
  - Show expandable pathway tables with score, matched genes, and median log2FC

## 3) Data Flow
1. User uploads gene file in frontend.
2. Frontend sends multipart request to `POST /analyze`.
3. Backend parses data and invokes R scoring.
4. R script computes pathway-level metrics and writes CSV.
5. Backend reads R output, groups by category, builds insights.
6. Frontend renders grouped results.

## 4) Current API Response Shape (High Level)
- `scores`: base scoring metadata (source column, rows used, etc.)
- `insights`: generated interpretation strings
- `pathway`:
  - `status`, `code`, `stdout`, `stderr`, `runner`, `output_file`
  - `scores[]` with:
    - `category`
    - `kegg_id`
    - `pathway`
    - `score`
    - `n_genes`
    - `median_fc`
  - `categories[]` grouped view for dashboard

## 5) What Is Working Now
- End-to-end upload → score → dashboard flow is operational.
- Backend is running on `127.0.0.1:8050`.
- KEGG pathway scoring is active and returning category/group data.
- UI has category overview and expandable pathway details.
- API + UI integration is functioning with real uploaded data.

## 6) Known Gaps / Risks
- First run can be slower while KEGG cache is populated.
- Some pathways may return `0` matches depending on uploaded dataset coverage.
- API currently returns very large `stdout` logs from R; this may be noisy for production.
- The old base `scores` block is still returned alongside pathway results (useful for debugging, may be reduced later).

## 7) Suggested Next Steps
1. Reduce/trim `stdout` returned by API in production mode.
2. Add optional filtering (e.g., only pathways with matched genes > 0).
3. Add export feature (CSV/PDF report).
4. Add lightweight test coverage for `/analyze` payload structure.
5. Add environment/config controls for cache behavior and verbosity.

## 8) Key Files
- `backend/main.py`
- `backend/services/r_integration.py`
- `backend/services/scoring.py`
- `r-service/generate_pathway.R`
- `frontend/app/page.tsx`
- `data/pathway_scores.csv`
- `data/kegg_cache/`
