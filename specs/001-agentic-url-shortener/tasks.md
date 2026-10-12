# Implementation Tasks: Agentic Software Engineering System: URL Shortener

**Input**: spec.md (clarified), plan.md, accepted ADR-001…011, checklists/quality-checklist.md

## Universal Task Policy (applies to every task below — not restated per row)

- **TDD obligation**: where marked `[TDD]`, the task follows the mandatory sequence — write failing test → run it → confirm it fails for the expected reason → implement minimum passing behavior → run it → refactor → run the regression suite → update docs/traceability. No task marked `[TDD]` is complete without an actually-executed `pytest` run attached as evidence at its Task-Group Checkpoint.
- **Documentation impact**: every task updates the relevant file under `docs/` (architecture, operations, or scenarios) in the same commit as the code it documents — never deferred to a later "docs cleanup" task.
- **Traceability update**: every task appends/updates its row(s) in `docs/traceability/matrix.md` (created at T045, then maintained incrementally by every subsequent task — in practice this means T045 is pulled earlier as a living file, updated per task group rather than written once at the end).
- **Risk/guardrail**: default guardrail for every task is "no unrelated file changes in the same commit" (constitution Principle X) and "no silent architecture/requirement drift" (if a task reveals a conflict with an approved artifact, stop and report per the Controlled Implementation rules — do not silently resolve).
- **Completion criteria (default)**: requirement mapping exists; test-first evidence exists where `[TDD]`; validation was actually executed (not claimed); documentation is current; traceability is updated; applicable checklist items pass; residual risks (if any) are stated.
- **NFR-009 (Testability)**: satisfied structurally by every `[TDD]` task's independent `pytest` target — no task is itself "the testability task"; `/speckit-analyze` verifies this universally rather than via one dedicated task.
- **Human approval**: a task is marked `[HUMAN]` only where it specifically requires a gate decision beyond the standing ADR/spec approvals already recorded; all other tasks execute under already-approved architecture without re-asking.

## Phase 0 — Engineering Baseline (Day 1 AM)

| ID | Objective | Requirements/ADRs | Target Paths | Deps | Parallel | TDD | Validation |
|---|---|---|---|---|---|---|---|
| T001 | Project scaffold: `pyproject.toml`, src layout, pytest config, lint config | ADR-001 | `pyproject.toml`, `src/shortener/__init__.py`, `tests/__init__.py` | — | no | no | `pytest --collect-only` succeeds (0 tests, 0 errors) |
| T002 | Local validation script (lint + test, single entrypoint) | ADR-009 | `scripts/validate.sh` | T001 | no | no | `./scripts/validate.sh` runs and exits 0 on empty suite |
| T003 | DB connection/session module + migration runner | ADR-002 | `src/shortener/persistence/db.py`, `src/shortener/migrations/runner.py` | T001 | no | [TDD] | `pytest tests/unit/persistence/test_migration_runner.py` |
| T004 | Migration 0001: baseline schema (short_links, redirect_events, api_keys, idempotency_keys, workflow_runs, state_transitions, decisions, approval_records, policy_evaluations, audit_events) | data-model.md, ADR-002, ADR-004, ADR-008 | `src/shortener/migrations/0001_baseline.sql` (+ `.down.sql`) | T003 | no | [TDD] | migration up/down/up test passes |
| T005 | FastAPI app skeleton + `/healthz`, `/readyz`, module boundary enforcement | ADR-001, FR-021, NFR-004 | `src/shortener/api/app.py`, `src/shortener/api/health.py` | T004 | no | [TDD] | `pytest tests/integration/test_health.py`; `uvicorn` boots locally |

## Phase 1 — Core URL Behavior (Day 1 PM)

