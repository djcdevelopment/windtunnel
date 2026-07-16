"""HEARTH: a minimal local MCP gateway with a tool-call ledger.

Part of the windtunnel workbook: https://github.com/djcdevelopment/windtunnel
Tools appear in Claude Code automatically once wired via .mcp.json.
Every call is appended to ledger.jsonl and indexed in ledger.sqlite.
"""
import functools
import hashlib
import json
import sqlite3
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
from mcp.server.fastmcp import FastMCP

HOME = Path(__file__).parent
SCOPE = Path("C:/work")       # tools may only touch paths under here — point at YOUR projects dir
OLLAMA = "http://127.0.0.1:11434"
MODEL = "qwen2.5-coder:14b"

mcp = FastMCP("hearth")

# ---------- the ledger ----------
_db = sqlite3.connect(HOME / "ledger.sqlite", check_same_thread=False)
_db.execute("""CREATE TABLE IF NOT EXISTS events(
    id TEXT PRIMARY KEY, ts TEXT, tool TEXT, ok INTEGER,
    duration_ms REAL, args_preview TEXT, error TEXT)""")
_db.commit()


def _digest(obj) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(obj, default=str, sort_keys=True).encode()).hexdigest()[:16]


def ledgered(fn):
    """Every tool call becomes one ledger event. This is the whole trick."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        started = time.perf_counter()
        event = {
            "event_id": str(uuid.uuid4()),
            "ts": datetime.now(timezone.utc).isoformat(),
            "tool": fn.__name__,
            "args_preview": json.dumps(kwargs, default=str)[:300],
            "args_digest": _digest(kwargs),
            "ok": True, "error": None,
        }
        try:
            result = fn(*args, **kwargs)
            event["result_digest"] = _digest(result)
            return result
        except Exception as exc:
            event.update(ok=False, error=f"{type(exc).__name__}: {exc}")
            raise
        finally:
            event["duration_ms"] = round((time.perf_counter() - started) * 1000, 2)
            with open(HOME / "ledger.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")
            _db.execute("INSERT INTO events VALUES(?,?,?,?,?,?,?)",
                        (event["event_id"], event["ts"], event["tool"],
                         int(event["ok"]), event["duration_ms"],
                         event["args_preview"], event["error"]))
            _db.commit()
    return wrapper


def _in_scope(path: str) -> Path:
    p = (SCOPE / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
    if not str(p).lower().startswith(str(SCOPE.resolve()).lower()):
        raise ValueError(f"path {p} is outside HEARTH scope {SCOPE}")
    return p


# ---------- the tools ----------
@mcp.tool()
@ledgered
def hearth_status() -> dict:
    """HEARTH self-test: ledger location and total event count."""
    n = _db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    return {"hearth": "burning", "ledger": str(HOME / "ledger.jsonl"), "events": n}


@mcp.tool()
@ledgered
def read_file(path: str, max_bytes: int = 200_000) -> dict:
    """Read a text file (scope-checked)."""
    data = _in_scope(path).read_text(encoding="utf-8", errors="replace")
    return {"path": path, "truncated": len(data) > max_bytes, "content": data[:max_bytes]}


@mcp.tool()
@ledgered
def write_file(path: str, content: str) -> dict:
    """Write a text file (scope-checked); creates parent dirs."""
    p = _in_scope(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return {"path": str(p), "bytes": len(content)}


@mcp.tool()
@ledgered
def run_tests(directory: str, command: str = "python -m pytest -q --tb=short") -> dict:
    """Run a test command in a directory; returns a compact digest, never full output."""
    p = subprocess.run(command, cwd=_in_scope(directory), shell=True,
                       capture_output=True, text=True, timeout=600)
    tail = (p.stdout + p.stderr).strip().splitlines()[-15:]
    return {"exit_code": p.returncode, "ok": p.returncode == 0, "tail": tail}


@mcp.tool()
@ledgered
def local_generate(prompt: str, system: str = "", max_tokens: int = 1024) -> dict:
    """Generate text with the LOCAL model (free, runs on your GPU).
    Use for: summarizing, extracting, boilerplate, drafts, classification."""
    r = httpx.post(f"{OLLAMA}/api/generate", json={
        "model": MODEL, "prompt": prompt, "system": system or None,
        "stream": False, "options": {"num_predict": max_tokens}}, timeout=300)
    r.raise_for_status()
    body = r.json()
    return {"text": body.get("response", ""),
            "model": MODEL,
            "tokens_in": body.get("prompt_eval_count"),
            "tokens_out": body.get("eval_count"),
            "duration_ms": round(body.get("total_duration", 0) / 1e6)}


if __name__ == "__main__":
    mcp.settings.host = "127.0.0.1"
    mcp.settings.port = 8710
    mcp.run(transport="streamable-http")
