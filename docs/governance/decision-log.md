# Human Decision Log

Append-only record of every explicit human decision made by the candidate (Belede Rahul) during this assessment's execution, outside of the application's own `approval_records`/`decisions` tables (which track decisions *within* orchestration runs once the system exists). This log tracks the meta-level SpecKit lifecycle gates.

| # | Date | Gate | Decision |
|---|---|---|---|
| 1 | 2026-10-12 | Pre-spec stack direction | Python + FastAPI + SQLite |
| 2 | 2026-10-12 | Pre-spec agent mode | Deterministic, with optional real-LLM plug-in |
| 3 | 2026-10-12 | Human Gate 1 (Constitution) | Self-verified against required coverage list; no changes requested |
| 4 | 2026-10-12 | Human Gate 2 (Specification) | Self-verified against rejection criteria; no changes requested |
| 5 | 2026-10-12 | Human Gate 3 (Clarify) — CL-01 | Greenfield = batch link creation |
| 6 | 2026-10-12 | Human Gate 3 (Clarify) — CL-02 | Brownfield = optional `max_clicks` limit |
| 7 | 2026-10-12 | Human Gate 3 (Clarify) — CL-03 | Ambiguous text = vague+contradictory expiry statement |
| 8 | 2026-10-12 | Human Gate 3 (Clarify) — CL-04 | Idempotency = client-supplied `Idempotency-Key` header |
| 9 | 2026-10-12 | Human Gate 3 (Clarify) — CL-05 | Block SSRF-style private/loopback redirect targets |
| 10 | 2026-10-12 | Human Gate 3 (Clarify) — CL-06 | No login system; static `X-API-Key` for attribution only |
| 11 | 2026-10-12 | Human Gate 3 (Clarify) — CL-07 | No default link expiry |
| 12 | 2026-10-12 | Human Gate 3 (Clarify) — CL-08 | Rate limit: 60 create-requests/min per API key |
| 13 | 2026-10-12 | Human Gate 3 (Clarify) — CL-09 | Approve NFR-007 as a non-binding demonstration performance target |
| 14 | 2026-10-12 | Human Gate 4 (ADRs) | All 11 ADRs accepted as proposed |
| 15 | 2026-10-12 | Pre-code gate | Task plan (52 tasks) and independent review's 4 conditions approved; implementation authorized to begin |

| 16 | 2026-10-12 | Ambiguous scenario (CL-03) — CLARIFY answer | "New links only" — new links get a default expiry; already-shared links never retroactively affected |
| 17 | 2026-10-12 | Ambiguous scenario — ARCH_APPROVAL | Approved: `SHORTENER_DEFAULT_TTL_DAYS` (default 90, max 365), new-links-only, `no_expiry` opt-out |
| 18 | 2026-10-12 | Ambiguous scenario — SECURITY_APPROVAL | Approved: config.py change validated (bounded TTL, no secret exposure) |

Subsequent entries will record: the final combined release-readiness decision for all three scenarios (Phase 5).
