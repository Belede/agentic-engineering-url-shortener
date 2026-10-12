# Feature Specification: Agentic Software Engineering System: URL Shortener

**Feature Branch**: `001-agentic-url-shortener`

**Created**: 2026-10-12

**Status**: Draft — pending Human Gate 2 approval

**Input**: Interview Assignment "Build an Agentic Software Engineering System — URL Shortener" (see `docs/assessment/assignment.md`), executed under the project constitution (`.specify/memory/constitution.md`) via the controlled SpecKit + Claude Code guidance in `docs/governance/ai-native-sdlc-guide.md`.

## Business Objective

Demonstrate how a governed agentic execution system transforms software requirements into reviewable engineering outcomes across the complete SDLC. The system must demonstrate requirement understanding, ambiguity detection, requirement normalization, decomposition, architecture and design, controlled implementation, testing and validation, documentation, security and risk checks, release readiness, human oversight, and final engineering reporting.

## Demonstration Domain

A URL shortener service, treated as a production-oriented prototype (not a toy demo), supporting:

- short URL creation
- short-code generation
- redirect resolution
- basic redirect analytics
- expiration
- validation
- reliability controls
- appropriate failure handling
- operational health

## Primary Capability: Agentic SDLC Orchestration

The orchestration system is the critical differentiator of this assessment. It must coordinate the following stages as a governed workflow, not a linear script:

1. Requirement ingestion
2. Requirement normalization
3. Ambiguity detection
4. Human clarification
5. Task decomposition
6. Architecture and design
7. Implementation
8. Testing
9. Documentation
10. Security and risk validation
11. Release-readiness determination
12. Final engineering summary

The orchestration MUST:

- use explicit dependencies or equivalent state transitions (a dependency graph, not a fixed sequence)
- support sequential and parallel activities
- synchronize dependent activities
- persist workflow state (survive process restart / resumed session)
- preserve context and decision lineage
- enforce stage entry and exit conditions
- enforce human approval checkpoints
- apply bounded retries
- support fallback
- support rollback or compensation
- enter safe-stop when continuation is unsafe
- resume safely following recoverable interruption
- dynamically re-plan when upstream outputs change, while preserving governance
- record audit-grade execution evidence
- expose reliability and orchestration measurements (success rate, retry/rollback frequency, MTTR, latency)

A linear sequence of agent calls is explicitly **not** sufficient evidence of orchestration (constitution Principle II).

## User Types

| ID | User Type | Representative Needs |
|----|-----------|----------------------|
| UT-01 | API Consumer | Create short links, resolve redirects, read analytics via the public API |
| UT-02 | Software Engineer | Extend/modify the shortener (brownfield), run tests, read architecture docs |
| UT-03 | Human Reviewer / Approver | Approve or reject ADRs, clarifications, security-sensitive changes |
| UT-04 | Release Owner | Approve or reject release-readiness decisions per orchestration run |
| UT-05 | Assessment Reviewer | Independently verify requirement coverage, orchestration evidence, and traceability from the repository alone |

## User Scenarios & Testing *(mandatory)*

### User Story 1 — API consumer creates and resolves short links (Priority: P1)

As an API consumer, I create a short link from a long URL and later resolve it via redirect, so that I can share compact links that work reliably.

**Why this priority**: This is the baseline demonstrable capability; without it there is no product to orchestrate around.

**Independent Test**: `POST /api/v1/links` with a valid URL returns a short code; `GET /{code}` issues an HTTP redirect to the original URL. Testable with no other capability implemented.

**Acceptance Scenarios**:
1. **Given** a valid `https://` URL, **When** the consumer creates a link, **Then** the system returns a unique short code and the canonical URL (FR-001).
2. **Given** an existing short code, **When** a client requests `GET /{code}`, **Then** the system issues a redirect to the stored target URL and records an analytics event (FR-004, FR-006).
3. **Given** a malformed or disallowed-scheme URL, **When** the consumer attempts to create a link, **Then** the system rejects the request with a structured error and creates no record (FR-002).

---

### User Story 2 — Engineering team runs a governed SDLC workflow for a new requirement (Priority: P1)

As the engineering team (human + orchestration), I submit a new requirement and the system decomposes it, designs it, implements it under test, documents it, and produces a release-readiness decision — pausing for my approval at defined gates.

**Why this priority**: This is the assessment's central differentiator; without it, the URL shortener is just a CRUD service.

