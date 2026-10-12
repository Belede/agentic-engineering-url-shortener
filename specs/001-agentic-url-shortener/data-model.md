# Data Model

Versioned alongside `contracts/openapi.yaml`. Schema version tracks the SQLite migration number; contract version tracks the API's semver (ADR-002, ADR-004).

## Application Plane

### `short_links`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `code` | TEXT | PRIMARY KEY | base62, 7 chars (ADR-003) |
| `target_url` | TEXT | NOT NULL | validated scheme + SSRF-blocked (NFR-001, CL-05) |
| `created_by` | TEXT | NOT NULL, FK→`api_keys.key_id` | attribution only (CL-06) |
| `created_at` | TEXT (ISO8601) | NOT NULL | |
| `expires_at` | TEXT (ISO8601) | NULLABLE | null = permanent. CL-07's "no default expiry" baseline was superseded by CL-03's resolution (ambiguous scenario, v1.3.0): new links now default to `SHORTENER_DEFAULT_TTL_DAYS` (90 days) unless `no_expiry=true` or an explicit `expires_at`/`ttl_seconds` is given — existing links already in the database are never retroactively affected, since this default is applied only at creation time. |
| `max_clicks` | INTEGER | NULLABLE | added by migration 0002 (CL-02, brownfield) |
| `click_count` | INTEGER | NOT NULL DEFAULT 0 | atomically incremented on redirect when `max_clicks` is set |
| `status` | TEXT | NOT NULL DEFAULT 'active' | `active` \| `exhausted` |

### `redirect_events`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | |
| `code` | TEXT | NOT NULL, FK→`short_links.code` | |
| `occurred_at` | TEXT (ISO8601) | NOT NULL | |
| `outcome` | TEXT | NOT NULL | `resolved` \| `expired` \| `exhausted` \| `not_found` |

### `api_keys`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `key_id` | TEXT | PRIMARY KEY | the `X-API-Key` value (prototype: pre-seeded, not self-service) |
| `label` | TEXT | NOT NULL | human-readable caller label |
| `created_at` | TEXT (ISO8601) | NOT NULL | |

### `idempotency_keys`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `key` | TEXT | PRIMARY KEY (composite w/ `caller_id`) | client-supplied `Idempotency-Key` (CL-04) |
| `caller_id` | TEXT | NOT NULL, FK→`api_keys.key_id` | |
| `result_code` | TEXT | NOT NULL | the `short_links.code` originally created |
| `created_at` | TEXT (ISO8601) | NOT NULL | retention window enforced by application logic, not a DB TTL (documented limitation) |

## Orchestration / Control Plane

### `workflow_runs`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `run_id` | TEXT | PRIMARY KEY | UUID, the correlation id (FR-025) |
| `requirement_input` | TEXT | NOT NULL | original raw requirement text |
| `scenario_type` | TEXT | NOT NULL | `greenfield` \| `brownfield` \| `ambiguous` \| `fault_injection` |
| `current_state` | TEXT | NOT NULL | current node name (plan.md §3) |
| `policy_pack_version` | TEXT | NOT NULL | e.g. `1.0.0` (FR-027) |
| `terminal_status` | TEXT | NULLABLE | `DONE` \| `SAFE_STOP` \| `REJECTED`, null while in progress |
| `created_at` | TEXT (ISO8601) | NOT NULL | |
| `updated_at` | TEXT (ISO8601) | NOT NULL | |

### `state_transitions`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | |
| `run_id` | TEXT | NOT NULL, FK→`workflow_runs.run_id` | |
| `from_state` | TEXT | NULLABLE | null for the initial transition |
| `to_state` | TEXT | NOT NULL | |
| `actor` | TEXT | NOT NULL | `system` \| a human identifier |
| `reason` | TEXT | NOT NULL | |
| `occurred_at` | TEXT (ISO8601) | NOT NULL | |

