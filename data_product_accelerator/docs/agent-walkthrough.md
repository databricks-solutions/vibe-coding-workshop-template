# Genie Space Optimizer v2.0 — Agent Walkthrough

Design document for how the AI agent navigates the optimization skill. Structured around three principles: progressive disclosure, long-running session management, and structured context engineering.

**References:**
- [Anthropic: Effective Context Engineering for AI Agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Anthropic: Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [AgentSkills.io Specification](https://agentskills.io/specification)

---

## Section 1: Progressive Disclosure Navigation

The skill is structured in three layers following the AgentSkills.io specification. The agent loads only what it needs, when it needs it.

### Layer 1: Metadata (~100 tokens)

Loaded when the skill system scans all available skills to match user intent.

```yaml
name: genie-optimization-orchestrator
description: "Interactive Genie Space optimization loop using MLflow GenAI evaluation..."
```

The agent decides whether to activate this skill based on the description alone. No reference files are loaded.

### Layer 2: Instructions (~288 lines)

Loaded when the skill is activated. The full `SKILL.md` is read.

The agent now knows:
- The 9-step loop structure
- Quality dimensions and targets
- That reference files exist for each step
- The progress tracking mechanism

But it does NOT yet have the code patterns, GEPA API details, or judge implementations. These remain in Layer 3.

### Layer 3: Resources (loaded just-in-time per step)

Each step in SKILL.md includes a `Load:` directive pointing to reference files. The agent reads these only when it reaches that step.

| Step | What to Load | Approximate Size |
|------|-------------|-----------------|
| 1 | `benchmark-patterns.md`, `benchmark-intake-workflow.md` | ~400 lines |
| 2 | `optimization-code-patterns.md` §Snapshot | ~30 lines |
| 3 | `optimization-code-patterns.md` §Judge Suite | ~200 lines |
| 4 | `gepa-integration.md` OR `optimization-workflow.md` §Introspection | ~200 lines |
| 5 | `control-levers.md` | ~400 lines |
| 6 | `optimization-workflow.md` §Convergence | ~50 lines |
| * | `prompt-registry-patterns.md` (first run only) | ~100 lines |

**Why this matters:** Loading all reference files upfront would consume ~2000+ lines of context. By loading per-step, the agent keeps ~300-400 lines in working memory at any time, preserving attention for the actual task.

### Navigation Pattern

The agent assembles understanding layer by layer:

```
1. Read SKILL.md → understand the 9-step loop
2. Reach Step 1 → read benchmark-patterns.md for question writing
3. Complete Step 1 → discard benchmark patterns from active memory
4. Reach Step 3 → read optimization-code-patterns.md for judge code
5. ...and so on
```

This mirrors the Anthropic guidance: "Agents can assemble understanding layer by layer, maintaining only what's necessary in working memory."

---

## Section 2: Long-Running Session Management

The optimization loop can run for up to 2.5 hours across 5 iterations. This exceeds typical context windows, requiring structured persistence.

### The Progress File Pattern

Inspired by Anthropic's long-running agent harness (`claude-progress.txt`), the optimizer uses `optimization-progress.json`:

```
Session Start
├── Read optimization-progress.json (if resuming)
├── Read git log (recent commits)
├── Read MLflow experiment (run IDs, metrics)
└── Determine: which iteration, what's next

Per Iteration
├── Run evaluation
├── Update progress file with results
├── Commit to git
└── Log to MLflow

Session End (or Context Window Reset)
├── Write final progress file
├── Git commit with descriptive message
└── MLflow run logged
```

### Session Startup Protocol

When the agent starts (or resumes), it follows this sequence:

1. **Check for `optimization-progress.json`** — if present, read it to determine current state
2. **Read git log** — last 5 commits to understand recent changes
3. **Read MLflow experiment** — run IDs, iteration numbers, metrics
4. **Determine next action** — based on `progress.next_action` or `progress.remaining_failures`

### Session Shutdown Protocol

Before the context window resets or the user ends the session:

1. **Write `optimization-progress.json`** with current iteration results
2. **Git commit** with descriptive message (e.g., "iter-2: fix table disambiguation — schema accuracy 72% → 89%")
3. **Log MLflow run** with all judge scores and artifacts
4. **No half-applied proposals** — ensure dual persistence is complete

### Handling Context Window Compaction

When the agent's context is compacted (token limit, session timeout):

**What the agent preserves (in progress file):**
- Current iteration number
- Per-judge scores for each iteration
- Which failure clusters have been addressed
- Which proposals were applied and their results
- Next action to take

**What the agent can reconstruct (from external state):**
- Full benchmark questions (from YAML file)
- Metadata snapshots (from MLflow artifacts)
- Detailed evaluation results (from MLflow experiment runs)

**What the agent can discard:**
- Full reference file contents (re-loaded via `Load:` directives)
- Previous iteration's raw evaluation output
- Code pattern implementations (re-read from reference files)

---

## Section 3: 3-Layer Judging Flow with Arbiter

### Visual Decision Flow

```
Question → Genie → SQL Response
                       │
                       ▼
            ┌─────────────────────┐
            │  LAYER 1: Quality   │
            │  (6 judges, always) │
            └──────────┬──────────┘
                       │
                       ▼
            ┌─────────────────────┐
            │  LAYER 2: Results   │
            │  (execute both SQLs)│
            └──────────┬──────────┘
                       │
              Results match? ──YES──→ Score complete
                       │
                      NO
                       │
              Layer 1 mostly pass? ──NO──→ Genie is wrong, optimize
                       │
                      YES
                       │
                       ▼
            ┌─────────────────────┐
            │  LAYER 3: Arbiter   │
            │  (which SQL is     │
            │   correct?)         │
            └──────────┬──────────┘
                       │
            ┌──────────┼──────────────────────┐
            │          │                      │
     genie_correct  both_correct     ground_truth_correct
            │          │                      │
     Auto-update   Add disambig.      Optimize metadata
     benchmark     instruction        to fix Genie
```

### Data Flow Between Layers

- **Layer 1 → GEPA:** Judge rationales become Actionable Side Information (ASI)
- **Layer 1 → Introspection:** Rationales clustered by root cause pattern
- **Layer 2 → Layer 3:** Result comparison data feeds the arbiter
- **Layer 3 → Benchmark:** Arbiter corrections update the ground truth YAML + MLflow dataset

---

## Section 4: GEPA Optimization Loop

### How `evaluate_genie` Works

```
GEPA proposes candidate metadata
        │
        ▼
Apply metadata to Genie Space (API)
        │
        ▼
Wait 12s (rate limit)
        │
        ▼
Query Genie with benchmark question
        │
        ▼
Score with Layer 1 judges
        │
        ▼
Return (overall_score, ASI)
        │
        ▼
GEPA's reflection LM reads ASI
        │
        ▼
Proposes next mutation based on rationales
```

### GEPA's Reflection Reading Judge Rationales

The key insight: GEPA's reflection LM reads the judge rationales (ASI) to understand WHY a candidate scored well or poorly, then proposes targeted mutations. This is more efficient than random search because the rationales explain the causal relationship between metadata and SQL generation quality.

### Rate Limit Budget

With `cache_evaluation=True`, GEPA avoids re-querying Genie for identical metadata+question pairs. The budget for `max_metric_calls=150` allows approximately 10 candidate evaluations across 15 questions.

### When to Fall Back

| Signal | Action |
|--------|--------|
| GEPA import fails | Fall back to Tier 2 (LLM Introspection) |
| < 15 benchmark questions | Use Tier 2 (insufficient data for GEPA) |
| Primarily UC metadata changes needed | Use Tier 2 (GEPA optimizes instructions, not DDL) |
| Judge accuracy < 70% agreement with human labels | Use Tier 3 (SIMBA alignment first) |

---

## Section 5: Reference Index for the Agent

Complete map of "If you need X, read Y" — the agent's bookmark system.

| Need | Read This File | Section |
|------|---------------|---------|
| Write benchmark questions | `references/benchmark-patterns.md` | Category Coverage, Writing Effective Questions |
| Validate user-submitted benchmarks | `references/benchmark-intake-workflow.md` | Validation Pipeline |
| Validate ground truth SQL | `references/optimization-code-patterns.md` | §Ground Truth Validation |
| Sync YAML to MLflow Dataset | `references/optimization-code-patterns.md` | §MLflow Dataset Sync |
| Snapshot Genie metadata | `references/optimization-code-patterns.md` | §MLflow Dataset Sync |
| Query Genie via API | `references/optimization-code-patterns.md` | §run_genie_query |
| Create 3-layer judge suite | `references/optimization-code-patterns.md` | §Judge Suite |
| Compare SQL result sets | `references/optimization-code-patterns.md` | §Result Comparison |
| Handle arbiter verdicts | `references/optimization-code-patterns.md` | §Arbiter |
| Cluster failures | `references/optimization-code-patterns.md` | §Introspection |
| Generate metadata proposals | `references/optimization-code-patterns.md` | §Introspection |
| Run GEPA metadata optimization | `references/gepa-integration.md` | §Full Optimization Orchestration |
| Build GEPA seed candidate | `references/gepa-integration.md` | §Seed Candidate Extraction |
| Optimize judge prompts | `references/gepa-integration.md` | §Judge Prompt Optimization |
| Apply control lever changes | `references/control-levers.md` | Per-lever sections |
| Map proposals to levers | `references/control-levers.md` | §Introspective Proposal Mapping |
| Register optimizer prompts | `references/prompt-registry-patterns.md` | §Initial Registration |
| Load prompts by alias | `references/prompt-registry-patterns.md` | §Loading Prompts |
| Roll back prompts | `references/prompt-registry-patterns.md` | §Rollback Pattern |
| Check convergence criteria | `references/optimization-workflow.md` | §Convergence Criteria |
| Handle regressions | `references/optimization-workflow.md` | §Phase 4 |
| Deploy bundle | `references/autonomous-ops-integration.md` | §Three-Phase Deployment |
| Troubleshoot deploy failures | `references/autonomous-ops-integration.md` | §Self-Healing Deploy |
| Track progress across sessions | `references/optimization-code-patterns.md` | §Progress Tracking |
| Golden queries YAML format | `assets/templates/golden-queries.yaml` | Header comments |
| Progress file schema | `assets/templates/optimization-progress.json` | Full template |
| Report format | `assets/templates/optimization-report.md` | Full template |

This index serves as the lightweight identifier system described in Anthropic's context engineering guide — the agent doesn't load all these files upfront but knows exactly where to look when it needs specific information.
