"""
Agent Skills - Lakebase Query Executor
========================================

Executes database queries against Lakebase (PostgreSQL) using the
existing LakebaseService from the server module.
"""

import logging
import time
from typing import Any, Dict, List

from agent_skills.executors.base import BaseExecutor
from agent_skills.models import SkillManifest

logger = logging.getLogger(__name__)


class LakebaseQueryExecutor(BaseExecutor):
    """
    Executor for Lakebase (PostgreSQL) database queries.

    Reuses the existing LakebaseService for connection management
    and OAuth authentication.
    """

    def __init__(self, manifest: SkillManifest):
        super().__init__(manifest)
        self._service = None

    def _get_service(self):
        """Get the Lakebase service instance."""
        if self._service is None:
            try:
                from server.services.lakebase import get_lakebase_service
                self._service = get_lakebase_service()
            except Exception as e:
                logger.error(f"[LakebaseExecutor] Failed to get LakebaseService: {e}")
                raise
        return self._service

    async def _execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a Lakebase query."""
        service = self._get_service()
        query_type = self.manifest.config.extra.get("query_type", "search_listings")

        if query_type == "search_listings":
            return await self._search_listings(service, inputs)
        elif query_type == "get_listing":
            return await self._get_listing(service, inputs)
        elif query_type == "get_reviews":
            return await self._get_reviews(service, inputs)
        elif query_type == "get_destinations":
            return await self._get_destinations(service)
        else:
            logger.warning(f"[LakebaseExecutor] Unknown query_type: {query_type}")
            return {"items": [], "total_count": 0}

    async def _search_listings(
        self, service: Any, inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Search listings from Lakebase."""
        location = inputs.get("location", "")
        guests = inputs.get("guests", 2)
        price_max = inputs.get("price_max")
        limit = inputs.get("limit", 10)

        results = service.search_listings(
            location=location,
            guests=guests,
            price_max=price_max,
            limit=limit,
        )

        if not results:
            return {"items": [], "total_count": 0}

        items = []
        for row in results:
            items.append({
                "id": f"stay_{row['id']}",
                "name": row["title"],
                "location": f"{row['city']}, {row['state']}",
                "pricePerNight": float(row["price_per_night"]),
                "rating": float(row.get("rating", 0)),
                "highlights": [
                    f"{row.get('bedrooms', 1)} bedrooms",
                    f"Up to {row.get('max_guests', 2)} guests",
                    row.get("property_type", "property").capitalize(),
                ],
                "source": "lakehouse",
                "reviewCount": row.get("review_count", 0),
            })

        # Apply rating filter if specified
        rating_min = inputs.get("rating_min")
        if rating_min:
            items = [i for i in items if i["rating"] >= rating_min]

        return {"items": items, "total_count": len(items)}

    async def _get_listing(
        self, service: Any, inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get a single listing by ID."""
        listing_id = inputs.get("listing_id", "")
        result = service.get_listing_by_id(listing_id)
        if result:
            return {"listing": result, "found": True}
        return {"listing": None, "found": False}

    async def _get_reviews(
        self, service: Any, inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get reviews for a listing."""
        listing_id = inputs.get("listing_id", "")
        limit = inputs.get("limit", 10)
        results = service.get_reviews_for_listing(listing_id, limit)
        return {"reviews": results or [], "total_count": len(results or [])}

    async def _get_destinations(self, service: Any) -> Dict[str, Any]:
        """Get popular destinations."""
        results = service.get_popular_destinations()
        return {"destinations": results or [], "total_count": len(results or [])}

    async def _mock_execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Return mock Lakebase results."""
        time.sleep(0.2)
        location = inputs.get("location", "Miami")
        return {
            "items": [
                {
                    "id": "stay_1",
                    "name": f"Beautiful Home in {location}",
                    "location": f"{location}, FL",
                    "pricePerNight": 189.0,
                    "rating": 4.7,
                    "highlights": ["3 bedrooms", "Up to 6 guests", "House"],
                    "source": "lakehouse",
                    "reviewCount": 23,
                },
                {
                    "id": "stay_2",
                    "name": f"Cozy Apartment in {location}",
                    "location": f"{location}, FL",
                    "pricePerNight": 129.0,
                    "rating": 4.5,
                    "highlights": ["1 bedroom", "Up to 3 guests", "Apartment"],
                    "source": "lakehouse",
                    "reviewCount": 15,
                },
            ],
            "total_count": 2,
        }
