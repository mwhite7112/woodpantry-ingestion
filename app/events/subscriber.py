import logging
from collections.abc import Callable, Coroutine
from typing import Any

import aio_pika

logger = logging.getLogger(__name__)


async def start_consumer(
    channel: aio_pika.abc.AbstractChannel,
    queue_name: str,
    routing_key: str,
    handler: Callable[[aio_pika.abc.AbstractIncomingMessage], Coroutine[Any, Any, None]],
) -> None:
    """Declare exchange + queue, bind, and start consuming messages."""
    exchange = await channel.declare_exchange(
        "woodpantry.topic",
        aio_pika.ExchangeType.TOPIC,
        durable=True,
    )

    queue = await channel.declare_queue(queue_name, durable=True)
    await queue.bind(exchange, routing_key=routing_key)

    logger.info("Consuming %s (bound to %s)", queue_name, routing_key)
    await queue.consume(handler)
