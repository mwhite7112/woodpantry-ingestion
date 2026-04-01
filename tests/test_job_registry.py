"""Tests for the in-memory phone-to-job registry."""

from unittest.mock import patch

from app.workers.job_registry import JobRegistry


class TestJobRegistry:
    def test_register_and_lookup(self):
        reg = JobRegistry()
        reg.register("+15551234567", "job-abc")
        assert reg.lookup("+15551234567") == "job-abc"

    def test_lookup_missing(self):
        reg = JobRegistry()
        assert reg.lookup("+15559999999") is None

    def test_remove(self):
        reg = JobRegistry()
        reg.register("+15551234567", "job-abc")
        reg.remove("+15551234567")
        assert reg.lookup("+15551234567") is None

    def test_remove_missing_is_noop(self):
        reg = JobRegistry()
        reg.remove("+15559999999")  # should not raise

    def test_overwrite(self):
        reg = JobRegistry()
        reg.register("+15551234567", "job-1")
        reg.register("+15551234567", "job-2")
        assert reg.lookup("+15551234567") == "job-2"

    def test_ttl_expiry(self):
        reg = JobRegistry(ttl_seconds=60)
        reg.register("+15551234567", "job-abc")

        # Advance time past TTL
        with patch("app.workers.job_registry.time") as mock_time:
            mock_time.time.return_value = 9999999999.0
            assert reg.lookup("+15551234567") is None

    def test_not_expired(self):
        reg = JobRegistry(ttl_seconds=60)

        with patch("app.workers.job_registry.time") as mock_time:
            mock_time.time.return_value = 1000.0
            reg.register("+15551234567", "job-abc")

            mock_time.time.return_value = 1030.0  # 30s later, within TTL
            assert reg.lookup("+15551234567") == "job-abc"

    def test_multiple_phones(self):
        reg = JobRegistry()
        reg.register("+15551111111", "job-a")
        reg.register("+15552222222", "job-b")
        assert reg.lookup("+15551111111") == "job-a"
        assert reg.lookup("+15552222222") == "job-b"
