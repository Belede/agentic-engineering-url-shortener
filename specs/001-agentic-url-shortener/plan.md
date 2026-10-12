# Technical Plan: Agentic Software Engineering System: URL Shortener

**Status**: Draft — architecture decisions formalized separately as ADRs (Human Gate 4)

**Input**: `spec.md` (clarified), constitution v1.0.0

## 1. System Context

**System boundary**: a single locally-runnable service process exposing (a) the URL-shortener HTTP API and (b) the orchestration HTTP API, backed by one SQLite database file. No external network dependency is required to run or test the prototype.

**Actors**: API Consumer (UT-01), Software Engineer (UT-02), Human Reviewer/Approver (UT-03), Release Owner (UT-04), Assessment Reviewer (UT-05) — see spec.md User Types.

**External dependencies**: none required. An optional real-LLM adapter (behind `LLM_PROVIDER=none|anthropic`) may call the Anthropic API for one illustrative reasoning step only when explicitly enabled; default is `none` (fully deterministic, per the human-confirmed agent-mode decision).

**Trust boundaries**: the HTTP boundary is the only trust boundary — all external input (URLs, headers, workflow commands) is untrusted until validated. The SQLite file is local, single-process-owned; no separate trust boundary inside the process.

**Major runtime components**:
- `api/` — FastAPI HTTP delivery layer (shortener endpoints + orchestration endpoints)
- `domain/` — shortener domain logic (pure functions/classes, no framework imports)
- `orchestration/` — workflow engine: dependency graph, state machine, gates, retries, audit
- `persistence/` — SQLite repositories (one per aggregate), migrations
- `policy/` — versioned compliance/change-control policy evaluation
- `telemetry/` — structured logging, metrics, audit-event sink

**Data ownership**: the shortener domain owns `ShortLink`/`RedirectEvent`; the orchestration domain owns `WorkflowRun`/`StateTransition`/`ApprovalRecord`/`PolicyEvaluation`/`AuditEvent`. Both persist to the same SQLite file but through separate repository modules — no cross-domain direct table access.

**Application-plane vs. control-plane**: the shortener API/domain/persistence is the **application plane** (what end users exercise). The orchestration engine is the **control/orchestration plane** (what governs how changes to the application plane get built). They are physically separate modules so the control plane's own tests do not require the application plane to exist, and vice versa — this separation is itself validated in `/speckit-analyze` and `/speckit-converge`.

## 2. URL Shortener Architecture

### API and schema deliverables (versioned, explicit)

- `specs/001-agentic-url-shortener/contracts/openapi.yaml` — OpenAPI 3.0 contract, starting at **v1.0.0** (baseline: single-link create, redirect, health). Each scenario that adds a capability bumps this file's version under change control (CL-01 → 1.1.0 batch create; CL-02 → schema/contract note for `max_clicks`).
- `specs/001-agentic-url-shortener/data-model.md` — request/response/error schemas, `ShortLink`, `RedirectEvent`, and orchestration entities (`WorkflowRun`, `StateTransition`, `ApprovalRecord`, `PolicyEvaluation`, `AuditEvent`), plus compatibility/migration rules.
- Every contract change records: ownership (human candidate), version impact (semver), backward-compatibility impact, affected consumers (API Consumer only, single-service), required tests (contract tests under `tests/contract/`), documentation impact, rollout/migration steps, and the human approval that authorized it (an ADR or a per-scenario `ARCH_APPROVAL`).

### Components

| Component | Responsibility |
|---|---|
| API delivery | FastAPI routers for `/api/v1/links*`, `/{code}` redirect, `/healthz`, `/readyz`, `/api/v1/workflows*` |
| Domain logic | URL validation (scheme + SSRF-block), short-code generation, expiry evaluation, click-limit evaluation |
| Short-code generation | Base62, 7 chars, cryptographically random; collision check against the DB unique constraint with bounded regeneration (max 5 attempts, else `503 CODE_SPACE_EXHAUSTED` — practically unreachable at this scale, included for completeness) |
| URL validation | scheme allow-list (`http`,`https`), length limit, private/loopback IP block (CL-05) |
| Redirect resolution | lookup by code → check expiry → check `max_clicks` (CL-02, post-brownfield) → record `RedirectEvent` → 302 |
| Persistence | SQLite via a thin repository layer (no ORM magic; explicit SQL, explicit migrations under `src/shortener/migrations/`) |
| Analytics | `RedirectEvent` table + a simple aggregate-count read endpoint |
| Expiration | `expires_at` nullable column; evaluated at redirect time (lazy expiry, no background sweeper needed for a prototype) |
| Health/readiness | `/healthz` = process up; `/readyz` = DB reachable |
| Telemetry | structured JSON logs + an in-process metrics registry queryable via `/api/v1/metrics` |
| Configuration | environment variables, documented in `docs/operations/configuration.md`, validated at startup |

