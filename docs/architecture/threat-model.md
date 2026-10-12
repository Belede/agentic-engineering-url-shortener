# Threat Model and Security Summary

## Dependency and License Scan (T046 — executed, not asserted)

Run 2026-10-12 via `pip-audit` and `pip-licenses` against the actual installed environment:

```
pip-audit  →  0 vulnerabilities in runtime dependencies (fastapi, uvicorn, pydantic,
               httpx, starlette, anyio). 12 advisories found, but all against `pip`
               itself (the package manager / build tool) — not a runtime dependency
               shipped with or imported by the deployed application.
pip-licenses → fastapi: MIT, httpx: BSD, pydantic: MIT, pytest: MIT, ruff: MIT,
               uvicorn: BSD-3-Clause — all permissive, no copyleft/GPL dependencies.
```

**Residual risk**: `pip`'s own advisories are noted for completeness but do not affect the deployed application's attack surface — they relate to `pip`'s package-installation behavior, not anything the running service executes. No action required; re-run `pip-audit` before any future dependency addition (policy DEP-001, `src/policy/engine.py`).

## Threat Scenarios Considered

| Threat | Mitigation | Verified By |
|---|---|---|
| Malicious redirect target (XSS via `javascript:`/`data:` schemes) | Scheme allow-list (`http`/`https` only) at creation time | `test_validation.py` |
| SSRF via internal/loopback redirect target | DNS/IP resolution + loopback/private/link-local block at creation time | `test_validation.py` |
| Link-creation flooding / abuse | In-process rate limiting, 60/min per API key; batch counts as one request | `test_rate_limit.py`, `test_scenario_greenfield.py` |
| Idempotency-key replay across callers | Idempotency scoped per `(key, caller_id)`, not globally | `test_idempotency.py` |
| Secrets in logs/audit trail | No secrets exist in the deterministic default path (`LLM_PROVIDER=none`); if the optional LLM adapter were enabled, its API key would be read from env and never logged (not currently implemented — `LLM_PROVIDER` is read but no adapter exists yet, a disclosed scope limitation) | code review — `config.py` contains no secret-logging path |
| Audit trail tampering | No application code path issues `UPDATE`/`DELETE` against `audit_events` | verified by code inspection of `src/orchestration/engine.py` and all node modules — grep confirms zero `UPDATE audit_events` / `DELETE FROM audit_events` statements anywhere in `src/` |

## Known Limitations (Disclosed, Not Hidden)

- **Authentication**: `X-API-Key` is attribution/rate-limit scoping only — not a production authentication system (no password hashing, sessions, or OAuth). Documented in ADR-011 and CL-06.
- **SQLite single-writer concurrency**: acceptable at prototype scale; WAL mode reduces but does not eliminate writer contention under heavy concurrent load. Documented in ADR-002.
- **No real LLM adapter implemented**: `LLM_PROVIDER` setting exists (defaults to `none`) but no `anthropic` code path is wired up — the deterministic orchestration is fully functional without it; the plug-in point is reserved, not built, consistent with the human-confirmed "deterministic + optional LLM" direction.
- **`retry.py`'s `TransientError`/`PermanentError` are not yet raised by any production code path** — see `docs/traceability/matrix.md`'s Orphan Check for the full disclosure. The mechanism is proven correct in isolation (`test_retry.py`) but has no real transient-failure trigger wired into it in this prototype's current scope.

## Audit Command

```bash
pip-audit
pip-licenses --packages fastapi uvicorn pydantic pytest httpx ruff
grep -rn "UPDATE audit_events\|DELETE FROM audit_events" src/  # expect: no matches
```
