# Verification Sources Master List

Maps every skill to the official documentation URLs used to verify its patterns are current. Organized by domain.

**How to use:** During an audit, fetch each URL and compare key patterns against the skill's instructions.

---

## GenAI Agents Domain (High Volatility)

> The GenAI course lives under `genai-agents/{00-course-orchestrator, foundation/, sdlc/, tracks/}`.
> URLs below track the current MLflow 3 GenAI doc family on `docs.databricks.com/aws/en/mlflow3/genai/`.

### `genai-agents/00-course-orchestrator`
| URL | Check For |
|---|---|
| https://docs.databricks.com/aws/en/generative-ai/agent-framework/ | Agent Framework overview, supported agent types |
| https://mlflow.org/docs/latest/genai/serving/responses-agent | ResponsesAgent API, class signature |
| https://docs.databricks.com/aws/en/mlflow3/genai/eval-monitor/ | Evaluation & monitoring overview |
| https://docs.databricks.com/aws/en/mlflow3/genai/tracing/ | Tracing API, span types |
| https://docs.databricks.com/aws/en/genie/conversation-api | Genie Agents API endpoints |
| https://docs.databricks.com/aws/en/mlflow3/genai/eval-monitor/production-monitoring | Production monitoring patterns |
| https://docs.databricks.com/aws/en/lakebase/ | Lakebase API, database operations |
| https://docs.databricks.com/aws/en/generative-ai/agent-framework/multi-agent-genie | Multi-agent patterns |

### `genai-agents/foundation/01-mlflow-genai-foundation`
| URL | Check For |
|---|---|
| https://mlflow.org/docs/latest/genai/serving/responses-agent | ResponsesAgent class, model signature inference |
| https://docs.databricks.com/aws/en/mlflow3/genai/tracing/app-instrumentation/automatic | Autolog integrations |
| https://mlflow.org/docs/latest/models.html#model-signature | Model signature spec |

### `genai-agents/foundation/02-experiment-tracing-and-uc-storage`
| URL | Check For |
|---|---|
| https://docs.databricks.com/aws/en/mlflow3/genai/tracing/trace-unity-catalog | UC OTEL trace storage, table schema, grants |
| https://docs.databricks.com/aws/en/mlflow3/genai/tracing/app-instrumentation/ | Auto/manual/combined tracing, decorators, span types |
| https://docs.databricks.com/aws/en/mlflow3/genai/tracing/third-party/otel-span-attributes | gen_ai.* semantic-convention attributes |

### `genai-agents/foundation/03-tools-and-data-access`, `04-ai-gateway`, `05-knowledge-assistant`
| URL | Check For |
|---|---|
| https://docs.databricks.com/aws/en/generative-ai/agent-framework/ | Tool calling, UC function tools |
| https://docs.databricks.com/aws/en/ai-gateway/ | AI Gateway config, rate limits, guardrails |
| https://docs.databricks.com/aws/en/generative-ai/agent-bricks/knowledge-assistant | Knowledge Assistant setup |

### `genai-agents/sdlc/01-prompt-registry`
| URL | Check For |
|---|---|
| https://docs.databricks.com/aws/en/mlflow3/genai/prompt-registry/ | Prompt registry API, UC-backed versioning |

### `genai-agents/sdlc/02-evaluation-datasets`, `04-evaluation-runs`
| URL | Check For |
|---|---|
| https://docs.databricks.com/aws/en/mlflow3/genai/eval-monitor/concepts/eval-harness | evaluate() harness, predict_fn, dataset contract |
| https://docs.databricks.com/aws/en/mlflow3/genai/eval-monitor/evaluate-conversations | Conversation (multi-turn) evaluation |

### `genai-agents/sdlc/03-scorers-and-judges`
| URL | Check For |
|---|---|
| https://docs.databricks.com/aws/en/mlflow3/genai/eval-monitor/concepts/scorers | Built-in scorers, judge model URI (provider:/model) |
| https://docs.databricks.com/aws/en/mlflow3/genai/eval-monitor/custom-judge/ | make_judge() import (mlflow.genai.judges), template vars, feedback_value_type |
| https://docs.databricks.com/aws/en/mlflow3/genai/eval-monitor/custom-scorers | @scorer decorator, code-based scorers |

