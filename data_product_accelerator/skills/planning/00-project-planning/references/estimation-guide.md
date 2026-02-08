# Estimation Guide - Project Plan Methodology

## Effort Estimation Guidelines

### By Phase

| Phase | Effort Range | Factors |
|-------|--------------|---------|
| **Phase 1.1: ML Models** | 2-4 weeks | Model complexity, feature engineering, training time |
| **Phase 1.2: TVFs** | 1-2 weeks | Query complexity, parameter validation, testing |
| **Phase 1.3: Metric Views** | 1 week | Aggregation complexity, join patterns |
| **Phase 1.4: Monitoring** | 1 week | Custom metrics, monitor configuration |
| **Phase 1.5: Dashboards** | 2-3 weeks | Widget count, visualization complexity, JSON editing |
| **Phase 1.6: Genie Spaces** | 1-2 weeks | Space configuration, benchmark questions, testing |
| **Phase 1.7: Alerting** | 1-2 weeks | Alert logic, notification configuration |
| **Phase 2: Agents** | 3-5 weeks | Framework setup, agent development, testing |
| **Phase 3: Frontend** | 2-4 weeks | UI complexity, integration points |

### By Artifact Type

| Artifact Type | Effort Per Artifact | Notes |
|---------------|---------------------|-------|
| **TVF** | 2-4 hours | Simple queries faster, complex joins slower |
| **Metric View** | 4-6 hours | YAML complexity, join patterns |
| **ML Model** | 1-2 days | Feature engineering, training, validation |
| **Dashboard Page** | 4-8 hours | Widget count, visualization complexity |
| **Genie Space** | 1-2 days | Configuration, benchmark questions, testing |
| **Alert** | 1-2 hours | SQL query, threshold configuration |
| **Monitor** | 2-4 hours | Custom metrics, configuration |
| **Agent** | 3-5 days | Framework integration, Genie Space connection, testing |

## Dependency Management

### Critical Path

1. **Gold Layer** → All Phase 1 artifacts
2. **Phase 1.6 (Genie Spaces)** → Phase 2 (Agents)
3. **Phase 1 artifacts** → Phase 1.6 (Genie Spaces)
4. **Phase 2 (Agents)** → Phase 3 (Frontend)

### Parallel Work Opportunities

- **Phase 1.1-1.5:** Can be developed in parallel (different domains)
- **Phase 1.7:** Can be developed in parallel with other Phase 1 artifacts
- **Phase 2.2:** Specialized agents can be developed in parallel
- **Phase 3:** Can start UI mockups while Phase 2 is in progress

## Risk Management Strategies

### Technical Risks

| Risk | Mitigation |
|------|------------|
| **Genie Space API changes** | Test early, use stable API versions |
| **Gold layer schema changes** | Version control, change management |
| **Agent framework compatibility** | Proof of concept early |
| **Performance issues** | Load testing, optimization |

### Process Risks

| Risk | Mitigation |
|------|------------|
| **Scope creep** | Clear phase boundaries, change control |
| **Resource availability** | Cross-training, documentation |
| **Timeline pressure** | Buffer time, prioritization |

## Progress Tracking Templates

### Artifact Status Table

| Artifact | Domain | Status | Dependencies | Effort | Notes |
|----------|--------|--------|---------------|--------|-------|
| get_cost_by_tag | 💰 Cost | ✅ Complete | Gold layer | 3h | Tested |

**Status Values:** 📋 Planned | 🚧 In Progress | ✅ Complete | ❌ Blocked | ⚠️ At Risk
