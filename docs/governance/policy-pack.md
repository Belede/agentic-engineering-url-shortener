# Policy Pack v1.0.0

Versioned compliance/change-control policy guardrails evaluated by `src/policy/engine.py` on every orchestration run (FR-027, constitution Principle VI). Every run records which policy pack version it was evaluated against.

| ID | Description | Mandatory | Outcome values |
|---|---|---|---|
| SEC-001 | No disallowed URL scheme or SSRF-unsafe target introduced | Yes | PASS / FAIL / EXCEPTION-REQUESTED |
| CHG-001 | Architecture/contract changes require an approved ADR or `ARCH_APPROVAL` | Yes | PASS / FAIL / EXCEPTION-REQUESTED |
| DEP-001 | No unapproved new third-party dependency introduced | Yes | PASS / FAIL / EXCEPTION-REQUESTED |
| AUD-001 | Audit trail remains append-only for the life of the repository | Yes | PASS (structural — enforced by the absence of any UPDATE/DELETE code path against `audit_events`, ADR-008) |

## Exception Workflow

A FAIL on a mandatory policy blocks downstream progression (`has_mandatory_failure()`, verified by `/speckit-converge` at release time) unless a valid, approved exception exists. An exception (`src/policy/exceptions.py`) requires:

- `policy_id` — which policy the exception covers
- `reason` — why the exception is warranted
- `scope` — how narrowly it applies (e.g. "this run only")
- `approving_authority` — a non-empty human identity; `apply_exception()` structurally rejects an empty value
- `compensating_control` — what mitigates the risk in place of full compliance
- `expires_at` — an explicit expiry; `is_exception_valid()` returns `False` once passed, at which point the policy reverts to blocking FAIL

An evaluation against a policy with a valid, unexpired, approved exception returns `EXCEPTION-REQUESTED` rather than `FAIL`, and does not block release readiness. An evaluation with no applicable violation returns `PASS`. A policy not applicable to the current run (none currently defined, reserved for future growth) returns `NOT-APPLICABLE`.

## Versioning

Amendments to this policy pack follow the same semantic-versioning discipline as the constitution (`.specify/memory/constitution.md`): MAJOR for removing/redefining a mandatory policy, MINOR for adding one, PATCH for wording clarifications. Changing the mandatory/advisory status of an existing policy is a MAJOR change and requires human approval via the same ADR/change-control path as any other material architecture decision.
