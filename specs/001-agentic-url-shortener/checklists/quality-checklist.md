# Quality and Readiness Checklists

Status: generated from approved spec.md, plan.md, and accepted ADRs. Each item is objectively verifiable against an artifact, behavior, or evidence — not a subjective adjective. Checked at `/speckit-analyze` (pre-implementation) and again at `/speckit-converge` (post-implementation).

Legend: ☐ not yet verifiable (pre-implementation) · will become ☑/☒ with evidence once code/tests exist.

## 1. Requirements

- ☐ Every FR-/NFR- identifier in spec.md maps to at least one task in tasks.md
- ☐ Every FR-/NFR- has an observable (pass/fail-testable) acceptance criterion
- ☐ Negative acceptance criteria exist for creation, resolution, and persistence failure paths (FR-002, FR-005, FR-010)
- ☐ No requirement contains an unresolved `NEEDS CLARIFICATION`/`OPEN-Q-*` marker

## 2. Architecture

- ☐ Application plane and orchestration plane are in separate top-level modules with no cross-import of internals
- ☐ Every component listed in plan.md §2/§3 has a corresponding source directory
- ☐ No component exists in source that is not traceable to a plan.md component or an accepted ADR

## 3. Architecture Decision Records

- ☐ Every ADR has a Status of Accepted, Rejected, or Superseded — none left Proposed once implementation begins
- ☐ Every ADR's Traceability section references real requirement/spec/plan identifiers that exist
- ☐ No ADR is marked Accepted without a recorded human approval (see Human Gate 4 record in this repository's commit history)

## 4. Agentic Orchestration

- ☐ The orchestration graph is represented as data (adjacency/transition table), not nested if/else control flow only
- ☐ At least one genuine parallel fan-out/fan-in point exists and is tested (plan.md §3, `TEST` node)
- ☐ At least one conditional branch exists and is tested (`SECURITY_APPROVAL` edge)
- ☐ Workflow state persists across a process restart (tested, not just claimed)
- ☐ Decision lineage (requirement → decision → approval → task → code) is reconstructable from persisted data alone

## 5. Controlled Autonomy

- ☐ No code path allows `IMPLEMENT` to begin before `ARCH_APPROVAL` (and `SECURITY_APPROVAL` where applicable) is recorded as approved
- ☐ No code path allows `RELEASE_APPROVAL`'s outcome to be set without an explicit human-initiated call

## 6. Human Approvals

- ☐ Every human-gate node (`CLARIFY`, `ARCH_APPROVAL`, `SECURITY_APPROVAL`, `RELEASE_APPROVAL`) has zero system-initiated outbound transitions (unit-tested, ADR-005)
- ☐ Every `approval_records` row has a non-null `decided_by`, `timestamp`, and `rationale`
- ☐ No approval is inferred from timeout or silence (explicit test asserting absence of timeout-based auto-advance)

## 7. Security

- ☐ Disallowed URL schemes are rejected at creation (test exists)
- ☐ SSRF-style private/loopback targets are rejected at creation (test exists, CL-05)
- ☐ Rate limiting enforced and tested (CL-08)
- ☐ No secret or API key appears in logs or audit events (grep-verifiable)
- ☐ Dependency/license scan executed and recorded as part of release-readiness evidence

## 8. Compliance and Change-Control Policy Enforcement

- ☐ Every workflow run records the policy pack version evaluated
- ☐ Every mandatory policy check produces PASS/FAIL/EXCEPTION-REQUESTED/NOT-APPLICABLE — never left blank
- ☐ A mandatory FAIL blocks progression (tested)
- ☐ Any EXCEPTION-REQUESTED has a recorded human approval, rationale, scope, compensating control, and expiry condition — none left implicit
- ☐ No policy evaluation exists without a recorded version

## 9. Reliability and Recovery

- ☐ Retry attempts are bounded (max observed ≤ 2 retries in any test or run; no unbounded-retry code path)
- ☐ Transient vs. permanent failure classification is explicit in code (not implicit)
- ☐ At least one rollback path and one compensation path are each independently tested and distinguished
- ☐ Safe-stop is reachable via a real test (forced retry exhaustion or forced defect), not only described in prose
- ☐ Resume re-enters only the failed node, not the full graph (tested)

## 10. Observability and Auditability

- ☐ Every state transition produces exactly one `audit_events` row (completeness test)
- ☐ Every run has a stable, queryable `run_id` present on every related audit row and log line
- ☐ MTTR calculation excludes unrecovered failures from its denominator (unit-tested against a known expected value)
- ☐ Demonstration metrics are explicitly labeled as such in any generated report (not presented as production statistics)

## 11. TDD and Testing

- ☐ Git history shows a failing-test commit (or verified-failing state) preceding the corresponding implementation commit, for a representative sample of tasks
- ☐ All test layers listed in plan.md §10 have at least one test file
- ☐ The full suite is runnable with one documented command and the result is reproducible from a clean clone

## 12. Greenfield Scenario

- ☐ Requirement-quality checks are recorded for the batch-creation requirement and show all 6 checks passing
- ☐ No `CLARIFY` gate is invoked for this scenario (explicitly verified, not just absent)
- ☐ Contract version bump (1.0.0 → 1.1.0) is reflected in `contracts/openapi.yaml` and documented

## 13. Brownfield Scenario

- ☐ Impact analysis artifact exists and was produced *before* any code change for this scenario (commit-order verifiable)
- ☐ Migration 0002 has a tested up and down script
- ☐ Concurrency test for atomic `max_clicks` counting exists and passes

## 14. Ambiguous-Requirement Scenario

- ☐ Both defects in the CL-03 text (vague term, contradiction) are explicitly named in the recorded `QUALITY_CHECK` failure output
- ☐ `CLARIFY` genuinely blocks `DECOMPOSE`/`DESIGN` until a human decision is recorded (no auto-continuation)
- ☐ A `RENORMALIZE` replanning event with a before/after task diff is recorded after the human decision

## 15. Documentation

- ☐ README/quickstart instructions, run verbatim from a clean clone, produce a working system (SC-001)
- ☐ Architecture documentation reflects actual implemented components, not only planned ones
- ☐ Known limitations and residual risks are documented, not omitted

## 16. Traceability

- ☐ `docs/traceability/matrix.md` maps every FR-/NFR- to scenario, design, ADR, task, code path, test, and evidence
- ☐ No orphan requirement (unmapped to any task)
- ☐ No orphan task (unmapped to any requirement)
- ☐ No orphan implementation (code with no corresponding requirement or ADR)

## 17. GitHub Evidence

- ☐ Commit history shows the real execution sequence (constitution → spec → clarify → plan → ADR → checklist → tasks → analyze → implement → scenarios → converge), not manufactured/reordered commits
- ☐ No commit message claims a result that the commit's diff does not support

## 18. Release Readiness

- ☐ Release decision is exactly one of READY / READY WITH ACCEPTED LIMITATIONS / NOT READY
- ☐ Decision is not READY while any mandatory policy check or required scenario remains incomplete
- ☐ Residual risks are disclosed alongside a READY WITH ACCEPTED LIMITATIONS decision, if used

## 19. Assessment Submission

- ☐ All deliverables from the assignment brief are present: working prototype, architecture overview, three scenarios, setup instructions, testing approach/limitations/trade-offs
- ☐ Reviewer navigation guide exists and every claim in it resolves to a real repository path/command
