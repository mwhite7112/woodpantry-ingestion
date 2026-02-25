import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class ResolveResult:
    def __init__(self, ingredient_id: str, confidence: float, created: bool):
        self.ingredient_id = ingredient_id
        self.confidence = confidence
        self.created = created


async def resolve(name: str) -> ResolveResult:
    """Resolve an ingredient name via the Dictionary Service."""
    async with httpx.AsyncClient(base_url=settings.dictionary_url) as client:
        resp = await client.post("/ingredients/resolve", json={"name": name})
        resp.raise_for_status()
        data = resp.json()

    ingredient = data["ingredient"]
    return ResolveResult(
        ingredient_id=ingredient["ID"],
        confidence=data["confidence"],
        created=data["created"],
    )
