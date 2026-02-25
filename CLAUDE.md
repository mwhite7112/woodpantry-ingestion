# woodpantry-ingestion — Ingestion Pipeline

## Role in Architecture

The ingestion pipeline is the **only service that handles raw, dirty input**. Receipt photos, free-text blobs, SMS messages — all raw input flows through here. Other services receive clean, normalized, structured data.

This service is **Phase 2+** — it does not exist in Phase 1. In Phase 1, Recipe Service and Pantry Service call the OpenAI API directly. In Phase 2, that LLM logic is extracted here and the flows become async via RabbitMQ.

Responsibilities:
- Twilio webhook handler for inbound SMS/MMS
- OCR via vision LLM for receipt photos (Phase 3)
- Structured extraction from free-text for both pantry items and recipes
- Calling `/ingredients/resolve` on all extracted ingredients
- Posting staged results to Pantry Service or publishing `recipe.imported`
- Tracking in-progress jobs per Twilio phone number for CONFIRM reply handling

This service intentionally has no UI and no "clean" data — it is a pure I/O processing worker. This is why it is written in **Python** rather than Go: the workload is entirely I/O bound (LLM API calls, HTTP calls to other services, RabbitMQ), and the Python ecosystem (OpenAI SDK, Twilio helper library, aio-pika) is a natural fit.

## Technology

- Language: **Python 3.12+**
- HTTP: **FastAPI** + **uvicorn** — for the Twilio webhook endpoint
- Async HTTP client: **httpx** — for calling other WoodPantry services
- RabbitMQ: **aio-pika** — async AMQP client
- LLM: **openai** Python SDK — `gpt-5-mini` for text extraction, `gpt-5` for vision/OCR (Phase 3)
- Twilio: **twilio** Python helper library
- Data validation: **Pydantic v2**
- Package management: **uv** + `pyproject.toml`
- No database — job-to-phone mapping is in-memory with TTL (see below)

## Service Dependencies

- **Calls**: Ingredient Dictionary (`/ingredients/resolve`), Pantry Service (POST staged items), Recipe Service (status updates)
- **Called by**: Twilio (inbound webhook), RabbitMQ events
- **Subscribes to**: `pantry.ingest.requested`, `recipe.import.requested`
- **Publishes**: `recipe.imported`

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/healthz` | Health check |
| POST | `/twilio/inbound` | Twilio webhook — inbound SMS/MMS handler |

The Twilio webhook is the only external-facing HTTP endpoint. All other processing is queue-driven.

## Key Patterns

### Twilio Webhook Flow (SMS text)

```
POST /twilio/inbound (from Twilio)
  → Validate Twilio signature (use twilio.request_validator)
  → Parse From number + Body text
  → Publish pantry.ingest.requested { raw_text, from_number, job_id }
  → Reply SMS: "Processing your list..."
  (async) Ingestion worker consumes event:
    → LLM extraction → resolve ingredients → POST staged items to Pantry Service
    → Reply SMS: "N items staged. M need review. Reply CONFIRM to commit."
  User replies CONFIRM:
    → POST /twilio/inbound with Body=CONFIRM
    → Look up pending job_id for From number
    → Call POST /pantry/ingest/:job_id/confirm
    → Reply SMS: "Done! N items added to your pantry."
```

### Twilio Webhook Flow (MMS photo — Phase 3)

```
POST /twilio/inbound with MediaUrl0 present
  → Download image from Twilio media URL
  → Send image to gpt-5 vision with receipt OCR prompt
  → Continue as text flow above
