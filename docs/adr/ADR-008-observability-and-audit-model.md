# ADR-008: Observability and Audit Model

## Status

Accepted — approved by human candidate (Belede Rahul), 2026-10-12

## Context

Constitution Principle IX requires a correlation id per run, recorded state transitions/decisions/approvals/retries/failures/replanning/terminal outcomes, and audit evidence with actor type, action, timestamp, affected artifact/state, result, and reason — with demonstration metrics clearly distinguished from production measurements.

## Decision Drivers

- Must support full reconstruction of a run from persisted evidence alone (not reliant on conversational/chat memory)
- Must compute reliability metrics (success rate, retry/rollback frequency, MTTR, latency) from real recorded data
- Must not conflate demonstration measurements with production claims

## Options Considered

### Option 1: Append-only `audit_events` table + structured JSON logs + an in-process metrics registry, all keyed by `run_id`

- Advantages: self-contained (no external observability stack needed); directly queryable by a reviewer via SQL or a provided `/api/v1/metrics` and `/api/v1/workflows/{run_id}/audit` endpoint; append-only table structurally prevents retroactive evidence tampering at the application layer
- Disadvantages: no production-grade distributed tracing (not needed — single process)
- Risks: none material for this scope
- Implementation impact: medium
- Assessment implications: reviewer can independently reconstruct any run from the repository/running instance alone — strong "GitHub evidence" and "auditability" scoring support

### Option 2: External observability stack (e.g., OpenTelemetry Collector + Grafana)

- Advantages: production-realistic tooling
- Disadvantages: significant setup overhead disproportionate to a 2–3 day, single-process prototype; reviewer friction
- Risks: scope overrun
- Implementation impact: high
- Assessment implications: risks being graded as "integrated a tool" rather than "designed an audit model"

### Option 3: Plain unstructured print/log statements, no persisted audit table

- Advantages: trivial
- Disadvantages: not queryable, not reconstructable, fails constitution Principle IX outright; explicit failure trap "incomplete audit evidence"
- Risks: fails a non-negotiable principle
- Implementation impact: n/a — rejected

## Decision

Adopt **Option 1**: append-only `audit_events` table, structured JSON logs carrying `run_id`, and an in-process metrics registry computing success rate, retry/rollback frequency, MTTR (per plan.md §6 formula), unrecovered-failure count, and end-to-end latency from the `audit_events`/`state_transitions` tables directly — never from hand-maintained counters that could drift from reality.

## Rationale

Deriving metrics from the same persisted event stream that forms the audit trail (rather than separately-maintained counters) guarantees the two can never silently disagree, and keeps every reliability claim traceable to a specific, queryable row — directly satisfying Evidence-Based Completion (Principle XI).

## Consequences

- **Positive**: any claim in the final engineering summary about retries, rollbacks, or MTTR can be re-derived by a reviewer running one query.
- **Negative**: metrics computation adds a query/aggregation layer rather than simple counter increments.
- **Operational**: no external dependency; metrics available immediately after any run.
- **Testing**: MTTR calculation is unit-tested against a constructed set of recovered/unrecovered events with a known expected result.
- **Governance**: every metrics report explicitly labels the population size and exclusions (per plan.md §6), preventing synthetic demonstration numbers from being mistaken for production statistics.

## Risks and Mitigations

- Risk: a demonstration metric (e.g., MTTR from 3 scenario runs) could be misread as a production SLA. Mitigation: every generated metrics report and the final engineering summary explicitly label demonstration-data scope (constitution Principle IX; plan.md §6).

## Reversibility

High — the audit/metrics layer reads from persisted events and can be re-implemented (e.g., swapped for a real observability backend later) without changing what gets recorded.

## Traceability

- Requirements: FR-025, FR-026
- Spec sections: Non-Functional Requirements — Observability, Auditability
- Plan sections: §6, §7
- Expected tasks: audit-trail, logs-metrics-traces task groups

## Validation

Validated by: an MTTR unit test with a known-expected result, an audit-event completeness test (every transition type produces exactly one audit event), and manual reviewer verification via the metrics endpoint after a scenario run.
