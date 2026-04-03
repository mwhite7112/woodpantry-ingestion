"""Tests for the Twilio webhook flow."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from fastapi import FastAPI

from app.api.twilio import router
from app.workers.job_registry import JobRegistry


class TestTwilioWebhook:
    async def test_inbound_sms_publishes_pantry_ingest_request(self):
        app = FastAPI()
        app.include_router(router)
        registry = JobRegistry()

        validator = MagicMock()
        validator.validate.return_value = True

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            with (
                patch("app.api.twilio.RequestValidator", return_value=validator),
                patch(
                    "app.api.twilio.publish_pantry_ingest_requested",
                    new=AsyncMock(),
                ) as mock_publish,
                patch("app.api.twilio.settings.twilio_auth_token", "test-token"),
                patch("app.api.twilio.job_registry", registry),
            ):
                response = await client.post(
                    "/twilio/inbound",
                    data={"From": "+15551234567", "Body": "milk, eggs"},
                    headers={"X-Twilio-Signature": "sig"},
                )

        assert response.status_code == 202
        mock_publish.assert_awaited_once()
        publish_call = mock_publish.call_args.kwargs
        assert publish_call["raw_text"] == "milk, eggs"
        assert publish_call["from_number"] == "+15551234567"
        assert publish_call["job_id"]
        assert registry.phone_for(publish_call["job_id"]) == "+15551234567"
        assert registry.latest_pending("+15551234567") is None

    async def test_invalid_signature_returns_403(self):
        app = FastAPI()
        app.include_router(router)

        validator = MagicMock()
        validator.validate.return_value = False

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            with (
                patch("app.api.twilio.RequestValidator", return_value=validator),
                patch(
                    "app.api.twilio.publish_pantry_ingest_requested",
                    new=AsyncMock(),
                ) as mock_publish,
                patch("app.api.twilio.settings.twilio_auth_token", "test-token"),
            ):
                response = await client.post(
                    "/twilio/inbound",
                    data={"From": "+15551234567", "Body": "milk, eggs"},
                    headers={"X-Twilio-Signature": "bad-sig"},
                )

        assert response.status_code == 403
        mock_publish.assert_not_awaited()

    async def test_confirm_routes_to_latest_pending_job(self):
        app = FastAPI()
        app.include_router(router)
        registry = JobRegistry()
        registry.track_job("+15551234567", "job-old")
        registry.track_job("+15551234567", "job-new")
        registry.mark_ready("job-old")
        registry.mark_ready("job-new")

        validator = MagicMock()
        validator.validate.return_value = True

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            with (
                patch("app.api.twilio.RequestValidator", return_value=validator),
                patch("app.api.twilio.confirm_job", new=AsyncMock()) as mock_confirm_job,
                patch("app.api.twilio.send_outbound_sms", new=AsyncMock()) as mock_send_sms,
                patch("app.api.twilio.settings.twilio_auth_token", "test-token"),
                patch("app.api.twilio.job_registry", registry),
            ):
                response = await client.post(
                    "/twilio/inbound",
                    data={"From": "+15551234567", "Body": "CONFIRM"},
                    headers={"X-Twilio-Signature": "sig"},
                )

        assert response.status_code == 200
        mock_confirm_job.assert_awaited_once_with("job-new")
        mock_send_sms.assert_awaited_once()
        assert registry.latest_pending("+15551234567") == "job-old"
