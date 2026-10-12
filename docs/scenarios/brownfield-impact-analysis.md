# Scenario B: Brownfield Impact Analysis — Optional `max_clicks` Limit

**Status**: Written and committed BEFORE any code change for this scenario (per the guide's Brownfield Impact Analysis Gate — no code changes may precede this document).

## Requirement Input

> "Add an optional click limit to existing links; once reached, further redirects return 410 LINK_EXHAUSTED." (CL-02, recorded 2026-10-12.)

## Current Behavior (inspected directly against the real repository at commit `4e5d1b9`)

- `src/shortener/persistence/links_repository.py`: the `ShortLink` dataclass already declares a speculative `max_clicks: int | None = None` field (added early, during T012, as a forward-looking placeholder), but:
  - the baseline schema (`src/shortener/migrations/0001_baseline.sql`) has **no `max_clicks` column** — only `click_count INTEGER NOT NULL DEFAULT 0`, which exists but is never read or written anywhere yet.
  - `get_link()`'s `SELECT` does not select `max_clicks` or `click_count` at all.
- `src/shortener/api/redirect.py`: `redirect()` checks only expiry (`_is_expired`). There is no click-count check, no `410 LINK_EXHAUSTED` path, and no logic that increments any counter.
- `contracts/openapi.yaml` (v1.1.0): `CreateLinkRequest` has no `max_clicks` field; no `410` response is documented for `GET /{code}` beyond the existing expiry case.
- `data-model.md` already documents `max_clicks` as a column "added by migration 0002 (CL-02, brownfield)" — i.e., the data model was pre-planned for this change but not yet implemented.

## Requested Behavior

- Caller may optionally set `max_clicks` on link creation.
- Once a link's redirect count reaches `max_clicks`, further redirect attempts return `410 LINK_EXHAUSTED` instead of resolving.
- Existing links (created before this change) must be unaffected — they have no `max_clicks` and remain unlimited.
- Counting must be correct under concurrent redirects to the same link (no link exceeds its limit due to a race).

## Impacted Modules

| Module | Impact |
|---|---|
| `src/shortener/migrations/` | New migration `0002_max_clicks.sql` — add `max_clicks INTEGER` (nullable) to `short_links`. `click_count` already exists from migration 0001 and will now actually be used. Reversible (`0002_max_clicks.down.sql` drops the column). |
| `src/shortener/persistence/links_repository.py` | `get_link()` SELECT must add `max_clicks`; `create_link()` must accept and persist `max_clicks`; new function needed for an **atomic conditional UPDATE** that increments `click_count` only if `click_count < max_clicks` (or `max_clicks IS NULL`), returning whether the increment succeeded — this is the concurrency-safety mechanism, not an application-level lock. |
| `src/shortener/api/redirect.py` | Must call the new atomic check before issuing the redirect; return `410 LINK_EXHAUSTED` (distinct error code from the existing expiry `410`) when exhausted. |
| `src/shortener/api/links.py` | `CreateLinkRequest`/`BatchItem` gain an optional `max_clicks` field; `_to_response` and batch result shaping need no change (not returned in create response per current design — reviewable at `ARCH_APPROVAL`). |
| `contracts/openapi.yaml` | `CreateLinkRequest.max_clicks` (optional integer); new `410` response variant documented for `GET /{code}`. No major version bump — additive, backward-compatible (minor bump 1.1.0 → 1.2.0 is sufficient, confirmed at `ARCH_APPROVAL`). |
| `data-model.md` | Already anticipated this column; update to reflect the actual migration number and confirm no other drift. |

## Impacted Interfaces / API Contracts

- `POST /api/v1/links` and `POST /api/v1/links/batch`: new optional request field `max_clicks`.
- `GET /{code}`: new possible `410` outcome (`LINK_EXHAUSTED`), distinguishable from the existing expiry `410` by response body `error` field.

## Impacted Domain Rules

- Redirect resolution gains a second gating condition (expiry, then exhaustion) — order matters for which error a caller sees if both apply (design decision: check expiry first, since an expired link is a stronger/prior-in-time condition; to be confirmed at `ARCH_APPROVAL`).

## Impacted Persistence

- One new nullable column; existing rows get `NULL` (unlimited) by default — zero data migration needed beyond the `ALTER TABLE`.
- `click_count` (already present but dormant since migration 0001) becomes load-bearing.

## Impacted Orchestration States

- None. This is a pure application-plane change; no orchestration schema or node logic is affected (confirms ADR-001's plane-separation boundary holds for a real brownfield change, not just greenfield).

## Impacted Telemetry

- `redirect_events.outcome` gains a new possible value: `"exhausted"` (alongside existing `resolved`/`expired`/`not_found`).

## Impacted Documentation

- `contracts/openapi.yaml`, `data-model.md`, this impact analysis, and `docs/scenarios/brownfield.md` (evidence doc, written after implementation).

## Direct Tests Required

- Migration 0002 up/down/up cycle (mirrors the existing `test_baseline_migration.py` pattern).
- Atomic click-counting concurrency test: N parallel redirects against a link with `max_clicks = K` (K < N) must result in exactly K successful `302`s and the rest `410 LINK_EXHAUSTED` — no link ever exceeds its limit.
- `410 LINK_EXHAUSTED` returned once the limit is reached on a subsequent (non-concurrent) request.
- Link with no `max_clicks` set continues to redirect unlimited times (regression).

## Regression Tests

- All existing `tests/contract/test_redirect.py` and `tests/integration/test_analytics_concurrency.py` tests must continue to pass unmodified — they exercise links with `max_clicks = NULL`, which must behave exactly as before.

## Security Risks

- None material. `max_clicks` is caller-supplied but bounded by normal integer validation (positive integer); no new attack surface beyond standard input validation already in place.

## Reliability Risks

- The core risk is a race condition in counting under concurrent redirects. Mitigated by using a single atomic `UPDATE ... WHERE click_count < max_clicks` (or `max_clicks IS NULL`) statement — the database's own atomicity guarantees correctness, not application-level locking (consistent with ADR-003's approach to short-code uniqueness).

## Data Compatibility Risks

- None. Nullable column, default `NULL`, fully backward-compatible. No backfill needed.

## Rollback / Compensation Implications

- **Rollback is feasible** for this change up until the migration has been applied somewhere outside the sandbox (per ADR-006's `applied_externally` predicate) — the down script is tested as part of the up/down/up cycle before this is considered "applied externally" anywhere.
- If the migration were already applied to a shared environment before a defect was found, compensation (not rollback) would apply instead — not expected in this single-environment prototype, but the mechanism exists (`src/orchestration/reliability/compensation.py`) should the brownfield scenario's own orchestration run need to demonstrate it.

## Architectural Decisions Affected

- None new. This change operates entirely within ADR-002 (persistence strategy: SQLite, explicit migrations) and ADR-003's precedent (atomic DB-level operation for concurrency safety) — no new ADR required, confirmed at `ARCH_APPROVAL` rather than a separate ADR gate.

## Downstream Tasks Requiring Replanning

- None outside this scenario's own task set (T039, T040). No other in-flight work depends on `short_links` schema shape.

---

## Change Impact Summary

Small, well-contained, additive change: one nullable column, one new atomic repository function, one new conditional branch in the redirect handler, one new contract field/response variant. No orchestration-plane impact. Primary engineering risk is the concurrency correctness of the click-counting update, directly addressed by a dedicated concurrency test before this scenario is considered complete.

## Human Approval Requirement

This impact analysis requires `ARCH_APPROVAL` (migration-aware) before `T039`/`T040` implementation begins — see `docs/governance/decision-log.md` for the recorded decision once given.
