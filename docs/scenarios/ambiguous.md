# Scenario C: Ambiguous Requirement — Expiry Contradiction

## Original Ambiguous Input (CL-03)

> "Links should expire automatically after a while, but links that have already been shared must never break."

## Detected Ambiguity

`orchestration.nodes.quality_check.run_quality_checks()` — the **same, generic** 6 checks that passed the Greenfield requirement cleanly — found two failures:

- `no_vague_temporal_terms`: FAIL — "after a while" is not a measurable bound.
- `no_internal_contradiction`: FAIL — "expire" and "must never break" are asserted of the same subject (already-shared links).

The other four checks (`has_acceptance_criteria`, `within_policy_boundary`, `within_architecture_boundary`, `is_testable`) still passed — the defects are specific and named, not a blanket rejection.

## Workflow State Before Detection → Transition to CLARIFY

`INGEST → QUALITY_CHECK` (checks run, 2 of 6 fail) `→ CLARIFY`. Verified: zero `DECOMPOSE`/`DESIGN` transitions exist in the run's history before this point — nothing downstream was guessed (`tests/e2e/test_scenario_ambiguous.py`).

## Why Implementation Could Not Safely Continue

Proceeding would have required silently picking one of at least two incompatible interpretations (expire everything eventually, vs. never expire anything already shared) — exactly the kind of material ambiguity constitution Principle I requires be resolved or recorded, not guessed.

## Human Clarification Request and Real Recorded Decision

Asked via chat, 2026-10-12. **Real answer given by the human candidate (Belede Rahul)**: *"New links only"* — new links get a default expiry; links that already exist (already shared) are never retroactively affected. This resolves the contradiction by scoping expiry to creation time rather than applying it globally. Recorded via `POST /api/v1/workflows/{run_id}/clarify` into `approval_records` and `decisions` (not fabricated — `tests/e2e/test_scenario_ambiguous_resume.py::test_clarify_endpoint_records_the_real_answer_and_resumes`).

## Downstream Impact Analysis and Replanning

`RENORMALIZE` produced a real before/after task diff: the old blocked task ("implement expiry — contradictory") was removed; three new tasks were added (config field, new-links-only application logic, `no_expiry` opt-out). The run then re-entered `DECOMPOSE → DESIGN`, passing back through full governance rather than a shortcut.

## Design (Human-Approved)

Add `SHORTENER_DEFAULT_TTL_DAYS` (default 90, validated ≤ 365) to `src/shortener/config.py` — a security-sensitive file. Applied **only at creation time** for new links that set neither `expires_at`/`ttl_seconds` nor `no_expiry=true`. No migration (reuses the existing `expires_at` column). Contract `1.2.0 → 1.3.0`.

**Real human approvals** (both given via chat, 2026-10-12, Belede Rahul): `ARCH_APPROVAL` — approved; `SECURITY_APPROVAL` — approved (config.py change validated: bounded TTL, no secret exposure).

## Implementation

- `src/shortener/config.py::Settings.default_ttl_days` — along the way, TDD surfaced and fixed a **real latent bug**: the original `Settings` dataclass read `os.environ.get(...)` directly as field defaults, which Python evaluates once at class-definition time, not per-instantiation — meaning every setting was silently frozen to whatever the environment held at import time, for the life of the process. Fixed via `Settings.from_env()`, which reads fresh on every call. This bug predates this scenario (present since T005) and was only caught here because this scenario's test monkeypatched an env var for the first time in the suite.
- `src/shortener/api/links.py::_resolve_expires_at()` — now applies the default TTL when nothing else is specified and `no_expiry` is not set.

## Testing

- `test_full_run_reaches_release_approval_after_real_human_approvals` — the complete governed sequence: clarify → renormalize → decompose → design → (real) `ARCH_APPROVAL` → (real) `SECURITY_APPROVAL` → implement → test (parallel) → document → parked at `RELEASE_APPROVAL` (not auto-approved — covered by the combined final release decision, Phase 5).
- `tests/unit/test_config_default_ttl.py` — including the regression test for the latent env-caching bug.
- Regression: `test_create_with_no_expiry_fields_is_permanent` was renamed/updated to `test_create_with_no_fields_gets_the_default_ttl` + a new `test_create_with_no_expiry_true_remains_permanent` — the old CL-07 assumption is explicitly retired, not silently broken.

## Audit Trail

Every transition in this scenario (`QUALITY_CHECK → CLARIFY`, the human's `clarify` call, `RENORMALIZE`, `DECOMPOSE → DESIGN → ARCH_APPROVAL → SECURITY_APPROVAL → IMPLEMENT → TEST → DOCUMENT`) is recorded in `state_transitions` and `audit_events`, queryable via `GET /api/v1/workflows/{run_id}`.

## Terminal Outcome (at time of writing)

Parked at `RELEASE_APPROVAL` — intentionally. Release readiness for this scenario is decided together with Greenfield and Brownfield at the combined final release-readiness gate (Phase 5), not fabricated per-scenario.

## Reviewer Verification

```bash
pytest tests/e2e/test_scenario_ambiguous.py tests/e2e/test_scenario_ambiguous_resume.py -v
```
Expected: 7 passed.
