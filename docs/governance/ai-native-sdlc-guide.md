# AI-Native SDLC Execution Guide — Operating Reference

> Condensed operating reference derived from the controlled technical guidance document governing this repository's execution process. The full source document is the candidate's internal working copy and is not reproduced verbatim here; this file captures the operational structure that the repository's process, commits, and gates are built against, for reviewer traceability.

## Tooling Decision

| Role | Owner |
|------|-------|
| Sole SDLC methodology, specification framework, planning framework, task authority, governance model, lifecycle state | **SpecKit** |
| Primary AI coding assistant and execution runtime | **Claude Code** |
| Evidence repository, change history, review surface, submission mechanism | **GitHub** |
| Architecture owner, decision authority, approval authority, reviewer, final quality owner | **Human Candidate (Belede Rahul)** |

## Lifecycle

```
/speckit-constitution
  → /speckit-specify
  → /speckit-clarify
  → Human Requirements Approval
  → /speckit-plan
  → Architecture Decision Records
  → Human Architecture Approval
  → /speckit-checklist
  → /speckit-tasks
  → /speckit-analyze
  → Pre-Implementation Review
  → /speckit-implement
  → Incremental TDD Execution
  → Scenario Demonstrations (Greenfield / Brownfield / Ambiguous)
  → /speckit-converge
  → Independent Assessment Review
  → Release-Readiness Decision
```

## Human Gates (non-negotiable)

1. **Gate 1 — Constitution**: verify non-linear orchestration, state persistence, human ownership, bounded retry, rollback/compensation, safe-stop, dynamic replanning, audit-grade evidence, TDD, and evidence-based completion are explicitly covered.
2. **Gate 2 — Specification**: reject any spec that chooses technology prematurely, silently resolves ambiguity, lacks negative behavior, omits a required scenario, presents orchestration as a linear chain, lacks human approval, lacks recovery/safe-stop, or cannot be tested/traced.
3. **Gate 3 — Clarification**: material decisions are made and recorded by the human candidate personally — never delegated to "best practices" or "sensible defaults."
4. **Gate 4 — ADRs**: every material architecture decision is reviewed and explicitly Accepted or Rejected by the human candidate; an ADR is never self-approved by the AI.
5. Additional per-run gates during implementation: `ARCH_APPROVAL`, `SECURITY_APPROVAL`, `CLARIFY`, `RELEASE_APPROVAL` — each requires an explicit recorded human decision; silence is never approval.

## Claude Code-Specific Guardrails

- **Do not let Claude become a second framework** — reject any proposed roadmap, state file, task numbering, or planning document that bypasses SpecKit's own stages.
- **Do not run unbounded autonomous implementation** — stop at task-group boundaries (one coherent group + its tests + its documentation + its traceability), then inspect and commit.
- **Do not allow Claude to approve its own decisions** — ADRs are proposed by Claude, Accepted only by the human.
- **Do not use Claude's own summary as evidence** — acceptable evidence is requirement + design + implementation + test + executed output + scenario record, not a narrative claim.
- **Do not allow silent architecture drift** — if an approved design proves impractical: stop, document, update the plan/ADR, get re-approval, regenerate affected tasks, re-analyze, resume.
- **Maintain context hygiene** — every new session re-reads the authoritative SpecKit artifacts and current repository/task state rather than relying on conversational memory.

## Final Operating Principle

SpecKit decides what stage the project is in. The specification decides what must be built. The plan and ADRs decide how it will be built. The task graph decides execution order. Claude Code performs the approved engineering work. Tests determine whether behavior is correct. Checklists determine whether quality obligations are satisfied. GitHub preserves the evidence. **The human candidate owns every material decision and the final outcome.**
