# NL2SQL Agent

Internal, read-only natural language to SQL agent for PMs, analysts, support, and ops to self-serve data questions safely. It will later plug in an open-source Hugging Face model to generate SQL, but currently returns mocked responses.

## What it does
- Exposes a FastAPI service with a `/ask` endpoint for natural language questions.
- Designed to produce read-only, validated SQL against a demo SQLite database.
- Includes placeholders for prompts, guardrails, and agent orchestration logic.

## Run locally
1. Install dependencies (use a virtualenv): `pip install -r requirements.txt`
2. Start the API: `uvicorn app.main:app --reload`
3. Test health: `curl http://127.0.0.1:8000/health`
4. Send a question: `curl -X POST http://127.0.0.1:8000/ask -H "Content-Type: application/json" -d '{"question": "What are our top customers?"}'`

## Notes
- The SQLite demo database lives at `data/demo.db` (currently empty).
- Agent logic, guardrails, and prompt engineering are stubs to be filled in later.
- Keep all generated SQL read-only and safe as the system evolves.