### `genai-agents/sdlc/05-logged-model-and-uc-registration`, `06-deployment-and-automation`
| URL | Check For |
|---|---|
| https://docs.databricks.com/aws/en/mlflow3/genai/ | LoggedModel, UC model registration |
| https://docs.databricks.com/aws/en/dev-tools/bundles/ | Asset Bundle job triggers |
| https://docs.databricks.com/aws/en/machine-learning/model-serving/ | Serving endpoint deployment |

### `genai-agents/sdlc/07-production-monitoring`
| URL | Check For |
|---|---|
| https://docs.databricks.com/aws/en/mlflow3/genai/eval-monitor/production-monitoring | Registered scorers, sampling, backfill |
| https://docs.databricks.com/aws/en/mlflow3/genai/tracing/trace-unity-catalog | Trace archival, retention, monitoring warehouse |
| https://docs.databricks.com/aws/en/mlflow3/genai/human-feedback/ | Human feedback / labeling sessions |

### `genai-agents/tracks/*` (custom Agent App)
| URL | Check For |
|---|---|
| https://docs.databricks.com/aws/en/generative-ai/agent-framework/ | ResponsesAgent, agent framework patterns |
| https://docs.databricks.com/aws/en/machine-learning/model-serving/create-manage-serving-endpoints | OBO auth, SystemAuthPolicy |
| https://docs.databricks.com/aws/en/lakebase/ | Lakebase memory (short/long-term) |

---

## Semantic Layer Domain (High Volatility)

### `semantic-layer/00-semantic-layer-setup`
| URL | Check For |
|---|---|
| https://docs.databricks.com/aws/en/metric-views/semantic-metadata | Metric view overview |
| https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-qry-select-tvf | TVF syntax |
| https://docs.databricks.com/aws/en/genie/trusted-assets | Genie trusted assets |
| https://docs.databricks.com/api/workspace/genie | Genie API endpoints |

### `semantic-layer/01-metric-views-patterns`
| URL | Check For |
|---|---|
| https://docs.databricks.com/aws/en/metric-views/create/sql | CREATE VIEW WITH METRICS syntax |
| https://docs.databricks.com/aws/en/metric-views/yaml-ref | YAML field names, supported types |
| https://docs.databricks.com/aws/en/metric-views/semantic-metadata | Semantic metadata spec version |
| https://docs.databricks.com/aws/en/metric-views/joins | Join syntax, snowflake schema |
| https://docs.databricks.com/aws/en/metric-views/measure-formats | Measure format options |

### `semantic-layer/02-databricks-table-valued-functions`
| URL | Check For |
|---|---|
| https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-qry-select-tvf | TVF SQL syntax |
| https://docs.databricks.com/aws/en/genie/trusted-assets#tips-for-writing-functions | Genie TVF requirements |

### `semantic-layer/03-genie-space-patterns`
| URL | Check For |
|---|---|
| https://docs.databricks.com/aws/en/genie/trusted-assets | Trusted asset configuration |
| https://docs.databricks.com/api/workspace/genie | API endpoints, space schema |

### `semantic-layer/04-genie-space-export-import-api`
| URL | Check For |
|---|---|
| https://docs.databricks.com/api/workspace/genie/createspace | Create Space request/response schema |
| https://docs.databricks.com/api/workspace/genie/updatespace | Update Space API |
| https://docs.databricks.com/api/workspace/genie/listspaces | List Spaces API |
| https://docs.databricks.com/genie/ | Genie overview, new features |

### `semantic-layer/05-genie-optimization-orchestrator`
| URL | Check For |
|---|---|
| https://docs.databricks.com/api/workspace/genie | Conversation API schema |
| https://docs.databricks.com/aws/en/genie/trusted-assets | Control levers, asset types |

---

## Monitoring Domain (Medium Volatility)

### `monitoring/00-observability-setup`
| URL | Check For |
|---|---|
| https://learn.microsoft.com/en-us/azure/databricks/lakehouse-monitoring/create-monitor-api | Monitor creation API |
| https://docs.databricks.com/aws/en/dashboards/ | Dashboard API |
| https://docs.databricks.com/api/workspace/alerts | Alerts API v2 |

