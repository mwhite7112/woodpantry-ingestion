"""In-memory phone-to-job mapping for Twilio SMS CONFIRM flow.

TODO: Stub for W-5 (Twilio integration). Maps From phone number to the most
recent in-progress job ID so CONFIRM replies can be routed correctly.
"""

import time


class JobRegistry:
    """Simple dict with TTL for phone → job_id mapping."""

    def __init__(self, ttl_seconds: int = 1800):
        self._ttl = ttl_seconds
        self._jobs: dict[str, tuple[str, float]] = {}  # phone → (job_id, expires_at)

    def register(self, phone: str, job_id: str) -> None:
        self._jobs[phone] = (job_id, time.time() + self._ttl)

    def lookup(self, phone: str) -> str | None:
        entry = self._jobs.get(phone)
        if entry is None:
            return None
        job_id, expires_at = entry
        if time.time() > expires_at:
            del self._jobs[phone]
            return None
        return job_id

    def remove(self, phone: str) -> None:
        self._jobs.pop(phone, None)
