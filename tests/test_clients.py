"""Tests for HTTP service clients with mocked httpx."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.clients.dictionary import ResolveResult, resolve
from app.clients.pantry import StageResult, stage_items
from app.prompts.pantry import ExtractedItem


def _mock_response(json_data: dict | None = None, status_code: int = 200) -> httpx.Response:
    """Build a real httpx.Response with controlled data."""
    resp = httpx.Response(
        status_code=status_code,
        json=json_data,
        request=httpx.Request("POST", "http://test"),
    )
    return resp


class TestDictionaryClient:
    async def test_resolve_success(self):
        response_data = {
            "ingredient": {"ID": "uuid-123"},
            "confidence": 0.95,
            "created": False,
        }
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=_mock_response(response_data))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.clients.dictionary.httpx.AsyncClient", return_value=mock_client):
            result = await resolve("chicken breast")

        assert isinstance(result, ResolveResult)
        assert result.ingredient_id == "uuid-123"
        assert result.confidence == 0.95
        assert result.created is False

    async def test_resolve_created(self):
        response_data = {
            "ingredient": {"ID": "uuid-new"},
            "confidence": 1.0,
            "created": True,
        }
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=_mock_response(response_data))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.clients.dictionary.httpx.AsyncClient", return_value=mock_client):
            result = await resolve("dragon fruit")

        assert result.created is True

    async def test_resolve_http_error(self):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=_mock_response(status_code=500))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("app.clients.dictionary.httpx.AsyncClient", return_value=mock_client),
            pytest.raises(httpx.HTTPStatusError),
        ):
            await resolve("bad request")


class TestPantryClient:
    async def test_stage_items_success(self):
        response_data = {"staged_count": 2, "needs_review_count": 1}
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=_mock_response(response_data))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        items = [
            ExtractedItem(
                raw_text="2 lbs chicken",
                name="chicken",
                quantity=2.0,
                unit="lbs",
                confidence=0.95,
            ),
            ExtractedItem(
                raw_text="1 onion",
                name="onion",
                quantity=1.0,
                unit="each",
                confidence=0.8,
            ),
        ]
        resolved_ids = {0: "uuid-chicken", 1: None}

        with patch("app.clients.pantry.httpx.AsyncClient", return_value=mock_client):
            result = await stage_items("job-123", items, resolved_ids)

        assert isinstance(result, StageResult)
        assert result.staged_count == 2
        assert result.needs_review_count == 1

        # Verify the POST was called with the right path
        call_args = mock_client.post.call_args
        assert "/pantry/ingest/job-123/stage" in call_args.args[0]

    async def test_stage_items_http_error(self):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=_mock_response(status_code=422))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        items = [
            ExtractedItem(
                raw_text="milk",
                name="milk",
                quantity=1.0,
                unit="gallon",
                confidence=0.9,
            ),
        ]

        with (
            patch("app.clients.pantry.httpx.AsyncClient", return_value=mock_client),
            pytest.raises(httpx.HTTPStatusError),
        ):
            await stage_items("job-bad", items, {0: None})
