"""Explicit orchestration dependency graph. ADR-004, plan.md §3.

Represented as DATA (a node set + an edge list), not nested if/else control
flow — this is what makes the orchestration engine's claims inspectable and
testable rather than merely narrated (see the Independent Reviewer Gate's
review question #1).

Each edge is (from_state, to_state, actor) where actor is "system" or
"human". HUMAN_GATE_STATES are the nodes where constitution Principle III
("no approval inferred from silence") applies — enforced structurally below
by the fact that no edge leaving a human-gate node may have actor="system".
"""

NODES = (
    "INGEST", "QUALITY_CHECK", "CLARIFY", "DECOMPOSE", "DESIGN",
    "ARCH_APPROVAL", "SECURITY_APPROVAL", "IMPLEMENT", "TEST",
    "DOCUMENT", "RELEASE_APPROVAL", "RENORMALIZE", "SAFE_STOP",
    "ROLLBACK", "COMPENSATE", "DONE",
)

HUMAN_GATE_STATES = frozenset({"CLARIFY", "ARCH_APPROVAL", "SECURITY_APPROVAL", "RELEASE_APPROVAL"})

# (from_state, to_state, actor) — actor is "system" or "human".
TRANSITIONS: tuple[tuple[str, str, str], ...] = (
    ("INGEST", "QUALITY_CHECK", "system"),

    # Branch: well-defined requirement proceeds directly; a failed quality
    # check routes to the human-gated CLARIFY node (Scenario A vs C).
    ("QUALITY_CHECK", "DECOMPOSE", "system"),
    ("QUALITY_CHECK", "CLARIFY", "system"),

    # CLARIFY is a human gate: only an explicit human decision leaves it.
    ("CLARIFY", "RENORMALIZE", "human"),

    ("RENORMALIZE", "DECOMPOSE", "system"),
    ("DECOMPOSE", "DESIGN", "system"),
    ("DESIGN", "ARCH_APPROVAL", "system"),

    # ARCH_APPROVAL is a human gate. Two valid "approved" outcomes (branch:
    # straight to IMPLEMENT, or via the conditional SECURITY_APPROVAL edge
    # when the design touches a security-sensitive path) plus a rejection
    # path to SAFE_STOP — all human-actor transitions.
    ("ARCH_APPROVAL", "IMPLEMENT", "human"),
    ("ARCH_APPROVAL", "SECURITY_APPROVAL", "human"),
    ("ARCH_APPROVAL", "SAFE_STOP", "human"),

    # SECURITY_APPROVAL is a human gate.
    ("SECURITY_APPROVAL", "IMPLEMENT", "human"),
    ("SECURITY_APPROVAL", "SAFE_STOP", "human"),

    ("IMPLEMENT", "TEST", "system"),
    ("IMPLEMENT", "ROLLBACK", "system"),  # reversible implementation failure
    # Late ambiguity (fault-injection variant, spec.md Scenario A): a
    # material gap discovered mid-implementation suspends to the same
    # human-gated CLARIFY node as early ambiguity, reusing RENORMALIZE for
    # scoped resumption rather than a second, parallel mechanism.
    ("IMPLEMENT", "CLARIFY", "system"),

    # TEST fans out internally (unit/contract/security sub-groups) and fans
    # back in here; a retry-exhausted transient failure safe-stops.
    ("TEST", "DOCUMENT", "system"),
    ("TEST", "SAFE_STOP", "system"),

    ("DOCUMENT", "RELEASE_APPROVAL", "system"),

    # RELEASE_APPROVAL is a human gate.
    ("RELEASE_APPROVAL", "DONE", "human"),
    ("RELEASE_APPROVAL", "SAFE_STOP", "human"),

    # Safe-stop resume is always human-initiated and re-enters at the failed
    # node (FR-024); each of these targets is a realistic re-entry point.
    ("SAFE_STOP", "DESIGN", "human"),
    ("SAFE_STOP", "IMPLEMENT", "human"),
    ("SAFE_STOP", "TEST", "human"),

    # Rollback (reversible) returns to the pre-failure state automatically;
    # compensation (irreversible) requires human approval (ADR-006).
    ("ROLLBACK", "DESIGN", "system"),
    ("IMPLEMENT", "COMPENSATE", "human"),
    ("COMPENSATE", "TEST", "system"),
)


def allowed_transitions(from_state: str) -> list[tuple[str, str]]:
    return [(to, actor) for (frm, to, actor) in TRANSITIONS if frm == from_state]


def is_valid_transition(from_state: str, to_state: str, actor: str) -> bool:
    return (from_state, to_state, actor) in TRANSITIONS
