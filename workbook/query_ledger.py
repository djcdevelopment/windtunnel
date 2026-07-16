"""Query your receipts: per-tool call counts, error rates, and durations.

Usage:
    python query_ledger.py [path\\to\\ledger.sqlite]

Defaults to ledger.sqlite next to this script (where hearth_gateway.py
writes it). Stdlib only — the whole point of a JSONL+SQLite manifest is
that interrogating it costs nothing.
"""
import sqlite3
import sys
from pathlib import Path

db_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "ledger.sqlite"
if not db_path.exists():
    sys.exit(f"no ledger at {db_path} — run the gateway and make some calls first")

db = sqlite3.connect(db_path)
rows = db.execute("""
    SELECT tool,
           COUNT(*)                          AS calls,
           SUM(ok = 0)                       AS errors,
           ROUND(AVG(duration_ms), 1)        AS avg_ms,
           ROUND(SUM(duration_ms) / 1000, 1) AS total_s
    FROM events GROUP BY tool ORDER BY calls DESC""").fetchall()

total = sum(r[1] for r in rows)
print(f"{db_path} — {total} events\n")
print(f"{'tool':<18}{'calls':>7}{'errors':>8}{'avg ms':>10}{'total s':>10}")
for tool, calls, errors, avg_ms, total_s in rows:
    print(f"{tool:<18}{calls:>7}{errors:>8}{avg_ms:>10}{total_s:>10}")

last = db.execute("SELECT ts, tool, ok FROM events ORDER BY ts DESC LIMIT 1").fetchone()
if last:
    print(f"\nlast event: {last[0]}  {last[1]}  ok={bool(last[2])}")
