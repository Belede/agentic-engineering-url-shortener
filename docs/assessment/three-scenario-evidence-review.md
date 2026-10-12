# Three-Scenario Evidence Review

Read-only review (no files modified by this review itself) against the implemented evidence for Greenfield, Brownfield, and Ambiguous-Requirement, per the governance guide's Scenario Evidence Review prompt. This content was substantively covered inside `docs/assessment/convergence-report.md`'s "Three Scenarios" section during convergence; it is reproduced here as its own standalone artifact in the guide's prescribed format, since that is itself a documentation gap the guide calls for closing (not a change in finding).

## Scenario Readiness Matrix

| Check | Greenfield | Brownfield | Ambiguous |
|---|---|---|---|
| Requirement input exists | ✅ CL-01, `spec.md` | ✅ CL-02, `spec.md` | ✅ CL-03, `spec.md` |
| Interpretation/normalization exists | ✅ `run_quality_checks()`, all 6 pass | ✅ decomposed directly (no ambiguity) | ✅ 2/6 checks fail, both named |
| Decomposition exists | ✅ `run_decompose` call in `test_scenario_greenfield.py` | ✅ `run_decompose` call in `test_scenario_brownfield.py` | ✅ `run_decompose` post-`RENORMALIZE` |
| Dependency graph visible | ✅ `graph.py` (shared across all runs) | ✅ same | ✅ same |
| Orchestration path visible | ✅ full trace to `DONE` | ✅ full trace to `RELEASE_APPROVAL` | ✅ full trace to `RELEASE_APPROVAL`, including `CLARIFY`→`RENORMALIZE` |
| State transitions visible | ✅ `state_transitions` table, queried directly in tests | ✅ same | ✅ same |
| Human gates visible | ✅ real `ARCH_APPROVAL` | ✅ real `ARCH_APPROVAL` (migration-aware) | ✅ real `CLARIFY` answer + `ARCH_APPROVAL` + `SECURITY_APPROVAL` |
| Tests exist | ✅ 6 tests | ✅ 6 tests | ✅ 7 tests (3 detection + 4 resumption) |
| Validation executed | ✅ `pytest` run, not claimed | ✅ same | ✅ same |
| Failure behavior demonstrated | ✅ rate-limit-creates-zero-links | ✅ concurrency-correctness under real parallel load | ✅ CLARIFY genuinely blocks downstream work |
| Audit evidence exists | ✅ `audit_events` rows per transition | ✅ same | ✅ same |
| Documentation matches execution | ✅ `greenfield.md`, test counts re-verified | ✅ `brownfield.md` + `brownfield-impact-analysis.md`, counts re-verified | ✅ `ambiguous.md`, counts re-verified |
| Terminal outcome exists | ✅ `DONE` | ✅ `RELEASE_APPROVAL` → decided READY WITH ACCEPTED LIMITATIONS at the combined gate | ✅ same |
| Limitations disclosed | ✅ no batch-level idempotency (documented) | ✅ single-writer SQLite concurrency (documented) | ✅ CL-07 superseded, documented not rewritten |

## Materially Distinct? (explicit cross-check)

- **Greenfield**: additive, zero `CLARIFY` transitions, reaches `DONE` directly.
- **Brownfield**: migration-bearing, gated by a pre-code impact-analysis artifact (commit-order verified), concurrency-focused validation.
- **Ambiguous**: the only scenario touching `CLARIFY`/`RENORMALIZE`, the only one requiring both `ARCH_APPROVAL` and `SECURITY_APPROVAL`, the only one that surfaced a real latent bug during implementation.

Confirmed materially distinct — not three variations on the same path with different labels.

## Missing Evidence

None found in this pass. (The one gap this review process itself exists to catch — Brownfield's missing orchestration-run E2E test — was found and fixed during `/speckit-converge`, commit `6fc41b0`, before this standalone document was written.)

## Unsupported Claims

None found. Every test-count claim in all three scenario docs was re-verified against an actual `pytest` run during this review (see `docs/traceability/reviewer-navigation.md`'s verified counts, cross-checked again here: Greenfield 6, Brownfield 6, Ambiguous 3+4=7).

## Cross-Scenario Inconsistencies

None found. All three share the same graph (`graph.py`), the same node implementations, and the same audit/decision schema — no scenario reimplements orchestration behavior independently, which rules out the most likely source of cross-scenario inconsistency.

## Mandatory Remediation

None required.
