# ADR-003: Short-Code Generation and Collision Handling

## Status

Accepted — approved by human candidate (Belede Rahul), 2026-10-12

## Context

FR-003 requires guaranteed short-code uniqueness, including under concurrent creation (edge case in spec.md). FR-009 requires deterministic collision handling without unbounded retry.

## Decision Drivers

- Correctness under concurrency without a central lock service
- Short, URL-safe codes
- Bounded, deterministic collision handling

## Options Considered

### Option 1: Base62 random, 7 characters, DB unique constraint + bounded regeneration

- Advantages: ~3.5 trillion possible codes at 7 chars (62^7); collision probability negligible at prototype scale; DB unique constraint is the actual source of truth for concurrency safety (no application-level race); bounded regeneration (max 5 attempts) handles the astronomically rare collision deterministically
- Disadvantages: a failed insert (constraint violation) costs one wasted DB round-trip per collision (rare)
- Risks: none material
- Implementation impact: low
- Assessment implications: easy to test (force a collision by seeding a known code, then assert regeneration + eventual bounded failure)

### Option 2: Sequential ID + hash/encode

- Advantages: no collisions possible by construction
- Disadvantages: sequential IDs leak creation-order/volume information (minor info-disclosure concern); requires a central counter which becomes a concurrency bottleneck or needs its own atomic-increment design anyway
- Risks: information disclosure; counter contention
- Implementation impact: medium
- Assessment implications: more moving parts to explain for marginal benefit

### Option 3: UUID truncated to N characters

- Advantages: no central counter
- Disadvantages: higher collision probability per character than base62 random at equal length; less URL-friendly character set unless re-encoded (which reduces to Option 1 anyway)
- Risks: collision probability harder to reason about precisely
- Implementation impact: low
- Assessment implications: weaker story for "demonstrate engineering judgment" than an explicit base62 scheme

## Decision

Adopt **Option 1**: Base62 random, 7 characters, DB unique constraint as the concurrency-safety mechanism, bounded regeneration (max 5 attempts) on constraint violation, else `503 CODE_SPACE_EXHAUSTED`.

## Rationale

The DB unique constraint — not application-level locking — is what actually guarantees correctness under concurrent creation (FR-003, FR-008), which is simpler and more robust than trying to coordinate uniqueness in application code. Bounded regeneration satisfies FR-009's "no unbounded retry" requirement explicitly.

## Consequences

- **Positive**: concurrency-safe by construction via the database; simple to implement and test.
- **Negative**: a vanishingly rare but theoretically possible exhaustion path exists and must be handled (not ignored) — `503 CODE_SPACE_EXHAUSTED` after 5 attempts.
- **Operational**: no additional infrastructure.
- **Testing**: collision path is directly testable by pre-seeding a known code and asserting correct regeneration behavior.
- **Governance**: no policy implications.

## Risks and Mitigations

- Risk: a test or demo might never actually exercise the collision path naturally (62^7 space). Mitigation: a dedicated unit test seeds a forced collision to exercise the regeneration branch explicitly, rather than relying on luck.

## Reversibility

High — isolated to one function in `domain/shortcode.py`; changing the scheme later does not affect already-issued codes' validity.

## Traceability

- Requirements: FR-001, FR-003, FR-008, FR-009
- Spec sections: Functional Requirements — URL Shortener Domain; Edge Cases
- Plan sections: §2
- Expected tasks: url-shortening task group

## Validation

Validated by: unit tests for generation format, forced-collision regeneration test, and a concurrency test issuing parallel create requests and asserting all resulting codes are unique.
