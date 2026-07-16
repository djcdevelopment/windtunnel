# The HEARTH Workbook — a local MCP gateway + JSONL manifest for your AI agent

Build a small, always-on local gateway that (1) records **every tool call your frontier
agent makes** as one line in an append-only JSONL manifest, and (2) lets that agent
**offload grunt work to a local model** on your own GPU. ~90 minutes on a Windows machine,
no prior MCP experience required. Styled version:
[HEARTH-WORKBOOK.html](https://djcdevelopment.github.io/windtunnel/HEARTH-WORKBOOK.html).

> A hearth is the small fire that never goes out at the center of the camp: always warm,
> always watched, everything cooked on it. That's what you're building — a small,
> always-on fire your AI agents gather around.

**Why it lives in this repo:** every experiment in the [wind tunnel](../README.md) ran on
idle local hardware through a grown-up descendant of exactly this gateway — the JSONL
ledger you build here is the same instrument that let us catch our own judge inflating
effects ~3× (Round 6). Receipts first; conclusions second.

## What you're building, and why

When Claude Code (or any frontier agent) works on your machine today, it reaches for tools
ad hoc — a shell command here, a file edit there — and none of it is captured anywhere you
control. Two things are wrong with that picture:

1. **You have no record.** When something goes sideways, or you want to know what your
   agent actually *did*, there's nothing to query. The model's memory of what it did is
   not the same thing.
2. **You're paying frontier prices for grunt work.** Summarizing a log, drafting
   boilerplate, extracting fields — a local model on your own GPU does these at the cost
   of electricity, and your GPU is sitting right there.

One small daemon fixes both: a local **MCP gateway** that exposes tools to your agent over
HTTP and writes **every single call to a ledger** — a JSONL file plus a SQLite index.
The agent does the thinking; your machine does the hands; the ledger is the receipts.

MCP ([Model Context Protocol](https://modelcontextprotocol.io)) is the open standard that
makes this plug-and-play: Claude Code speaks it natively, so once your gateway is up, its
tools appear in the agent like built-ins.

**A note on priorities:** this guide was first written for gamers with an idle GPU. That
had it backwards. The GPU is the garnish — the manifest is the product. If you have no
GPU, point `local_generate` at any budget cloud endpoint and build the rest unchanged.

## What's in this folder

| File | What it is |
|---|---|
| [`hearth_gateway.py`](hearth_gateway.py) | the whole gateway — ~150 lines, five tools, the `ledgered` decorator |
| [`test_client.py`](test_client.py) | end-to-end checkpoint: a real MCP client calling the gateway |
| [`query_ledger.py`](query_ledger.py) | interrogate your receipts: per-tool counts, error rates, durations |
| [`start-hearth.cmd`](start-hearth.cmd) | logon wrapper for Task Scheduler (Step 5) |

## What you need

| Piece | Spec / version | Why |
|---|---|---|
| Windows PC | Windows 10/11 | this guide is for the consumer-Windows crowd |
| NVIDIA GPU | ~12 GB VRAM | runs a 14B coding model fully on-GPU at pleasant speed |
| RAM / CPU | 32 GB+ / modern CPU | stretch to bigger models with partial CPU offload later |
| Python | 3.11+ (3.12 recommended) | the gateway is ~150 lines of Python |
| Ollama | latest Windows build | easiest local-model server; one installer, one command |
| Claude Code | latest | your frontier agent and MCP client |
| A local model | `qwen2.5-coder:14b` (~9 GB) | fits in 12 GB VRAM; strong at code/text chores |

> **You have a copilot for this workbook.** Every step below is something Claude Code (or
> Claude in your browser) can help with. Stuck on an error? Paste it in and ask. You're
> not just building an agent workbench — you're allowed to use the agent to build it.

## Step 1 — Install Ollama and pull a model

1. Download and run the Windows installer from `https://ollama.com/download`. It installs
   a background server on port `11434` that starts when you log in.
2. Pull the model (~9 GB download):

```powershell
ollama pull qwen2.5-coder:14b
```

**✔ Checkpoint** — ask the model something and watch your GPU do the work (first call
loads the model into VRAM, ~10s; after that it's fast):

```powershell
ollama run qwen2.5-coder:14b "Write a haiku about a fire that never goes out."
Invoke-RestMethod http://127.0.0.1:11434/api/tags | Select-Object -Expand models | Format-Table name
```

## Step 2 — Python environment + the MCP SDK

```powershell
mkdir C:\hearth
cd C:\hearth
python -m venv venv
.\venv\Scripts\pip install "mcp[cli]" httpx
```

**✔ Checkpoint**

```powershell
.\venv\Scripts\python -c "import mcp; print('mcp OK:', mcp.__name__)"
```

## Step 3 — The gateway (one file, with a ledger)

Copy [`hearth_gateway.py`](hearth_gateway.py) from this folder to
`C:\hearth\hearth_gateway.py`. It exposes five tools over MCP and logs *every call* to
both `ledger.jsonl` (append-only, human-readable) and `ledger.sqlite` (queryable).

The logging decorator is the heart of HEARTH — everything that passes through the fire is
remembered:

```python
def ledgered(fn):
    """Every tool call becomes one ledger event. This is the whole trick."""
```

Each call becomes one JSONL line:

```json
{"event_id": "b41c…", "ts": "2026-07-16T14:02:11+00:00", "tool": "local_generate",
 "args_preview": "{\"prompt\": \"Summarize this build log…\"}", "args_digest": "sha256:9f2c…",
 "ok": true, "result_digest": "sha256:77aa…", "duration_ms": 2140.55}
```

**Before running:** check the `SCOPE` constant — tools refuse to touch any path outside
it. It ships as `C:/work`; point it at the folder your projects actually live in. The
scope check is your seatbelt.

**✔ Checkpoint** — start the gateway in one PowerShell window:

```powershell
cd C:\hearth
.\venv\Scripts\python hearth_gateway.py
```

You should see `Uvicorn running on http://127.0.0.1:8710`. Leave it running. In a
*second* window, prove a real MCP client can call a tool end to end (copy
[`test_client.py`](test_client.py) next to the gateway):

```powershell
C:\hearth\venv\Scripts\python C:\hearth\test_client.py
```

Expected: a list of five tools, then `"hearth": "burning"`. Now check your receipts —
the call you just made is already in the ledger:

```powershell
Get-Content C:\hearth\ledger.jsonl -Tail 2
```

## Step 4 — Wire it into Claude Code

Two small files in the project folder where you use Claude Code (e.g. `C:\work\myproject`):

**1 · `.mcp.json`** — tells Claude Code the gateway exists:

```json
{
  "mcpServers": {
    "hearth": {
      "type": "http",
      "url": "http://127.0.0.1:8710/mcp"
    }
  }
}
```

**2 · `CLAUDE.md`** — add a section telling Claude *when* to use it. Without this, Claude
has the tools but no habit:

```markdown
## Local-first offload (HEARTH)

A local model is available via the `hearth` MCP server's `local_generate`
tool, plus ledgered file/test tools. Before spending frontier tokens on a
self-contained sub-task, delegate it to the local model:

- summarizing / condensing a file, log, or diff you have already read
- extracting structured data (fields, lists, JSON) from unstructured text
- generating boilerplate (config, test scaffold, docstring, commit draft)
- classifying / labeling / yes-no triage over a chunk of text

Rules: the local model has NO repo access — pass all needed context in the
prompt. If the output is unusable, do the task yourself; one retry max.
First call after boot pays a model-load tax (~10s) — that is not a failure.
```

> **⚠ The restart trap (this one costs everyone an hour).** Claude Code loads MCP config
> at startup. After creating `.mcp.json` you must **fully restart the application AND
> start a new session** in that project. An existing session — even one that helped you
> write the config — will never see the server. On the first new session, approve the
> project's `hearth` server when prompted.

**✔ Checkpoint** — in the fresh session, type:

```
Use the hearth_status tool, then use local_generate to write a two-line poem about a hearth.
```

You should see Claude call both tools (they show as `mcp__hearth__...`) and the poem
should come back from *your GPU*, not the cloud. Then the money shot — prove the ledger
caught it all (copy [`query_ledger.py`](query_ledger.py) next to the gateway):

```powershell
C:\hearth\venv\Scripts\python C:\hearth\query_ledger.py C:\hearth\ledger.sqlite
```

Every tool call your agent has ever made — counts, error rates, durations. That's HEARTH
working.

## Step 5 — Keep the fire lit (auto-start)

Copy [`start-hearth.cmd`](start-hearth.cmd) to `C:\hearth\start-hearth.cmd`, then register
it to run at logon (plain PowerShell, no admin needed):

```powershell
$action  = New-ScheduledTaskAction -Execute 'C:\hearth\start-hearth.cmd'
$trigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
Register-ScheduledTask -TaskName 'Hearth' -Action $action -Trigger $trigger
```

> **⚠ Use `python.exe`, not `pythonw.exe`, in the wrapper.** `pythonw` under Task
> Scheduler dies silently with no log and no error — we learned this the hard way. With
> `python.exe` + the log redirect, any failure leaves evidence in `hearth.log`.

**✔ Checkpoint** — stop your manual gateway window (Ctrl+C), then:

```powershell
Start-ScheduledTask -TaskName Hearth
Start-Sleep 5
Test-NetConnection 127.0.0.1 -Port 8710 | Select-Object TcpTestSucceeded
```

`TcpTestSucceeded : True` means the fire relights itself every time you log in.

## Troubleshooting — the traps we actually hit

| Symptom | Cause | Fix |
|---|---|---|
| Claude Code doesn't show any `hearth` tools | MCP config loads at app startup only | fully restart the app AND open a new session; approve the server when prompted |
| Gateway fails to parse a JSON config you wrote from PowerShell | PowerShell 5.1's `Out-File -Encoding utf8` writes a UTF-8 BOM | write JSON from Python, an editor, or use `-Encoding ascii` |
| Gateway "runs" from Task Scheduler but nothing listens | `pythonw.exe` dying silently | use `python.exe` with output redirected to a log |
| Port 8710 behaves strangely / calls hit a stale server | an old gateway process still holds the port | `Get-NetTCPConnection -LocalPort 8710 -State Listen` → stop that PID, restart the task |
| First `local_generate` after boot is slow or times out | model loading into VRAM (~10s, once) | not a failure; retry once. Optionally warm it at logon with a tiny generate call |
| `local_generate` returns nonsense / ignores your text | local 14B models are honest workers, not geniuses | give them ALL the context in the prompt, ask for one narrow thing, and verify — the ledger makes their error rate measurable, which is the point |

## Where this goes next

You now have the kernel of something bigger. In rough order of payoff:

- **Add per-caller keys** — an `X-Hearth-Key` header and a `callers.json` turn "who did
  what" from a guess into a ledger field.
- **Add coarser tools** — a `git_commit_push` that stages/commits/pushes in one audited
  call; a lint digest; whatever your inner loop repeats.
- **Query your economics** — `query_ledger.py` is the seed; one evening of SQL against
  the index gives you a dashboard proving what your GPU is saving you.
- **The learning loop** — in the full HEARTH design, the ledger feeds a projection layer
  that derives what your machines are actually *capable* of from evidence, and routes
  each task to the cheapest runner that can do it. The experiments in the
  [main lab log](../README.md) — including the round where the judge itself turned out to
  be the confound — are what that looks like grown up. The ledger you built today is its
  foundation.

Light it, keep it lit, and let everything cook on the same fire.

---

**Provenance:** distilled from the HEARTH build in the commandcenter lab
(Derek Ciula / Steppe Integrations), July 2026 · written with Claude (Fable 5).
The production instance runs four backends behind this same door — two local machines,
two cloud tiers — every call ledgered with the resolved backend and model.
