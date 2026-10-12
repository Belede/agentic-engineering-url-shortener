"""QUALITY_CHECK node: 6 deterministic, generic requirement-quality checks.
FR-016, CL-03, constitution Principle I (ambiguities resolved or recorded).

These checks are intentionally generic (not keyed to one planted example) —
independent review condition: proven by GREENFIELD_REQUIREMENT also passing
cleanly in tests/orchestration/test_quality_check.py, not just by catching
the one ambiguous-scenario text.
"""
import re
from dataclasses import dataclass, field

VAGUE_TEMPORAL_PATTERNS = (
    r"\bafter a while\b", r"\beventually\b", r"\bsoon\b", r"\bshortly\b",
    r"\bat some point\b", r"\bquickly\b",
)

# (pattern_a, pattern_b): if BOTH appear, the requirement asserts two
# incompatible behaviors about the same subject.
CONTRADICTION_PAIRS = (
    (r"\bexpire[sd]?\b", r"\bnever break\b"),
    (r"\bexpire[sd]?\b", r"\bmust never\b"),
    (r"\bdelete[sd]?\b", r"\bmust never\b"),
    (r"\bremove[sd]?\b", r"\bmust always\b"),
)

# Deliberately small, prototype-scoped denylists (constitution Principle VI:
# versioned policy guardrails; ADR-001: approved architecture is SQLite/FastAPI).
POLICY_FORBIDDEN_PHRASES = (
    "disable rate limit", "disable auth", "remove authentication", "skip validation",
)
ARCHITECTURE_FORBIDDEN_PHRASES = (
    "use mongodb", "use postgres cluster", "switch to microservices", "use a message queue",
)


@dataclass
class QualityCheckResult:
    checks: dict[str, bool]
    failures: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(self.checks.values())


def _has_acceptance_criteria(text: str) -> bool:
    """A requirement has at least one concrete, measurable signal: a digit
    (a bound, count, or status code) or an explicit must/should/when/given
    clause naming observable behavior."""
    has_number = bool(re.search(r"\d", text))
    has_concrete_clause = bool(re.search(r"\b(must|should|returns?|when|given)\b", text, re.IGNORECASE))
    return has_number or has_concrete_clause


def _no_vague_temporal_terms(text: str) -> bool:
    return not any(re.search(p, text, re.IGNORECASE) for p in VAGUE_TEMPORAL_PATTERNS)


def _no_internal_contradiction(text: str) -> bool:
    return not any(
        re.search(a, text, re.IGNORECASE) and re.search(b, text, re.IGNORECASE)
        for a, b in CONTRADICTION_PAIRS
    )


def _within_policy_boundary(text: str) -> bool:
    return not any(p in text.lower() for p in POLICY_FORBIDDEN_PHRASES)


def _within_architecture_boundary(text: str) -> bool:
    return not any(p in text.lower() for p in ARCHITECTURE_FORBIDDEN_PHRASES)


def _is_testable(text: str) -> bool:
    """Crude but explicit structural heuristic: not posed as a question,
    and long enough to express a subject + behavior."""
    stripped = text.strip()
    if stripped.endswith("?"):
        return False
    return len(stripped.split()) >= 4


CHECKS = {
    "has_acceptance_criteria": _has_acceptance_criteria,
    "no_vague_temporal_terms": _no_vague_temporal_terms,
    "no_internal_contradiction": _no_internal_contradiction,
    "within_policy_boundary": _within_policy_boundary,
    "within_architecture_boundary": _within_architecture_boundary,
    "is_testable": _is_testable,
}


def run_quality_checks(requirement_text: str) -> QualityCheckResult:
    checks = {name: fn(requirement_text) for name, fn in CHECKS.items()}
    failures = [name for name, passed in checks.items() if not passed]
    return QualityCheckResult(checks=checks, failures=failures)
