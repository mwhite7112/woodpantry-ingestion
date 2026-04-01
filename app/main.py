import logging
from contextlib import asynccontextmanager

import aio_pika
import uvicorn
from fastapi import FastAPI

from app.config import settings
from app.events.publisher import init_publisher
from app.events.subscriber import start_consumer
from app.workers.pantry_ingest import handle_pantry_ingest_requested
from app.workers.recipe_ingest import handle_recipe_import_requested

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start RabbitMQ consumers on startup, clean up on shutdown."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    connection: aio_pika.abc.AbstractConnection | None = None
    try:
        connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=10)

        await init_publisher(channel)

        await start_consumer(
            channel=channel,
            queue_name="ingestion.recipe-import-requested",
            routing_key="recipe.import.requested",
            handler=handle_recipe_import_requested,
        )

        if settings.pantry_url:
            await start_consumer(
                channel=channel,
                queue_name="ingestion.pantry-ingest-requested",
                routing_key="pantry.ingest.requested",
                handler=handle_pantry_ingest_requested,
            )
        else:
            logger.warning("PANTRY_URL not set — pantry ingest consumer not started")

        logger.info("RabbitMQ consumers started")
    except Exception:
        logger.exception("Failed to connect to RabbitMQ — consumers not started")

    yield

    if connection and not connection.is_closed:
        await connection.close()
        logger.info("RabbitMQ connection closed")


app = FastAPI(title="woodpantry-ingestion", lifespan=lifespan)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


def main():
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