### `monitoring/01-lakehouse-monitoring-comprehensive`
| URL | Check For |
|---|---|
| https://databricks-sdk-py.readthedocs.io/en/latest/workspace/dataquality/data_quality.html | DataQualityAPI method signatures: create_monitor(monitor), create_refresh(object_type, object_id, refresh), delete_monitor, get_monitor, list_refresh, cancel_refresh, update_monitor(object_type, object_id, monitor, update_mask) |
| https://databricks-sdk-py.readthedocs.io/en/latest/dbdataclasses/dataquality.html | Monitor, DataProfilingConfig, DataProfilingCustomMetric, DataProfilingCustomMetricType, TimeSeriesConfig, SnapshotConfig, AggregationGranularity, RefreshState field names and enum values |
| https://docs.databricks.com/api/azure/workspace/dataquality/createmonitor | REST API request/response schema |
| https://learn.microsoft.com/en-us/azure/databricks/lakehouse-monitoring/ | Monitoring overview |
| https://learn.microsoft.com/en-us/azure/databricks/lakehouse-monitoring/custom-metrics | Custom metric syntax (AGGREGATE, DERIVED, DRIFT), output_data_type format |
| https://learn.microsoft.com/en-us/azure/databricks/lakehouse-monitoring/create-monitor-api | API reference |

### `monitoring/02-databricks-aibi-dashboards`
| URL | Check For |
|---|---|
| https://docs.databricks.com/aws/en/dashboards/ | Dashboard JSON schema, widget types |

### `monitoring/03-sql-alerting-patterns`
| URL | Check For |
|---|---|
| https://docs.databricks.com/api/workspace/alerts | Alert API v2 schema, condition types |

### `monitoring/04-anomaly-detection`
| URL | Check For |
|---|---|
| https://databricks-sdk-py.readthedocs.io/en/latest/workspace/dataquality/data_quality.html | DataQualityAPI method signatures: create_monitor(monitor), delete_monitor(object_type, object_id), get_monitor, update_monitor(object_type, object_id, monitor, update_mask), list_monitor (unimplemented) |
| https://databricks-sdk-py.readthedocs.io/en/latest/dbdataclasses/dataquality.html | Monitor, AnomalyDetectionConfig field names (excluded_table_full_names), object_type/object_id semantics |
| https://learn.microsoft.com/en-us/azure/databricks/data-quality-monitoring/anomaly-detection/ | Anomaly detection overview, freshness/completeness concepts |
| https://learn.microsoft.com/en-us/azure/databricks/data-quality-monitoring/anomaly-detection/results | system.data_quality_monitoring.table_results schema, nested struct fields |
| https://learn.microsoft.com/en-us/azure/databricks/data-quality-monitoring/anomaly-detection/alerts | Alert integration |

---

## Silver Layer Domain (Medium Volatility)

### `silver/00-silver-layer-setup`
| URL | Check For |
|---|---|
| https://docs.databricks.com/aws/en/dlt/expectations | DLT expectations API |
| https://docs.databricks.com/aws/en/ldp/expectation-patterns#portable-and-reusable-expectations | Portable expectations syntax |
| https://docs.databricks.com/aws/en/notebooks/share-code | Notebook sharing patterns |
| https://docs.databricks.com/aws/en/ldp/ | Lakeflow Declarative Pipelines overview |
| https://docs.databricks.com/aws/en/ldp/developer/python-ref | Python API (pyspark.pipelines) |

### `silver/01-dlt-expectations-patterns`
| URL | Check For |
|---|---|
| https://docs.databricks.com/aws/en/dlt/expectations | Expectation decorators, severity levels |
| https://docs.databricks.com/aws/en/ldp/expectation-patterns | Expectation patterns, quarantine |
| https://docs.databricks.com/aws/en/ldp/expectation-patterns#portable-and-reusable-expectations | Portable expectations |
| https://docs.databricks.com/aws/en/dlt/observability | DQ monitoring |

### `silver/02-dqx-patterns`
| URL | Check For |
|---|---|
| https://github.com/databrickslabs/dqx | DQX library version, API changes |
| https://github.com/databrickslabs/dqx/blob/main/CHANGELOG.md | Breaking changes, new features |

---

## ML Domain (High Volatility)

### `ml/00-ml-pipeline-setup`
| URL | Check For |
|---|---|
| https://learn.microsoft.com/en-us/azure/databricks/mlflow/experiments | Experiment API |
| https://docs.databricks.com/aws/en/mlflow/logged-model | LoggedModel API |
| https://learn.microsoft.com/en-us/azure/databricks/machine-learning/manage-model-lifecycle/ | UC Model Registry |
| https://learn.microsoft.com/en-us/azure/databricks/machine-learning/feature-store/ | Feature Store API |
| https://docs.databricks.com/aws/en/machine-learning/feature-store/uc/index.html | UC Feature Engineering |
| https://mlflow.org/docs/latest/models.html#model-signature | Model signature spec |

