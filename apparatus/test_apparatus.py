"""Stdlib self-tests for the bilevel apparatus. Run: python test_apparatus.py

Mirrors the autoreason PR's verification ethos (classifier routing + controller
dry-run tested before any empirical claim). No network, no model.
"""
import json
import math
import pathlib

import judge_robustness
import mechanism_library
import signatures

HERE = pathlib.Path(__file__).parent
TRACE = json.loads((HERE / "windtunnel_trace.json").read_text(encoding="utf-8"))

_passed = 0


def check(cond, label):
    global _passed
    assert cond, f"FAIL: {label}"
    _passed += 1
    print(f"  ok  {label}")


# --- classifier -----------------------------------------------------------
res = signatures.classify(TRACE)
check(res["selected"] == "non_convergence",
      "non_convergence is the selected (highest-severity) signature")

by_name = {s.name: s for s in res["signatures"]}
check(by_name["non_convergence"].fired and by_name["non_convergence"].severity == 1.0,
      "non_convergence fires at full severity (0/12 cells converged)")
check(by_name["judge_herding"].fired,
      "judge_herding fires (completeness lens spread 1.3 < 2.0)")
check(not by_name["candidate_collapse"].data_sufficient,
      "candidate_collapse correctly reports insufficient data (single-chain matrix)")
check(not by_name["position_bias"].data_sufficient,
      "position_bias correctly reports insufficient data (order axis not isolated)")
check(not by_name["premature_convergence"].fired,
      "premature_convergence does NOT fire (0 cells converged -- opposite failure)")

# every signature name is covered exactly once, matching the six-signature library
check(sorted(by_name) == sorted(signatures.SEVERITY_ORDER),
      "all six autoreason signatures are present exactly once")

# --- mechanism library ----------------------------------------------------
rec = mechanism_library.recommend(res["selected"])
check(rec["mechanism"]["bundle"][0].startswith("cap_laps"),
      "non_convergence recommends a lap cap (the measured control knob)")
check("concise" in rec["bonus"]["name"],
      "the cross-cutting bonus mechanism is the concise-author prompt")

# --- judge robustness -----------------------------------------------------
jr = judge_robustness.report(TRACE, "concise_author")
check(math.isclose(jr["consensus_effect"], 2.8, abs_tol=0.05),
      f"consensus (neutral) effect is +2.8 (got {jr['consensus_effect']:+0.2f})")
check(math.isclose(jr["inflation_factor"], 8.0 / 2.8, rel_tol=1e-6),
      f"single-lens inflation ~= 2.86x (got {jr['inflation_factor']:0.3f})")
check("completeness" in jr["sign_flip_lenses"],
      "the completeness lens would flip the sign of the concise-author gain")
check(jr["required_gate_votes"] >= 2,
      f"gate needs >= 2 votes to resolve the effect (got {jr['required_gate_votes']})")

# thorough_critic (autoreason's 'escalate critic difficulty') measured below baseline
tc = judge_robustness.effect_by_lens(TRACE, "thorough_critic")
check(tc["neutral"] < 0,
      f"escalate-critic mechanism measured BELOW baseline on neutral judge ({tc['neutral']:+0.1f})")

print(f"\n{_passed} checks passed.")