### `decisions`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | |
| `run_id` | TEXT | NOT NULL, FK→`workflow_runs.run_id` | |
| `decision_type` | TEXT | NOT NULL | `assumption` \| `clarification` \| `replan` |
| `content` | TEXT | NOT NULL | |
| `source_reference` | TEXT | NULLABLE | e.g. `CL-03`, an ADR id |
| `recorded_at` | TEXT (ISO8601) | NOT NULL | |

### `approval_records`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | |
| `run_id` | TEXT | NOT NULL, FK→`workflow_runs.run_id` | |
| `gate` | TEXT | NOT NULL | `ARCH_APPROVAL` \| `SECURITY_APPROVAL` \| `CLARIFY` \| `RELEASE_APPROVAL` |
| `decision` | TEXT | NOT NULL | `approved` \| `rejected` |
| `decided_by` | TEXT | NOT NULL | human identifier (ADR-005) |
| `rationale` | TEXT | NOT NULL | |
| `decided_at` | TEXT (ISO8601) | NOT NULL | |

### `policy_evaluations`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | |
| `run_id` | TEXT | NOT NULL, FK→`workflow_runs.run_id` | |
| `policy_id` | TEXT | NOT NULL | |
| `policy_version` | TEXT | NOT NULL | |
| `outcome` | TEXT | NOT NULL | `PASS` \| `FAIL` \| `EXCEPTION-REQUESTED` \| `NOT-APPLICABLE` |
| `exception_reference` | TEXT | NULLABLE | FK→`policy_exceptions.id` when applicable |
| `evaluated_at` | TEXT (ISO8601) | NOT NULL | |

### `policy_exceptions`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | |
| `policy_id` | TEXT | NOT NULL | |
| `reason` | TEXT | NOT NULL | |
| `scope` | TEXT | NOT NULL | |
| `approving_authority` | TEXT | NOT NULL | |
| `compensating_control` | TEXT | NOT NULL | |
| `approved_at` | TEXT (ISO8601) | NOT NULL | |
| `expires_at` | TEXT (ISO8601) | NOT NULL | |

### `audit_events` (append-only)

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | |
| `run_id` | TEXT | NULLABLE | null only for non-run-scoped system events, if any |
| `actor_type` | TEXT | NOT NULL | `system` \| `human` |
| `action` | TEXT | NOT NULL | |
| `occurred_at` | TEXT (ISO8601) | NOT NULL | |
| `affected_artifact` | TEXT | NOT NULL | |
| `result` | TEXT | NOT NULL | |
| `reason` | TEXT | NOT NULL | |

No application code path issues `UPDATE`/`DELETE` against `audit_events` (ADR-008) — enforced by review, not a DB trigger, for this prototype scope (documented limitation).

## Compatibility and Migration Rules

- Migration 0001 establishes the baseline schema above (minus `max_clicks`).
- Migration 0002 (brownfield scenario, CL-02) adds `short_links.max_clicks` as a nullable column with a reversible down script that drops it — existing rows are unaffected (all existing links keep `max_clicks = NULL`, i.e., unlimited, preserving current behavior for pre-existing links).
- No migration changes an existing column's type or drops a non-null constraint without a corresponding ADR and `ARCH_APPROVAL`.

## Representative Examples

```json
// POST /api/v1/links request
{ "target_url": "https://example.com/very/long/path", "ttl_seconds": 86400 }

// 201 response
{ "code": "aZ3kLq9", "short_url": "https://short.local/aZ3kLq9", "target_url": "https://example.com/very/long/path", "expires_at": "2026-10-13T12:00:00Z" }

// 400 response (invalid scheme)
{ "error": "INVALID_SCHEME", "message": "Only http/https URLs are accepted." }

// 410 response (link exhausted, post-brownfield)
{ "error": "LINK_EXHAUSTED", "message": "This link has reached its maximum number of redirects." }
```

Executable contract validation lives in `tests/contract/`, generated against `contracts/openapi.yaml`.
