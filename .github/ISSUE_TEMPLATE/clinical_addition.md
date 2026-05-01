---
name: Clinical Addition
about: Propose a new clinical system definition or action set
title: "[CLINICAL] Add Thyroid system definition"
labels: clinical
assignees: ''

---

## System/Intervention to Add
Which system, actions, or outcome predictions?

## Clinical Rationale
What KEGG pathways are involved? Why is this important?

## Evidence
- [ ] Based on KEGG database
- [ ] Referenced clinical literature
- [ ] Tested with sample patients

## Proposed Definition
```json
{
  "SystemName": {
    "label": "...",
    "bands": [
      {
        "priority": "Critical",
        "issue": "...",
        "actions": {
          "lifestyle": [],
          "nutrition": [],
          "clinical": []
        },
        "expected_outcome": "..."
      }
    ]
  }
}
```

## Testing
- Tested against sample data: [ ]
- Actions are specific/actionable: [ ]
- Outcomes are realistic: [ ]

## References
- KEGG pathway IDs: [list]
- Clinical sources: [links]
