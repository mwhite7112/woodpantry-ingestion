"""Tests for RabbitMQ message handler workers."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

from app.clients.dictionary import ResolveResult
from app.clients.pantry import StageResult
from app.prompts.pantry import ExtractedItem, ExtractionResponse
from app.prompts.recipe import StagedIngredient, StagedRecipe


def _make_message(body: dict) -> AsyncMock:
    """Create a mock aio-pika IncomingMessage."""
    msg = AsyncMock()
    msg.body = json.dumps(body).encode()
    # message.process() returns an async context manager (not an awaitable).
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock()
    ctx.__aexit__ = AsyncMock(return_value=False)
    msg.process = MagicMock(return_value=ctx)
    return msg


class TestRecipeImportWorker:
    @patch("app.workers.recipe_ingest.publish_recipe_import_failed", new_callable=AsyncMock)
    @patch("app.workers.recipe_ingest.publish_recipe_imported", new_callable=AsyncMock)
    @patch("app.workers.recipe_ingest.extract_recipe", new_callable=AsyncMock)
    async def test_success(self, mock_extract, mock_publish_ok, mock_publish_fail):
        staged = StagedRecipe(
            title="Test Soup",
            ingredients=[StagedIngredient(name="onion", quantity=1, unit="each")],
        )
        mock_extract.return_value = staged

        msg = _make_message({"job_id": "job-1", "raw_input": "make test soup with onion"})

        from app.workers.recipe_ingest import handle_recipe_import_requested

        await handle_recipe_import_requested(msg)

        mock_extract.assert_awaited_once_with("make test soup with onion")
        mock_publish_ok.assert_awaited_once()
        call_kwargs = mock_publish_ok.call_args
        assert call_kwargs.kwargs["job_id"] == "job-1"
        mock_publish_fail.assert_not_awaited()

    @patch("app.workers.recipe_ingest.publish_recipe_import_failed", new_callable=AsyncMock)
    @patch("app.workers.recipe_ingest.publish_recipe_imported", new_callable=AsyncMock)
    @patch("app.workers.recipe_ingest.extract_recipe", new_callable=AsyncMock)
    async def test_extraction_failure_publishes_failed(
        self, mock_extract, mock_publish_ok, mock_publish_fail
    ):
        mock_extract.side_effect = ValueError("LLM returned garbage")

        msg = _make_message({"job_id": "job-bad", "raw_input": "not a recipe"})

        from app.workers.recipe_ingest import handle_recipe_import_requested

        await handle_recipe_import_requested(msg)

        mock_publish_ok.assert_not_awaited()
        mock_publish_fail.assert_awaited_once()
        assert mock_publish_fail.call_args.kwargs["job_id"] == "job-bad"

    @patch("app.workers.recipe_ingest.publish_recipe_import_failed", new_callable=AsyncMock)
    @patch("app.workers.recipe_ingest.publish_recipe_imported", new_callable=AsyncMock)
    @patch("app.workers.recipe_ingest.extract_recipe", new_callable=AsyncMock)
    async def test_missing_raw_input_publishes_failed(
        self, mock_extract, mock_publish_ok, mock_publish_fail
    ):
        msg = _make_message({"job_id": "job-no-input"})

        from app.workers.recipe_ingest import handle_recipe_import_requested

        await handle_recipe_import_requested(msg)

        mock_extract.assert_not_awaited()
        mock_publish_fail.assert_awaited_once()


class TestPantryIngestWorker:
    @patch("app.workers.pantry_ingest.stage_items", new_callable=AsyncMock)
    @patch("app.workers.pantry_ingest.resolve", new_callable=AsyncMock)
    @patch("app.workers.pantry_ingest.extract_pantry", new_callable=AsyncMock)
    async def test_success(self, mock_extract, mock_resolve, mock_stage):
        mock_extract.return_value = ExtractionResponse(
            items=[
                ExtractedItem(
                    raw_text="2 lbs chicken",
                    name="chicken",
                    quantity=2.0,
                    unit="lbs",
                    confidence=0.95,
                ),
            ]
        )
        mock_resolve.return_value = ResolveResult(
            ingredient_id="uuid-chicken", confidence=0.95, created=False
        )
        mock_stage.return_value = StageResult(staged_count=1, needs_review_count=0)

        msg = _make_message({"job_id": "job-p1", "raw_text": "2 lbs chicken"})

        from app.workers.pantry_ingest import handle_pantry_ingest_requested

        await handle_pantry_ingest_requested(msg)

        mock_extract.assert_awaited_once_with("2 lbs chicken")
        mock_resolve.assert_awaited_once_with("chicken")
        mock_stage.assert_awaited_once()

    @patch("app.workers.pantry_ingest.stage_items", new_callable=AsyncMock)
    @patch("app.workers.pantry_ingest.resolve", new_callable=AsyncMock)
    @patch("app.workers.pantry_ingest.extract_pantry", new_callable=AsyncMock)
    async def test_resolve_failure_continues(self, mock_extract, mock_resolve, mock_stage):
        """If dictionary resolve fails for one item, it should continue with None."""
        mock_extract.return_value = ExtractionResponse(
            items=[
                ExtractedItem(
                    raw_text="mystery item",
                    name="mystery",
                    quantity=1.0,
                    unit="each",
                    confidence=0.5,
                ),
            ]
        )
        mock_resolve.side_effect = Exception("Dictionary unavailable")
        mock_stage.return_value = StageResult(staged_count=1, needs_review_count=1)

        msg = _make_message({"job_id": "job-p2", "raw_text": "mystery item"})

        from app.workers.pantry_ingest import handle_pantry_ingest_requested

        await handle_pantry_ingest_requested(msg)

        # Should still call stage_items with None for the unresolved ingredient
        mock_stage.assert_awaited_once()
        call_args = mock_stage.call_args
        assert call_args.kwargs["resolved_ids"] == {0: None}

    @patch("app.workers.pantry_ingest.stage_items", new_callable=AsyncMock)
    @patch("app.workers.pantry_ingest.resolve", new_callable=AsyncMock)
    @patch("app.workers.pantry_ingest.extract_pantry", new_callable=AsyncMock)
    async def test_extraction_failure_does_not_crash(self, mock_extract, mock_resolve, mock_stage):
        mock_extract.side_effect = ValueError("LLM error")

        msg = _make_message({"job_id": "job-p3", "raw_text": "garbage"})

        from app.workers.pantry_ingest import handle_pantry_ingest_requested

        # Should not raise — the worker catches and logs
        await handle_pantry_ingest_requested(msg)

        mock_resolve.assert_not_awaited()
        mock_stage.assert_not_awaited()
