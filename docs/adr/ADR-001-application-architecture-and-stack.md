# ADR-001: Application Architecture and Language/Framework

## Status

Accepted — approved by human candidate (Belede Rahul), 2026-10-12

## Context

The prototype must run locally within a 2–3 day timebox, expose both a shortener API and an orchestration API, and demonstrate production-grade modularity (constitution Principle VII) without unjustified distributed-system complexity (spec.md Planning Constraints).

## Decision Drivers

- Speed of implementation within the timebox
- Built-in support for versioned API contracts (OpenAPI)
- Testability without external infrastructure
- Human-stated direction (confirmed 2026-10-12): Python + FastAPI + SQLite

## Options Considered

### Option 1: Python + FastAPI, single-process modular monolith

- Approach: one process, clearly separated modules (`api/`, `domain/`, `orchestration/`, `persistence/`, `policy/`, `telemetry/`)
- Advantages: FastAPI auto-generates OpenAPI; Pydantic gives strong input validation for free; fast local iteration; large test ecosystem (pytest)
- Disadvantages: Python's GIL limits true parallel CPU-bound work (not a concern here — I/O-bound prototype)
- Risks: none material at this scale
- Implementation impact: low — straightforward FastAPI app structure
- Assessment implications: reviewer can run it with a single `uvicorn` command; contract is self-documenting

### Option 2: Node.js + Express/Fastify, single-process modular monolith

- Approach: equivalent structure in TypeScript
- Advantages: similar async I/O model; strong typing with TS
- Disadvantages: OpenAPI generation requires an extra library (no FastAPI-equivalent built-in); human did not express a preference for this stack
- Risks: slightly more setup overhead for contract generation within timebox
- Implementation impact: medium
- Assessment implications: equally reviewable, but more scaffolding needed

### Option 3: Microservice split (shortener service + orchestration service)

- Approach: two separately deployed services communicating over HTTP
- Advantages: closer to "real" production topology; clean plane separation enforced by process boundary
- Disadvantages: directly contradicts the Planning Constraints ("avoid unjustified distributed-system complexity"); adds deployment/orchestration overhead disproportionate to a 2–3 day assessment; harder for a reviewer to run
- Risks: scope overrun, higher chance of an incomplete/unreliable demo
- Implementation impact: high
- Assessment implications: risks failing the "demonstrability, testability, clarity" criterion in favor of superficial "production-scale" appearance

## Decision

Adopt **Option 1**: Python + FastAPI, single-process modular monolith, with logical (not physical) separation between the application plane and the orchestration/control plane.

## Rationale

This best satisfies the timebox, the constitution's maintainability principle (modular, testable, replaceable), and the Planning Constraints' explicit preference for demonstrability over distributed-system complexity, while still giving the orchestration/application separation the assignment's "Workflow Orchestration" requirement calls for.

## Consequences

- **Positive**: fast to build and test; OpenAPI contract comes nearly for free; single command to run for reviewers.
- **Negative**: the two planes share a process and a database file, so a bug in one can in principle affect the other's availability — mitigated by module boundaries and tests that exercise each plane independently (plan.md §1).
- **Operational**: single process to start/stop/monitor; no deployment orchestration needed for the assessment.
- **Testing**: both planes are unit-testable in isolation; integration tests exercise them together.
- **Governance**: keeps the constitution's plane-separation principle enforceable via `/speckit-analyze` checks rather than physical infrastructure.

## Risks and Mitigations

- Risk: accidental coupling between planes over time. Mitigation: `/speckit-analyze` and `/speckit-converge` explicitly check for plane-separation drift (plan.md §1).

## Reversibility

Low-cost to reverse early (swap FastAPI for another framework before significant code exists); moderate cost after implementation begins (would require re-doing API delivery layer only — domain/orchestration logic is framework-agnostic by design).

## Traceability

- Requirements: NFR-004 (Maintainability), all FR-0xx (hosted by this architecture)
- Spec sections: System Context, Planning Constraints
- Plan sections: §1, §2
- Expected tasks: engineering-baseline and walking-skeleton task group

## Validation

Validated by: the application successfully starting via a single documented command from a clean clone (SC-001), and by `/speckit-analyze` confirming no plane-separation violations.
