"""FastAPI entry point for the NL2SQL agent service."""

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .agent import run_agent, stats_snapshot
from .models import AskRequest, AskResponse

app = FastAPI(
    title="NL2SQL Agent",
    description="Internal-safe natural language to SQL agent",
    version="0.1.0",
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/", include_in_schema=False)
def serve_ui() -> FileResponse:
    """Serve the demo UI."""
    return FileResponse("app/static/index.html")


@app.get("/health")
def health_check() -> dict:
    """Lightweight health check for uptime probes."""
    return {"status": "ok"}


@app.get("/stats")
def stats() -> dict:
    """Return lightweight, in-memory demo stats (no user tracking)."""
    return stats_snapshot()


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    """Handle natural language questions and return a SQL-backed answer."""
    # The agent handles guardrails and safe execution internally.
    return run_agent(request.question)
