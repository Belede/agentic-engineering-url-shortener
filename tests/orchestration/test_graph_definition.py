"""T015: explicit graph definition. ADR-004, plan.md §3.

The single most important test in this repository: it structurally enforces
ADR-005 (no auto-advance out of a human-gate node) and the constitution's
"approval inferred from silence" prohibition — not by convention, but by
asserting a property of the graph's data.
"""
from orchestration.graph import (
    HUMAN_GATE_STATES,
    NODES,
    TRANSITIONS,
    allowed_transitions,
    is_valid_transition,
)


def test_all_declared_nodes_are_known():
    expected = {
        "INGEST", "QUALITY_CHECK", "CLARIFY", "DECOMPOSE", "DESIGN",
        "ARCH_APPROVAL", "SECURITY_APPROVAL", "IMPLEMENT", "TEST",
        "DOCUMENT", "RELEASE_APPROVAL", "RENORMALIZE", "SAFE_STOP",
        "ROLLBACK", "COMPENSATE", "DONE",
    }
    assert set(NODES) == expected


def test_every_transition_references_a_known_node():
    for from_state, to_state, _actor in TRANSITIONS:
        assert from_state in NODES
        assert to_state in NODES


def test_human_gate_states_match_constitution_principle_iii():
    assert HUMAN_GATE_STATES == {"CLARIFY", "ARCH_APPROVAL", "SECURITY_APPROVAL", "RELEASE_APPROVAL"}


def test_no_system_actor_transition_leaves_a_human_gate_node():
    """The load-bearing structural guarantee (ADR-005): a run can never
    auto-advance out of CLARIFY/ARCH_APPROVAL/SECURITY_APPROVAL/RELEASE_APPROVAL.
    """
    for from_state, to_state, actor in TRANSITIONS:
        if from_state in HUMAN_GATE_STATES:
            assert actor == "human", (
                f"{from_state} -> {to_state} has actor={actor!r}; "
                "only 'human' actors may leave a human-gate node"
            )


def test_allowed_transitions_returns_edges_for_a_state():
    edges = allowed_transitions("QUALITY_CHECK")
    targets = {to for to, _actor in edges}
    assert "DECOMPOSE" in targets
    assert "CLARIFY" in targets


def test_is_valid_transition_true_for_declared_edge():
    assert is_valid_transition("INGEST", "QUALITY_CHECK", actor="system") is True


def test_is_valid_transition_false_for_undeclared_edge():
    assert is_valid_transition("INGEST", "DONE", actor="system") is False


def test_is_valid_transition_false_for_wrong_actor():
    """A human gate's edge declared actor='human' must reject a 'system' actor
    attempting the same from/to pair — this is what actually blocks silent
    auto-advance at runtime, not just at graph-definition time."""
    assert is_valid_transition("ARCH_APPROVAL", "IMPLEMENT", actor="system") is False
    assert is_valid_transition("ARCH_APPROVAL", "IMPLEMENT", actor="human") is True


def test_parallel_fanout_point_exists_in_test_node():
    """TEST node must declare multiple independent sub-groups (plan.md §3) —
    represented as a graph attribute, verified in test_engine's fan-out test;
    here we only assert the node itself is reachable and has a fan-in edge."""
    edges = allowed_transitions("TEST")
    targets = {to for to, _actor in edges}
    assert "DOCUMENT" in targets  # fan-in target after parallel sub-groups


def test_security_approval_is_a_conditional_branch_not_always_taken():
    """ARCH_APPROVAL can go straight to IMPLEMENT (no security-sensitive path
    touched) OR via SECURITY_APPROVAL (when it is) — both edges must exist."""
    targets = {to for to, _actor in allowed_transitions("ARCH_APPROVAL")}
    assert "IMPLEMENT" in targets
    assert "SECURITY_APPROVAL" in targets
