"""T017: QUALITY_CHECK node — 6 deterministic, generic checks. FR-016, CL-03.

Per the pre-implementation independent review (condition #3), these checks
must be generic — proven by a well-formed, unrelated requirement also
passing cleanly, not just by recognizing the one planted CL-03 example.
"""
from orchestration.nodes.quality_check import run_quality_checks

GREENFIELD_REQUIREMENT = (
    "Add POST /api/v1/links/batch for 1-25 items with per-item results (HTTP 200)."
)
AMBIGUOUS_REQUIREMENT = (
    "Links should expire automatically after a while, but links that have "
    "already been shared must never break."
)


def test_well_formed_requirement_passes_all_six_checks():
    result = run_quality_checks(GREENFIELD_REQUIREMENT)
    assert result.passed is True
    assert len(result.checks) == 6
    assert all(result.checks.values())
    assert result.failures == []


def test_ambiguous_requirement_fails_vague_temporal_and_contradiction_checks():
    result = run_quality_checks(AMBIGUOUS_REQUIREMENT)
    assert result.passed is False
    assert "no_vague_temporal_terms" in result.failures
    assert "no_internal_contradiction" in result.failures
    # the other four checks are unrelated to this requirement's specific
    # defects and should still pass — proves the checks are independent,
    # not one monolithic pass/fail blob.
    assert result.checks["has_acceptance_criteria"] is True
    assert result.checks["within_policy_boundary"] is True
    assert result.checks["within_architecture_boundary"] is True
    assert result.checks["is_testable"] is True


def test_another_vague_requirement_also_fails_generically():
    """A different vague requirement (not CL-03's exact wording) must also
    be caught — this is the generality proof the independent review asked for."""
    result = run_quality_checks("The system should respond quickly, eventually.")
    assert result.passed is False
    assert "no_vague_temporal_terms" in result.failures


def test_requirement_violating_policy_boundary_fails():
    result = run_quality_checks("Disable rate limit for all internal callers.")
    assert result.checks["within_policy_boundary"] is False
    assert result.passed is False


def test_requirement_violating_architecture_boundary_fails():
    result = run_quality_checks("Switch persistence to use MongoDB instead.")
    assert result.checks["within_architecture_boundary"] is False
    assert result.passed is False


def test_question_form_requirement_is_not_testable():
    result = run_quality_checks("Should links expire?")
    assert result.checks["is_testable"] is False


def test_requirement_with_no_acceptance_signal_fails_that_check():
    result = run_quality_checks("Improve the system.")
    assert result.checks["has_acceptance_criteria"] is False
