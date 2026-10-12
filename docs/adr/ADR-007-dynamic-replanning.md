# ADR-007: Dynamic Replanning Model

## Status

Accepted — approved by human candidate (Belede Rahul), 2026-10-12

## Context

Constitution Principle II requires the orchestration to dynamically re-plan when upstream outputs change (e.g., after a human clarification answer) while preserving governance — not silently drifting and not blindly regenerating everything downstream.

## Decision Drivers

- Must regenerate only artifacts actually affected by the changed upstream decision (not the entire run)
- Must preserve the prior version for decision lineage (constitution Principle II, X)
- Must re-apply governance gates to the regenerated artifacts, not skip them

## Options Considered

### Option 1: Versioned task/decomposition records with a diff-based `RENORMALIZE` node

- Approach: when a `CLARIFY` answer changes the requirement, `RENORMALIZE` re-runs normalization, diffs the new task decomposition against the prior version, marks unaffected tasks unchanged (carried forward), and creates new/updated task rows only for affected scope; the run then proceeds through `DECOMPOSE`→`DESIGN`→`ARCH_APPROVAL` again for the affected scope
- Advantages: minimal, inspectable blast radius; prior versions retained for lineage; governance gates naturally re-apply because the graph re-enters `DESIGN`→`ARCH_APPROVAL` rather than skipping them
- Disadvantages: diffing logic adds implementation complexity
- Risks: an imperfect diff could under- or over-scope the regenerated set — mitigated by conservative diffing (when in doubt, mark affected) and a dedicated replanning test
- Implementation impact: medium
- Assessment implications: directly demonstrated by the ambiguous-requirement scenario's documented before/after task diff

### Option 2: Full restart — discard all prior artifacts and re-run the entire graph from `INGEST`

- Advantages: simplest to implement
- Disadvantages: destroys decision lineage for unaffected upstream work; wasteful; does not demonstrate *dynamic* (scoped) replanning, just a restart
- Risks: fails the "preserve context and decision lineage" requirement
- Implementation impact: low but low-quality
- Assessment implications: explicit failure trap — "missing context propagation," "missing decision lineage"

### Option 3: Silent in-place mutation of the existing decomposition with no versioning

- Advantages: least storage
- Disadvantages: no audit trail of what changed or why; directly contradicts "undocumented architecture drift" prohibition
- Risks: fails traceability and auditability principles
- Implementation impact: n/a — rejected

## Decision

Adopt **Option 1**: versioned decomposition with a diff-based `RENORMALIZE` node that scopes regeneration to affected tasks only and re-applies all downstream governance gates to the regenerated scope.

## Rationale

This is the only option that genuinely demonstrates *dynamic* replanning (scoped, lineage-preserving, re-governed) rather than either a full restart or a silent mutation — both of which are explicit failure traps named in the governance guide's Analyze stage.

## Consequences

- **Positive**: strong, inspectable evidence of real replanning behavior; prior decision lineage is never lost.
- **Negative**: more implementation and testing surface than a naive restart.
- **Operational**: replanning events are a distinct, queryable audit-event type.
- **Testing**: a dedicated replanning test asserts the diff correctly scopes to affected tasks only.
- **Governance**: regenerated artifacts pass back through the same `ARCH_APPROVAL`/`SECURITY_APPROVAL` gates as original artifacts — no shortcut path.

## Risks and Mitigations

- Risk: diff logic misses a genuinely affected downstream task. Mitigation: conservative diffing policy (affected-by-default for any task referencing a changed requirement field) plus an explicit test case asserting this conservative behavior.

## Reversibility

Moderate — the diffing algorithm can be refined without changing the versioned-record schema, provided the schema itself (in `data-model.md`) remains stable.

## Traceability

- Requirements: FR-018
- Spec sections: User Story 4; Edge Cases
- Plan sections: §3 (RENORMALIZE node), §4
- Expected tasks: dynamic-replanning task group

## Validation

Validated by: a replanning unit test and the ambiguous-requirement scenario's end-to-end evidence (docs/scenarios/ambiguous.md), which records the before/after task diff explicitly.
