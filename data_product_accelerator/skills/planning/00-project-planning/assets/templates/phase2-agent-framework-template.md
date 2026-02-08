# Phase 2: Agent Framework - AI Agents

## Overview

**Status:** {status}
**Dependencies:** Phase 1 (Use Cases) - especially 1.6 Genie Spaces ✅
**Estimated Effort:** {weeks}

---

## Purpose

AI agents provide natural language interfaces to data assets. Agents use Genie Spaces
as their query interface - they do NOT write SQL directly. This architecture provides:

- Natural language understanding via Genie Spaces
- Abstraction from underlying data schema changes
- Built-in query guardrails and optimization
- Benchmark testing framework from Genie Spaces

---

## Agent Layer Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    USER / FRONTEND APPLICATION                       │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR AGENT                                │
│  Purpose: Intent classification, multi-domain query coordination     │
│  Genie Space: Unified {Project} Monitor                             │
│  Capabilities: Route to specialized agents, synthesize responses     │
└─────────────────────────────────────────────────────────────────────┘
                    │               │               │
        ┌───────────┘               │               └───────────┐
        ▼                           ▼                           ▼
┌───────────────────┐   ┌───────────────────┐   ┌───────────────────┐
│  {Domain 1} Agent │   │  {Domain 2} Agent │   │  {Domain N} Agent │
│  Genie: {D1} Int  │   │  Genie: {D2} Int  │   │  Genie: {DN} Int  │
└───────────────────┘   └───────────────────┘   └───────────────────┘
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────────────────────────────────────────────────────────────┐
│                         GENIE SPACES (Phase 1.6)                       │
│  Each agent uses its dedicated Genie Space as the query interface      │
└───────────────────────────────────────────────────────────────────────┘
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────────────────────────────────────────────────────────────┐
│                    DATA ASSETS (Phase 1.1-1.5, 1.7)                    │
│  TVFs | Metric Views | ML Models | Lakehouse Monitors | Gold Tables   │
└───────────────────────────────────────────────────────────────────────┘
```

---

## Agent-to-Genie Space Mapping

| Agent | Dedicated Genie Space | Purpose |
|-------|----------------------|---------|
| {Domain 1} Agent | {Domain 1} Intelligence | {domain 1} queries via NL |
| {Domain 2} Agent | {Domain 2} Intelligence | {domain 2} queries via NL |
| Orchestrator Agent | Unified {Project} Monitor | Intent classification |

---

## Agent Summary by Domain

| Domain | Icon | Agent Name | Genie Space | Capabilities |
|--------|------|------------|-------------|--------------|
| {Domain 1} | {emoji} | {Domain 1} Agent | {Domain 1} Intelligence | {capabilities} |
| {Domain 2} | {emoji} | {Domain 2} Agent | {Domain 2} Intelligence | {capabilities} |
| Unified | 🌐 | Orchestrator Agent | Unified Monitor | Multi-domain coordination |

---

## {Domain 1} Agent

**Name:** {Domain 1} Intelligence Agent
**Focus:** {focus area}
**Genie Space:** {Domain 1} Intelligence ← Agent's primary tool
**System Prompt Source:** Genie Space instructions

**How Agent Uses Genie Space:**
1. Agent receives natural language query from user/orchestrator
2. Agent sends query to Genie Space via tool call
3. Genie Space translates NL to SQL and executes
4. Agent receives results and synthesizes response

**Capabilities (via Genie Space):**
- Answer {domain}-related questions using Genie Space NL interface
- Access {domain} TVFs indirectly (Genie routes to correct TVF)
- Retrieve {domain} ML predictions (Genie accesses prediction tables)
- Generate {domain} insights from Metric Views

---

## Three-Level Testing Strategy

### Level 1: Genie Space Standalone (Phase 1.6)

Validate Genie Spaces work before agent integration:
- [ ] All benchmark questions return correct results
- [ ] Query latency < 10 seconds
- [ ] >80% accuracy on domain-specific questions

### Level 2: Agent Integration (Phase 2)

Validate agents correctly use Genie Spaces:
- [ ] Agent correctly routes queries to Genie Space tool
- [ ] Agent interprets Genie Space results accurately
- [ ] >90% intent classification accuracy
- [ ] Correct tool usage patterns

### Level 3: Multi-Agent Workflow (Phase 2)

Validate Orchestrator coordinates specialized agents:
- [ ] Orchestrator correctly classifies multi-domain intent
- [ ] Sub-queries routed to correct specialized agents
- [ ] Responses synthesized coherently
- [ ] >85% multi-intent classification accuracy

---

## Implementation Checklist

### Prerequisites (Must Complete First)
- [ ] All Genie Spaces deployed and responding (Phase 1.6 complete)
- [ ] Genie Space benchmark questions validated
- [ ] Genie Space instructions finalized (become agent system prompts)

### Agent Development
- [ ] Define agent system prompts (derived from Genie Space instructions)
- [ ] Configure Genie Space as agent tool (LangChain/LangGraph)
- [ ] Implement agent response synthesis logic
- [ ] Test agent-to-Genie Space integration

### Orchestrator Development
- [ ] Define orchestrator routing logic
- [ ] Map intents to specialized agents
- [ ] Implement multi-agent coordination
- [ ] Test multi-domain query handling

### Deployment
- [ ] Deploy agents to Model Serving
- [ ] Configure API endpoints
- [ ] Set up monitoring and logging
- [ ] Validate end-to-end workflows

---

## Next Phase

**→ [Phase 3: Frontend App](./phase3-frontend-app.md)**