**Independent Test**: Submit a well-formed requirement to the orchestration entry point; observe the run progress through normalization → decomposition → design (ARCH_APPROVAL gate) → implementation → testing → RELEASE_APPROVAL gate, with a persisted, inspectable run record at every step.

**Acceptance Scenarios**:
1. **Given** a complete, testable, unambiguous requirement, **When** it is submitted, **Then** the orchestration records requirement-quality checks, proceeds without an artificial clarification gate, and still produces full decomposition, decision lineage, and evidence (FR-011, Scenario A).
2. **Given** an architecture-impacting design proposal, **When** the orchestration reaches the design stage, **Then** it halts at `ARCH_APPROVAL` and does not proceed to implementation until a human explicitly approves or rejects (FR-013).
3. **Given** a completed, tested implementation, **When** the orchestration reaches release evaluation, **Then** it halts at `RELEASE_APPROVAL` and reports one of READY / READY WITH ACCEPTED LIMITATIONS / NOT READY, pending human sign-off (FR-020).

---

### User Story 3 — Engineer makes a brownfield change against the running shortener (Priority: P2)

As a software engineer, I request an enhancement to the existing shortener (e.g., a new optional field) and the orchestration first analyzes the real impact on the existing codebase before touching anything.

**Why this priority**: Required scope item (Scenario B); demonstrates codebase reasoning, not just greenfield generation.

**Independent Test**: Submit a brownfield change request against the already-implemented service; verify an impact-analysis artifact (impacted modules/routes/schemas/tests) is produced and committed before any code changes, and that the `ARCH_APPROVAL` gate reflects real analysis output, not a generic template.

**Acceptance Scenarios**:
1. **Given** an approved brownfield requirement, **When** orchestration begins, **Then** it performs impact analysis against the current repository state (not a static description) and records impacted modules, routes, schemas, and tests (FR-014).
2. **Given** the impact analysis is complete, **When** the design requires a schema/migration change, **Then** the system records a reversible migration plan and blocks implementation on human architecture approval (FR-015).

---

### User Story 4 — Ambiguous requirement is safely suspended and resumed (Priority: P2)

As a human reviewer, when I submit an incomplete or contradictory requirement, I expect the orchestration to detect this, stop before unsafe implementation, ask me a focused question, and resume correctly once I answer — not guess.

**Why this priority**: Required scope item (Scenario C); demonstrates governed ambiguity handling, the opposite failure mode of silent assumption.

**Independent Test**: Submit a requirement with a detectable defect (missing acceptance criteria, vague temporal language, or an internal contradiction). Verify the run transitions to `CLARIFY`, blocks downstream work, and only resumes (with correct downstream re-planning) after an explicit recorded human answer.

**Acceptance Scenarios**:
1. **Given** a requirement lacking acceptance criteria, **When** it is submitted, **Then** the orchestration flags the specific defect, halts at `CLARIFY`, and does not infer an answer (FR-016).
2. **Given** a human answers the clarification, **When** the orchestration resumes, **Then** it re-plans only the affected downstream artifacts and records the replanning event in the audit trail (FR-017, FR-018).

---

### User Story 5 — Assessment reviewer verifies the submission from the repository alone (Priority: P3)

As an assessment reviewer, I clone the repository and, using only the README and reviewer navigation guide, run the app, run the tests, inspect a workflow run, and verify every orchestration behavior claimed in the documentation.

**Why this priority**: Required deliverable; without it the other work is not verifiable.

**Independent Test**: Follow `docs/traceability/reviewer-navigation.md` from a clean clone with no prior context and confirm every numbered claim resolves to a real, executable path.

**Acceptance Scenarios**:
1. **Given** a clean clone, **When** the reviewer follows the quickstart, **Then** the application starts and the test suite passes using only documented commands (FR-021).
2. **Given** the reviewer navigation guide, **When** the reviewer looks up any orchestration capability (retry, rollback, safe-stop, replanning), **Then** a concrete command and expected observable result is provided (FR-022).

### Edge Cases

