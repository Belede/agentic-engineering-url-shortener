# Agentic Software Engineering System: URL Shortener — Constitution

## Project Context

This repository is an engineering assessment submission. Reviewers will assess working behavior, architecture, engineering decisions, AI-assisted development process, task decomposition, testing discipline, governance, traceability, change history, documentation, and engineering judgment.

The URL shortener is the demonstration domain. The central differentiator is a governed, stateful, non-linear agentic software engineering orchestration system that transforms requirements into reviewable engineering outcomes across the complete software development lifecycle (SDLC).

## Core Principles

### I. Specification Before Implementation

No production implementation may begin without an approved specification. Requirements must be testable and traceable. Functional and non-functional requirements must remain distinguishable. Ambiguities must be resolved or recorded as explicit assumptions. Material upstream changes must trigger downstream impact analysis. Existing code must not become an undocumented substitute for the specification.

### II. Explicit Agentic Orchestration

The orchestration system must be more than sequential agent chaining. The system must use an explicit dependency graph or equivalent stateful model. It must support sequential paths, parallel paths, synchronization, branching, dynamic replanning, interruption, and resumption. Every stage must define inputs, outputs, entry criteria, exit criteria, ownership, and failure behavior. Workflow state, cross-stage context, artifact provenance, and decision lineage must be preserved. Agent autonomy must be bounded, observable, and auditable.

### III. Human Governance

Humans retain ownership of requirements, architecture, security-sensitive decisions, material exceptions, destructive changes, release readiness, and final quality. High-impact actions require explicit human approval. Approval, rejection, escalation, timeout, and safe-stop behavior must be defined. Mandatory approval gates must not be silently skipped. Lack of response must not be interpreted as approval.

### IV. Test-Driven Engineering

Apply red-green-refactor TDD to domain and orchestration behavior wherever technically practical. Write an initially failing test before corresponding implementation. Verify that the test fails for the expected reason. Implement only the minimum behavior needed to pass. Refactor only while tests remain green. Include unit, integration, API contract, orchestration transition, reliability, security, and end-to-end tests. Task completion requires executed validation, not merely generated code.

### V. Security and Privacy by Design

Validate and normalize external input. Restrict acceptable URL schemes. Address malicious redirect and abuse scenarios. Do not expose secrets or sensitive information in logs. Apply secure configuration defaults. Use least privilege and explicit trust boundaries. Document authentication assumptions, rate limiting, threat scenarios, and security trade-offs. Include dependency and secret scanning in release readiness.

### VI. Compliance and Change-Control Policy Enforcement

Define versioned policy guardrails covering security, compliance, privacy, audit retention, approved dependencies, software licensing, and change control. Every orchestration run must identify the policy version evaluated. Every applicable policy check must produce one of: PASS, FAIL, EXCEPTION-REQUESTED, or NOT-APPLICABLE. A failed mandatory policy check must block downstream workflow progression. A policy exception must require explicit human approval. Every exception must record: applicable policy, reason, scope, approving authority, compensating control, approval timestamp, and expiry/review condition. Changes to approved requirements, architecture, schemas, workflow states, security controls, or release criteria must pass through formal impact analysis and change approval. Release readiness must fail if a mandatory compliance or change-control policy remains violated or has an unapproved exception. Policy outcomes and exceptions must be included in audit and traceability evidence.

### VII. Architecture and Maintainability

Separate domain logic, API delivery, persistence, orchestration, policy enforcement, telemetry, and infrastructure concerns. Prefer explicit interfaces for external dependencies. Record material architectural decisions and rejected alternatives. Avoid complexity that cannot be justified by requirements or demonstrability. Keep code modular, readable, testable, and replaceable.

### VIII. Reliability and Recovery

Classify transient and permanent failures. Use bounded retries where appropriate. Define backoff and timeout behavior. Apply idempotency to repeatable operations. Define fallback behavior. Distinguish rollback from compensation. Define safe-stop conditions. Preserve deterministic terminal outcomes. Support controlled resumption after interruption. Capture evidence of success, failure, retry, compensation, recovery, and latency.

### IX. Observability and Auditability

Assign a correlation or run identifier to each orchestration execution. Record state transitions, decisions, approvals, retries, failures, replanning events, and terminal outcomes. Audit evidence must include actor type, action, timestamp, affected artifact or state, result, and reason. Logs, metrics, traces, and workflow history must support reconstruction of an execution. Demonstration metrics must be clearly distinguished from production measurements.

