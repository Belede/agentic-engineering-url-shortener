# ADR-004: Orchestration Model, Dependency Graph Representation, and Workflow State Persistence

## Status

Accepted — approved by human candidate (Belede Rahul), 2026-10-12

## Context

This is the assignment's "critical differentiator" requirement: the orchestration must be an explicit, stateful, non-linear graph — not sequential agent chaining — supporting parallel paths, synchronization, branching, replanning, and resumption, with persisted state and decision lineage (constitution Principle II; spec.md Primary Capability).

## Decision Drivers

- Must be genuinely non-linear and inspectable, not a disguised linear chain (explicit failure trap called out in the governance guide's Analyze and Independent Reviewer gates)
- Must persist across process restarts
- Must be implementable and testable within the 2–3 day timebox without external workflow-engine infrastructure

## Options Considered

### Option 1: Explicit adjacency-table state machine, persisted in the same SQLite DB

- Approach: nodes and allowed transitions defined in code as an explicit graph (`orchestration/graph.py`); current state, history, and decision lineage persisted in `workflow_runs`/`state_transitions`/`decisions` tables; node handlers are independently testable pure-ish functions invoked by a small engine loop
- Advantages: no external infrastructure; graph is inspectable as data (can be queried, visualized, unit-tested per-transition); persistence reuses the already-chosen datastore (ADR-002); directly supports resume (re-read last state, re-enter graph)
- Disadvantages: hand-built engine has less tooling/visualization than a mature workflow product
- Risks: risk of accidentally degenerating into a disguised linear chain if not deliberately designed with branches/parallel fan-out — mitigated by the explicit branch/parallel/replan nodes defined in plan.md §3 and validated by `/speckit-analyze`'s explicit failure-trap check
- Implementation impact: medium — this is the most substantial component of the prototype, proportionate to its role as the "critical differentiator"
- Assessment implications: fully inspectable by a reviewer via direct DB queries or a provided CLI/endpoint — strong evidence story

### Option 2: External workflow engine (e.g., Temporal, Airflow) embedded in-process or via Docker

- Advantages: production-grade durability/retry semantics out of the box
- Disadvantages: adds a heavyweight dependency disproportionate to a 2–3 day assessment; reviewer setup friction; risks the assessment being graded on "did you integrate X" rather than "do you understand orchestration," which the assignment's emphasis on demonstrating the concepts yourself argues against
- Risks: scope overrun; obscures the candidate's own design reasoning behind a third-party engine's abstractions
- Implementation impact: high
- Assessment implications: weakens "clarity and defensibility of decisions" — harder to explain internals that are a third party's code

### Option 3: Pure in-memory linear script with try/except retry wrapping

- Advantages: fastest to write
- Disadvantages: not a dependency graph, no real persistence, no genuine parallel/branch/replan support — this is exactly the disguised-linear-chaining failure mode the governance guide explicitly instructs reviewers to detect and penalize
- Risks: fails the assignment's core differentiator entirely
- Implementation impact: n/a — rejected outright

## Decision

Adopt **Option 1**: a hand-built, explicit adjacency-table state machine with SQLite-persisted state, history, and decision lineage; node handlers independently unit-testable; the engine loop is a thin, separately-testable driver over the graph definition.

## Rationale

This is the only option that satisfies the non-negotiable orchestration principle (constitution Principle II) within the timebox without introducing disproportionate infrastructure, and it keeps the design fully explainable and defensible by the candidate — directly serving the "Defensibility of decisions" scoring dimension.

## Consequences

- **Positive**: fully inspectable, fully owned design; reuses existing persistence (no new infra); directly testable per-node and per-transition.
- **Negative**: a hand-built engine is less battle-tested than a mature product — acceptable and disclosed as a prototype-scope trade-off, not production infrastructure.
- **Operational**: the engine runs in-process; a crashed process simply means the next run (or an explicit resume call) re-reads persisted state.
- **Testing**: every node and every transition is unit-testable in isolation; a small number of end-to-end tests exercise full scenario runs.
- **Governance**: this component is exactly what `/speckit-analyze`'s explicit-failure-trap list (linear chaining, missing parallel execution, missing synchronization, missing persistent state, etc.) will be checked against — it is the highest-scrutiny component in the repository.

## Risks and Mitigations

- Risk: reviewer perceives the graph as "just an if/else chain with extra names." Mitigation: the graph definition is data (an explicit adjacency structure), not nested conditionals; parallel fan-out/fan-in inside `TEST` and the conditional `SECURITY_APPROVAL` edge (plan.md §3) are concretely demonstrated, not merely asserted.

## Reversibility

Low-to-moderate — the node/transition contract (inputs/outputs/pre/postconditions) is the stable interface; the underlying engine loop implementation can be revised without changing persisted data shapes, as long as the schema in `data-model.md` is respected.

## Traceability

- Requirements: FR-011 through FR-027 (all orchestration FRs)
- Spec sections: Primary Capability: Agentic SDLC Orchestration
- Plan sections: §3, §4
- Expected tasks: dependency-graph, workflow-state-machine, context-and-decision-lineage task groups

## Validation

Validated by: orchestration state-transition tests (every node, every allowed/prohibited transition), a resume test, a parallel fan-out/fan-in test inside `TEST`, and the three required end-to-end scenario tests.
