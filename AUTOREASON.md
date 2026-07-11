# windtunnel → autoreason

**windtunnel is a generalized, local-first testing lab** — controlled evaluation experiments on idle
consumer hardware (Nvidia + Intel GPUs) instead of frontier API tokens. This note is how it lines up with
[autoreason](https://github.com/NousResearch/autoreason): it **stress-tests the evaluation layer that
self-improving reasoning loops depend on** — the judged quality gate at the center of your
[bilevel PR #2](https://github.com/NousResearch/autoreason/pull/2).

## Take-away (if you read one line)

A self-improving loop's quality gate must **diversify its judge, not repeat it.** Our judge is
*near-deterministic on repeat* (within-cell σ **0.40**, median 0 over 192 cells), so repeat votes buy almost
nothing. All the real noise is *which lens/model you pick* (**~4.6–6.5 pt per item**). Resolving a genuine
**+3.05-pt** effect takes **~19 lens-diverse votes** — and a single-lens / 1-vote gate can *flip a decision's
sign*. That sizes your `--gate-votes` directly.

## What we measured — mapped to your PR

- **Your quality gate → ~19 lens-diverse votes.** Repeat-voting one judge is worthless (σ 0.40). Diversity is
  the entire lever. → [recommendations R1](https://djcdevelopment.github.io/windtunnel/RECOMMENDATIONS.html)
- **Your "diversify judge lenses" mechanism → backed, with a caveat.** Cross-*model* disagreement (**4.6**) ≈
  cross-*rubric* (**6.5**) for same-family judges — both matter, neither dominates. A different model *family*
  likely separates more. → R2
- **Your judge-herding signature → quantified.** One rubric lens (completeness) collapses the arm spread to
  **1.3 pt** and *flips* the concise-author effect (+2.8 → **−0.2**). →
  [crossover map](https://djcdevelopment.github.io/windtunnel/AUTOREASON-CROSSOVER.html)
- **A mechanism your library doesn't have → the concise-author prompt.** "Shortest complete, buildable answer;
  lead with the decision." **+3.05 pt**, wins under *every* rubric and *both* judge models, and is the most
  judge-robust arm. Cheap to graft into the inner loop.

## The honest arc (it's a lab, not a pitch)

We *ran* this — and running it earned its keep twice: it caught our **own wrong hypothesis** (we blamed a
300-token judge budget; a direct test refuted it) and surfaced a hardware limit that **disqualified one of our
judge models** (AM4's 32 GB DDR4 host-RAM ceiling — the lab's own documented constraint). Both are logged in
the open. → [OxenTODO](https://djcdevelopment.github.io/windtunnel/OxenTODO.html) ·
[corrections log](https://djcdevelopment.github.io/windtunnel/RECOMMENDATIONS.html)

## Run it / go deeper

- **[apparatus/](apparatus/)** — runnable, stdlib-only, **zero tokens**: it executes your outer loop's
  *diagnosis step* over our real trace, deterministically — matching your "no LLM at the diagnosis step" thesis.
  `python run_apparatus.py`.
- Rendered deep-dives: [crossover](https://djcdevelopment.github.io/windtunnel/AUTOREASON-CROSSOVER.html) ·
  [proof run](https://djcdevelopment.github.io/windtunnel/APPARATUS-PROOF.html) ·
  [recommendations + plan](https://djcdevelopment.github.io/windtunnel/RECOMMENDATIONS.html) ·
  [Matrix lab log](https://djcdevelopment.github.io/windtunnel/MATRIX-WIND-TUNNEL-LOG.html).
- **Offer:** your PR notes its empirical benefit is unproven. This lab has the harness and the idle compute to
  produce that benchmark — happy to run your `run_bilevel.py` outer loop over a wind-tunnel inner tournament.

## Status

Living documents. The two judge-robustness experiments above are **complete** (192 cells, K=6, run on idle
OMEN/AM4). The corrections log is deliberate — a lab that visibly corrects itself is more trustworthy, not less.
