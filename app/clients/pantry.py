"""HTTP client for the Pantry Service."""

import logging
from dataclasses import dataclass

import httpx

from app.config import settings
from app.prompts.pantry import ExtractedItem

logger = logging.getLogger(__name__)


@dataclass
class StageResult:
    staged_count: int
    needs_review_count: int


async def stage_items(
    job_id: str,
    items: list[ExtractedItem],
    resolved_ids: dict[int, str | None],
) -> StageResult:
    """POST extracted items to the Pantry Service staging endpoint.

    Args:
        job_id: The ingestion job ID (created upstream by whoever published the event).
        items: Extracted items from LLM.
        resolved_ids: Map of item index → ingredient_id (or None if unresolved).
    """
    payload = {
        "items": [
            {
                "raw_text": item.raw_text,
                "ingredient_id": resolved_ids.get(i),
                "quantity": item.quantity,
                "unit": item.unit,
                "confidence": item.confidence,
            }
            for i, item in enumerate(items)
        ],
    }

    async with httpx.AsyncClient(base_url=settings.pantry_url) as client:
        resp = await client.post(
            f"/pantry/ingest/{job_id}/stage",
            json=payload,
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()

    return StageResult(
        staged_count=data["staged_count"],
        needs_review_count=data["needs_review_count"],
    )