```

### Phone-to-Job Mapping

Map `From` phone number → most recent in-progress job ID so CONFIRM replies work. Use a simple in-memory dict with a TTL (e.g. 30 minutes). Sufficient for a single-user homelab — no persistence needed across restarts.

```python
# app/workers/job_registry.py
jobs: dict[str, tuple[str, float]] = {}  # phone → (job_id, expires_at)
```

### Queue Consumer: pantry.ingest.requested

```
1. LLM extraction: call OpenAI API (gpt-5-mini) with structured extraction prompt
2. For each extracted item: POST /ingredients/resolve → get ingredient_id
3. POST staged items to Pantry Service
4. Send confirmation SMS via Twilio API
5. On failure: mark job as failed, send error SMS
```

### Queue Consumer: recipe.import.requested

```
1. LLM extraction: call OpenAI API (gpt-5-mini) with recipe extraction prompt
2. For each ingredient: POST /ingredients/resolve → get ingredient_id
3. Publish recipe.imported with full structured recipe payload
4. On failure: update Recipe Service job status to failed
```

### Extraction Prompts

Keep prompts in `app/prompts/` as string constants. Prompts must request structured JSON output and include a confidence field per item. Use Pydantic models to validate the JSON the LLM returns — do not trust raw LLM output.

### Async Architecture

The service runs two concurrent components under one process:
1. **FastAPI/uvicorn** — handles inbound Twilio webhook requests
2. **aio-pika consumer** — listens for RabbitMQ events and processes them

Both run on the same asyncio event loop. Use `asyncio.gather` or `anyio` task groups to start both on startup.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8080` | HTTP listen port (for Twilio webhook) |
| `RABBITMQ_URL` | required | RabbitMQ connection string |
| `DICTIONARY_URL` | required | Ingredient Dictionary base URL |
| `PANTRY_URL` | required | Pantry Service base URL |
| `RECIPE_URL` | required | Recipe Service base URL |
| `OPENAI_API_KEY` | required | OpenAI API key (extraction + vision) |
| `EXTRACT_MODEL` | `gpt-5-mini` | OpenAI model for text extraction |
| `VISION_MODEL` | `gpt-5` | OpenAI model for receipt OCR / vision (Phase 3) |
| `TWILIO_ACCOUNT_SID` | required | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | required | Twilio auth token (also used to validate webhook signatures) |
| `TWILIO_FROM_NUMBER` | required | Twilio phone number for outbound SMS |
| `LOG_LEVEL` | `info` | Log level |

## Directory Layout

```
woodpantry-ingestion/
├── app/
│   ├── main.py                    ← FastAPI app + asyncio entrypoint
│   ├── api/
│   │   └── twilio.py              ← webhook handler + signature validation
│   ├── workers/
│   │   ├── pantry_ingest.py       ← pantry extraction consumer
│   │   ├── recipe_ingest.py       ← recipe extraction consumer
│   │   ├── sms.py                 ← Twilio reply + CONFIRM flow
│   │   └── job_registry.py        ← in-memory phone → job_id map
│   ├── llm/
│   │   └── openai.py              ← OpenAI client (extraction + vision)
│   ├── clients/
│   │   ├── dictionary.py          ← httpx client for Ingredient Dictionary
│   │   ├── pantry.py              ← httpx client for Pantry Service
│   │   └── recipes.py             ← httpx client for Recipe Service
│   ├── events/
│   │   ├── subscriber.py          ← aio-pika consumer setup
│   │   └── publisher.py           ← aio-pika publisher
│   ├── prompts/
│   │   ├── pantry.py              ← pantry extraction prompt + Pydantic output model
│   │   └── recipe.py              ← recipe extraction prompt + Pydantic output model
│   └── config.py                  ← settings via pydantic-settings
├── kubernetes/
├── Dockerfile
├── pyproject.toml
└── README.md
```

## Outstanding Work

- **Pantry ingest worker** (`pantry.ingest.requested` consumer) — blocked on W-2 adding `POST /pantry/ingest/:job_id/stage` endpoint to the Pantry Service. The worker stub is at `app/workers/pantry_ingest.py`.
- **Twilio webhook handler** — W-5 scope. Stub at `app/api/twilio.py`.
- **Receipt photo/OCR flow** — Phase 3.
- **Tests** — unit and integration tests to be added.

## What to Avoid

- Do not build business logic for clean data into this service — it is a processing worker only.
- Do not skip Twilio signature validation — the webhook endpoint is public.
- Do not let LLM extraction errors crash the worker — catch exceptions, mark the job as failed, and continue consuming.
- Do not store pantry or recipe state here — this service holds no persistent data beyond the in-memory job registry.
- Do not use synchronous HTTP calls (`requests`) — use `httpx` async client throughout to avoid blocking the event loop.
