"""Tests for the RabbitMQ event publisher."""

import json
from unittest.mock import AsyncMock

import pytest

from app.events import publisher


class TestPublisher:
    @pytest.fixture(autouse=True)
    def _reset_publisher(self):
        """Reset module-level publisher state between tests."""
        publisher._channel = None
        publisher._exchange = None
        yield
        publisher._channel = None
        publisher._exchange = None

    async def test_init_publisher(self):
        mock_channel = AsyncMock()
        mock_exchange = AsyncMock()
        mock_channel.declare_exchange = AsyncMock(return_value=mock_exchange)

        await publisher.init_publisher(mock_channel)

        mock_channel.declare_exchange.assert_awaited_once_with(
            "woodpantry.topic",
            publisher.aio_pika.ExchangeType.TOPIC,
            durable=True,
        )
        assert publisher._exchange is mock_exchange

    async def test_publish_recipe_imported(self):
        mock_exchange = AsyncMock()
        publisher._exchange = mock_exchange

        staged_data = {"title": "Test", "ingredients": []}
        await publisher.publish_recipe_imported("job-1", staged_data)

        mock_exchange.publish.assert_awaited_once()
        call_args = mock_exchange.publish.call_args
        message = call_args.args[0]
        body = json.loads(message.body)
        assert body["job_id"] == "job-1"
        assert body["status"] == "staged"
        assert body["staged_data"] == staged_data
        assert call_args.kwargs["routing_key"] == "recipe.imported"

    async def test_publish_recipe_import_failed(self):
        mock_exchange = AsyncMock()
        publisher._exchange = mock_exchange

        await publisher.publish_recipe_import_failed("job-bad", "extraction error")

        call_args = mock_exchange.publish.call_args
        body = json.loads(call_args.args[0].body)
        assert body["status"] == "failed"
        assert body["error"] == "extraction error"

    async def test_publish_without_init_raises(self):
        with pytest.raises(RuntimeError, match="not initialized"):
            await publisher._publish("some.key", {"data": "test"})
