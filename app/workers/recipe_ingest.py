import json
import logging

import aio_pika

from app.events.publisher import publish_recipe_import_failed, publish_recipe_imported
from app.llm.openai import extract_recipe

logger = logging.getLogger(__name__)


async def handle_recipe_import_requested(
    message: aio_pika.abc.AbstractIncomingMessage,
) -> None:
    """Process a recipe.import.requested event.

    1. Parse the event payload (job_id, raw_input)
    2. Call LLM to extract structured recipe
    3. Publish recipe.imported with staged data or failure
    """
    async with message.process():
        body = json.loads(message.body)
        job_id = body.get("job_id", "unknown")

        logger.info("Processing recipe import for job %s", job_id)

        try:
            raw_input = body["raw_input"]
            staged = await extract_recipe(raw_input)

            await publish_recipe_imported(
                job_id=job_id,
                staged_data=staged.model_dump(exclude_none=True),
            )
        except Exception:
            logger.exception("Recipe import failed for job %s", job_id)
            await publish_recipe_import_failed(
                job_id=job_id,
                error=f"Extraction failed for job {job_id}",
            )
