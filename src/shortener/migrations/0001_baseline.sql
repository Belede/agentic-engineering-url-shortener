-- Migration 0001: baseline schema (ADR-002, ADR-004, ADR-008; data-model.md)

CREATE TABLE api_keys (
    key_id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE short_links (
    code TEXT PRIMARY KEY,
    target_url TEXT NOT NULL,
    created_by TEXT NOT NULL REFERENCES api_keys(key_id),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    expires_at TEXT,
    click_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active'
);

CREATE TABLE redirect_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL REFERENCES short_links(code),
    occurred_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    outcome TEXT NOT NULL
);
CREATE INDEX idx_redirect_events_code ON redirect_events(code);

CREATE TABLE idempotency_keys (
    key TEXT NOT NULL,
    caller_id TEXT NOT NULL REFERENCES api_keys(key_id),
    result_code TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    PRIMARY KEY (key, caller_id)
);

CREATE TABLE workflow_runs (
    run_id TEXT PRIMARY KEY,
    requirement_input TEXT NOT NULL,
    scenario_type TEXT NOT NULL,
    current_state TEXT NOT NULL,
    policy_pack_version TEXT NOT NULL,
    terminal_status TEXT,
    security_sensitive INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE state_transitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES workflow_runs(run_id),
    from_state TEXT,
    to_state TEXT NOT NULL,
    actor TEXT NOT NULL,
    reason TEXT NOT NULL,
    occurred_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX idx_state_transitions_run ON state_transitions(run_id);

CREATE TABLE decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES workflow_runs(run_id),
    decision_type TEXT NOT NULL,
    content TEXT NOT NULL,
    source_reference TEXT,
    recorded_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX idx_decisions_run ON decisions(run_id);

CREATE TABLE approval_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES workflow_runs(run_id),
    gate TEXT NOT NULL,
    decision TEXT NOT NULL,
    decided_by TEXT NOT NULL,
    rationale TEXT NOT NULL,
    decided_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX idx_approval_records_run ON approval_records(run_id);

CREATE TABLE policy_exceptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    policy_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    scope TEXT NOT NULL,
    approving_authority TEXT NOT NULL,
    compensating_control TEXT NOT NULL,
    approved_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    expires_at TEXT NOT NULL
);

CREATE TABLE policy_evaluations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES workflow_runs(run_id),
    policy_id TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    outcome TEXT NOT NULL,
    exception_reference INTEGER REFERENCES policy_exceptions(id),
    evaluated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX idx_policy_evaluations_run ON policy_evaluations(run_id);

CREATE TABLE audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT,
    actor_type TEXT NOT NULL,
    action TEXT NOT NULL,
    occurred_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    affected_artifact TEXT NOT NULL,
    result TEXT NOT NULL,
    reason TEXT NOT NULL
);
CREATE INDEX idx_audit_events_run ON audit_events(run_id);
