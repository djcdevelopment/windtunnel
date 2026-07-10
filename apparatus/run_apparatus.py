"""run_apparatus.py -- the bilevel outer-loop DIAGNOSIS step, run over real wind-tunnel data.

This is the "show we can" entrypoint. It performs one iteration of the autoreason-style
outer loop against the wind-tunnel's own Rounds 5-6 trace:

    1. read the trace                          (no model)
    2. classify the failure signature          (deterministic, signatures.py)
    3. look up the mechanism bundle            (mechanism_library.py, seeded w/ measured deltas)
    4. size the quality gate from judge noise  (judge_robustness.py)

Every step is rule-based arithmetic -- no LLM call, no tokens spent -- which is exactly
the property the autoreason PR argues for ("the outer loop is deterministic ... for
auditability and cost efficiency"). It is also the two-economies doctrine: the outer
loop is sunk-compute cheap; reserve metered frontier tokens for the inner generation.

Usage:
    python run_apparatus.py                 # runs over the bundled trace, prints a report
    python run_apparatus.py --arm concise_author
"""
from __future__ import annotations

import argparse
import json
import pathlib

import judge_robustness
import mechanism_library
import signatures

HERE = pathlib.Path(__file__).parent
RULE = "=" * 78
THIN = "-" * 78


def load_trace(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--trace", default=str(HERE / "windtunnel_trace.json"))
    ap.add_argument("--arm", default="concise_author",
                    help="arm to size the quality gate for (vs the control arm)")
    args = ap.parse_args()

    trace = load_trace(pathlib.Path(args.trace))

    print(RULE)
    print("BILEVEL OUTER LOOP -- diagnosis pass over wind-tunnel trace")
    print(f"  source : {trace['source']}")
    print(f"  arms   : {', '.join(trace['arms'])}   (control = {trace['control_arm']})")
    print(f"  lenses : {', '.join(trace['judge_lenses'])}   (consensus = {trace['consensus_lens']})")
    print("  cost   : 0 tokens -- rule-based classifier, no LLM in the diagnosis step")
    print(RULE)

    # --- step 2: classify -----------------------------------------------------
    result = signatures.classify(trace)
    print("\n[1] FAILURE-SIGNATURE SCAN  (six autoreason signatures)\n")
    for s in result["signatures"]:
        mark = "FIRED" if s.fired else ("n/a  " if not s.data_sufficient else "clear")
        print(f"  {mark}  {s.name:<22} sev={s.severity:0.2f}")
        print(f"         {s.evidence}")
    selected = result["selected"]
    print(f"\n  >> selected signature (highest severity): {selected}")

    # --- step 3: mechanism ----------------------------------------------------
    rec = mechanism_library.recommend(selected)
    print("\n" + THIN)
    print("[2] MECHANISM LOOKUP  (signature -> config delta, seeded with measured deltas)\n")
    if rec["mechanism"]:
        m = rec["mechanism"]
        print(f"  signature      : {rec['signature']}")
        print(f"  config bundle  : {m['bundle']}")
        print(f"  wind-tunnel ev : {m['windtunnel_evidence']}")
        print(f"  measured delta : {m['measured_delta']}")
    print(f"\n  cross-cutting lever (not in autoreason's library yet):")
    b = rec["bonus"]
    print(f"    {b['name']}: {b['bundle']}")
    print(f"    measured: {b['measured_delta']}")

    # --- step 4: size the gate ------------------------------------------------
    jr = judge_robustness.report(trace, args.arm)
    print("\n" + THIN)
    print(f"[3] GATE SIZING  (judge robustness for arm '{args.arm}' vs {jr['control']})\n")
    eff = ", ".join(f"{k}={v:+0.1f}" for k, v in jr["effects_by_lens"].items())
    print(f"  effect by lens       : {eff}")
    print(f"  consensus effect     : {jr['consensus_effect']:+0.1f}  (lens: {jr['consensus_lens']})")
    print(f"  single-lens inflation: {jr['inflation_factor']:0.2f}x  (max lens / consensus)")
    print(f"  between-lens noise   : {jr['cross_lens_std']:0.2f} pts (sample std across lenses)")
    print(f"  sign-flip lenses     : {jr['sign_flip_lenses'] or 'none'}  "
          f"(lenses that would REVERT a real gain)")
    print(f"  required gate votes  : {jr['required_gate_votes']}  "
          f"(to resolve the effect at ~2 sigma)")

    print("\n" + RULE)
    print("VERDICT")
    print(f"  Wind-tunnel data is a live instance of autoreason's '{selected}' signature.")
    flips = jr["sign_flip_lenses"]
    if flips:
        print(f"  A 1-vote gate drawing the '{flips[0]}' lens would REVERT the "
              f"{args.arm} gain (+{jr['consensus_effect']:0.1f} under consensus).")
    print(f"  => the gate needs >= {jr['required_gate_votes']} lens-diverse votes, not 1. "
          "This is the math that backs the autoreason gate.")
    print(RULE)


if __name__ == "__main__":
    main()
