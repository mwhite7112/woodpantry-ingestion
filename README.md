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
| `pantry.ingest.failed` | Publishes | Failure payload when pantry extraction or staging fails |

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
| `TWILIO_AUTH_TOKEN` | optional | Also used to validate `/twilio/inbound` request signatures |
| `TWILIO_FROM_NUMBER` | optional | Outbound SMS number for staged and confirm replies |
| `LOG_LEVEL` | `info` | Log level |

Twilio-specific notes:

- `/twilio/inbound` requires `TWILIO_AUTH_TOKEN` so the service can reject invalid `X-Twilio-Signature` headers.
- Outbound staged and confirm reply SMS messages require all of `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_FROM_NUMBER`.
- New text messages publish `pantry.ingest.requested` with `job_id`, `raw_text`, and `from_number`.
- `CONFIRM` replies call `POST /pantry/ingest/{job_id}/confirm` for the most recent staged pending job tracked for that phone number.

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

## Twilio SMS Flow

1. Twilio sends `POST /twilio/inbound`.
2. The webhook validates the Twilio signature, reads `From` and `Body`, and creates a pantry ingest job for normal text messages.
3. The webhook publishes `pantry.ingest.requested { job_id, raw_text, from_number }`.
4. After pantry staging completes, the worker sends an outbound SMS with staged counts and `CONFIRM` instructions.
5. A `CONFIRM` reply confirms the most recent pending staged pantry job for that phone number and sends a completion SMS.

## Outstanding Work

- **Receipt photo/OCR flow** — Phase 3
