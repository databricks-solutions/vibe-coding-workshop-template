# Recommended Project File Structure

```
src/agents/
├── __init__.py
├── config.py                    # AgentSettings dataclass
├── agent.py                     # Main ResponsesAgent class
├── orchestrator.py              # LangGraph workflow definition
├── intent_classifier.py         # Domain routing logic
├── synthesizer.py               # Cross-domain response synthesis
│
├── genie/
│   ├── __init__.py
│   ├── client.py                # Genie API wrapper
│   ├── config.py                # Genie Space IDs and config
│   └── formatter.py             # Query result formatting
│
├── memory/
│   ├── __init__.py
│   ├── short_term.py            # CheckpointSaver wrapper
│   ├── long_term.py             # DatabricksStore wrapper
│   └── tools.py                 # LangChain memory tools
│
├── prompts/
│   ├── __init__.py
│   ├── registry.py              # Prompt definitions
│   ├── manager.py               # Load/update functions
│   └── ab_testing.py            # A/B testing logic
│
├── evaluation/
│   ├── __init__.py
│   ├── judges.py                # Custom scorer definitions
│   ├── helpers.py               # _extract_response_text, _call_llm_for_scoring
│   └── dataset.py               # Evaluation dataset management
│
├── monitoring/
│   ├── __init__.py
│   ├── scorers.py               # Production scorer definitions
│   ├── archival.py              # Trace archival configuration
│   └── dashboards.py            # Monitoring query helpers
│
├── setup/
│   ├── log_agent_model.py       # Model logging notebook
│   ├── deployment_job.py        # Evaluation + deployment notebook
│   ├── register_prompts.py      # Prompt registration notebook
│   ├── setup_lakebase.py        # Memory table setup notebook
│   └── register_scorers.py      # Production scorer registration
│
└── notebooks/
    ├── exploration.py           # Ad-hoc testing notebook
    └── genie_optimization.py    # Genie accuracy testing
```
