# Scenario A: Greenfield — Batch Link Creation

## Requirement Input

> "Add POST /api/v1/links/batch for 1-25 items with per-item results (HTTP 200)."

(CL-01, recorded 2026-10-12.)

## Requirement Quality Checks (why clarification was NOT needed)

Run through `orchestration.nodes.quality_check.run_quality_checks()` — all 6 checks passed:

| Check | Result |
|---|---|
| `has_acceptance_criteria` | PASS — contains concrete numeric bounds ("1-25") and status code ("HTTP 200") |
| `no_vague_temporal_terms` | PASS |
| `no_internal_contradiction` | PASS |
| `within_policy_boundary` | PASS |
| `within_architecture_boundary` | PASS |
| `is_testable` | PASS |

This is the actual evidence-based reason the run proceeded `QUALITY_CHECK → DECOMPOSE` directly, never touching `CLARIFY` — verified in `tests/e2e/test_scenario_greenfield.py::test_greenfield_requirement_proceeds_without_clarification_gate`, which asserts zero `CLARIFY` transitions in the run's history.

## Decomposition

- Task: add `POST /api/v1/links/batch`, validate 1–25 items, per-item results.

## Design

- Additive endpoint — no breaking change.
- The whole batch is charged against the caller's rate limit **up front**: a `429` on the batch creates **zero** links (verified: `test_batch_rate_limited_request_creates_zero_links`).
- No batch-level idempotency — documented limitation; per-item `Idempotency-Key` is not supported for batch creation in this version.
- No database migration required.
- Contract: `1.0.0 → 1.1.0` (additive — `contracts/openapi.yaml`).

## Human Approval

`ARCH_APPROVAL`: approved by Belede Rahul — "Additive, no breaking change, no migration — approved." Recorded in `approval_records`.

## Implementation

`POST /api/v1/links/batch` in `src/shortener/api/links.py` — validates each item independently (scheme/SSRF, length), generates a unique code per successful item, returns per-item `created`/`error` results with overall `200` status even on partial failure.

## Testing

- `tests/e2e/test_scenario_greenfield.py` — 6 tests: per-item results, partial failure, 1–25 bound enforcement, rate-limit-as-one-request, zero-links-on-429, and the full orchestration-run trace with zero `CLARIFY` transitions.
- Parallel `TEST` node fan-out (unit/contract/security) executed as part of the governed run.

## Release

`RELEASE_APPROVAL`: `READY`, approved by Belede Rahul — "All tests pass, contract updated, documentation current." Run reached terminal state `DONE`.

## Reviewer Verification

```bash
pytest tests/e2e/test_scenario_greenfield.py -v
```
Expected: 6 passed. Inspect the governed run's full history via `GET /api/v1/workflows/{run_id}` (see `docs/traceability/reviewer-navigation.md`).
