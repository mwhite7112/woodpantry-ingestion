"""Tests for Pydantic extraction models."""

import pytest
from pydantic import ValidationError

from app.prompts.pantry import ExtractedItem, ExtractionResponse
from app.prompts.recipe import StagedIngredient, StagedRecipe


class TestStagedRecipe:
    def test_minimal(self):
        recipe = StagedRecipe(
            title="Test Soup",
            ingredients=[StagedIngredient(name="onion")],
        )
        assert recipe.title == "Test Soup"
        assert len(recipe.ingredients) == 1
        assert recipe.description is None

    def test_full(self):
        recipe = StagedRecipe(
            title="Chicken Stir Fry",
            description="Quick weeknight dinner",
            servings=4,
            prep_minutes=10,
            cook_minutes=15,
            tags=["asian", "quick"],
            steps=["Slice chicken", "Heat oil", "Stir fry"],
            ingredients=[
                StagedIngredient(
                    name="chicken breast",
                    quantity=1.5,
                    unit="lbs",
                    preparation_notes="sliced thin",
                ),
                StagedIngredient(name="soy sauce", quantity=2, unit="tbsp"),
            ],
        )
        assert recipe.servings == 4
        assert len(recipe.ingredients) == 2
        assert recipe.ingredients[0].preparation_notes == "sliced thin"

    def test_missing_title_raises(self):
        with pytest.raises(ValidationError):
            StagedRecipe(ingredients=[StagedIngredient(name="onion")])

    def test_missing_ingredients_raises(self):
        with pytest.raises(ValidationError):
            StagedRecipe(title="Bad Recipe")

    def test_empty_ingredients_allowed(self):
        recipe = StagedRecipe(title="Empty Recipe", ingredients=[])
        assert recipe.ingredients == []

    def test_optional_ingredient_default(self):
        ing = StagedIngredient(name="cilantro")
        assert ing.is_optional is False
        assert ing.quantity is None
        assert ing.unit is None


class TestExtractionResponse:
    def test_valid(self):
        resp = ExtractionResponse(
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
        assert len(resp.items) == 1
        assert resp.items[0].confidence == 0.95

    def test_empty_items(self):
        resp = ExtractionResponse(items=[])
        assert resp.items == []

    def test_missing_required_field_raises(self):
        with pytest.raises(ValidationError):
            ExtractedItem(raw_text="chicken", name="chicken", quantity=2.0, unit="lbs")

    def test_from_dict(self):
        data = {
            "items": [
                {
                    "raw_text": "3 onions",
                    "name": "onion",
                    "quantity": 3.0,
                    "unit": "each",
                    "confidence": 0.9,
                }
            ]
        }
        resp = ExtractionResponse.model_validate(data)
        assert resp.items[0].name == "onion"
