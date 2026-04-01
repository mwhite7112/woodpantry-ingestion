"""Pantry ingest worker — consumes pantry.ingest.requested events.

Flow:
1. Parse the event payload (job_id, raw_text)
2. Call LLM to extract items
3. Resolve each item via Dictionary Service
4. POST staged items to Pantry Service
"""

import json
import logging

import aio_pika

from app.clients.dictionary import resolve
from app.clients.pantry import stage_items
from app.events.publisher import publish_pantry_ingest_failed
from app.llm.openai import extract_pantry

logger = logging.getLogger(__name__)


async def handle_pantry_ingest_requested(
    message: aio_pika.abc.AbstractIncomingMessage,
) -> None:
    """Process a pantry.ingest.requested event."""
    async with message.process():
        body = json.loads(message.body)
        job_id = body.get("job_id", "unknown")

        logger.info("Processing pantry ingest for job %s", job_id)

        try:
            raw_text = body["raw_text"]
            extracted = await extract_pantry(raw_text)

            logger.info(
                "Extracted %d items for job %s",
                len(extracted.items),
                job_id,
            )

            # Resolve each item against the Dictionary Service
            resolved_ids: dict[int, str | None] = {}
            for i, item in enumerate(extracted.items):
                try:
                    result = await resolve(item.name)
                    resolved_ids[i] = result.ingredient_id
                except Exception:
                    logger.warning(
                        "Dictionary resolve failed for %r in job %s",
                        item.name,
                        job_id,
                        exc_info=True,
                    )
                    resolved_ids[i] = None

            # POST staged items to Pantry Service
            stage_result = await stage_items(
                job_id=job_id,
                items=extracted.items,
                resolved_ids=resolved_ids,
            )

            logger.info(
                "Pantry ingest staged for job %s: %d items, %d need review",
                job_id,
                stage_result.staged_count,
                stage_result.needs_review_count,
            )

        except Exception:
            logger.exception("Pantry ingest failed for job %s", job_id)
            await publish_pantry_ingest_failed(
                job_id=job_id,
                error=f"Pantry ingest failed for job {job_id}",
            )
