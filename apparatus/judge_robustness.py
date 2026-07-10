"""Judge-robustness math -- the wind-tunnel's contribution to the autoreason gate.

autoreason's outer loop only keeps a mechanism change if it passes a *quality gate*:
a majority vote across `--gate-votes` blind pairwise trials, then rounds-to-converge
is the objective. That gate is judged. If the judge is biased, the gate climbs a
biased gradient and the whole hill-climb chases noise.

The wind-tunnel is, in effect, a controlled study of exactly that risk. Round 6
re-judged the same 192 finals under three rubric lenses. This module turns those
numbers into the quantities the autoreason gate needs to size itself:

  * inflation_factor     -- how much a single lens exaggerates an effect vs consensus
  * cross_lens_std       -- the between-lens noise a single-lens gate is exposed to
  * sign_flip_lenses     -- lenses that would REVERT a real improvement
  * required_gate_votes  -- votes needed to resolve the true effect against that noise

Pure stdlib arithmetic. Deterministic. No tokens.
"""
from __future__ import annotations

import math
import statistics


def effect_by_lens(trace: dict, arm: str, control: str | None = None) -> dict[str, float]:
    """Per-lens effect of `arm` vs the control arm (points)."""
    control = control or trace["control_arm"]
    out = {}
    for lens in trace["judge_lenses"]:
        out[lens] = trace["by_arm_by_lens"][arm][lens] - trace["by_arm_by_lens"][control][lens]
    return out


def inflation_factor(effects: dict[str, float], consensus_lens: str) -> float:
    """Largest single-lens effect / the consensus-lens effect.

    This is the wind-tunnel's headline '~3x' made into a computed number.
    """
    base = effects[consensus_lens]
    if base == 0:
        return math.inf
    return max(effects.values()) / base


def cross_lens_std(effects: dict[str, float]) -> float:
    """Sample std of the same effect measured under different lenses = between-lens noise."""
    vals = list(effects.values())
    return statistics.stdev(vals) if len(vals) > 1 else 0.0


def sign_flip_lenses(effects: dict[str, float], consensus_lens: str) -> list[str]:
    """Lenses whose sign disagrees with the consensus -- they'd revert a real change."""
    consensus_sign = math.copysign(1.0, effects[consensus_lens]) if effects[consensus_lens] else 0.0
    flips = []
    for lens, e in effects.items():
        if lens == consensus_lens:
            continue
        if e == 0 or math.copysign(1.0, e) != consensus_sign:
            flips.append(lens)
    return flips


def required_gate_votes(effect: float, noise: float, z: float = 2.0) -> float:
    """Votes needed to resolve `effect` against per-vote `noise` at ~z sigma.

    Model: each gate vote is a noisy estimate with std = noise (here, the between-lens
    std -- the uncertainty a lens-drawn vote actually carries). A K-vote mean has
    standard error noise/sqrt(K). Require effect >= z * SE  =>  K >= (z*noise/effect)^2.

    Heuristic, and labelled as such -- but it turns 'diversify the judge' from a slogan
    into a number: with a ~+3 effect and ~4 pt between-lens noise, a 1-vote gate is
    hopeless.
    """
    if effect <= 0:
        return math.inf
    return math.ceil((z * noise / effect) ** 2)


def report(trace: dict, arm: str) -> dict:
    """One-shot readout for `arm` vs control across all lenses."""
    control = trace["control_arm"]
    consensus = trace["consensus_lens"]
    effects = effect_by_lens(trace, arm, control)
    eff_consensus = effects[consensus]
    noise = cross_lens_std(effects)
    return {
        "arm": arm,
        "control": control,
        "consensus_lens": consensus,
        "effects_by_lens": effects,
        "consensus_effect": eff_consensus,
        "inflation_factor": inflation_factor(effects, consensus),
        "cross_lens_std": noise,
        "sign_flip_lenses": sign_flip_lenses(effects, consensus),
        "required_gate_votes": required_gate_votes(eff_consensus, noise),
    }


if __name__ == "__main__":  # pragma: no cover
    import json
    import pathlib
    trace = json.loads((pathlib.Path(__file__).parent / "windtunnel_trace.json").read_text())
    r = report(trace, "concise_author")
    print(json.dumps(r, indent=2))
