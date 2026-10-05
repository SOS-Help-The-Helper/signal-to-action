"""Loops spec tests. No fixtures needed — the spec is self-contained.

Run from the distill root: python3 -m signal_action.tests.test_loops
"""
from signal_action.loops import (
    COORDINATION_LOOP,
    ENGINE,
    EVALUATION_LOOP,
    FORBIDDEN_LABEL,
    FRAMEWORK,
    HELPER_NOUN,
    INNER_LOOPS,
    INTERNAL_SCORER,
    JUDGMENT,
    MEMORY_LOOP,
    NON_COLLAPSIBLE_RULES,
    OUTER_STAGES,
    REQUEST_NOUN,
    RESOURCE_NOUN,
    TRUST_LOOP,
    VENDOR_DECISION_MODEL,
    InnerLoop,
    Lane,
    LoopSpecError,
    validate_loop,
)


def test_stage_order_exact():
    names = [s.name for s in OUTER_STAGES]
    assert names == ["Signal", "Judgment", "Proposal", "Human Decision",
                     "Action", "Outcome", "Learning"], names
    # the outer loop is NOT called "coordination"
    assert "Coordination" not in names
    print("stage order exact: OK")


def test_stages_have_contracts():
    for s in OUTER_STAGES:
        assert s.description and s.handoff, f"stage {s.name} missing contract"
    by_name = {s.name: s for s in OUTER_STAGES}
    assert by_name["Judgment"].lane is Lane.SORTING
    assert by_name["Proposal"].lane is Lane.SYNTHESIS
    assert by_name["Human Decision"].lane is Lane.DECISION
    print("stage contracts: OK")


def test_non_collapsible_rules():
    joined = " ".join(NON_COLLAPSIBLE_RULES)
    for key in ("silently", "Evidence", "Unknown", "not proof of execution",
                "Humans own irreversible", "Every outcome feeds learning",
                "append-only ledger"):
        assert key in joined, f"missing rule fragment: {key}"
    print("non-collapsible rules: OK")


def test_inner_loop_steps_exact():
    assert list(COORDINATION_LOOP.steps) == ["Match", "Route", "Commit", "Track", "Learn"]
    assert COORDINATION_LOOP.subtitle == "maintains the commitment record"
    assert list(MEMORY_LOOP.steps) == ["Outcome", "Memory", "Judgment"]
    assert MEMORY_LOOP.subtitle == "maintains the decision rules"
    assert list(TRUST_LOOP.steps) == ["Evidence", "Score", "Routing weight"]
    assert TRUST_LOOP.subtitle == "maintains the routing weights"
    assert list(EVALUATION_LOOP.steps) == ["Override", "Eval set", "Calibration"]
    assert EVALUATION_LOOP.subtitle == "maintains the calibration set"
    assert len(INNER_LOOPS) == 4
    print("inner loop steps exact: OK")


def test_validate_accepts_canonical():
    for loop in INNER_LOOPS:
        assert validate_loop(loop) is True, loop.name
    print("validate accepts canonical loops: OK")


def test_validate_rejects_missing_decay():
    bad = InnerLoop(name="NoDecay", subtitle="x", steps=("A", "B"),
                    gating="human gate", decay="")
    try:
        validate_loop(bad)
    except LoopSpecError as e:
        assert "decay" in str(e).lower(), e
    else:
        raise AssertionError("missing decay did not raise LoopSpecError")
    print("validate rejects missing decay: OK")


def test_validate_rejects_missing_gating():
    bad = InnerLoop(name="NoGate", subtitle="x", steps=("A", "B"),
                    gating="", decay="expires after 7 days")
    try:
        validate_loop(bad)
    except LoopSpecError as e:
        assert "gating" in str(e).lower(), e
    else:
        raise AssertionError("missing gating did not raise LoopSpecError")
    print("validate rejects missing gating: OK")


def test_validate_rejects_empty_steps():
    bad = InnerLoop(name="NoSteps", subtitle="x", steps=(),
                    gating="g", decay="d")
    try:
        validate_loop(bad)
    except LoopSpecError:
        pass
    else:
        raise AssertionError("empty steps did not raise LoopSpecError")
    print("validate rejects empty steps: OK")


def test_naming_constants():
    assert FRAMEWORK == "Signal-to-Action"
    assert ENGINE == "Relay"
    assert JUDGMENT == "Judgment"
    assert VENDOR_DECISION_MODEL == "TypeSafe Jev"
    assert INTERNAL_SCORER == "SOS scorer"
    assert "Jev" not in INTERNAL_SCORER.split()  # never bare "Jev" internally
    print("naming constants: OK")


def test_language_constants():
    assert REQUEST_NOUN == "requests"
    assert RESOURCE_NOUN == "resources"
    assert HELPER_NOUN == "helpers"
    assert FORBIDDEN_LABEL == "survivor"
    print("language constants: OK")


if __name__ == "__main__":
    test_stage_order_exact()
    test_stages_have_contracts()
    test_non_collapsible_rules()
    test_inner_loop_steps_exact()
    test_validate_accepts_canonical()
    test_validate_rejects_missing_decay()
    test_validate_rejects_missing_gating()
    test_validate_rejects_empty_steps()
    test_naming_constants()
    test_language_constants()
    print("\nALL LOOP TESTS PASSED")
