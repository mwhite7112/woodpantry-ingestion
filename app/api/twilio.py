"""Twilio inbound webhook handler."""

import asyncio
import logging
from urllib.parse import parse_qsl
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, Response, status
from twilio.request_validator import RequestValidator
from twilio.rest import Client

from app.clients.pantry import confirm_job
from app.config import settings
from app.events.publisher import publish_pantry_ingest_requested
from app.workers.job_registry import job_registry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/twilio", tags=["twilio"])

EMPTY_TWIML_RESPONSE = "<Response></Response>"


def _empty_twiml(status_code: int = status.HTTP_200_OK) -> Response:
    return Response(
        content=EMPTY_TWIML_RESPONSE,
        media_type="application/xml",
        status_code=status_code,
    )


def _build_stage_complete_message(staged_count: int, needs_review_count: int) -> str:
    return (
        f"{staged_count} items staged. "
        f"{needs_review_count} need review. "
        "Reply CONFIRM to add them to your pantry."
    )


def _build_confirmed_message() -> str:
    return "Done. Your latest staged pantry items were added to the pantry."


def _build_no_pending_message() -> str:
    return "No pending pantry ingest job was found for this number."


def _build_twilio_validator() -> RequestValidator:
    if not settings.twilio_signature_validation_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Twilio signature validation is not configured",
        )
    return RequestValidator(settings.twilio_auth_token)


async def _validate_twilio_request(request: Request) -> dict[str, str]:
    signature = request.headers.get("X-Twilio-Signature")
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing Twilio signature",
        )

    body = await request.body()
    params = dict(parse_qsl(body.decode("utf-8"), keep_blank_values=True))
    validator = _build_twilio_validator()

    if not validator.validate(str(request.url), params, signature):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid Twilio signature",
        )
    return params


async def send_outbound_sms(to_number: str, body: str) -> None:
    """Send an outbound SMS via Twilio's REST API."""
    if not settings.twilio_outbound_enabled:
        logger.warning("Twilio outbound SMS skipped; credentials are not fully configured")
        return

    def _send() -> None:
        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        client.messages.create(
            body=body,
            from_=settings.twilio_from_number,
            to=to_number,
        )

    await asyncio.to_thread(_send)


@router.post("/inbound")
async def inbound_sms(request: Request) -> Response:
    """Handle inbound Twilio SMS for pantry ingest and CONFIRM replies."""
    params = await _validate_twilio_request(request)
    from_number = params.get("From", "").strip()
    body = params.get("Body", "").strip()

    if not from_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing From phone number",
        )

    if body.upper() == "CONFIRM":
        job_id = job_registry.latest_pending(from_number)
        if job_id is None:
            await send_outbound_sms(from_number, _build_no_pending_message())
            return _empty_twiml()

        await confirm_job(job_id)
        job_registry.remove_job(job_id)
        await send_outbound_sms(from_number, _build_confirmed_message())
        return _empty_twiml()

    if not body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing SMS body",
        )

    job_id = str(uuid4())
    job_registry.track_job(from_number, job_id)
    await publish_pantry_ingest_requested(
        job_id=job_id,
        raw_text=body,
        from_number=from_number,
    )
    return _empty_twiml(status.HTTP_202_ACCEPTED)
