"""Tests for LLM extraction functions with mocked OpenAI client."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.prompts.pantry import ExtractionResponse
from app.prompts.recipe import StagedRecipe


def _mock_completion(content: str | None) -> AsyncMock:
    """Build a mock OpenAI chat completion response."""
    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock()]
    mock_response.choices[0].message.content = content
    return mock_response


class TestExtractRecipe:
    @pytest.fixture(autouse=True)
    def _patch_client(self):
        with patch("app.llm.openai._client") as mock_client:
            self.mock_client = mock_client
            self.mock_create = AsyncMock()
            mock_client.chat.completions.create = self.mock_create
            yield

    async def test_valid_extraction(self):
        payload = {
            "title": "Pasta Carbonara",
            "ingredients": [
                {"name": "spaghetti", "quantity": 1, "unit": "lb"},
                {"name": "pancetta", "quantity": 4, "unit": "oz"},
            ],
        }
        self.mock_create.return_value = _mock_completion(json.dumps(payload))

        from app.llm.openai import extract_recipe

        result = await extract_recipe("Make pasta carbonara with spaghetti and pancetta")

        assert isinstance(result, StagedRecipe)
        assert result.title == "Pasta Carbonara"
        assert len(result.ingredients) == 2

    async def test_empty_response_raises(self):
        self.mock_create.return_value = _mock_completion(None)

        from app.llm.openai import extract_recipe

        with pytest.raises(ValueError, match="empty response"):
            await extract_recipe("some recipe text")

    async def test_invalid_json_raises(self):
        self.mock_create.return_value = _mock_completion("not json at all")

        from app.llm.openai import extract_recipe

        with pytest.raises(ValueError, match="invalid JSON"):
            await extract_recipe("some recipe text")

    async def test_validation_error_raises(self):
        # Valid JSON but missing required fields
        self.mock_create.return_value = _mock_completion(json.dumps({"bad": "data"}))

        from app.llm.openai import extract_recipe

        with pytest.raises(ValueError, match="failed validation"):
            await extract_recipe("some recipe text")


class TestExtractPantry:
    @pytest.fixture(autouse=True)
    def _patch_client(self):
        with patch("app.llm.openai._client") as mock_client:
            self.mock_client = mock_client
            self.mock_create = AsyncMock()
            mock_client.chat.completions.create = self.mock_create
            yield

    async def test_valid_extraction(self):
        payload = {
            "items": [
                {
                    "raw_text": "2 lbs chicken breast",
                    "name": "chicken breast",
                    "quantity": 2.0,
                    "unit": "lbs",
                    "confidence": 0.95,
                },
                {
                    "raw_text": "1 dozen eggs",
                    "name": "eggs",
                    "quantity": 12.0,
                    "unit": "each",
                    "confidence": 0.9,
                },
            ]
        }
        self.mock_create.return_value = _mock_completion(json.dumps(payload))

        from app.llm.openai import extract_pantry

        result = await extract_pantry("2 lbs chicken breast, 1 dozen eggs")

        assert isinstance(result, ExtractionResponse)
        assert len(result.items) == 2
        assert result.items[0].name == "chicken breast"

    async def test_empty_response_raises(self):
        self.mock_create.return_value = _mock_completion(None)

        from app.llm.openai import extract_pantry

        with pytest.raises(ValueError, match="empty response"):
            await extract_pantry("some items")

    async def test_empty_items_list(self):
        self.mock_create.return_value = _mock_completion(json.dumps({"items": []}))

        from app.llm.openai import extract_pantry

        result = await extract_pantry("")
        assert result.items == []
