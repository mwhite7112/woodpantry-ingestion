"""HTTP client for the Pantry Service.

TODO: Implement once W-2 adds POST /pantry/ingest/:job_id/stage endpoint.

Expected contract:
    POST /pantry/ingest/{job_id}/stage
    Body: { "items": [ { "raw_text", "name", "quantity", "unit", "confidence" } ] }
    Response 200: { "staged_count": int, "needs_review_count": int }
"""