## 3. Agentic Orchestration Architecture

### Model

A **persisted, explicit state machine per workflow run**, not a linear function-call chain. Each run is a row in `workflow_runs` plus an append-only `state_transitions` table forming the audit trail. Stage logic is implemented as pure, independently-testable "node handlers" that the engine invokes based on the current state and the dependency graph — not a single monolithic `run()` function.

### Nodes (stages)

| Node | Purpose | Preconditions | Postconditions | Actor | Timeout | Retry |
|---|---|---|---|---|---|---|
| `INGEST` | Normalize raw requirement text into a structured requirement record | run created | requirement normalized | system | 5s | 2 attempts, backoff 1s |
| `QUALITY_CHECK` | Run deterministic requirement-quality checks (6 checks: has acceptance criteria, no vague temporal terms, no internal contradiction, within policy boundary, within architecture boundary, testable) | requirement normalized | checks recorded; routes to `DECOMPOSE` or `CLARIFY` | system | 5s | 1 (deterministic, no retry value) |
| `CLARIFY` | Halt for human clarification when quality checks fail | quality check failed | human decision recorded | **human** | none (blocks indefinitely) | n/a |
| `DECOMPOSE` | Produce task breakdown + dependency edges | requirement accepted (direct or post-clarify) | task list persisted | system | 10s | 2 |
| `DESIGN` | Produce the design proposal (API/schema/migration impact) | decomposition complete | design proposal persisted | system | 10s | 2 |
| `ARCH_APPROVAL` | Halt for human architecture sign-off | design proposal exists | approval/rejection recorded | **human** | none | n/a |
| `SECURITY_APPROVAL` | Halt for human sign-off when a security-sensitive file/path is touched | design touches a security-sensitive path | approval/rejection recorded | **human** | none | n/a |
| `IMPLEMENT` | Apply the approved design (code + tests, TDD) | `ARCH_APPROVAL` = approved (and `SECURITY_APPROVAL` if required) | code + tests committed | system (Claude Code, human-supervised) | n/a (bounded by task) | n/a |
| `TEST` | Execute the test suite for the affected area | implementation complete | pass/fail recorded | system | 60s | 1 retry on infra flake only |
| `DOCUMENT` | Update docs + traceability | tests pass | docs updated | system | 10s | 2 |
| `RELEASE_APPROVAL` | Halt for human release decision | tests pass, docs updated, policy evaluated | READY/READY WITH LIMITATIONS/NOT READY recorded | **human** | none | n/a |
| `RENORMALIZE` | Re-run `QUALITY_CHECK`-equivalent analysis after a human clarification answer changes the requirement | `CLARIFY` resolved | requirement re-normalized, downstream tasks diffed | system | 10s | 2 |
| `SAFE_STOP` | Terminal failure state | unrecoverable check failure, or repeated retry exhaustion | run halted, human notified | system → human resume | n/a | n/a |
| `ROLLBACK` | Revert a reversible change | a committed change must be undone | prior state restored | system, human-approved | n/a | n/a |
| `COMPENSATE` | Apply a compensating action for an irreversible change | rollback infeasible | compensating record created | system, human-approved | n/a | n/a |
| `DONE` | Terminal success state | `RELEASE_APPROVAL` = approved | run closed | — | n/a | n/a |

### Graph properties demonstrated

