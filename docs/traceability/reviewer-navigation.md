# Reviewer Navigation Guide

Every claim below names an exact repository path, an exact command where applicable, and the expected observable result — verify any of them directly.

## 1. Project Objective

`docs/assessment/assignment.md` (the brief) and `specs/001-agentic-url-shortener/spec.md` (the governed specification built from it).

## 2. Run the Application

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"
uvicorn shortener.api.app:app --reload
curl http://localhost:8000/healthz   # expect {"status":"up"}
```

## 3. Run the Tests

```bash
./scripts/validate.sh   # lint + full suite
# or: pytest -v
```
Expected: 171 passed (at commit `95fce55`; grows with Phase 5 commits).

## 4. Exercise the URL Shortener

```bash
curl -X POST localhost:8000/api/v1/links -H "X-API-Key: demo-key" \
  -H "Content-Type: application/json" -d '{"target_url":"https://example.com"}'
curl -i localhost:8000/<code>   # expect 302
```
(Seed `demo-key` via `api_keys_repository.create_key` or use the key created by any test fixture — no pre-seeded production key ships in this repo by design.)

## 5. Initiate an Orchestration Workflow

```bash
curl -X POST localhost:8000/api/v1/workflows -H "X-API-Key: demo-key" \
  -d '{"requirement": "Add batch link creation, 1-25 items", "scenario_type": "greenfield"}'
```
Expected: `{"run_id": "...", "current_state": "INGEST", ...}`.

## 6. Inspect Workflow State

```bash
curl localhost:8000/api/v1/workflows/<run_id>
```
Expected: full `state_history`, `decisions`, `approvals` arrays — `src/orchestration/api.py::get_workflow`.

## 7. Perform a Human Approval

```bash
curl -X POST localhost:8000/api/v1/workflows/<run_id>/approve \
  -d '{"gate":"ARCH_APPROVAL","decision":"approved","decided_by":"you","rationale":"..."}'
```
Test: `tests/orchestration/test_arch_approval_gate.py`.

## 8. Demonstrate Retry

`tests/orchestration/test_retry.py::test_retries_transient_failure_then_succeeds` — bounded, exponential backoff.

## 9. Demonstrate Compensation or Rollback

`tests/orchestration/test_rollback.py` (explicit `is_rollback_feasible()` predicate), `tests/orchestration/test_compensation.py` (requires non-empty human approver).

## 10. Demonstrate Safe-Stop

`tests/orchestration/test_safe_stop_resume.py::test_safe_stopped_run_cannot_progress_without_explicit_resume`.

## 11. Demonstrate Dynamic Replanning

`tests/orchestration/test_replanning.py::test_renormalize_computes_a_real_diff_not_a_full_discard` — real before/after task diff, not a full restart.

## 12. Greenfield Scenario

`docs/scenarios/greenfield.md` (narrative) + `tests/e2e/test_scenario_greenfield.py` (executable). Run: `pytest tests/e2e/test_scenario_greenfield.py -v` → 6 passed.

## 13. Brownfield Scenario

`docs/scenarios/brownfield-impact-analysis.md` (impact analysis, committed before any code — verify: `git log --oneline -- docs/scenarios/brownfield-impact-analysis.md src/shortener/migrations/0002_max_clicks.sql` shows the analysis commit `06524b2` precedes the migration commit `392ad44`) + `docs/scenarios/brownfield.md` + `tests/e2e/test_scenario_brownfield.py` → 6 passed, including the concurrency test and the full impact-analysis-gated orchestration-run trace.

## 14. Ambiguous-Requirement Scenario

`docs/scenarios/ambiguous.md` + `tests/e2e/test_scenario_ambiguous.py` (detection/halt, 3 passed) + `tests/e2e/test_scenario_ambiguous_resume.py` (real human-answered resumption, 4 passed).

## 15. Architecture

`specs/001-agentic-url-shortener/plan.md` (full architecture), `docs/architecture/threat-model.md` (security).

## 16. ADRs

`docs/adr/ADR-001` through `ADR-011`, all `Accepted` with a recorded human-approval date.

## 17. Requirement Traceability

`docs/traceability/matrix.md` — every FR-/NFR- mapped to scenario/ADR/task/code/test, with an explicit Orphan Check.

## 18. Audit Evidence

```bash
curl localhost:8000/api/v1/workflows/<run_id>
```
and directly: `sqlite3 shortener.db "SELECT * FROM audit_events WHERE run_id='<run_id>'"`.

## 19. Reliability Measurements

```bash
pytest tests/orchestration/test_mttr_calculation.py -v
```
MTTR formula and known-expected-value test: `src/orchestration/telemetry/metrics.py`, `tests/orchestration/test_mttr_calculation.py`.

## 20. Security Controls

`docs/architecture/threat-model.md` — dependency/license scan results, threat scenarios, disclosed limitations.

## 21. Known Limitations

`docs/architecture/threat-model.md` ("Known Limitations" section) and `docs/traceability/matrix.md` ("Orphan Check" section).

## 22. Final Engineering Summary

`docs/assessment/final-engineering-summary.md` (generated after convergence — see Phase 5 commits).

## 23. API Contracts, Schemas, Versions, Examples, Contract Tests

`specs/001-agentic-url-shortener/contracts/openapi.yaml` (currently v1.3.0; version history in its `info.description` field across commits), `specs/001-agentic-url-shortener/data-model.md`, `tests/contract/`.

## 24. Compliance / Change-Control Results and Approved Exceptions

`docs/governance/policy-pack.md`, `src/policy/engine.py`, `src/policy/exceptions.py`, `tests/orchestration/test_policy_evaluation.py`, `tests/orchestration/test_policy_exception.py`.

## 25. MTTR Calculation Inputs, Population, Exclusions, Unrecovered Failures

`specs/001-agentic-url-shortener/plan.md` §6 (formula), `src/orchestration/telemetry/metrics.py` (implementation — recovered events only in the denominator, unrecovered counted separately), `tests/orchestration/test_mttr_calculation.py` (known-expected-value: 2 recovered @ 10s/20s → MTTR=15s, 1 unrecovered excluded).
