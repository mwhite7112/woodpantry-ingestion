# woodpantry-ingestion

Ingestion Pipeline for WoodPantry. The only service that handles raw, dirty input — receipt photos, SMS messages, free-text blobs. Processes input via LLM, resolves ingredients against the Dictionary, and posts structured staged data to core services.

Written in **Python** (FastAPI + aio-pika + httpx). Purely I/O bound — LLM API calls, HTTP calls to other services, RabbitMQ. No CPU-intensive work.

**Phase 2+ only.** In Phase 1, Recipe and Pantry services call the OpenAI API directly. This service extracts that logic and makes all ingest flows async via RabbitMQ.

## HTTP Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/healthz` | Health check |
| POST | `/twilio/inbound` | Twilio inbound SMS/MMS webhook (W-5) |

All other processing is queue-driven.

## Queue Events

| Event | Direction | Description |
|-------|-----------|-------------|
| `recipe.import.requested` | Subscribes | Triggers recipe extraction worker |
| `recipe.imported` | Publishes | Structured recipe payload after extraction |
| `pantry.ingest.requested` | Subscribes | Triggers pantry extraction worker |

## Tech Stack

| Concern | Library |
|---------|---------|
| HTTP server | FastAPI + uvicorn |
| Async HTTP client | httpx |
| RabbitMQ | aio-pika |
| LLM | openai (Python SDK) |
| SMS | twilio |
| Data validation | Pydantic v2 |
| Config | pydantic-settings |
| Package management | uv + pyproject.toml |

## Configuration

| Env Var | Default | Description |
|---------|---------|-------------|
| `PORT` | `8080` | HTTP listen port |
| `RABBITMQ_URL` | required | RabbitMQ connection string |
| `DICTIONARY_URL` | `http://woodpantry-ingredients:8080` | Ingredient Dictionary base URL |
| `RECIPE_URL` | `http://woodpantry-recipes:8080` | Recipe Service base URL |
| `PANTRY_URL` | optional | Pantry Service base URL (required for pantry ingest consumer) |
| `OPENAI_API_KEY` | required | OpenAI API key (extraction + vision) |
| `EXTRACT_MODEL` | `gpt-5-mini` | OpenAI model for text extraction |
| `VISION_MODEL` | `gpt-5` | OpenAI model for receipt OCR / vision (Phase 3) |
| `TWILIO_ACCOUNT_SID` | optional | Twilio credentials (W-5) |
| `TWILIO_AUTH_TOKEN` | optional | Also used to validate webhook signatures (W-5) |
| `TWILIO_FROM_NUMBER` | optional | Outbound SMS number (W-5) |
| `LOG_LEVEL` | `info` | Log level |

## Development

```bash
# Install dependencies
uv sync

# Run the service (requires RABBITMQ_URL and OPENAI_API_KEY)
uv run uvicorn app.main:app --reload --port 8080

# Lint
uv run ruff check app/

# Run tests
uv run pytest
```

## Outstanding Work

- **Twilio webhook handler** — W-5 scope
- **Receipt photo/OCR flow** — Phase 3
- **Tests** — unit and integration tests to be added