- **Sequential path**: `INGEST → QUALITY_CHECK → DECOMPOSE → DESIGN → ARCH_APPROVAL → IMPLEMENT → TEST → DOCUMENT → RELEASE_APPROVAL → DONE` (Scenario A happy path).
- **Conditional branch**: `QUALITY_CHECK → CLARIFY` only when a check fails; otherwise `QUALITY_CHECK → DECOMPOSE` directly (Scenario A vs. Scenario C).
- **Parallel + synchronization**: within `TEST`, unit/contract/security test groups execute as independent parallel tasks that must all complete before the node exits to `DOCUMENT` (fan-out/fan-in).
- **Re-entrant branch**: `ARCH_APPROVAL → SECURITY_APPROVAL` is a conditional edge taken only when the design touches a security-sensitive path (`config.py`-equivalent), demonstrating graph replanning v2/v3 (edge added after initial graph construction, per CL-03's downstream impact).
- **Safe-stop + resume**: any node's bounded-retry exhaustion or a detected consistency bug (e.g., a path-resolution defect caught by an automated check) routes to `SAFE_STOP`; only an explicit human **resume** action re-enters the graph at the failed node, re-running only that node (not the whole graph).
- **Rollback vs. compensation**: a reversible step (e.g., an uncommitted design doc) uses `ROLLBACK`; an irreversible step (e.g., a migration already applied to the sandbox DB) uses `COMPENSATE` (a recorded, reviewed corrective action) — see ADR for the rollback-vs-compensation boundary.
- **Dynamic replanning**: `RENORMALIZE` demonstrates replanning — when the human's `CLARIFY` answer changes the requirement, only downstream tasks derived from the changed requirement are regenerated; already-valid upstream artifacts are not redone.

## 4. State and Decision Lineage

Persisted per run, in `workflow_runs` + `state_transitions` + `decisions`:
- workflow instance state (current node, status)
- normalized requirement (as ingested, and as re-normalized after any `RENORMALIZE`)
- task decomposition (versioned; a new version is created on replan, old versions retained for lineage)
- dependency edges between tasks
- decisions and assumptions (each tagged with the clarification or ADR that produced it)
- approvals and rejections (`approval_records` — gate, decision, decided-by, timestamp, rationale)
- artifact versions (contract version, migration version referenced per run)
- test outcomes (linked to the `TEST` node's execution)
- risk outcomes (residual risks recorded at `DESIGN` and `RELEASE_APPROVAL`)
- replanning history (`RENORMALIZE` events, with before/after task diffs)
- correlation identifier (`run_id`, a UUID, present on every log line and audit event for that run)
- terminal status (`DONE`, `SAFE_STOP`, or explicit `REJECTED`)

## 5. Human-in-the-Loop Controls

Mandatory approval gates: `CLARIFY` (unresolved ambiguity), `ARCH_APPROVAL` (architecture), `SECURITY_APPROVAL` (security-sensitive paths), destructive/irreversible change (routed through `COMPENSATE` approval), constitutional exception (ADR-level, see constitution Governance Requirements), material risk acceptance (`RELEASE_APPROVAL` with READY WITH ACCEPTED LIMITATIONS), release readiness (`RELEASE_APPROVAL`), final submission (outside the orchestration engine — the human candidate's own `git push`/tag action, see Final Step-by-Step Execution Sequence).

No gate has a default timeout-to-approve. A gate left unanswered leaves the run parked at that node indefinitely; the engine never advances it on silence (constitution Principle III, enforced by a unit test asserting the state machine has no "auto-advance" transition out of any human-gate node).

## 6. Reliability

- **Transient failure**: classified as infra-layer (DB connection error, filesystem I/O error) — eligible for bounded retry.
- **Permanent failure**: classified as domain-layer (validation failure, policy FAIL) — not retried; routed to the appropriate terminal/branch state.
- **Retry bounds**: max 2 retries per node (3 total attempts), exponential backoff starting at 1s, capped at 4s. Retry-exhausted transient failure routes to `SAFE_STOP`.
- **Timeout**: per-node timeout as listed in the node table (§3); a timed-out node is treated as a failure for retry-classification purposes.
- **Idempotency**: node handlers are written to be safely re-invocable (re-running `QUALITY_CHECK` on the same input produces the same checks; re-running `DECOMPOSE` after a resume does not duplicate task rows — upsert by `(run_id, task_key)`).
- **Fallback**: `DOCUMENT` node falls back to a minimal auto-generated changelog stub (clearly labeled `[fallback: doc-generator unavailable]`) if the primary documentation step errors, so a doc-tooling outage does not block the whole run — the fallback output is always flagged for human follow-up.
- **Rollback vs. compensation**: rollback is used when the affected artifact has not yet been committed/applied outside the sandbox (e.g., an uncommitted migration file). Compensation is used once a change has been applied somewhere rollback cannot cleanly reach (e.g., a migration already run against a sandbox DB) — a recorded corrective action is taken instead of a destructive undo.
- **Safe-stop**: entered on (a) retry exhaustion of a transient failure, (b) a detected correctness bug in a verification node itself (e.g., checking the wrong path), or (c) any attempt to bypass a human gate. Only explicit human **resume** re-enters the graph, and resume re-runs only the failed node(s), not the whole run.
- **Partial failure / dependency unavailability**: if the SQLite file is locked/unavailable, the affected node fails as transient and retries; if still unavailable after retry exhaustion, the run safe-stops rather than silently skipping persistence.

### MTTR instrumentation

```
MTTR = Total recovery duration across recovered failure events
       ÷ Number of recovered failure events
```
Captured per failure event: `failure_detected_at`, `recovery_start_at` (human resume action, or automatic retry start), `recovery_complete_at`, `recovery_mechanism` (`retry` | `resume` | `compensation`), `recovered` (bool). Only `recovered = true` events are included in the MTTR denominator; unrecovered (permanently safe-stopped, unresumed) events are reported separately as an **unrecovered-failure count**, never folded into MTTR. All MTTR figures in this repository are demonstration measurements from the three required scenarios plus fault-injection variants — explicitly not production statistics (constitution Principle IX).

## 7. Observability

- **Logs**: structured JSON, one line per significant action, always including `run_id` when applicable.
- **Metrics**: in-process counters/gauges — workflow success rate, failure rate, retry frequency, rollback/compensation frequency, MTTR, unrecovered-failure count, end-to-end latency per run — exposed at `/api/v1/metrics` and summarized in `docs/operations/metrics.md` after the scenario runs.
- **Traces**: `run_id` + per-node `started_at`/`ended_at` timestamps function as a lightweight internal trace; no external tracing backend is required for the prototype.
- **Audit events**: append-only `audit_events` table — actor type, action, timestamp, affected artifact/state, result, reason — one row per state transition, approval, retry, rollback/compensation, and replanning event.

## 8. Security

- Input validation on every API field (Pydantic models with explicit constraints).
- Allowed URL schemes: `http`, `https` only (NFR-001).
- SSRF-style abuse: reject targets resolving to loopback/private/link-local ranges at creation time (CL-05).
- Rate limiting: 60 requests/minute per `X-API-Key`, in-process token bucket (CL-08).
- Authentication assumption: static `X-API-Key` header, attribution only, no login system — documented limitation, not production auth (CL-06).
- Secrets management: no secrets are required for the deterministic default; if the optional LLM adapter is enabled, its API key is read from an environment variable and never logged.
- Dependency risk: `pip-audit` (or equivalent) run as part of release-readiness validation; results recorded, not fabricated.
- Audit integrity: `audit_events` is append-only at the application layer (no UPDATE/DELETE code path against that table).
- Least privilege: the orchestration engine has no shell/filesystem-write capability beyond its own SQLite file and designated `docs/`/`specs/` output paths during a run — it does not self-modify `.specify/memory/constitution.md` or `docs/adr/*` (those remain human-edited/approved files).
- Secure defaults: `LLM_PROVIDER=none` by default; rate limiting and SSRF-block are always-on, not opt-in.
- Threat model: documented in `docs/architecture/threat-model.md` (created during implementation), covering malicious-redirect abuse, link-flooding/rate-limit evasion, and idempotency-key replay.

## 9. Compliance and Change Control

- **Policy domains**: security, dependency/licensing, change-control (architecture/contract/schema changes require an approved ADR or `ARCH_APPROVAL`), audit-retention (append-only, retained for the life of the repository).
- **Policy model**: versioned policy pack at `docs/governance/policy-pack.md`, starting at **v1.0.0**. Every workflow run records the policy pack version it was evaluated against.
- **Evaluation outputs**: PASS / FAIL / EXCEPTION-REQUESTED / NOT-APPLICABLE per policy, per run, stored in `policy_evaluations`.
- **Mandatory vs. advisory**: security and change-control policies are mandatory (block progression on FAIL); a style/lint policy is advisory (recorded, does not block).
- **Compliance-check stage**: runs inside `TEST` (parallel with the test groups) and again as part of `RELEASE_APPROVAL` evidence.
- **Change-request / impact-analysis workflow**: any change to an approved requirement, architecture, schema, or release criterion must route through `DESIGN` → `ARCH_APPROVAL` again (re-entry, not a side-channel edit) — this is how the brownfield and ambiguous scenarios demonstrate change control.
- **Policy exception workflow**: an EXCEPTION-REQUESTED outcome halts at a dedicated approval point (modeled as `SECURITY_APPROVAL` when security-scoped, or `ARCH_APPROVAL` otherwise) and, once approved, is recorded with rationale, scope, approving authority, compensating control, timestamp, and expiry/review condition (constitution Principle VI).
- **Release-blocking condition**: `RELEASE_APPROVAL` evidence must show zero unresolved mandatory FAILs and zero expired/unapproved exceptions, or the run cannot be marked READY.

## 10. Testing

- Domain unit tests (`tests/unit/`) — validation, short-code generation, expiry/click-limit logic.
- API contract tests (`tests/contract/`) — generated/validated against `contracts/openapi.yaml`.
- Persistence tests (`tests/unit/persistence/`) — repository behavior, migration up/down.
- Integration tests (`tests/integration/`) — API → domain → persistence, in-process, SQLite file-backed.
- Orchestration state-transition tests (`tests/orchestration/`) — every node, every allowed/prohibited transition.
- Approval/rejection tests — gate halts on no-decision; advances only on explicit decision.
- Retry/timeout/fallback tests — simulated transient failures via dependency-injected fault points.
- Rollback/compensation tests — forced scenarios exercising both paths.
- Safe-stop/resume tests — forced retry exhaustion → safe-stop → explicit resume → correct single-node re-entry.
- Replanning tests — `RENORMALIZE` diff correctness.
- Concurrency tests — parallel redirect requests against a `max_clicks`-limited link (post-brownfield); parallel create requests racing on short-code generation.
- Security tests — scheme rejection, SSRF-block, rate-limit enforcement.
- End-to-end tests (`tests/e2e/`) — one per required scenario (A/B/C) driving the real orchestration engine and real API together.
- Release-readiness checks — policy evaluation + full suite execution, wired into `RELEASE_APPROVAL` evidence generation.

TDD is applied per constitution Principle IV: failing test → confirmed failure reason → minimal implementation → pass → refactor → regression suite → docs/traceability update, for every applicable task in `tasks.md`.

## 11. Scenario Designs

| | Greenfield (A) | Brownfield (B) | Ambiguous (C) |
|---|---|---|---|
| Initial input | "Add batch link creation, 1–25 items" | "Add an optional click limit to existing links" | "Links should expire automatically after a while, but links that have already been shared must never break." |
| Interpretation | Complete, consistent, testable — quality checks pass | Enhancement to existing, real-code impact analysis required | Quality checks fail: vague term + contradiction |
| Decomposition | New endpoint + batch validation + rate-limit-as-one-request task | Migration task + atomic-update task + new 410 outcome task | Blocked until `CLARIFY` resolved, then decomposition of the agreed interpretation |
| Orchestration path | `INGEST→QUALITY_CHECK→DECOMPOSE→DESIGN→ARCH_APPROVAL→IMPLEMENT→TEST→DOCUMENT→RELEASE_APPROVAL→DONE` | same, plus brownfield impact-analysis artifact gating `DESIGN` | `INGEST→QUALITY_CHECK→CLARIFY→RENORMALIZE→DECOMPOSE→DESIGN→ARCH_APPROVAL→(SECURITY_APPROVAL if applicable)→IMPLEMENT→TEST→DOCUMENT→RELEASE_APPROVAL→DONE` |
| Approvals | `ARCH_APPROVAL` | `ARCH_APPROVAL` (migration-aware) | `CLARIFY` + `ARCH_APPROVAL` (+ `SECURITY_APPROVAL` if config touched) |
| Failure paths demonstrated | bounded retry on a simulated transient infra fault during `TEST` | safe-stop + resume after a deliberately injected check-path defect, fixed test-first | — (ambiguity itself is the demonstrated "failure path": unsafe continuation prevented) |
| Validation | contract test v1.0.0→1.1.0 diff, full suite | migration up/down verified, concurrency test for atomic click counting | re-normalized requirement's acceptance criteria tested |
| Evidence | `docs/scenarios/greenfield.md` + audit export | `docs/scenarios/brownfield.md` + audit export + migration evidence | `docs/scenarios/ambiguous.md` + audit export + replanning diff |
| Terminal outcome | `DONE`, contract 1.1.0 | `DONE`, migration 0002 applied | `DONE`, requirement re-normalized and implemented per approved interpretation |

## 12. Technology Decisions (summary — formalized as ADRs)

| Decision | Options | Selected | Rationale (summary — full ADR has detail) |
|---|---|---|---|
| Language/framework | Python+FastAPI, Node+Express, Go+net/http | **Python + FastAPI** | Human-confirmed direction; OpenAPI contract generation built in; fast to test |
| Persistence | SQLite, Postgres, in-memory | **SQLite** | No external service needed for a local prototype; still supports real migrations/transactions |
| Short-code generation | Base62 random, sequential+hash, UUID-truncated | **Base62 random, 7 chars** | Short, URL-safe, negligible collision probability at prototype scale, no central counter bottleneck |
| Orchestration state storage | In-memory only, file-based JSON, SQLite tables | **SQLite tables (same DB)** | Enables real persistence/resume without a second datastore; transactional consistency with domain writes |
| Dependency graph representation | Hard-coded sequence, explicit adjacency table, external workflow engine | **Explicit adjacency table in code + DB-persisted current/allowed-transitions** | Matches constitution Principle II without taking on an external engine dependency inappropriate for a 2–3 day prototype |
| Agent reasoning mode | Deterministic only, real-LLM only, deterministic+optional LLM plug-in | **Deterministic + optional LLM plug-in** | Human-confirmed; reproducible tests by default, illustrative real-LLM path available without being load-bearing |

Full ADRs for each material decision are at `docs/adr/` and require explicit human Accept/Reject (Human Gate 4) before implementation proceeds.

## 13. Traceability

```
Requirement (FR-/NFR-) → Scenario (A/B/C) → Design (plan.md §11) → ADR (docs/adr/) →
Task (tasks.md) → Code (src/) → Test (tests/) → Validation (executed output) →
Documentation (docs/) → Evidence (docs/scenarios/, audit export)
```
Maintained in `docs/traceability/matrix.md`, generated/updated during `/speckit-tasks` and kept current through `/speckit-converge`.

## 14. Delivery Sequence (2–3 day timebox)

| Day | Milestone | Must-have | Deferred (backlog) |
|---|---|---|---|
| 1 (AM) | Engineering baseline + walking skeleton | repo scaffold, FastAPI app boots, `/healthz`, SQLite migration 0001, CI-equivalent local test runner | — |
| 1 (PM) | Core URL behavior | create/redirect/expire/analytics (FR-001–006, FR-021), security/validation (NFR-001, CL-05), auth/rate-limit (CL-06/08) | custom vanity codes |
| 2 (AM) | Orchestration state model + approval governance | state machine, persisted runs, `CLARIFY`/`ARCH_APPROVAL`/`SECURITY_APPROVAL`/`RELEASE_APPROVAL` gates, audit trail | external workflow engine integration |
| 2 (PM) | Reliability + observability | bounded retry, fallback, rollback/compensation, safe-stop/resume, MTTR instrumentation, metrics endpoint | distributed tracing backend |
| 3 (AM) | Three scenarios | Greenfield (batch), Brownfield (max_clicks + migration), Ambiguous (expiry contradiction) end-to-end through the real engine, plus fault-injection variants | additional scenario variants beyond required 3 |
| 3 (PM) | Release readiness | `/speckit-converge`, final independent assessment, final engineering summary, reviewer navigation guide, tag | performance tuning beyond NFR-007 demonstration |

**Stop conditions**: if Day 2 PM reliability work is incomplete by end of Day 2, defer MTTR dashboarding polish (keep raw instrumentation) rather than cut a required scenario. If a required scenario cannot be completed with real evidence by Day 3 AM, it is reported as `NOT READY` with an honest gap description rather than fabricated.

**Minimum defensible release-readiness outcome**: all three scenarios have real, inspectable orchestration runs with audit evidence, even if some NFR targets (e.g., NFR-007 latency) are only partially measured — partial measurement is disclosed, not hidden.

## Planning Constraints Acknowledged

Distributed-system complexity (multi-node orchestration engines, external message queues, managed cloud infra) is deliberately avoided. This plan optimizes for demonstrability, testability, and clarity within a single-process, single-datastore prototype, while still exercising every orchestration capability (parallelism, synchronization, retry, rollback/compensation, safe-stop, resume, replanning) the assignment requires. No application code is implemented during this planning stage.
