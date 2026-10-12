# Post-Implementation Analysis (`/speckit-analyze`, re-run)

**Scope**: re-run after all implementation (Phases 0–4) to check actual code against the approved constitution/spec/plan/ADRs — the pre-implementation pass (`docs/assessment/pre-implementation-analysis.md`) could only check design-time artifacts; this pass checks what was actually built.

## Executive Finding

Implementation is consistent with the approved design. One MEDIUM finding (module placement, not a functional defect) and three documented, intentional deviations (each already disclosed in its own scenario evidence doc at the time it happened, not surfaced here for the first time) are listed below. No CRITICAL or HIGH findings.

## Coverage Verification (executed, not asserted)

```
Plane separation: src/orchestration/ imports shortener.api.deps.get_db only
                   (one shared DB-connection utility) — no orchestration
                   business logic lives in shortener/, no shortener business
                   logic lives in orchestration/. ✅ (see MEDIUM finding below
                   on the import's naming/placement)
Audit append-only: grep confirms zero UPDATE/DELETE against audit_events
                   anywhere in src/. ✅
ADR statuses:      all 11 ADRs remain Accepted, none left Proposed. ✅
Open markers:      zero remaining OPEN-Q-*, TODO, FIXME, XXX in specs/ or src/. ✅
FR/NFR coverage:   all 30 FRs and 11 NFRs mapped in docs/traceability/matrix.md,
                   with code+test references verified to actually exist. ✅
```

## MEDIUM Finding: `orchestration/api.py` imports from `shortener.api.deps`

**Observation**: the orchestration plane's HTTP layer imports `get_db` from `shortener.api.deps`, a module that is otherwise shortener-API-specific. This works correctly (both planes share one SQLite connection pattern by design, ADR-001), but the import path implies a dependency on the shortener *API* package specifically, when conceptually orchestration only needs a generic DB-connection factory.

**Severity**: MEDIUM — naming/placement issue, not a functional or data-integrity defect. Both planes already correctly share the same physical database file by design (ADR-001); this is about where one small shared utility function lives, not about any behavior being wrong.

**Disposition**: documented as a known, accepted deviation rather than fixed this late in the timebox — moving `get_db` to a genuinely shared module (e.g. `src/common/db_deps.py`) would touch both planes' import graphs for a cosmetic improvement with real regression risk this close to release, and does not affect any requirement, test, or reviewer-facing claim. Tracked here for transparency (constitution Principle X — no silent architecture drift) and as a disclosed limitation, not hidden.

## Documented, Intentional Deviations (already disclosed at the time, cross-referenced here)

1. **Error-response shape fix in `redirect.py`** (commit `392ad44`, `docs/scenarios/brownfield.md`): originally used FastAPI's default `{"detail": ...}` wrapper for 404/410 errors, inconsistent with the documented `ErrorResponse` schema (`{"error", "message"}`). Fixed while touching the handler for the brownfield change; not a silent drift — called out in the brownfield evidence doc and covered by a dedicated regression test (`test_error_responses_match_documented_error_response_shape`).
2. **`Settings` dataclass env-caching bug fix** (commit `2754003`, `docs/scenarios/ambiguous.md`): a real latent bug (env vars read once at class-definition time, not per-instantiation) was caught by TDD while implementing the ambiguous scenario's resolution and fixed via `Settings.from_env()`. Disclosed in the scenario's evidence doc, not silently patched.
3. **CL-07 marked superseded, not rewritten** (commit `2754003`): the original "no default expiry" clarification record is preserved verbatim in `spec.md` with an explicit supersession note, rather than edited to read as if it always said something different — the historical decision lineage stays intact (constitution Principle X).

## Constitutional Compliance Re-Check

- **Principle II (Explicit Agentic Orchestration)**: confirmed non-linear — branching (`QUALITY_CHECK→CLARIFY` vs. `→DECOMPOSE`), conditional (`ARCH_APPROVAL→SECURITY_APPROVAL` only when security-sensitive), genuine parallel fan-out/fan-in (`TEST` node, proven by a real time-overlap assertion), dynamic replanning (`RENORMALIZE`, scoped diff) are all present in executed code and tests, not just design docs.
- **Principle III (Human Governance)**: `test_no_system_actor_transition_leaves_a_human_gate_node` is a standing regression test on the graph's own data — the strongest form of this guarantee available short of a formal proof.
- **Principle IV (TDD)**: every implementation task in this repository's history has a corresponding "confirmed failing, then implemented, then passing" tool-call sequence; Git history (single-author, agent-assisted session) reflects task-group-sized commits, not one monolithic dump.
- **Principle VIII (Reliability)**: all six reliability mechanisms (retry, fallback, rollback, compensation, safe-stop ×2 distinct cases) have dedicated, independently committed tests — not one combined "reliability" test.
- **Principle IX (Observability)**: MTTR and all metrics are demo-labeled (`demonstration_data: True` field) and derived from the same `audit_events`/`state_transitions` tables that form the audit trail, not separately maintained counters.
- **Principle XI (Evidence-Based Completion)**: every scenario evidence doc (`docs/scenarios/*.md`) cites exact test names and verified pass counts, cross-checked against an actual `pytest` run before being written down (see `docs/traceability/reviewer-navigation.md`'s verified counts).

## Unmapped Requirements / Tasks / Missing Tests / Missing Evidence

None beyond what `docs/traceability/matrix.md`'s own Orphan Check already discloses (the unwired `TransientError`/`PermanentError` retry classification).

## Corrective Sequence

No corrections required at this pass — the one MEDIUM finding is disposed of as a documented, accepted deviation (see above) rather than requiring a code change. Proceeding to the Final Independent Assessment.