- What happens when the target URL for a redirect has expired? → System MUST return `410 Gone` with a structured error, not a silent 404 or stale redirect (FR-005).
- What happens when two create-link requests race to use a collided short code? → Code generation MUST guarantee uniqueness under concurrency without relying on an external lock service (FR-003, FR-009).
- What happens when the persistence layer is unavailable mid-request? → The affected request MUST fail safely with a `503`-class error and no partial record; this is distinct from an application bug (FR-010).
- What happens when an orchestration run is interrupted (process restart) mid-stage? → The run MUST be resumable from its last persisted state, not restarted from scratch (FR-019).
- What happens when a human does not respond to an approval gate? → The run MUST remain paused indefinitely; silence MUST NOT be interpreted as approval (constitution Principle III; FR-013).
- What happens when an upstream artifact (e.g., approved design) changes after downstream tasks exist? → The orchestration MUST trigger dynamic replanning of only the affected downstream tasks (FR-018).

## Required Scenarios

### Scenario A: Greenfield

A well-defined greenfield requirement proceeds through: Requirement → Decomposition → Design → Implementation → Testing → Documentation → Validation → Release Readiness, **without** an artificial clarification gate when the requirement is complete, consistent, testable, and within approved policy/architecture boundaries. The run records the requirement-quality checks performed and the reason clarification was skipped. If material ambiguity emerges later, only the affected path is suspended for governed clarification and impact analysis, then resumed.

**Candidate requirement for this scenario** (confirmed at Human Gate 2 / Clarify): a new, additive API capability for the existing shortener that is unambiguous on its face. The exact capability is finalized during `/speckit-clarify` together with the human candidate, consistent with the constitution's prohibition on the AI silently choosing material scope — see `OPEN-Q-GF` below.

### Scenario B: Brownfield

An enhancement, refactor, or defect correction against the already-implemented URL shortener. Before any code changes, the system identifies impacted components, interfaces, data flows, tests, documentation, regression risk, and rollout/rollback considerations (see User Story 3).

**Candidate requirement for this scenario**: finalized during `/speckit-clarify` — see `OPEN-Q-BF` below.

### Scenario C: Ambiguous Requirement

Incomplete, unclear, or conflicting input is detected, implementation is prevented, human clarification is requested and recorded, downstream impact is identified, affected artifacts are updated, and the workflow resumes at the correct state (see User Story 4).

**Candidate requirement for this scenario**: finalized during `/speckit-clarify` — see `OPEN-Q-AMB` below.

## Requirements *(mandatory)*

### Functional Requirements — URL Shortener Domain

- **FR-001**: System MUST accept a URL creation request and return a unique short code and the canonical short URL for any input URL that passes validation (allowed scheme, well-formed, within length limit).
- **FR-002**: System MUST reject invalid or disallowed-scheme URLs with a structured error and MUST NOT create a persisted record for a rejected request.
- **FR-003**: System MUST guarantee short-code uniqueness, including under concurrent creation requests.
- **FR-004**: System MUST resolve a valid, non-expired short code to an HTTP redirect to the stored target URL.
- **FR-005**: System MUST reject resolution of an expired short code with a distinguishable error outcome (not a generic 404).
- **FR-006**: System MUST capture a redirect analytics event (at minimum: timestamp, short code) for every successful resolution.
- **FR-007**: System MUST define and apply idempotency behavior for duplicate/retried create requests [NEEDS CLARIFICATION: is idempotency based on a client-supplied key, or on exact URL+caller match? See `OPEN-Q-IDEMP`].
- **FR-008**: System MUST remain correct under concurrent requests to the same short code (no double-counted analytics from a single redirect, no lost updates).
- **FR-009**: System MUST handle short-code generation collisions deterministically (detect and regenerate, or reserve ranges) without unbounded retry.
- **FR-010**: System MUST fail safely (no partial writes, clear error class) when the persistence layer is unavailable.
- **FR-021**: System MUST expose an operational health/readiness endpoint distinguishing "process up" from "dependencies healthy."

### Functional Requirements — Orchestration