| ID | Objective | Requirements/ADRs | Target Paths | Deps | Parallel | TDD | Validation |
|---|---|---|---|---|---|---|---|
| T006 | URL validation: scheme allow-list + SSRF private/loopback block | FR-002, NFR-001, CL-05, ADR-011 | `src/shortener/domain/validation.py` | T005 | yes (w/ T007) | [TDD] | `pytest tests/unit/domain/test_validation.py` |
| T007 | Short-code generation + bounded collision regeneration | FR-001, FR-003, FR-009, ADR-003 | `src/shortener/domain/shortcode.py` | T005 | yes (w/ T006) | [TDD] | `pytest tests/unit/domain/test_shortcode.py` incl. forced-collision case |
| T008 | API-key auth dependency (`X-API-Key`) | CL-06, ADR-011 | `src/shortener/api/auth.py` | T005 | yes (w/ T006,T007) | [TDD] | `pytest tests/integration/test_auth.py` |
| T009 | `POST /api/v1/links` create (incl. optional `expires_at`/`ttl_seconds`, no default expiry) | FR-001, FR-002, CL-07, contracts v1.0.0 | `src/shortener/api/links.py` | T006,T007,T008 | no | [TDD] | `pytest tests/contract/test_create_link.py` |
| T010 | Idempotency-Key handling on create | FR-007, CL-04 | `src/shortener/api/links.py`, `src/shortener/persistence/idempotency.py` | T009 | no | [TDD] | `pytest tests/integration/test_idempotency.py` |
| T011 | Rate limiting (60/min per API key, in-process token bucket) | FR-028, CL-08 | `src/shortener/api/rate_limit.py` | T008 | yes (w/ T009) | [TDD] | `pytest tests/integration/test_rate_limit.py` |
| T012 | `GET /{code}` redirect + expiry check | FR-004, FR-005 | `src/shortener/api/redirect.py` | T009 | no | [TDD] | `pytest tests/contract/test_redirect.py` |
| T013 | Analytics: atomic `RedirectEvent` write in the same transaction as redirect decision | FR-006, FR-008, NFR-003, ADR-011 | `src/shortener/domain/analytics.py` | T012 | no | [TDD] | `pytest tests/integration/test_analytics_concurrency.py` (parallel redirects → exactly-one-event-per-redirect) |
| T014 | Persistence-failure handling (DB unavailable → `503`, no partial write) | FR-010 | `src/shortener/persistence/*.py` | T009,T012 | no | [TDD] | `pytest tests/unit/persistence/test_failure_handling.py` |

## Phase 2 — Orchestration State Model + Approval Governance (Day 2 AM)

| ID | Objective | Requirements/ADRs | Target Paths | Deps | Parallel | TDD | Validation |
|---|---|---|---|---|---|---|---|
| T015 | Graph definition (nodes + allowed transitions as data) | ADR-004, plan.md §3 | `src/orchestration/graph.py` | T004 | no | [TDD] | `pytest tests/orchestration/test_graph_definition.py` — asserts no auto-advance edge out of any human-gate node |
| T016 | Engine loop (dispatch handler for current state, persist transition + audit event) | ADR-004, ADR-008, FR-011, FR-025 | `src/orchestration/engine.py` | T015 | no | [TDD] | `pytest tests/orchestration/test_engine_loop.py` |
| T017 | `QUALITY_CHECK` node — 6 deterministic checks | FR-016, CL-03 | `src/orchestration/nodes/quality_check.py` | T016 | yes (w/ T019) | [TDD] | `pytest tests/orchestration/test_quality_check.py` — both well-formed and CL-03 defective input cases |
| T018 | `CLARIFY` node + `POST /api/v1/workflows/{id}/clarify` | FR-013, FR-017, NFR-011, ADR-005 | `src/orchestration/nodes/clarify.py`, `src/orchestration/api.py` | T017 | no | [TDD] | `pytest tests/orchestration/test_clarify_gate.py` |
| T019 | `DECOMPOSE` node | FR-011 | `src/orchestration/nodes/decompose.py` | T016 | yes (w/ T017) | [TDD] | `pytest tests/orchestration/test_decompose.py` |
| T020 | `DESIGN` node (incl. brownfield impact-analysis hook) | FR-014, FR-015 | `src/orchestration/nodes/design.py` | T019 | no | [TDD] | `pytest tests/orchestration/test_design.py` |
| T021 | `ARCH_APPROVAL` node + approve/reject API | FR-013, NFR-011, ADR-005 | `src/orchestration/nodes/arch_approval.py` | T020 | no | [TDD] | `pytest tests/orchestration/test_arch_approval_gate.py` |
| T022 | `SECURITY_APPROVAL` conditional edge (security-sensitive path touched) | NFR-011, ADR-005, constitution VI | `src/orchestration/nodes/security_approval.py` | T021 | no | [TDD] | `pytest tests/orchestration/test_security_approval_gate.py` |
| T023 | `IMPLEMENT` node (records task-group evidence; human-supervised execution) | constitution Principle IV | `src/orchestration/nodes/implement.py` | T022 | no | [TDD] | `pytest tests/orchestration/test_implement_node.py` |
| T024 | `TEST` node with parallel fan-out/fan-in (unit/contract/security groups) | ADR-004 (parallel evidence) | `src/orchestration/nodes/test_node.py` | T023 | no | [TDD] | `pytest tests/orchestration/test_parallel_fanout.py` |
| T025 | `DOCUMENT` node + fallback stub on doc-generator failure | ADR-006 (fallback) | `src/orchestration/nodes/document.py` | T024 | yes (w/ T026) | [TDD] | `pytest tests/orchestration/test_document_fallback.py` |
| T026 | `RELEASE_APPROVAL` node + approve API, READY/LIMITATIONS/NOT READY | FR-020, NFR-011 | `src/orchestration/nodes/release_approval.py` | T024 | yes (w/ T025) | [TDD] | `pytest tests/orchestration/test_release_approval_gate.py` |
| T027 | Workflow inspection API (`GET /api/v1/workflows/{id}`, state history) | FR-012 | `src/orchestration/api.py` | T016 | no | [TDD] | `pytest tests/integration/test_workflow_inspection.py` |

