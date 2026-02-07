"""
Agent Skills - Executors
========================

Typed executor classes for each skill type. Each executor knows how to
interpret a skill manifest and run the corresponding action.

Executor Registry:
    - LLMCallExecutor        → Calls Databricks model serving endpoints
    - GenieQueryExecutor     → Queries Databricks Genie Space
    - WebSearchExecutor      → Performs external web searches
    - LakebaseQueryExecutor  → Queries Lakebase PostgreSQL database
    - FunctionExecutor       → Runs arbitrary Python functions
    - PromptRegistryExecutor → Fetches prompts from Databricks Prompt Registry
"""

from agent_skills.executors.base import BaseExecutor
from agent_skills.executors.llm_executor import LLMCallExecutor
from agent_skills.executors.genie_executor import GenieQueryExecutor
from agent_skills.executors.web_search_executor import WebSearchExecutor
from agent_skills.executors.lakebase_executor import LakebaseQueryExecutor
from agent_skills.executors.function_executor import FunctionExecutor
from agent_skills.executors.prompt_registry_executor import PromptRegistryExecutor

__all__ = [
    "BaseExecutor",
    "LLMCallExecutor",
    "GenieQueryExecutor",
    "WebSearchExecutor",
    "LakebaseQueryExecutor",
    "FunctionExecutor",
    "PromptRegistryExecutor",
]
