# windtunnel → autoreason

**windtunnel is a generalized, local-first testing lab** — controlled evaluation experiments run on
idle consumer hardware (Nvidia + Intel GPUs) instead of frontier API tokens. It's where I pressure-test
local models, prompts, and — increasingly — *the evaluation layer itself*. The first study living here is
the [Matrix Wind-Tunnel](https://djcdevelopment.github.io/windtunnel/MATRIX-WIND-TUNNEL-LOG.html) (does planner↔critic self-refinement actually improve
planning output?).

This note is about one thing the lab turns out to be good for, and how it lines up with what
[autoreason](https://github.com/NousResearch/autoreason) is building: **stress-testing the evaluation layer
that self-improving reasoning loops depend on.**

## Why this lab supports autoreason

autoreason's [bilevel PR #2](https://github.com/NousResearch/autoreason/pull/2) adds a deterministic outer
loop that reads a tournament trace, diagnoses a failure signature, applies a mechanism, and keeps it only if a
**quality gate** passes. That gate is judged by an LLM — so the judge is the load-bearing assumption of the
whole scheme. Characterizing judges under controlled conditions is exactly what this lab does.

The Matrix Wind-Tunnel already ran the experiment that gate needs as a prior: it re-scored the same outputs
under multiple judge rubrics and found the rubric **inflated every effect ~3×** and could flip a decision's
sign. That isn't a critique of autoreason — it's empirical ground truth for the precise risk its gate is
exposed to, and it *sizes* the gate.

Concretely, the lab supports the initiative in four ways:

1. **Empirical judge-noise characterization** the gate needs to size `--gate-votes` — the data says a
   single-lens gate is unsafe.
2. **A runnable apparatus** ([apparatus/](apparatus/)) that executes autoreason's *diagnosis step* over real
   trace data — deterministic, zero tokens, matching its own "no LLM at the diagnosis step" thesis.
3. **The missing empirical benchmark** — the PR notes its benefit is unproven; this lab has the harness and
   the idle compute to produce it.
4. **A shared doctrine** — autoreason narrows to deterministic diagnosis "for auditability and cost
   efficiency"; that's this lab's two-economies principle (cheap sunk compute runs the controller; metered
   tokens only where they earn it).

## Start here → the artifacts

Coming from autoreason PR #2, read in this order:

1. **[AUTOREASON-CROSSOVER.html](https://djcdevelopment.github.io/windtunnel/AUTOREASON-CROSSOVER.html)** — the map: your six failure signatures, your
   mechanism library, and your gate, each set against what the lab measured.
2. **[APPARATUS-PROOF.html](https://djcdevelopment.github.io/windtunnel/APPARATUS-PROOF.html)** — proof it's real: the diagnosis step running over our
   trace (14/14 tests, zero tokens). Code in [apparatus/](apparatus/).
3. **[RECOMMENDATIONS.html](https://djcdevelopment.github.io/windtunnel/RECOMMENDATIONS.html)** — six data-ranked recommendations and the experiment plan,
   with live interim results and an open corrections log.

Going deeper: **[MATRIX-WIND-TUNNEL-LOG.html](https://djcdevelopment.github.io/windtunnel/MATRIX-WIND-TUNNEL-LOG.html)** is the underlying six-rounds study
the judge-confound result comes from. The repo [README](README.md) is the lab's own front page.

## Status

These are living documents. Two judge-robustness experiments (a repeat-judge variance decomposition and a
multi-model judge panel) are running on idle hardware as of 2026-07-10; `RECOMMENDATIONS.html` carries the
interim numbers and sheds its "preliminary" labels as the full runs land. The corrections log there is
deliberate — a lab that visibly corrects itself is more trustworthy, not less.