- **FR-011**: Orchestration MUST support creating a new workflow run from a submitted requirement and MUST persist the run's state across process restarts.
- **FR-012**: Orchestration MUST expose a way to inspect a run's current state, history of transitions, and decision lineage.
- **FR-013**: Orchestration MUST enforce human approval/rejection at defined gates (at minimum: architecture, security-sensitive change, release readiness) and MUST NOT infer approval from the absence of a response.
- **FR-014**: Orchestration MUST perform brownfield impact analysis against the real current repository state (not a static template) before any brownfield code change.
- **FR-015**: Orchestration MUST record migration/compatibility impact and block implementation on human approval when a schema or contract change is involved.
- **FR-016**: Orchestration MUST detect ambiguity (missing acceptance criteria, vague/undefined temporal terms, internal contradictions) in a submitted requirement and halt at a `CLARIFY` state rather than proceeding.
- **FR-017**: Orchestration MUST record the human's clarification decision and MUST NOT fabricate or auto-generate an answer on the human's behalf.
- **FR-018**: Orchestration MUST dynamically re-plan only the downstream artifacts affected by a changed upstream decision, and MUST record the replanning event.
- **FR-019**: Orchestration MUST support safe interruption and resumption: a run interrupted mid-stage MUST be resumable from its last persisted state without re-running already-completed, still-valid stages.
- **FR-020**: Orchestration MUST produce exactly one of READY / READY WITH ACCEPTED LIMITATIONS / NOT READY at release evaluation, and MUST NOT return READY while a mandatory check remains incomplete or failed.
- **FR-022**: Orchestration MUST apply bounded retry (explicit max attempts + backoff) to transient-classified failures, and MUST distinguish retry-exhausted outcomes from permanent failures.
- **FR-023**: Orchestration MUST support rollback for reversible changes and compensation for irreversible changes, and MUST record which mechanism was used and why.
- **FR-024**: Orchestration MUST enter a safe-stop terminal state when continuation would be unsafe (e.g., repeated check failure, unapproved required gate), and MUST require explicit human action to resume.
- **FR-025**: Orchestration MUST record audit-grade evidence (actor type, action, timestamp, affected artifact/state, result, reason) for every state transition, approval, retry, rollback, and replanning event.
- **FR-026**: Orchestration MUST compute and expose reliability metrics (success rate, retry frequency, rollback/compensation frequency, MTTR, end-to-end latency) from actual recorded run data, clearly labeled as demonstration measurements.
- **FR-027**: Orchestration MUST evaluate versioned compliance/change-control policy checks on every run and record PASS/FAIL/EXCEPTION-REQUESTED/NOT-APPLICABLE per applicable policy, blocking progression on an unresolved mandatory FAIL.

### Key Entities

- **ShortLink**: A shortened URL record — short code, target URL, created-at, expires-at (nullable), creator/caller reference, status.
- **RedirectEvent**: An analytics record of a single resolution — short code, timestamp, outcome (resolved/expired/not-found).
- **WorkflowRun**: A single orchestration execution instance — run id (correlation id), requirement input, current state, state history, policy version evaluated, terminal outcome.
- **StateTransition**: A recorded move between orchestration states — from-state, to-state, actor, timestamp, reason, triggering event.
- **ApprovalRecord**: A human decision at a gate — gate type, run id, decision (approve/reject), decided-by, timestamp, rationale.
- **PolicyEvaluation**: A recorded compliance/change-control check — policy id, policy version, outcome, evidence, exception reference (if any).
- **AuditEvent**: An append-only log entry — actor type, action, timestamp, affected artifact/state, result, reason.

## Non-Functional Requirements

- **NFR-001 (Security)**: Only `http`/`https` schemes are accepted for target URLs; no execution of attacker-supplied redirect targets beyond standard HTTP redirect semantics. [Proposed validation target, requires approval: reject `javascript:`, `data:`, `file:` schemes outright — see `OPEN-Q-SECURITY`.]
- **NFR-002 (Reliability)**: Bounded retry with a documented maximum attempt count and backoff strategy for transient persistence failures. [Proposed target: max 3 attempts — requires approval.]
- **NFR-003 (Scalability)**: The prototype MUST demonstrate correctness under concurrent load in its own test suite; production-scale load testing is explicitly out of scope and MUST be labeled as such.
- **NFR-004 (Maintainability)**: Domain logic, API delivery, persistence, orchestration, and policy enforcement MUST be in separately testable modules (constitution Principle VII).
- **NFR-005 (Observability)**: Every orchestration run MUST be traceable end-to-end via its correlation id across logs and persisted state.
- **NFR-006 (Auditability)**: Audit evidence MUST be queryable per run and MUST NOT be mutable after being written (append-only).
- **NFR-007 (Performance)**: [Proposed validation target, requires approval: p95 redirect resolution latency under 100ms on local prototype hardware, measured by the test suite — see `OPEN-Q-PERF`. Not a confirmed client requirement; the assignment specifies no numeric target.]
- **NFR-008 (Recoverability)**: A workflow run interrupted at any persisted state MUST be resumable with zero loss of prior decision lineage.
- **NFR-009 (Testability)**: Every orchestration state transition MUST be independently unit-testable without requiring a full end-to-end run.
- **NFR-010 (Change Safety)**: A brownfield change MUST NOT be implemented without a preceding, committed impact analysis.
- **NFR-011 (Controlled Autonomy)**: No agent-initiated action classified as high-impact (architecture change, security-sensitive change, destructive change, release decision) may execute without a recorded human approval.

