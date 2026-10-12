# Research Notes

Material technology evaluation is formalized as ADRs (`docs/adr/ADR-001` through `ADR-011`), each with Options Considered, Decision, and Rationale — not duplicated here to avoid two sources of truth.

## Open questions resolved outside the ADR process

- **SQLite WAL mode**: enabled at connection setup (`PRAGMA journal_mode=WAL`) to reduce writer contention under the concurrency tests required by FR-008/FR-030, consistent with ADR-002's documented single-writer limitation.
- **Base62 alphabet**: `[0-9A-Za-z]`, excluding no characters (unlike some schemes that exclude visually-ambiguous characters like `0`/`O`) — acceptable because codes are copy-pasted/clicked, not manually transcribed, for this prototype's use case.
- **UUID version for `run_id`**: UUID4 (random), no need for UUID7/time-ordered ids at this scale; simplicity preferred per Planning Constraints.
