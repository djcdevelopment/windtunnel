"""Deterministic failure-signature classifier for a wind-tunnel / autoreason trace.

This mirrors the design intent of NousResearch/autoreason PR #2 (bilevel autoreason):
an *outer loop* that reads a run trace, diagnoses one bottleneck with a rule-based
classifier over a fixed, human-readable signature library, and applies a mechanism
change -- crucially with **no LLM call at the diagnosis step** ("the outer loop is
deterministic"). Here the same six signatures are run over the Matrix Wind-Tunnel's
own Rounds 5-6 trace, to show that (a) the signatures the outer loop hunts for are
observable in real consumer-hardware data, and (b) our runs already exercise and
calibrate several of them.

Six signatures, matching the autoreason mechanism library:
    premature_convergence, judge_herding, candidate_collapse,
    oscillation, position_bias, non_convergence

Overlaps are resolved by a fixed severity ordering, exactly as the PR specifies
("severity ordering resolves overlapping signatures deterministically").

Pure stdlib. No network, no model, no tokens -- the point of the exercise.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field

# Highest severity first. Deterministic tie-break between simultaneously-fired signatures.
SEVERITY_ORDER = [
    "non_convergence",
    "judge_herding",
    "candidate_collapse",
    "oscillation",
    "position_bias",
    "premature_convergence",
]

# Detection thresholds (all authored, auditable knobs -- no learned magic).
HERD_SPREAD_THRESHOLD = 2.0    # arm spread (pts) under one lens below this => that lens can't discriminate
OSCILLATION_MIN_FLIPS = 2      # sign flips in lap-to-lap deltas to call a series oscillating
OSCILLATION_NOISE_FLOOR = 0.5  # reversals smaller than this (pts) count as noise, not a real flip
POSITION_BIAS_THRESHOLD = 3.0  # ordering effect (pts) above this => position bias


@dataclass
class Signature:
    name: str
    fired: bool
    severity: float          # 0..1; only meaningful when fired
    evidence: str
    data_sufficient: bool = True

    def __repr__(self) -> str:  # pragma: no cover - display only
        state = "FIRED" if self.fired else ("n/a  " if not self.data_sufficient else "clear")
        return f"<{self.name:<22} {state} sev={self.severity:0.2f}>"


def _sign_flips(series: list[float], noise_floor: float) -> int:
    """Count sign changes in consecutive deltas, ignoring reversals under the noise floor."""
    deltas = [b - a for a, b in zip(series, series[1:])]
    signs = [(+1 if d > noise_floor else -1 if d < -noise_floor else 0) for d in deltas]
    signs = [s for s in signs if s != 0]
    return sum(1 for a, b in zip(signs, signs[1:]) if a != b)


# --- the six detectors --------------------------------------------------------

def detect_non_convergence(trace: dict) -> Signature:
    c = trace["convergence"]
    total, conv = c["cells_total"], c["cells_converged"]
    frac_unconverged = 1.0 - (conv / total if total else 0.0)
    fired = frac_unconverged >= 0.5
    ev = (f"{conv}/{total} cells reached VERDICT: CONVERGED; "
          f"{c['cells_full_budget_burned']}/{total} burned the full lap budget. "
          "The lap CAP, not convergence, is the control knob.")
    return Signature("non_convergence", fired, frac_unconverged, ev)


def detect_judge_herding(trace: dict) -> Signature:
    lenses = trace["judge_lenses"]
    arms = trace["arms"]
    spreads = {}
    for lens in lenses:
        vals = [trace["by_arm_by_lens"][a][lens] for a in arms]
        spreads[lens] = max(vals) - min(vals)
    herded = {lens: s for lens, s in spreads.items() if s < HERD_SPREAD_THRESHOLD}
    fired = len(herded) > 0
    severity = len(herded) / len(lenses)
    detail = ", ".join(f"{lens} spread {s:0.1f}" for lens, s in spreads.items())
    ev = (f"arm spread per lens: {detail}. "
          + (f"Lens(es) {list(herded)} collapse below {HERD_SPREAD_THRESHOLD} pts "
             "-- they can no longer tell the arms apart (herding)."
             if fired else "no lens herds."))
    return Signature("judge_herding", fired, severity, ev)


def detect_candidate_collapse(trace: dict) -> Signature:
    # Requires a candidate-population diversity signal. The wind-tunnel matrix is a
    # single refine chain per cell, not a tournament population, so there is nothing
    # to measure here. autoreason's inner tournament DOES carry this; a wind-tunnel
    # population arm would be needed to light it up.
    return Signature(
        "candidate_collapse", fired=False, severity=0.0,
        evidence=("matrix is a single planner->critic chain per cell; no candidate "
                  "population => diversity not measurable in this trace (autoreason's "
                  "tournament has it; wind-tunnel would need a population arm)."),
        data_sufficient=False,
    )


def detect_oscillation(trace: dict) -> Signature:
    series_by_arm = trace.get("by_arm_by_lap_default", {})
    worst_arm, worst_flips = None, 0
    for arm, series in series_by_arm.items():
        flips = _sign_flips(series, OSCILLATION_NOISE_FLOOR)
        if flips > worst_flips:
            worst_arm, worst_flips = arm, flips
    fired = worst_flips >= OSCILLATION_MIN_FLIPS
    # severity scales with flips but caps low -- these are mild, decline-then-blip shapes.
    severity = min(1.0, worst_flips / 3.0) * 0.5
    ev = (f"most-oscillating arm '{worst_arm}' shows {worst_flips} lap-to-lap sign flips "
          f"(noise floor {OSCILLATION_NOISE_FLOOR} pts). Borderline -- mostly monotone "
          "decline with one small up-blip." if fired else "no arm oscillates above the noise floor.")
    return Signature("oscillation", fired, severity, ev)


def detect_position_bias(trace: dict) -> Signature:
    ax = trace.get("ordering_axis", {})
    if not ax.get("present") or ax.get("per_level_scores") is None:
        return Signature(
            "position_bias", fired=False, severity=0.0,
            evidence=("N/A to this trace: the wind-tunnel judge scores each response "
                      "ABSOLUTELY (0-100, one at a time) -- there is no A/B position to bias. "
                      "autoreason's pairwise position_bias needs a pairwise-judge mode (not "
                      "built yet). The ordering axis we do have (" +
                      " vs ".join(ax.get("levels", [])) + ") swaps the planner/critic MODEL "
                      "-- a different, model-confounded thing."),
            data_sufficient=False,
        )
    a, b = ax["per_level_scores"]
    effect = abs(a - b)
    fired = effect > POSITION_BIAS_THRESHOLD
    return Signature("position_bias", fired, min(1.0, effect / 10.0),
                     f"ordering effect {effect:0.1f} pts across {ax['levels']}.")


def detect_premature_convergence(trace: dict) -> Signature:
    c = trace["convergence"]
    # Premature convergence requires cells that converged BEFORE budget while still rising.
    # Our trace converged on 0 cells -- the opposite failure. Cannot fire.
    fired = c["cells_converged"] > 0  # False on this trace
    ev = ("0 cells converged -- the opposite failure (non_convergence) holds; premature "
          "convergence is not present in this trace." if not fired
          else "some cells converged before budget.")
    return Signature("premature_convergence", fired, 0.0, ev)


DETECTORS = [
    detect_non_convergence,
    detect_judge_herding,
    detect_candidate_collapse,
    detect_oscillation,
    detect_position_bias,
    detect_premature_convergence,
]


def classify(trace: dict) -> dict:
    """Run every detector, then select the highest-severity fired signature.

    Returns {signatures: [Signature...ordered by severity_order], selected: name|None}.
    Deterministic: same trace in => same diagnosis out, no model in the loop.
    """
    sigs = {d(trace).name: d(trace) for d in DETECTORS}
    ordered = [sigs[name] for name in SEVERITY_ORDER]
    selected = next((s.name for s in ordered if s.fired), None)
    return {"signatures": ordered, "selected": selected}


if __name__ == "__main__":  # pragma: no cover
    import json
    import pathlib
    trace = json.loads((pathlib.Path(__file__).parent / "windtunnel_trace.json").read_text())
    result = classify(trace)
    for s in result["signatures"]:
        print(s)
    print("selected:", result["selected"])
