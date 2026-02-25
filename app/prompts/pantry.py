"""Pantry extraction prompt and Pydantic models.

TODO: Pantry ingest worker not implemented until W-2 adds the staging endpoint
to the Pantry Service. Models defined here to match the expected contract.
"""

from pydantic import BaseModel


class ExtractedItem(BaseModel):
    raw_text: str
    name: str
    quantity: float
    unit: str
    confidence: float


class ExtractionResponse(BaseModel):
    items: list[ExtractedItem]


PANTRY_EXTRACTION_SYSTEM_PROMPT = """\
You are a grocery list extraction assistant. Given raw text containing a list of \
grocery or pantry items, extract each item and return a JSON object.

The JSON object must have a single field "items", which is an array of objects. \
Each object must have:
- "raw_text" (string): The original text for this item
- "name" (string): The normalized ingredient name (e.g. "chicken breast")
- "quantity" (number): Amount (e.g. 2, 0.5). Use 1 if not specified.
- "unit" (string): Unit of measure (e.g. "lbs", "cups"). Use "each" if not specified.
- "confidence" (number 0-1): Your confidence that the extraction is correct

Return ONLY the JSON object, no markdown fencing or extra text.\
"""
