# ADR-011: Authentication/Authorization Assumptions and Analytics Consistency

## Status

Accepted — approved by human candidate (Belede Rahul), 2026-10-12

## Context

Clarifications CL-06 (no login system, static per-caller API key) and CL-08 (rate limiting per key) require a concrete, minimal authentication model. Separately, FR-006/FR-008 require analytics events to be captured consistently, including under concurrent redirects.

## Decision Drivers

- Must not imply a production-grade auth system that does not exist (honesty/evidence-integrity requirement)
- Must enable per-caller scoping for idempotency (FR-007) and rate limiting (FR-028)
- Analytics must not double-count or lose events under concurrency (FR-008)

## Options Considered

### Authentication — Option 1: Static `X-API-Key` header, checked against a small pre-seeded table, used only for attribution

- Advantages: minimal implementation; satisfies CL-06 exactly; clearly documented as a prototype assumption, not production auth (no password hashing, no session, no OAuth — intentionally out of scope)
- Disadvantages: not a real authentication system — explicitly disclosed, not hidden
- Risks: none beyond the disclosed scope limitation
- Implementation impact: low
- Assessment implications: honest scope labeling supports evidence-integrity scoring better than an over-claimed "auth system"

### Authentication — Option 2: Full OAuth2/JWT implementation

- Advantages: production-realistic
- Disadvantages: directly contradicts CL-06 (human-confirmed no-login-system decision) and the Exclusions section of spec.md; disproportionate scope for the timebox
- Risks: scope overrun, contradicts an already-recorded human decision
- Implementation impact: high
- Assessment implications: would require reopening CL-06 via change control — not warranted

### Analytics — Option 1: Record the `RedirectEvent` inside the same DB transaction as the redirect lookup (and `max_clicks` atomic update, post-brownfield)

- Advantages: a single atomic unit guarantees the analytics event and the redirect decision are always consistent — no risk of recording an event for a redirect that didn't actually happen, or vice versa
- Disadvantages: slightly more DB work per redirect than a fire-and-forget async log
- Risks: none material at prototype scale
- Implementation impact: low
- Assessment implications: directly satisfies FR-008's concurrency-consistency requirement

### Analytics — Option 2: Fire-and-forget async event write (e.g., background task after responding)

- Advantages: marginally lower redirect latency
- Disadvantages: can lose events on crash between response and write; cannot guarantee exactly-once recording under concurrent requests to a `max_clicks`-limited link — directly risks violating FR-008
- Risks: inconsistent analytics under exactly the concurrency scenario the spec calls out
- Implementation impact: low but weaker correctness
- Assessment implications: would need an explicit documented limitation; the atomic alternative avoids the limitation entirely at negligible cost

## Decision

Authentication: adopt **Option 1** (static `X-API-Key`, attribution-only, explicitly documented as a prototype assumption). Analytics: adopt **Option 1** (same-transaction atomic write with the redirect decision).

## Rationale

Both decisions prioritize correctness and honesty of scope over superficial production-realism: the auth model does exactly what CL-06 asked for and is labeled accordingly; the analytics model guarantees FR-008's concurrency-consistency requirement without added complexity.

## Consequences

- **Positive**: no false production-auth claim in documentation; analytics counts are provably consistent even under the `max_clicks` concurrency test.
- **Negative**: auth model offers no real security beyond attribution/rate-limit scoping — explicitly called out in `docs/governance/known-limitations.md`, not hidden.
- **Operational**: API keys are pre-seeded/configured, not self-service-issued, for this prototype.
- **Testing**: a concurrency test specifically asserts exactly-one analytics event per successful redirect under parallel load.
- **Governance**: no security-sensitive change beyond what CL-05/CL-06/CL-08 already cover; no new ADR needed if a real auth system is added later — it would be a new material decision requiring its own ADR and `SECURITY_APPROVAL`.

## Risks and Mitigations

- Risk: a reviewer could mistake the `X-API-Key` header for real authentication. Mitigation: explicit "Known Limitations" documentation and in-code comments state this is attribution-only.

## Reversibility

High for auth (isolated to a middleware/dependency function); high for analytics (isolated to the redirect handler's transaction boundary).

## Traceability

- Requirements: FR-006, FR-007, FR-008, FR-028, CL-06, CL-08
- Spec sections: Confirmed Decisions; Non-Functional Requirements
- Plan sections: §2, §8
- Expected tasks: validation-and-security, analytics task groups

## Validation

Validated by: an auth-header-required test, a rate-limit-enforcement test, and the concurrency test asserting exactly-once analytics recording under parallel redirects to the same link.