---

## Gold Layer Domain (Low Volatility)

### `gold/00-gold-layer-design`
| URL | Check For |
|---|---|
| https://docs.databricks.com/data-governance/unity-catalog/constraints.html | Constraint syntax |

### `gold/01-gold-layer-setup`
| URL | Check For |
|---|---|
| https://docs.databricks.com/data-governance/unity-catalog/constraints.html | Constraint syntax |
| https://docs.databricks.com/dev-tools/bundles/ | Asset Bundle patterns |

### `gold/pipeline-workers/01-yaml-table-setup`
| URL | Check For |
|---|---|
| https://docs.databricks.com/dev-tools/bundles/settings.html#sync | Bundle sync settings |
| https://docs.databricks.com/tables/constraints.html | Constraint syntax |

### `gold/design-workers/06-table-documentation`
| URL | Check For |
|---|---|
| https://docs.databricks.com/lakehouse-architecture/medallion.html | Medallion architecture |
| https://docs.databricks.com/tables/constraints.html#declare-primary-key-and-foreign-key-relationships | PK/FK syntax |

### `gold/design-workers/02-dimension-patterns`
| URL | Check For |
|---|---|
| https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/ | Dimension design patterns |

### `gold/design-workers/03-fact-table-patterns`
| URL | Check For |
|---|---|
| https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/ | Fact table design patterns |

### `gold/design-workers/04-conformed-dimensions`
| URL | Check For |
|---|---|
| https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/ | Conformed dimensions, bus matrix |

### `gold/design-workers/05-erd-diagrams`
| URL | Check For |
|---|---|
| https://docs.databricks.com/sql/language-manual/sql-ref-datatypes.html | Data types |

---

## Infrastructure/Common Domain (Medium Volatility)

### `skills/databricks-asset-bundles`
| URL | Check For |
|---|---|
| https://docs.databricks.com/dev-tools/bundles/ | Bundle YAML schema, task types |
| https://docs.databricks.com/aws/en/dev-tools/bundles/resources | Resource types |

### `common/databricks-autonomous-operations`
| URL | Check For |
|---|---|
| https://github.com/databricks/databricks-sdk-py | SDK version, API changes |

### `common/unity-catalog-constraints`
| URL | Check For |
|---|---|
| https://docs.databricks.com/aws/en/tables/constraints#declare-primary-key-and-foreign-key-relationships | Constraint syntax |

### `common/schema-management-patterns`
| URL | Check For |
|---|---|
| https://docs.databricks.com/aws/en/optimizations/predictive-optimization | Predictive optimization syntax |

### `common/databricks-table-properties`
| URL | Check For |
|---|---|
| https://docs.databricks.com/aws/en/delta/clustering | CLUSTER BY AUTO syntax |
| https://docs.databricks.com/aws/en/optimizations/predictive-optimization | Predictive optimization |

---

## Bronze Layer Domain (Low Volatility)

### `bronze/00-bronze-layer-setup`
| URL | Check For |
|---|---|
| https://docs.databricks.com/unity-catalog/ | UC table creation |
| https://docs.databricks.com/delta/ | Delta table features |
| https://docs.databricks.com/dev-tools/bundles/ | Asset Bundle patterns |

---

## Skills Without External Verification Sources

These skills are self-contained and don't reference external APIs that change:

| Skill | Reason |
|---|---|
| `admin/create-agent-skill` | Internal convention, AgentSkills.io spec is stable |
| `admin/self-improvement` | Internal workflow |
| `admin/documentation-organization` | Internal convention |
| `admin/skill-freshness-audit` | This skill (self-referential) |
| `skill-navigator` | Internal routing |
| `skills/databricks-expert-agent` | Philosophy/principles, not API-dependent |
| `common/databricks-python-imports` | Stable Python import patterns |
| `common/naming-tagging-standards` | Internal convention |
| `gold/pipeline-workers/02-merge-patterns` | Stable MERGE SQL patterns |
| `gold/pipeline-workers/03-deduplication` | Stable deduplication patterns |
| `gold/pipeline-workers/04-grain-validation` | Stable grain validation logic |
| `gold/pipeline-workers/05-schema-validation` | Stable schema validation logic |
| `exploration/00-adhoc-exploration-notebooks` | Stable notebook patterns |
| `planning/00-project-planning` | Internal planning methodology |
