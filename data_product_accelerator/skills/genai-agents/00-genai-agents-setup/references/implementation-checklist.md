# Consolidated Implementation Checklist

## Phase 1: ResponsesAgent Foundation
- [ ] Agent class inherits from `mlflow.pyfunc.ResponsesAgent`
- [ ] `predict()` accepts `request: ResponsesAgentRequest`
- [ ] `predict()` returns `ResponsesAgentResponse`
- [ ] `predict_stream()` yields `ResponsesAgentStreamEvent` objects
- [ ] Final `output_item.done` event sent in streaming
- [ ] Input example uses `input` key (NOT `messages`)
- [ ] **NO `signature` parameter** in `log_model()` call
- [ ] `@mlflow.trace` decorator on `predict()` and key functions
- [ ] Span types specified (`AGENT`, `TOOL`, `LLM`, `RETRIEVER`)
- [ ] Trace storage configured in Unity Catalog
- [ ] OBO context detection (check env vars before using OBO)
- [ ] SystemAuthPolicy declares all resources (Genie, Warehouse, LLM, Lakebase)
- [ ] UserAuthPolicy declares required scopes
- [ ] Agent loads in AI Playground without errors

## Phase 2: Genie Integration
- [ ] Genie Space IDs configured per domain
- [ ] Conversation API used (start_conversation_and_wait)
- [ ] Query results extracted (get_message_attachment_query_result)
- [ ] **NO LLM fallback** for data queries
- [ ] Clear error messages when Genie fails
- [ ] "I will NOT generate fake data" in error messages
- [ ] Intent classification routes to correct domains
- [ ] Parallel domain queries with ThreadPoolExecutor
- [ ] Cross-domain synthesis with LLM

## Phase 3: Memory
- [ ] Lakebase instance name configured
- [ ] Setup script creates tables (run once)
- [ ] CheckpointSaver for short-term conversation context
- [ ] DatabricksStore for long-term user preferences
- [ ] Embedding endpoint configured (e.g., databricks-gte-large-en)
- [ ] Thread ID resolution: custom_inputs → conversation_id → new UUID
- [ ] thread_id returned in custom_outputs
- [ ] Graceful degradation if memory tables don't exist
- [ ] Memory tools created for autonomous agent use

## Phase 4: Prompt Management
- [ ] Unity Catalog agent_config table created
- [ ] Prompts registered to both UC and MLflow
- [ ] Agent loads prompts at runtime (lazy loading)
- [ ] Fallback defaults if UC unavailable
- [ ] SQL injection prevented (escaped single quotes)
- [ ] A/B testing aliases defined (champion/challenger)

## Phase 5: Evaluation
- [ ] Evaluation dataset loaded with correct schema
- [ ] 4-6 essential guidelines (NOT 8+)
- [ ] `_extract_response_text()` in ALL custom scorers
- [ ] Databricks SDK for LLM calls (NOT langchain_databricks)
- [ ] `_call_llm_for_scoring()` helper defined
- [ ] Foundation model endpoints (not pay-per-token)
- [ ] Temperature = 0.0 for judge consistency
- [ ] METRIC_ALIASES defined for backward compatibility
- [ ] check_thresholds() handles aliases
- [ ] Run name convention: eval_pre_deploy_YYYYMMDD_HHMMSS

## Phase 6: Deployment
- [ ] Deployment job triggers on MODEL_VERSION_CREATED
- [ ] Model name and version passed from trigger
- [ ] Evaluation dataset linked with mlflow.log_input()
- [ ] Three separate experiments (dev, eval, deploy)
- [ ] Run names follow convention (dev_*, eval_*, pre_deploy_*)
- [ ] Thresholds checked before promotion
- [ ] Model promoted with alias management

## Phase 7: Production Monitoring
- [ ] Scorers registered with unique names
- [ ] Immutable pattern: scorer = scorer.start(...)
- [ ] Safety at 100% sampling
- [ ] Expensive LLM judges at 5-20% sampling
- [ ] Custom heuristic scorers at 100% sampling
- [ ] Trace archival enabled to Unity Catalog
- [ ] Monitoring dashboard queries working
- [ ] All imports inline within scorer functions

## Phase 8: Genie Optimization
- [ ] Accuracy tests run for all benchmark questions
- [ ] Repeatability tested (3+ iterations, 12s between)
- [ ] Six control levers evaluated and applied
- [ ] Dual persistence: API update + repository update
- [ ] Arrays sorted before API PATCH
- [ ] Template variables preserved in repository files
