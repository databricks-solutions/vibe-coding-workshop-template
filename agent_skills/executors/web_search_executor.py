"""
Agent Skills - Web Search Executor
====================================

Executes web search skills using external providers (SerpAPI, Bing, Google CSE).
Falls back gracefully when no API key is configured.
"""

import logging
import os
import time
from typing import Any, Dict, List

from agent_skills.executors.base import BaseExecutor
from agent_skills.models import SkillManifest

logger = logging.getLogger(__name__)


class WebSearchExecutor(BaseExecutor):
    """
    Executor for web search skills.

    Supports multiple search providers and normalizes results into
    a consistent format of snippets and links.
    """

    def __init__(self, manifest: SkillManifest):
        super().__init__(manifest)

    async def _execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a web search."""
        query = inputs["query"]
        num_results = inputs.get("num_results", 10)

        provider = self._resolve_env_var(self.manifest.config.provider or "serpapi")
        api_key_env = self.manifest.config.api_key_env or "WEB_SEARCH_API_KEY"
        api_key = os.getenv(api_key_env)

        if not api_key:
            logger.warning("[WebSearchExecutor] No API key configured")
            return {
                "snippets": [],
                "links": [],
                "search_status": "no_config",
            }

        logger.info(f"[WebSearchExecutor] Searching with {provider}: {query[:80]}...")

        if provider == "serpapi":
            return await self._search_serpapi(query, api_key, num_results)
        elif provider == "bing":
            return await self._search_bing(query, api_key, num_results)
        elif provider == "google_cse":
            google_cse_id = os.getenv("GOOGLE_CSE_ID")
            return await self._search_google(query, api_key, google_cse_id, num_results)
        else:
            return {
                "snippets": [],
                "links": [],
                "search_status": "error",
                "error": f"Unknown provider: {provider}",
            }

    async def _search_serpapi(
        self, query: str, api_key: str, num_results: int
    ) -> Dict[str, Any]:
        """Search using SerpAPI."""
        import requests

        params = {
            "q": query + " hotels accommodations",
            "api_key": api_key,
            "num": num_results,
            "engine": "google",
        }

        response = requests.get(
            "https://serpapi.com/search", params=params, timeout=30
        )
        response.raise_for_status()
        data = response.json()

        return self._parse_organic_results(
            data.get("organic_results", []), num_results
        )

    async def _search_bing(
        self, query: str, api_key: str, num_results: int
    ) -> Dict[str, Any]:
        """Search using Bing API."""
        import requests

        headers = {"Ocp-Apim-Subscription-Key": api_key}
        params = {
            "q": query + " hotels accommodations",
            "count": num_results,
            "mkt": "en-US",
        }
        bing_endpoint = self.manifest.config.extra.get(
            "bing_endpoint", "https://api.bing.microsoft.com/v7.0/search"
        )

        response = requests.get(
            bing_endpoint, headers=headers, params=params, timeout=30
        )
        response.raise_for_status()
        data = response.json()

        snippets = []
        links = []
        for result in data.get("webPages", {}).get("value", [])[:num_results]:
            snippet = result.get("snippet", "")
            if snippet:
                snippets.append(snippet)
                links.append(
                    {
                        "title": result.get("name", ""),
                        "url": result.get("url", ""),
                        "snippet": snippet,
                    }
                )

        status = "ok" if snippets else "no_results"
        return {"snippets": snippets, "links": links, "search_status": status}

    async def _search_google(
        self, query: str, api_key: str, cse_id: str, num_results: int
    ) -> Dict[str, Any]:
        """Search using Google Custom Search."""
        import requests

        if not cse_id:
            return {
                "snippets": [],
                "links": [],
                "search_status": "no_config",
                "error": "Google CSE ID not configured",
            }

        params = {
            "key": api_key,
            "cx": cse_id,
            "q": query + " hotels accommodations",
            "num": min(num_results, 10),
        }

        response = requests.get(
            "https://www.googleapis.com/customsearch/v1",
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        snippets = []
        links = []
        for item in data.get("items", []):
            snippet = item.get("snippet", "")
            if snippet:
                snippets.append(snippet)
                links.append(
                    {
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "snippet": snippet,
                    }
                )

        status = "ok" if snippets else "no_results"
        return {"snippets": snippets, "links": links, "search_status": status}

    def _parse_organic_results(
        self, results: List[Dict], num_results: int
    ) -> Dict[str, Any]:
        """Parse SerpAPI organic results."""
        snippets = []
        links = []
        for result in results[:num_results]:
            snippet = result.get("snippet", "")
            if snippet:
                snippets.append(snippet)
                links.append(
                    {
                        "title": result.get("title", ""),
                        "url": result.get("link", ""),
                        "snippet": snippet,
                    }
                )

        status = "ok" if snippets else "no_results"
        return {"snippets": snippets, "links": links, "search_status": status}

    async def _mock_execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Return mock web search results."""
        time.sleep(0.5)
        return {
            "snippets": [
                "The best hotels near Miami concert venues include the Grand Hyatt.",
                "For concerts, fans recommend staying downtown for easy transit access.",
                "Budget-friendly options under $300/night include several boutique hotels.",
                "Many hotels offer shuttle service to major concert venues.",
                "Top-rated accommodations in Miami Beach feature ocean views.",
            ],
            "links": [
                {
                    "title": "Best Hotels Near Miami Concerts",
                    "url": "https://example.com/miami-hotels",
                    "snippet": "The best hotels near Miami concert venues include the Grand Hyatt.",
                },
                {
                    "title": "Where to Stay for Miami Events",
                    "url": "https://example.com/events-stay",
                    "snippet": "For concerts, fans recommend staying downtown.",
                },
            ],
            "search_status": "ok",
        }
