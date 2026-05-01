# Contributing to Genesis

Thank you for your interest in contributing to Genesis! This document outlines the process and guidelines.

## How to Contribute

### 1. Report Issues
Found a bug? Want a feature?

1. Check existing issues first
2. Create a new issue with:
   - Clear title (what's broken or missing)
   - Steps to reproduce (for bugs)
   - Expected vs. actual behavior
   - System info (OS, Python version, etc.)

### 2. Code Contributions

#### Setup Development Environment
```bash
git clone https://github.com/ambekarvikas/genesis_tool.git
cd genesis_tool

# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install pytest black flake8

# Frontend
cd ../frontend
npm install
```

#### Making Changes

**For backend features:**
- New clinical logic → `services/`
- Config updates → `config/` (JSON)
- Database schema → `models/`
- Tests → `tests/`

**For frontend:**
- Pages → `frontend/app/`
- Reusable components → `frontend/components/`
- Tests → `frontend/__tests__/`

#### Code Standards

**Python:**
```bash
# Format with Black
black backend/

# Lint with Flake8
flake8 backend/ --max-line-length=120

# Run tests
pytest tests/ -v
```

**TypeScript/React:**
```bash
# Format with Prettier
npm run format

# Lint
npm run lint
```

#### Commit Messages

Follow conventional commits:

```
feat(core): add mortality risk system
fix(api): handle missing gene matches gracefully
docs(readme): clarify deployment steps
test(confidence): add edge case for zero genes
refactor(clinical-engine): simplify band selection logic
```

#### Pull Request Process

1. **Create feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes:** Follow code standards above

3. **Test locally:**
   ```bash
   # Backend
   python -m pytest tests/
   
   # Frontend
   npm run build && npm run test
   ```

4. **Update docs** if needed (README, API docs, etc.)

5. **Push and create PR:**
   ```bash
   git push origin feature/your-feature-name
   ```
   
   In PR description:
   - What problem does this solve?
   - How was it tested?
   - Any breaking changes?
   - Screenshots/videos if UI change

6. **Address review feedback** (maintainers will review)

7. **Squash commits** if requested, then merge

## Contribution Areas

### 🟢 High Priority
- [ ] Additional system definitions (Thyroid, Metabolic Rate, Hormone Balance)
- [ ] EHR system integrations (Epic, Cerner)
- [ ] Mobile app (React Native)
- [ ] Advanced analytics (population trends, outcome validation)
- [ ] Multi-language support

### 🟡 Medium Priority
- [ ] Wearable API integrations (Apple Health, Fitbit, Oura)
- [ ] Batch analysis (process 100+ patients)
- [ ] Real-time dashboards
- [ ] Export formats (HL7, FHIR)

### 🔵 Nice to Have
- [ ] Dark mode UI
- [ ] Custom report templates
- [ ] Dr appointment scheduling integration
- [ ] Patient mobile access

## Clinical Contribution Guidelines

If you're adding new system definitions or clinical actions:

1. **Base on evidence:**
   - Cite KEGG pathways used
   - Reference clinical literature
   - Include mechanism of action

2. **Structure properly:**
   ```json
   {
     "SystemName": {
       "label": "Human-readable name",
       "system_weight": 1.0,
       "high_is_worse": false,
       "focus_goal": "What clinician should achieve",
       "default_symptoms": ["List of observable signs"],
       "bands": [
         {
           "min": 0, "max": 34,
           "priority": "Critical",
           "issue": "Pathophysiology summary",
           "impact": "What it means for the patient",
           "actions": {
             "lifestyle": ["Specific behavior changes"],
             "nutrition": ["Evidence-based nutrients/foods"],
             "clinical": ["Biomarker tests to order"]
           },
           "expected_outcome": "If done correctly, what improves in 6-8 weeks"
         }
       ]
     }
   }
   ```

3. **Test clinical accuracy:**
   - Run against sample patients
   - Validate action specificity (not generic)
   - Ensure outcomes are realistic

4. **Document reasoning:**
   - Comment why this band threshold
   - Link to pathway definitions
   - Note any assumptions

## Testing Clinical Logic

Before submitting PR with clinical changes:

```bash
# Test with sample data
curl -X POST http://127.0.0.1:8091/analyze \
  -F "patient_id=1" \
  -F "file=@data/sample_gene.csv"

# Verify:
# 1. Is priority correct for score?
# 2. Are actions specific + actionable?
# 3. Is outcome prediction realistic?
# 4. Is confidence score well-justified?
```

## Questions?

- **General**: Create discussion issue
- **Technical**: Tag with `[HELP]` in issue
- **Clinical**: Email vikas@example.com with context

## Recognition

Contributors will be:
- Listed in README contributors section
- Credited in commit history
- Mentioned in release notes

Thank you for making Genesis better! 🙏
