"""Claude Pro usage endpoint."""

from fastapi import APIRouter

from backend.collectors.claude_usage import collect_claude_usage, refresh_claude_usage

router = APIRouter()


@router.get("/claude-usage")
def get_claude_usage():
    """Return the last safe Claude usage snapshot, marked stale when old."""
    return collect_claude_usage()


@router.post("/claude-usage/refresh")
def refresh_claude_usage_snapshot():
    """Read the already-open authenticated agent-browser page without storing credentials."""
    return refresh_claude_usage()
