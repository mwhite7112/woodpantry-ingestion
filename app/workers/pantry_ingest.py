"""Pantry ingest worker — consumes pantry.ingest.requested events.

TODO: Not implemented until W-2 adds the staging endpoint to the Pantry Service.
Once available, this worker will:
1. Parse the event payload (job_id, raw_text, from_number)
2. Call LLM to extract items (app.llm.openai)
3. Resolve each item via Dictionary Service (app.clients.dictionary)
4. POST staged items to Pantry Service (app.clients.pantry)
5. Send confirmation SMS via Twilio (W-5 scope)
"""