### X. Traceability and Repository Integrity

Maintain traceability across requirement, scenario, decision, design, task, implementation, test, validation, documentation, and evidence. Use small, logically coherent commits. Commit messages must describe engineering intent. Do not fabricate approval, test, execution, or operational evidence. AI-generated artifacts require human review and ownership. Documentation must evolve with implementation.

### XI. Evidence-Based Completion

A feature or task is complete only when: (1) applicable requirements are identified; (2) decisions and assumptions are recorded; (3) acceptance criteria are satisfied; (4) required tests have been executed successfully; (5) security and reliability checks are complete; (6) documentation is current; (7) traceability is complete; (8) residual risks and limitations are disclosed; (9) required approval is recorded; (10) evidence is available for reviewer verification.

## Governance Requirements

### How constitutional compliance is assessed during planning

Every `/speckit-plan` and ADR-generation pass must explicitly cross-check proposed designs against each of the eleven principles above. `/speckit-analyze` performs the formal, read-only compliance pass before implementation begins, classifying any conflict as CRITICAL, HIGH, MEDIUM, or LOW. CRITICAL and HIGH findings block progression to `/speckit-implement` until resolved at their upstream source.

### How exceptions are proposed and approved

An exception to a non-negotiable principle, or to a mandatory compliance/change-control policy, must be proposed in writing (ADR or policy-exception record) stating: the principle or policy affected, the reason, the scope, the proposed compensating control, and an expiry or review condition. The human candidate (acting as approving authority) must explicitly approve the exception before it takes effect. No exception may be inferred from silence or self-approved by the AI assistant.

### Which principles cannot be waived

Principle III (Human Governance) and Principle X (Traceability and Repository Integrity) — specifically the prohibition on fabricated evidence and the requirement for human-owned approval — cannot be waived under any circumstance for this assessment. All other principles may be subject to a documented, human-approved exception with compensating controls.

### How amendments are versioned

This constitution follows semantic versioning (MAJOR.MINOR.PATCH):
- **MAJOR** — removal or redefinition of a non-negotiable principle, or a backward-incompatible governance change.
- **MINOR** — addition of a new principle or materially expanded governance section.
- **PATCH** — clarification, wording fix, or non-semantic correction.

Every amendment must be committed with a conventional commit message prefixed `docs(governance):` and must update the version/ratification footer below.

### How conflicts between principles are resolved

Where two principles appear to conflict in a specific design (e.g., Reliability's bounded-retry guidance vs. a Security control), the conflict is resolved by: (1) identifying the governing requirement or assignment constraint that motivates the decision; (2) documenting both options and the trade-off in an ADR; (3) requiring explicit human approval of the resolution. Human Governance (Principle III) and Evidence-Based Completion (Principle XI) take precedence over convenience or velocity in all cases.

### How non-compliance blocks release readiness

`/speckit-converge` must verify, for every mandatory compliance and change-control policy, that: the policy version evaluated is recorded; the policy outcome is PASS, FAIL, EXCEPTION-REQUESTED (with recorded human approval), or NOT-APPLICABLE; and no unresolved mandatory FAIL remains. Release readiness may only return `READY` or `READY WITH ACCEPTED LIMITATIONS` when every mandatory policy and principle either passes or carries an explicit, human-approved, time-bounded exception. A single unresolved mandatory failure forces `NOT READY`.

### Initial constitution version

This constitution is ratified at **version 1.0.0** as the governing baseline for the assessment. It may only be amended through an explicit, human-approved commit following the versioning rules above.

## Governance

This constitution supersedes all other practices, prompts, and informal conversation for this repository. Where instructions conflict, use this precedence: (1) official assessment requirements, (2) this approved constitution, (3) approved feature specification and clarifications, (4) approved technical plan and contracts, (5) approved Architecture Decision Records, (6) the SpecKit-generated task plan, (7) current implementation, (8) informal conversation. AI-generated artifacts require human review and explicit human ownership before being treated as approved. Complexity must be justified against an approved requirement or demonstrability need — SpecKit artifacts under `specs/`, `docs/adr/`, and `docs/governance/` are the authoritative reference for all contributors, human and AI.

**Version**: 1.0.0 | **Ratified**: 2026-10-12 | **Last Amended**: 2026-10-12