## Phase 3 — Reliability + Observability (Day 2 PM)

| ID | Objective | Requirements/ADRs | Target Paths | Deps | Parallel | TDD | Validation |
|---|---|---|---|---|---|---|---|
| T028 | Retry/backoff wrapper + transient/permanent classification | FR-022, NFR-002, ADR-006 | `src/orchestration/reliability/retry.py` | T016 | yes (w/ T029) | [TDD] | `pytest tests/orchestration/test_retry.py` — forced transient fault |
| T029 | Rollback mechanism | FR-023, ADR-006 | `src/orchestration/reliability/rollback.py` | T016 | yes (w/ T028) | [TDD] | `pytest tests/orchestration/test_rollback.py` |
| T030 | Compensation mechanism | FR-023, ADR-006 | `src/orchestration/reliability/compensation.py` | T016 | yes (w/ T028,T029) | [TDD] | `pytest tests/orchestration/test_compensation.py` |
| T031 | Safe-stop + explicit human resume API | FR-019, FR-024, NFR-008, ADR-006 | `src/orchestration/reliability/safe_stop.py`, `src/orchestration/api.py` | T028 | no | [TDD] | `pytest tests/orchestration/test_safe_stop_resume.py` — includes a process-restart-mid-stage resume case (FR-019) |
| T032 | `RENORMALIZE` dynamic replanning + before/after task diff | FR-018, ADR-007 | `src/orchestration/nodes/renormalize.py` | T018 | no | [TDD] | `pytest tests/orchestration/test_replanning.py` |
| T033 | Audit-event completeness (one row per transition) | FR-025, NFR-006, ADR-008 | `src/orchestration/telemetry/audit.py` | T016 | yes (w/ T034) | [TDD] | `pytest tests/orchestration/test_audit_completeness.py` |
| T034 | Metrics registry (success rate, retry/rollback freq, MTTR, latency) | FR-026, NFR-005, ADR-008, plan.md §6 MTTR formula | `src/orchestration/telemetry/metrics.py` | T033 | no | [TDD] | `pytest tests/orchestration/test_mttr_calculation.py` — known-expected-value case |
| T034b | Performance validation: p95 redirect-resolution latency, demonstration-labeled | NFR-007, CL-09 | `tests/performance/test_redirect_latency.py` | T012,T013 | yes (w/ T034) | [TDD] | `pytest tests/performance/test_redirect_latency.py` — asserts p95 < 100ms on local hardware, result recorded with explicit "demonstration measurement, not a production SLA" label per ADR-008 |
| T035 | Policy evaluation engine + policy-pack v1.0.0 | FR-027, constitution VI | `src/policy/engine.py`, `docs/governance/policy-pack.md` | T016 | no | [TDD] | `pytest tests/orchestration/test_policy_evaluation.py` |
| T036 | Policy-exception workflow (approval, rationale, expiry, compensating control) | constitution VI | `src/policy/exceptions.py` | T035 | no | [TDD] | `pytest tests/orchestration/test_policy_exception.py` |

## Phase 4 — Three Required Scenarios + Fault Injection (Day 3 AM)