## Exclusions (Out of Scope)

- Production-scale distributed infrastructure (multi-region, horizontal autoscaling, managed cloud deployment).
- Real end-user authentication/authorization system — only an authentication *assumption* is documented (see Clarify stage).
- A production LLM-backed reasoning engine is optional and, if included, is an illustrative plug-in behind a deterministic default (per confirmed decision below), not the graded orchestration mechanism.
- Billing, multi-tenancy, and custom-domain short links.

## Confirmed Decisions (pre-Clarify)

- **Stack**: Python + FastAPI + SQLite, proposed for formal ADR acceptance at the ADR gate (human-confirmed direction, 2026-10-12).
- **Agent execution mode**: Deterministic rule-based orchestration logic by default, with an optional, clearly labeled real-LLM plug-in point (human-confirmed direction, 2026-10-12).
- **Repository**: `Belede/agentic-engineering-url-shortener` on GitHub, private (human-confirmed, 2026-10-12).

## Open Questions for `/speckit-clarify` (Human Gate 3)

- **OPEN-Q-GF**: What is the exact greenfield capability to add (FR-### scope) for Scenario A?
- **OPEN-Q-BF**: What is the exact brownfield change to make against the already-implemented shortener for Scenario B?
- **OPEN-Q-AMB**: What is the exact ambiguous requirement text to feed Scenario C (must contain a genuine, detectable defect)?
- **OPEN-Q-IDEMP**: Idempotency key strategy for FR-007 — client-supplied `Idempotency-Key` header vs. exact-match URL+caller dedup?
- **OPEN-Q-SECURITY**: Confirm the exact disallowed URL schemes and any additional abuse controls (e.g., blocking localhost/internal IP targets — SSRF-style redirect abuse) for NFR-001.
- **OPEN-Q-PERF**: Confirm or reject the proposed NFR-007 latency target, or mark as non-binding demonstration-only.
- **OPEN-Q-AUTH**: What authentication assumption should the API consumer role operate under (none / static API key / none-with-rate-limit-by-IP)?
- **OPEN-Q-RATE**: Confirm whether rate limiting is in scope for this timeboxed prototype, and if so, what the limit should be.
- **OPEN-Q-EXPIRY**: Confirm default expiration behavior for newly created links (no default expiry vs. a default TTL).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A reviewer can create a short link and successfully resolve it via redirect using only documented commands, in under 2 minutes from a clean clone.
- **SC-002**: 100% of the three required scenarios (greenfield, brownfield, ambiguous) produce a persisted, inspectable workflow run with full state-transition history.
- **SC-003**: Every orchestration capability claimed in the reviewer navigation guide (retry, fallback, rollback/compensation, safe-stop, resume, replanning) has at least one executable demonstration with observable evidence in the repository.
- **SC-004**: 0 mandatory compliance/change-control policy failures remain unresolved at the final release-readiness decision.
- **SC-005**: 100% of functional requirements (FR-###) are mapped to at least one executed test in the final traceability matrix.

## Assumptions

- The assessment is timeboxed to 2–3 days of effort; scope is deliberately limited to what demonstrably satisfies the assignment's core requirements over production-scale completeness (constitution-aligned, per the Planning Constraints in the governance guide).
- The human candidate (Belede Rahul) is the sole approval authority for all human gates in this repository; no separate reviewer/approver role exists during development.
- Local execution (no cloud deployment) is sufficient for assessment purposes; the assignment does not require a hosted deployment.
- SpecKit's installed skill names use the `speckit-<verb>` form (e.g. `/speckit-constitution`) rather than the `speckit.<verb>` dotted form shown in the governance guide — these are the same lifecycle commands under the installed CLI version (`specify-cli` 1.1.4.dev0, pinned in `speckit-version.txt`).
