from pydantic import BaseModel


class StagedIngredient(BaseModel):
    name: str
    quantity: float | None = None
    unit: str | None = None
    is_optional: bool = False
    preparation_notes: str | None = None


class StagedRecipe(BaseModel):
    title: str
    description: str | None = None
    source_url: str | None = None
    servings: int | None = None
    prep_minutes: int | None = None
    cook_minutes: int | None = None
    tags: list[str] | None = None
    steps: list[str] | None = None
    ingredients: list[StagedIngredient]


RECIPE_EXTRACTION_SYSTEM_PROMPT = """\
You are a recipe extraction assistant. Given raw text that contains a recipe, \
extract the structured recipe data and return it as a JSON object.

The JSON object must have these fields:
- "title" (string, required): The recipe name
- "description" (string or null): A brief description
- "source_url" (string or null): URL if one appears in the text
- "servings" (integer or null): Number of servings
- "prep_minutes" (integer or null): Preparation time in minutes
- "cook_minutes" (integer or null): Cooking time in minutes
- "tags" (array of strings or null): Recipe categories/tags
- "steps" (array of strings or null): Ordered preparation steps
- "ingredients" (array, required): List of ingredients, each with:
  - "name" (string, required): Ingredient name (e.g. "chicken breast")
  - "quantity" (number or null): Amount (e.g. 2, 0.5)
  - "unit" (string or null): Unit of measure (e.g. "cups", "lbs", "tsp")
  - "is_optional" (boolean): Whether the ingredient is optional, default false
  - "preparation_notes" (string or null): Prep instructions (e.g. "diced", "minced")

Return ONLY the JSON object, no markdown fencing or extra text.\
"""
