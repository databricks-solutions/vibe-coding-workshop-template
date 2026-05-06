# {Project Name} — Use Case Catalog

**Planning Mode:** {acceleration / workshop}
**Total Use Cases:** {count}
**Domains Covered:** {domain_1}, {domain_2}, ...

---

## Use Case Summary

| UC# | Use Case Name | Domain | Gold Tables | Artifact Types | Example Question |
|-----|--------------|--------|-------------|---------------|-----------------|
| UC-001 | {Descriptive Name} | {Domain} | `fact_*`, `dim_*` | TVF, MV, Dashboard | "{Natural language question}?" |
| UC-002 | {Descriptive Name} | {Domain} | `fact_*`, `dim_*` | TVF, MV, Alert | "{Natural language question}?" |
| ... | ... | ... | ... | ... | ... |

---

## Use Case Cards

### UC-001: {Descriptive Name}

**Domain:** {Icon} {Domain Name}
**Business Problem:** {1-2 sentence description of the analytical or operational problem this use case addresses. Focus on the decision or insight stakeholders need.}

**Business Questions This Use Case Answers:**
1. {Question in natural language — phrased as a stakeholder would ask it}?
2. {Question}?
3. {Question}?
4. {Question}? *(optional)*
5. {Question}? *(optional)*

**Gold Tables:** `{catalog}.{gold_schema}.fact_*`, `{catalog}.{gold_schema}.dim_*`

**Implementing Artifacts:**

| Artifact Type | Name | Which Questions It Answers |
|--------------|------|---------------------------|
| TVF | `get_{metric}_by_{dimension}` | Q1, Q2 |
| Metric View | `{domain}_analytics_metrics` | Q1, Q3 |
| Dashboard | {Domain} Performance Dashboard | Q1-Q5 (visual) |
| Monitor | {Domain} Data Quality Monitor | (data reliability) |
| Alert | `{DOMAIN}-001-{SEVERITY}` | Q4 (proactive) |
| ML Model | {Model Name} | Q5 (predictive) |

**Stakeholders:** {executives, analysts, operations, data scientists}
**Success Criteria:** {What "done" looks like — e.g., "All 5 questions answerable via Genie Space with >=95% SQL accuracy"}

---

### UC-002: {Descriptive Name}

**Domain:** {Icon} {Domain Name}
**Business Problem:** {Problem statement}

**Business Questions This Use Case Answers:**
1. {Question}?
2. {Question}?
3. {Question}?

**Gold Tables:** `{tables}`

**Implementing Artifacts:**

| Artifact Type | Name | Which Questions It Answers |
|--------------|------|---------------------------|
| TVF | `get_*` | Q1, Q2 |
| Metric View | `*_metrics` | Q1, Q3 |
| Dashboard | {Name} | Q1-Q3 (visual) |

**Stakeholders:** {roles}
**Success Criteria:** {criteria}

---

*Repeat for each use case...*

---

## Traceability Matrix

Verify every question has at least one implementing artifact, and every artifact traces to at least one question.

| Question | TVF | Metric View | Dashboard | Monitor | Alert | ML Model | Genie Space |
|----------|-----|-------------|-----------|---------|-------|----------|-------------|
| UC-001 Q1: {Short form} | x | x | x | | | | x |
| UC-001 Q2: {Short form} | x | | | | | | x |
| UC-001 Q3: {Short form} | | x | x | | | | x |
| UC-002 Q1: {Short form} | x | | x | | | | x |
| ... | ... | ... | ... | ... | ... | ... | ... |

**Validation:** No row should be empty (every question needs an artifact). No artifact column should be all-empty (every artifact type serves at least one question).

---

## Coverage Summary

| Metric | Count |
|--------|-------|
| Total Use Cases | {N} |
| Total Business Questions | {N} |
| Total Artifact Mappings | {N} |
| Questions with >= 1 Artifact | {N}/{N} ({pct}%) |
| Artifacts with >= 1 Question | {N}/{N} ({pct}%) |
| Orphan Questions (no artifact) | {N} — {list if any} |
| Orphan Artifacts (no question) | {N} — {list if any} |

**Target:** 100% question coverage, 0 orphans.

**Automated validation:** Run `python scripts/validate_use_case_coverage.py plans/use-case-catalog.md` to verify these numbers programmatically.

---

## Cross-References

| Document | Relationship |
|----------|-------------|
| [Phase 1: Use Cases](./phase1-use-cases.md) | Master artifact inventory by domain |
| [Phase 1 Addendum 1.2: TVFs](./phase1-addendum-1.2-tvfs.md) | TVF specifications referenced in artifact tables |
| [Phase 1 Addendum 1.3: Metric Views](./phase1-addendum-1.3-metric-views.md) | Metric View definitions referenced in artifact tables |
| [Phase 1 Addendum 1.5: Dashboards](./phase1-addendum-1.5-aibi-dashboards.md) | Dashboard layouts that visualize use case questions |
| [Phase 1 Addendum 1.6: Genie Spaces](./phase1-addendum-1.6-genie-spaces.md) | Genie Spaces that answer use case questions via NL |
| [Phase 1 Addendum 1.7: Alerting](./phase1-addendum-1.7-alerting.md) | Alerts that proactively monitor use case thresholds |
