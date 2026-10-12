# ADR-010: Deployment and Local Execution Model

## Status

Accepted — approved by human candidate (Belede Rahul), 2026-10-12

## Context

The assignment requires a "working prototype (runnable end-to-end)" and setup instructions, reviewed within a timeboxed assessment. No deployment target (cloud, specific host) is specified.

## Decision Drivers

- Reviewer must be able to run the whole system in well under SC-001's 2-minute target from a clean clone
- No cloud account, credentials, or paid service should be required to evaluate the submission
- Must distinguish "production-grade discipline" from "production-scale infrastructure" per the Planning Constraints

## Options Considered

### Option 1: Local execution via `uvicorn` + a Python virtual environment, documented in `quickstart.md`

- Advantages: zero cost, zero external account, works offline (deterministic mode); matches the assignment's "working prototype" bar without implying unnecessary cloud spend or credential sharing
- Disadvantages: not a "real" deployed service — acceptable and explicitly scoped as a prototype, not a production deployment
- Risks: none material
- Implementation impact: low
- Assessment implications: reviewer runs it in minutes with no account setup

### Option 2: Containerized (Docker) local execution

- Advantages: more deployment-realistic, isolates dependencies
- Disadvantages: adds a Docker prerequisite for the reviewer; marginal benefit over a Python venv for a single-service prototype
- Risks: minor setup friction
- Implementation impact: low-medium (an optional `Dockerfile` can still be provided as a convenience, not a requirement)
- Assessment implications: neutral-to-positive if offered as an *additional* option alongside Option 1, not a replacement

### Option 3: Deployed to a public cloud endpoint for review

- Advantages: reviewer needs zero local setup at all
- Disadvantages: introduces cost, credential/secret management, and availability risk entirely outside the assignment's explicit scope; the assignment explicitly does not require this
- Risks: cost and security exposure disproportionate to benefit
- Implementation impact: high
- Assessment implications: not requested by the assignment; would be scope creep

## Decision

Adopt **Option 1** as the primary, required path (`quickstart.md`), with an optional `Dockerfile`/`docker-compose.yml` (Option 2) offered as a convenience if time permits within the timebox — not a required deliverable.

## Rationale

Directly serves SC-001 and the Planning Constraints' instruction to distinguish production-grade discipline from production-scale infrastructure; avoids disproportionate cost/credential risk for no assessment benefit.

## Consequences

- **Positive**: fastest possible reviewer path to a running system.
- **Negative**: no hosted demo link — acceptable, as the assignment asks for a runnable prototype, not a hosted one.
- **Operational**: none — the reviewer runs and stops the process themselves.
- **Testing**: the quickstart path itself is a tested deliverable — validated by running it from a genuinely clean clone before submission (Final Step-by-Step Execution Sequence, step 61).
- **Governance**: no deployment-pipeline policy needed for this scope.

## Risks and Mitigations

- Risk: environment drift (reviewer's Python version differs). Mitigation: `quickstart.md` pins a minimum Python version and uses `uv`/`venv` with a lockfile-equivalent (`requirements.txt` or `pyproject.toml` with pinned versions).

## Reversibility

High — adding a hosted or containerized deployment later does not require changing application code.

## Traceability

- Requirements: SC-001; Deliverables (Setup instructions)
- Spec sections: Success Criteria
- Plan sections: §1, §14
- Expected tasks: setup-and-quick-start task group

## Validation

Validated by: a literal clean-clone run-through performed before final submission (Final Step-by-Step Execution Sequence, step 61), with the observed result recorded in the reviewer navigation guide.
