import json
import logging

import aio_pika

logger = logging.getLogger(__name__)

_channel: aio_pika.abc.AbstractChannel | None = None
_exchange: aio_pika.abc.AbstractExchange | None = None


async def init_publisher(channel: aio_pika.abc.AbstractChannel) -> None:
    """Initialize the publisher with a channel and declare the exchange."""
    global _channel, _exchange
    _channel = channel
    _exchange = await channel.declare_exchange(
        "woodpantry.topic",
        aio_pika.ExchangeType.TOPIC,
        durable=True,
    )


async def publish_recipe_imported(
    job_id: str,
    staged_data: dict,
) -> None:
    """Publish a recipe.imported event with status=staged."""
    body = {
        "job_id": job_id,
        "status": "staged",
        "staged_data": staged_data,
    }
    await _publish("recipe.imported", body)
    logger.info("Published recipe.imported (staged) for job %s", job_id)


async def publish_recipe_import_failed(
    job_id: str,
    error: str,
) -> None:
    """Publish a recipe.imported event with status=failed."""
    body = {
        "job_id": job_id,
        "status": "failed",
        "error": error,
    }
    await _publish("recipe.imported", body)
    logger.warning("Published recipe.imported (failed) for job %s: %s", job_id, error)


async def _publish(routing_key: str, body: dict) -> None:
    if _exchange is None:
        raise RuntimeError("Publisher not initialized — call init_publisher first")

    message = aio_pika.Message(
        body=json.dumps(body).encode(),
        content_type="application/json",
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
    )
    await _exchange.publish(message, routing_key=routing_key)
