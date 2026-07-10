# apparatus — bilevel outer loop over the wind-tunnel trace

A small, deterministic apparatus that runs the **diagnosis step** of the
[autoreason bilevel outer loop](https://github.com/NousResearch/autoreason/pull/2)
(PR #2) over the Matrix Wind-Tunnel's own Rounds 5–6 data. No model in the loop, no
tokens spent — which is exactly the property that PR argues for ("the outer loop is
deterministic ... for auditability and cost efficiency"), and the wind-tunnel's
two-economies doctrine (cheap sunk-compute controller; reserve metered tokens for the
inner generation).

It exists to answer one question concretely: **does our math / runs support his
approach?** Yes — the wind-tunnel is a controlled study of the judge his quality gate
depends on, and this apparatus turns that study into the numbers the gate needs.

## Run it

```
python test_apparatus.py    # 14 stdlib checks
python run_apparatus.py     # one diagnosis pass over windtunnel_trace.json
python run_apparatus.py --arm minimalist_critic
```

Pure Python 3.12 standard library. No network, no GPU, no API key.

## Files

| file | what it is |
|---|---|
| `windtunnel_trace.json` | real Round 5–6 numbers, machine-readable (from `MATRIX-WIND-TUNNEL-LOG.html`) |
| `signatures.py` | deterministic classifier for the six autoreason failure signatures (mirrors his `mechanisms.py`) |
| `mechanism_library.py` | signature → config-delta bundle, **seeded with the wind-tunnel's measured deltas** |
| `judge_robustness.py` | inflation factor, between-lens noise, sign-flip lenses, required gate-votes |
| `run_apparatus.py` | ties the four steps into one outer-loop diagnosis report |
| `test_apparatus.py` | 14 self-tests |

## What it finds on our trace

- The wind-tunnel trace is a **live instance of `non_convergence`** (0/12 cells
  converged) and of **`judge_herding`** (the completeness lens can't tell arms apart).
- The one measured mechanism the autoreason library doesn't have — a **concise author
  prompt** — is +2.8 under a fair judge.
- **Gate sizing:** a single lens inflates the concise-author effect **2.86×**, the
  completeness lens **flips its sign**, and resolving the true +2.8 against 4.15-pt
  between-lens noise takes **≈9 lens-diverse votes**. `--gate-votes 1` is unsafe.

The proof run, rendered: [`../APPARATUS-PROOF.html`](../APPARATUS-PROOF.html).
The full crossover map: [`../AUTOREASON-CROSSOVER.html`](../AUTOREASON-CROSSOVER.html).
