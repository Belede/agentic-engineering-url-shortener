# Pre-Implementation Principal Engineer Review

Adopting a fresh, skeptical reviewer stance — not defending the ADRs or plan I drafted, treating this repository as if submitted by another candidate. No files modified by this review.

## Review Questions

1. **Is this genuinely stateful orchestration or sophisticated linear chaining?** — On paper, genuinely stateful: an explicit adjacency-table graph (plan.md §3) with branches (`QUALITY_CHECK`→`CLARIFY` vs. `QUALITY_CHECK`→`DECOMPOSE`), a conditional edge (`SECURITY_APPROVAL`), and persisted state. **But zero of this is executed yet** — this is a design claim, not evidence. The real test is whether the implemented graph in Phase 2 actually matches this design, which `/speckit-analyze` will need to re-check post-implementation.
2. **Where is parallel execution demonstrated?** — Designed into the `TEST` node (unit/contract/security groups fan out, synchronize before `DOCUMENT`). Thin: a single fan-out point is the only parallel path in the whole graph. Acceptable for a 2–3 day prototype, but worth being honest in the final summary that parallelism is demonstrated once, not pervasively.
3. **Where does synchronization occur?** — Same fan-in point. Same thinness caveat.
4. **How is state persisted and resumed?** — SQLite tables (ADR-004), explicit resume task (T031, now correctly citing FR-019 after this analysis's own correction round). Reasonable, but T031 is bundling three distinct behaviors — safe-stop entry, human-resume-after-safe-stop, and resume-after-process-crash (FR-019) — into one task. **Risk**: if implemented carelessly, the crash-resume case could get weaker test coverage than the safe-stop-resume case, because they're superficially similar but not identical (one resumes from a human-gated terminal state, the other from an arbitrary mid-stage interruption). Flagged as a condition below.
5. **How is decision lineage preserved?** — `decisions` table with `source_reference` linking back to CL-IDs/ADR-IDs. Reasonable design; depends entirely on implementation discipline (every node handler actually writing a `decisions` row) which cannot be verified until code exists.
6. **Which actions require human approval?** — Clearly enumerated (plan.md §5): `CLARIFY`, `ARCH_APPROVAL`, `SECURITY_APPROVAL`, `RELEASE_APPROVAL`. Good — this is the strongest-specified part of the design.
7. **Can mandatory approval be bypassed?** — ADR-005's "zero outbound system transitions" design is the right idea, but as designed it's enforced by *the absence of code*, not by a positive guard. The planned test (T015: "assert no auto-advance edge out of any human-gate node") is the actual enforcement mechanism — this test is load-bearing for the whole governance claim and must not be skipped or weakened during implementation.
8. **Are retry boundaries explicit?** — Yes, max 2 retries, explicit backoff (ADR-006). Good.
9. **Where is timeout behavior defined?** — Per-node table in plan.md §3. Defined for system nodes; human-gate nodes correctly have no timeout (by design, per constitution Principle III) — this is right, not an oversight.
10. **Is rollback technically feasible?** — The rollback/compensation boundary ("has the change left the sandbox") is conceptually sound but somewhat judgment-based rather than mechanically determined. **Risk**: at implementation time, this boundary needs a concrete, code-level test (not a prose rule) for which category a given failure falls into, or the distinction will be arbitrary in practice. Flagged as a condition below.
11. **Where is compensation used instead?** — Defined (ADR-006); not yet exercised by real evidence.
12. **What triggers safe-stop?** — Retry exhaustion, a detected verification-node defect, or an attempted gate bypass. Reasonably precise.
13. **How does dynamic replanning avoid uncontrolled change?** — `RENORMALIZE` re-enters `DESIGN`→`ARCH_APPROVAL`, so regenerated artifacts face the same gate as original ones (ADR-007). This is a genuinely good design choice — replanning doesn't get a governance shortcut.
14. **Can every major claim be validated?** — Mostly yes, with one gap this analysis itself found and fixed (NFR-007 had no validating task before this review — now T034b). That the gap existed at all, and was only caught by a deliberate self-check pass, is itself evidence that this kind of gap-hunting needs to happen again post-implementation, not just once pre-implementation.
15. **Are accepted ADRs reflected in tasks?** — Yes, verified by cross-reference sweep (pre-implementation-analysis.md).
16. **Are requirements independently testable?** — Each FR-/NFR- has an observable acceptance criterion in spec.md. Reasonable.
17. **Are tasks small and dependency-correct?** — Mostly yes. T031 (see point 4) and T043 (six fault-injection variants bundled under one task ID) are the two coarsest items — acceptable as *planned* parallelizable sub-work, but if implemented as one undifferentiated commit rather than six separately-reviewable ones, that would violate the "small, reviewable, dependency-safe changes" execution discipline.
18. **Is the brownfield scenario credible?** — Yes — it requires a real impact-analysis artifact (T038) committed *before* any code task (T039/T040), which is explicitly dependency-ordered in tasks.md. Good design; must be honored in commit order during implementation, not just in task numbering.
19. **Does the ambiguous scenario truly suspend unsafe execution?** — Designed to (T041 halts at `CLARIFY`, T042 only proceeds after a recorded human decision). Not yet executed — this is the scenario most worth scrutinizing once real, since "ambiguity detection" is easy to fake with a hardcoded check that only recognizes the one planted example (CL-03's exact wording) rather than genuinely evaluating the 6 quality checks. Flagged as a condition below.
20. **Is the evidence strategy authentic?** — The design explicitly separates demonstration measurements from production claims (NFR-007, ADR-008) and requires metrics to be derived from the same event stream as the audit trail, not hand-maintained counters. This is a genuinely good anti-fabrication design choice, assuming it's actually implemented this way rather than simplified under time pressure.

## Verdict

**PROCEED WITH CONDITIONS**

## Critical Findings

None at CRITICAL severity. The design is sound enough to begin implementation; the findings below are conditions on *how* implementation proceeds, not blockers to starting it.

## Architectural Weaknesses

- Plane separation (application vs. orchestration) is enforced by code review discipline and `/speckit-analyze`, not a structural guard (e.g., an import-linter rule). Low risk at this scale, but worth a lightweight automated check if time permits.

## Orchestration Weaknesses

- Parallelism is demonstrated at exactly one point in the graph (`TEST` fan-out/fan-in). Honest framing in the final summary should avoid overstating this as pervasive parallel orchestration.

## Governance Weaknesses

- The "no auto-advance out of a human-gate node" guarantee rests on one test (T015) remaining strict. This test must be treated as load-bearing and must not be weakened or skipped under time pressure.

## Testing Weaknesses

- None beyond the NFR-007 gap already corrected by this analysis round.

## Evidence Weaknesses

- None yet — no evidence exists to critique at this stage; this itself is the main limitation of a pre-implementation review and is expected, not a defect.

## Required Corrections Before Implementation

None blocking. The following are **conditions to honor during implementation**, not corrections to the plan itself:

1. When implementing T031, write genuinely distinct test cases for (a) safe-stop→human-resume and (b) process-crash-mid-stage→resume (FR-019) — do not treat them as one code path validated by one test.
2. When implementing the rollback-vs-compensation boundary (T029/T030), encode the "has this left the sandbox" distinction as an explicit, testable predicate in code — not an implicit judgment call buried in a conditional.
3. When implementing `QUALITY_CHECK` (T017), implement genuine checks against the 6 criteria (acceptance criteria present, no vague temporal terms, no internal contradiction, within policy/architecture boundary, testable) — not a hardcoded recognizer for the one planted CL-03 example. The greenfield scenario (a different, well-formed requirement) passing the same checks is the actual evidence this was done generically.
4. When implementing T043's fault-injection variants, commit them as separable, individually reviewable changes, not one bundled commit.

These four conditions are tracked in tasks.md's Universal Task Policy risk/guardrail note and will be checked again at `/speckit-converge`.
