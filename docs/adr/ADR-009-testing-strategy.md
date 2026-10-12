# ADR-009: Testing Strategy

## Status

Accepted — approved by human candidate (Belede Rahul), 2026-10-12

## Context

Constitution Principle IV mandates TDD wherever practical, with task completion requiring executed validation, not generated code alone. The orchestration engine in particular needs tests that can prove non-linear behavior, not just happy-path code coverage.

## Decision Drivers

- Must cover domain, API contract, persistence, integration, orchestration-transition, reliability, security, and end-to-end layers (plan.md §10)
- Must run entirely locally (pytest), no external CI dependency required for the reviewer to reproduce results
- Must support red-green-refactor in practice, not just in narrative

## Options Considered

### Option 1: pytest, layered test directories (`tests/unit`, `tests/contract`, `tests/integration`, `tests/orchestration`, `tests/e2e`), with a documented TDD sequence per task

- Advantages: mature, well-understood tooling; directory layout maps 1:1 to the layers the constitution requires be separately testable; `pytest -k` allows a reviewer to run any single layer independently
- Disadvantages: none material
- Risks: none material
- Implementation impact: low (standard Python tooling)
- Assessment implications: reviewer can verify TDD evidence by inspecting commit history (failing test commits preceding implementation commits) and by re-running the suite

### Option 2: A custom test runner / BDD framework (e.g., behave with Gherkin features)

- Advantages: scenario descriptions read closer to natural language
- Disadvantages: added tooling/learning overhead disproportionate to benefit for a solo 2–3 day assessment; pytest already supports expressive scenario tests via fixtures/parametrization
- Risks: scope overrun
- Implementation impact: medium
- Assessment implications: no material scoring benefit over Option 1 for this assignment

## Decision

Adopt **Option 1**: pytest with layered test directories matching the architectural layers, and a TDD discipline where each task's commit history shows a failing test committed (or verified failing) before the corresponding implementation, per the guide's TDD Sequence.

## Rationale

This directly maps testing structure to the constitution's modularity and testability principles and keeps TDD evidence verifiable through ordinary Git history inspection rather than requiring a reviewer to trust narrative claims.

## Consequences

- **Positive**: any reviewer with Python installed can run the full suite with one command; layer-by-layer execution is possible for triage.
- **Negative**: strict TDD discipline is slower per-task than writing implementation first — an accepted, intentional trade-off per constitution Principle IV.
- **Operational**: `pytest` in CI-equivalent local validation before every commit (Pre-Commit Review gate).
- **Testing**: this ADR is itself validated by its own existence being followed consistently — checked at `/speckit-converge`.
- **Governance**: "task completion requires executed validation" is enforced by the Task-Group Checkpoint prompt requiring actual command output, not claims.

## Risks and Mitigations

- Risk: time pressure within the 2–3 day box tempts implementation-first shortcuts. Mitigation: the Pre-Commit Review gate explicitly checks "tests written before implementation" and blocks commit approval if evidence is implementation-first.

## Reversibility

High — test tooling choice does not constrain application architecture.

## Traceability

- Requirements: constitution Principle IV; all FR-/NFR- (every requirement needs a verification method per `/speckit-analyze`)
- Spec sections: all
- Plan sections: §10
- Expected tasks: every task group (TDD sequence applies throughout)

## Validation

Validated by: `pytest` run output attached as evidence at each Task-Group Checkpoint and at convergence; Git history showing failing-test-then-implementation ordering for a sample of commits reviewed during Final Independent Assessment.
