# ADR-002: Persistence Strategy

## Status

Accepted — approved by human candidate (Belede Rahul), 2026-10-12

## Context

Both the shortener domain and the orchestration engine need durable, transactional storage that supports real migrations (brownfield scenario requires a reversible migration) without requiring an external database service for a local prototype.

## Decision Drivers

- No external service dependency for a reviewer to run
- Real transactional guarantees (atomic updates for `max_clicks`, CL-02)
- Support for an explicit, reversible migration (brownfield requirement)
- Human-confirmed stack direction: SQLite

## Options Considered

### Option 1: SQLite, single file, explicit hand-written migrations

- Advantages: zero external setup; real ACID transactions; trivial to reset for tests (fresh temp file per test run); migrations can be written as explicit, reviewable up/down SQL scripts
- Disadvantages: single-writer concurrency model (acceptable at prototype scale; documented as a known limitation, not hidden)
- Risks: none material for this scale
- Implementation impact: low
- Assessment implications: reviewer needs zero infrastructure setup

### Option 2: PostgreSQL via Docker

- Advantages: closer to a "real" production datastore, better concurrent-write characteristics
- Disadvantages: requires Docker as a reviewer prerequisite, adds setup friction directly contradicting SC-001's "under 2 minutes from clean clone" target
- Risks: environment-dependent failures outside the candidate's control
- Implementation impact: medium
- Assessment implications: risks reviewer friction reducing demonstrability

### Option 3: In-memory only (no persistence)

- Advantages: simplest possible
- Disadvantages: directly violates FR-011 (workflow state MUST persist across process restarts) and FR-019 (resume after interruption) — not viable
- Risks: fails explicit functional requirements
- Implementation impact: n/a — rejected outright

## Decision

Adopt **Option 1**: SQLite, single file, explicit hand-written up/down migration scripts under `src/shortener/migrations/`.

## Rationale

Satisfies FR-011/FR-019 (persistence/resume), supports the brownfield scenario's reversible migration requirement, and imposes zero setup burden on the reviewer — directly serving SC-001.

## Consequences

- **Positive**: trivial reviewer setup; real transactions; fast test runs (temp-file or in-memory SQLite per test).
- **Negative**: single-writer concurrency is a genuine prototype limitation — documented in `docs/governance/known-limitations.md`, not hidden.
- **Operational**: one file to back up/reset; no connection pool configuration needed.
- **Testing**: persistence tests run against real SQLite, not a mock, for high fidelity.
- **Governance**: migration scripts are reviewed artifacts subject to the same change-control policy as code (constitution Principle VI).

## Risks and Mitigations

- Risk: single-writer contention under concurrent test load. Mitigation: WAL mode enabled; brownfield concurrency test (max_clicks) specifically validates atomic-update correctness under this model rather than assuming it away.

## Reversibility

Moderate — migrating to Postgres later would require swapping the repository layer's SQL dialect and connection handling, but the repository-pattern boundary (ADR-001) contains the blast radius to `persistence/`.

## Traceability

- Requirements: FR-010, FR-011, FR-019, CL-02 (migration)
- Spec sections: Functional Requirements — Orchestration; Scenario B
- Plan sections: §2, §12
- Expected tasks: persistence-abstraction, brownfield-migration task groups

## Validation

Validated by: persistence unit tests, migration up/down/up test (brownfield scenario evidence), and a resume test that kills and restarts the process mid-run.
