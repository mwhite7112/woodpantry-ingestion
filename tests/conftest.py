"""Shared fixtures for woodpantry-ingestion tests.

Sets required env vars before any app modules are imported, so that
Settings() and the module-level OpenAI client don't fail at import time.
"""

import os

# Must be set before importing anything from app.*
os.environ.setdefault("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-fake-key")
os.environ.setdefault("DICTIONARY_URL", "http://localhost:8081")
os.environ.setdefault("PANTRY_URL", "http://localhost:8083")
