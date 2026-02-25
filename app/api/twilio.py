"""Twilio inbound webhook handler.

TODO: Stub for W-5. Will handle:
- Inbound SMS with grocery lists → publish pantry.ingest.requested
- CONFIRM replies → commit staged items
- MMS with receipt photos → OCR extraction (Phase 3)
"""

from fastapi import APIRouter

router = APIRouter(prefix="/twilio", tags=["twilio"])


# Not wired into the app yet — will be included in W-5.
