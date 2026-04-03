"""In-memory phone-to-job mapping for Twilio SMS CONFIRM flow."""

import time
from dataclasses import dataclass


@dataclass
class JobEntry:
    phone: str
    created_at: float
    expires_at: float
    ready_for_confirmation: bool = False


class JobRegistry:
    """Track Twilio SMS pantry jobs until the user replies CONFIRM."""

    def __init__(self, ttl_seconds: int = 1800):
        self._ttl = ttl_seconds
        self._jobs_by_id: dict[str, JobEntry] = {}

    def track_job(self, phone: str, job_id: str) -> None:
        now = time.time()
        self._jobs_by_id[job_id] = JobEntry(
            phone=phone,
            created_at=now,
            expires_at=now + self._ttl,
        )
        self._prune_expired()

    def register(self, phone: str, job_id: str) -> None:
        """Compatibility helper for tests that expect immediate lookup success."""
        self.track_job(phone, job_id)
        self.mark_ready(job_id)

    def mark_ready(self, job_id: str) -> None:
        self._prune_expired()
        entry = self._jobs_by_id.get(job_id)
        if entry is not None:
            entry.ready_for_confirmation = True

    def lookup(self, phone: str) -> str | None:
        return self.latest_pending(phone)

    def latest_pending(self, phone: str) -> str | None:
        self._prune_expired()
        ready_jobs = [
            (job_id, entry)
            for job_id, entry in self._jobs_by_id.items()
            if entry.phone == phone and entry.ready_for_confirmation
        ]
        if not ready_jobs:
            return None
        job_id, _entry = max(ready_jobs, key=lambda item: item[1].created_at)
        return job_id

    def phone_for(self, job_id: str) -> str | None:
        self._prune_expired()
        entry = self._jobs_by_id.get(job_id)
        if entry is None:
            return None
        return entry.phone

    def remove(self, phone: str) -> None:
        job_ids = [
            job_id for job_id, entry in self._jobs_by_id.items() if entry.phone == phone
        ]
        for job_id in job_ids:
            self._jobs_by_id.pop(job_id, None)

    def remove_job(self, job_id: str) -> None:
        self._jobs_by_id.pop(job_id, None)

    def _prune_expired(self) -> None:
        now = time.time()
        expired_job_ids = [
            job_id
            for job_id, entry in self._jobs_by_id.items()
            if now > entry.expires_at
        ]
        for job_id in expired_job_ids:
            self._jobs_by_id.pop(job_id, None)


job_registry = JobRegistry()