| ID | Objective | Requirements/ADRs | Target Paths | Deps | Parallel | TDD | Validation | Human |
|---|---|---|---|---|---|---|---|---|
| T037 | Greenfield: `POST /api/v1/links/batch`, run through full orchestration (contract 1.0.0→1.1.0) | CL-01, FR-029 | `src/shortener/api/links.py`, `contracts/openapi.yaml` | T026 | no | [TDD] | `pytest tests/e2e/test_scenario_greenfield.py` | [HUMAN] `ARCH_APPROVAL` for this run |
| T038 | Brownfield: impact-analysis artifact (pre-code) | CL-02, NFR-010 | `docs/scenarios/brownfield-impact-analysis.md` | T037 | no | n/a (analysis, not code) | committed before any T039/T040 code change | — |
| T039 | Brownfield: migration 0002 (`max_clicks` nullable column, reversible) | CL-02, ADR-002 | `src/shortener/migrations/0002_max_clicks.sql` (+`.down.sql`) | T038 | no | [TDD] | migration up/down/up test | [HUMAN] `ARCH_APPROVAL` (migration-aware) |
| T040 | Brownfield: atomic `max_clicks` check + `410 LINK_EXHAUSTED` | CL-02, FR-030 | `src/shortener/api/redirect.py` | T039 | no | [TDD] | `pytest tests/e2e/test_scenario_brownfield.py` — concurrency test for atomic counting | — |
| T041 | Ambiguous: feed CL-03 text through orchestration, verify `CLARIFY` halt with both defects named | CL-03, FR-016 | `tests/e2e/test_scenario_ambiguous.py` | T026 | no | [TDD] | run halts at `CLARIFY`, defect list matches CL-03 | [HUMAN] clarification answer required |
| T042 | Ambiguous: apply human clarification answer, `RENORMALIZE`, resume, implement agreed interpretation | CL-03, FR-018 | `src/shortener/...` (per agreed interpretation) | T041 | no | [TDD] | `pytest tests/e2e/test_scenario_ambiguous.py` (full run to `DONE`) | [HUMAN] `ARCH_APPROVAL` post-replan |
| T043 | Fault-injection variants: flaky→retry, doc-gen outage→fallback, late ambiguity, broken change→rollback, failed release→compensation, crash→resume | ADR-006, ADR-007 | `tests/e2e/test_fault_injection_*.py` | T028–T032 | yes (independent variants) | [TDD] | each variant's dedicated test | [HUMAN] gates per variant, test identities (per earlier confirmed decision) |
| T044 | Scenario evidence documentation | spec.md Required Scenarios | `docs/scenarios/greenfield.md`, `brownfield.md`, `ambiguous.md` | T037,T040,T042 | no | no | `/speckit` three-scenario evidence review passes | — |

## Phase 5 — Release Readiness (Day 3 PM)

| ID | Objective | Requirements/ADRs | Target Paths | Deps | Parallel | TDD | Validation | Human |
|---|---|---|---|---|---|---|---|---|
| T045 | Traceability matrix (requirement→scenario→design→ADR→task→code→test→evidence) | plan.md §13 | `docs/traceability/matrix.md` | all above | no | no | zero orphan requirements/tasks | — |
| T046 | Dependency/license scan + security summary | NFR-001, constitution V | `docs/architecture/threat-model.md` | T006,T011 | yes (w/ T045) | no | `pip-audit`-equivalent run recorded | — |
| T047 | Reviewer navigation guide | guide §26 | `docs/traceability/reviewer-navigation.md` | T045 | no | no | every claim resolves to a real path/command | — |
| T048 | `/speckit-analyze` (pre-implementation was run earlier; re-run post-implementation as part of convergence prep) | guide §13 | — | T044 | no | no | zero CRITICAL/HIGH findings outstanding | — |
| T049 | `/speckit-converge` | guide §22 | `docs/assessment/convergence-report.md` | T045–T048 | no | no | release decision computed | [HUMAN] reviews convergence output |
| T050 | Final Independent Assessment (hostile Principal Engineer review) | guide §23 | `docs/assessment/final-assessment.md` | T049 | no | no | PASS/BORDERLINE/FAIL verdict recorded | — |
| T051 | Final Engineering Summary (21-section schema) | guide §25 | `docs/assessment/final-engineering-summary.md` | T050 | no | no | all 21 sections present | — |
| T052 | Release-readiness decision + tag | guide §28 | git tag `assessment-submission-v1.0` | T051 | no | no | clean `git status`, clean clone verified | [HUMAN] final release decision |

## Dependency Notes

- Phase 1 tasks (T006–T014) do not depend on any Phase 2 orchestration task — they are independently testable (constitution Principle VII), confirming plane separation (ADR-001).
- T037 (Greenfield) and T038–T040 (Brownfield) both depend on the full orchestration engine (through T027) being complete, but are otherwise independent of each other and could execute in either order; T041–T042 (Ambiguous) similarly only depends on the engine, not on T037/T038–40 — sequenced last here only because CL-03's `SECURITY_APPROVAL` edge benefits from `config.py`-equivalent code already existing from earlier phases.
- T043's fault-injection variants are independent of each other and of T037/T038-40/T041-42 except for sharing the already-built reliability primitives (T028–T032) — genuinely parallelizable.
