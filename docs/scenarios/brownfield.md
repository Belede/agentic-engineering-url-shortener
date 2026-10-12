# Scenario B: Brownfield — Optional `max_clicks` Limit

## Requirement Input

> "Add an optional click limit to existing links; once reached, further redirects return 410 LINK_EXHAUSTED." (CL-02, recorded 2026-10-12.)

## Impact Analysis (Before Any Code Change)

Full analysis performed against the real repository state — see `docs/scenarios/brownfield-impact-analysis.md`, committed in commit `06524b2` **before** migration 0002 or any code change. Identified: one new nullable column, one new atomic repository function, one new redirect-handler branch, no orchestration-plane impact, and the concurrency risk that drove the dedicated test below.

## Migration

`src/shortener/migrations/0002_max_clicks.sql` — adds `short_links.max_clicks` (nullable INTEGER). Reversible: `0002_max_clicks.down.sql` uses SQLite 3.35+'s native `DROP COLUMN`. Up/down/up cycle verified with existing-row preservation (`tests/e2e/test_scenario_brownfield.py::test_0002_up_down_up_cycle_preserves_existing_rows`).

## Design

- Atomic conditional `UPDATE short_links SET click_count = click_count + 1 WHERE code = ? AND (max_clicks IS NULL OR click_count < max_clicks)` is the concurrency-safety mechanism — the database's own atomicity, not an application lock (same pattern as ADR-003's short-code collision handling).
- Expiry is checked **before** exhaustion (an expired link reports `LINK_EXPIRED`, not `LINK_EXHAUSTED`, even if also at its click limit).
- `410` responses for both expiry and exhaustion now carry a structured `{"error", "message"}` body matching `contracts/openapi.yaml`'s `ErrorResponse` — a contract-fidelity fix made while touching this handler (previously used FastAPI's default `{"detail": ...}` wrapper, inconsistent with the documented schema).

## Human Approval

`ARCH_APPROVAL` (migration-aware): approved by Belede Rahul.

## Implementation

- `src/shortener/persistence/links_repository.py::try_increment_click_count()` — the atomic check.
- `src/shortener/api/redirect.py` — now checks exhaustion after expiry, before recording the `resolved` analytics event.
- `src/shortener/api/links.py` — `CreateLinkRequest`/`BatchItem` gain optional `max_clicks`.

## Testing

- Migration up/down/up with existing-row preservation.
- **Regression**: links without `max_clicks` behave exactly as before (`test_link_without_max_clicks_is_unaffected_regression`) — all pre-existing `test_redirect.py` and `test_analytics_concurrency.py` tests pass unmodified.
- **Concurrency** (the impact analysis's named risk, directly addressed): 20 parallel requests against a `max_clicks=5` link yield exactly 5 successes and 15 `LINK_EXHAUSTED` — verified, not assumed (`test_concurrent_redirects_never_exceed_max_clicks`).
- **Orchestration run** (added during `/speckit-converge` — see `docs/assessment/post-implementation-analysis.md`): `test_brownfield_change_runs_through_impact_analysis_gated_orchestration` drives this change through the real engine end-to-end, referencing the committed impact-analysis artifact at the `DESIGN` step, with a real human `ARCH_APPROVAL`, through to `TEST`/`DOCUMENT`, parked at `RELEASE_APPROVAL`.

## Release

Contract bumped `1.1.0 → 1.2.0` (additive, backward-compatible).

## Reviewer Verification

```bash
pytest tests/e2e/test_scenario_brownfield.py -v
```
Expected: 6 passed, including the concurrency test and the full orchestration-run trace. Inspect commit `06524b2` to confirm the impact analysis predates commit containing migration 0002.
