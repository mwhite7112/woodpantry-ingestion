import json
import logging

from openai import AsyncOpenAI
from pydantic import ValidationError

from app.config import settings
from app.prompts.recipe import RECIPE_EXTRACTION_SYSTEM_PROMPT, StagedRecipe

logger = logging.getLogger(__name__)

_client = AsyncOpenAI(api_key=settings.openai_api_key)


async def extract_recipe(raw_text: str) -> StagedRecipe:
    """Call OpenAI to extract structured recipe data from raw text."""
    response = await _client.chat.completions.create(
        model=settings.extract_model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": RECIPE_EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": raw_text},
        ],
    )

    content = response.choices[0].message.content
    if not content:
        raise ValueError("OpenAI returned empty response")

    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"OpenAI returned invalid JSON: {e}") from e

    try:
        return StagedRecipe.model_validate(data)
    except ValidationError as e:
        raise ValueError(f"LLM output failed validation: {e}") from e
