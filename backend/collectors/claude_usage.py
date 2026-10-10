"""Read-only Claude.ai usage snapshot collector.

The browser helper is intentionally separate from FastAPI authentication. It reads
an already-authenticated browser page through agent-browser and stores only quota
percentages/reset labels, never cookies, tokens, prompts, or raw page text.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SNAPSHOT_RELATIVE = Path("integrations") / "claude_usage.json"
MAX_AGE_SECONDS = 180
_METER_RE = re.compile(r'meter "([^"]+)":\s*([0-9]+)')
_RESET_RE = re.compile(r'StaticText "(Resets [^"]+)"')
_USED_RE = re.compile(r'StaticText "([0-9]+)% used"')


def _snapshot_path(hermes_dir: str | None = None) -> Path:
    root = Path(hermes_dir or os.environ.get("HERMES_HOME") or os.path.expanduser("~/.hermes"))
    return root / SNAPSHOT_RELATIVE


def _parse_snapshot_text(text: str) -> dict[str, Any]:
    meters: dict[str, dict[str, Any]] = {}
    matches = list(_METER_RE.finditer(text))
    for index, match in enumerate(matches):
        label, value = match.group(1), int(match.group(2))
        block_start = matches[index - 1].end() if index else max(0, match.start() - 400)
        block_end = matches[index + 1].start() if index + 1 < len(matches) else match.end() + 240
        block = text[block_start:block_end]
        reset = _RESET_RE.findall(block)
        used = _USED_RE.findall(block)
        meters[label] = {
            "used_percent": value,
            "reset_text": reset[-1] if reset else None,
            "used_text": f"{used[-1]}% used" if used else f"{value}% used",
        }

    current = meters.get("Current session")
    all_models = meters.get("All models")
    fable = meters.get("Fable")
    if not current and not all_models and not fable:
        raise ValueError("Claude usage meters not found; open claude.ai Settings > Usage")

    return {
        "provider": "claude",
        "status": "fresh",
        "authenticated": True,
        "source": "claude.ai/settings/usage",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "current_window": current,
        "weekly": {
            "all_models": all_models,
            "fable": fable,
        },
    }


def collect_claude_usage(hermes_dir: str | None = None) -> dict[str, Any]:
    path = _snapshot_path(hermes_dir)
    if not path.exists():
        return {
            "provider": "claude",
            "status": "not_configured",
            "authenticated": False,
            "source": "claude.ai/settings/usage",
            "snapshot_path": str(path),
            "error": "No usage snapshot. Run the local browser refresh command.",
        }

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        fetched = datetime.fromisoformat(str(data.get("fetched_at", "")).replace("Z", "+00:00"))
        age = max(0, int((datetime.now(timezone.utc) - fetched).total_seconds()))
        data["age_seconds"] = age
        if age > MAX_AGE_SECONDS and data.get("status") == "fresh":
            data["status"] = "stale"
        data["snapshot_path"] = str(path)
        return data
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {
            "provider": "claude",
            "status": "error",
            "authenticated": False,
            "source": "claude.ai/settings/usage",
            "snapshot_path": str(path),
            "error": f"Invalid usage snapshot: {exc}",
        }


def refresh_claude_usage(hermes_dir: str | None = None) -> dict[str, Any]:
    """Capture the current authenticated agent-browser page and save a safe snapshot."""
    browser_cmd = (
        shutil.which("agent-browser")
        or shutil.which("agent-browser.cmd")
        or str(Path.home() / "AppData" / "Roaming" / "npm" / "agent-browser.cmd")
    )
    try:
        result = subprocess.run(
            [browser_cmd, "snapshot"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "error", "authenticated": False, "error": f"agent-browser unavailable: {exc}"}

    if result.returncode != 0:
        return {"status": "error", "authenticated": False, "error": result.stderr.strip() or result.stdout.strip()}

    try:
        data = _parse_snapshot_text(result.stdout)
        path = _snapshot_path(hermes_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return data | {"snapshot_path": str(path)}
    except ValueError as exc:
        return {"status": "reauth_required", "authenticated": False, "error": str(exc)}
