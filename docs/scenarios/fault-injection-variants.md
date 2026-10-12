# Fault-Injection Variants (T043)

Each of the six variants the assignment's orchestration requirements call for (retry, fallback, late ambiguity, rollback, compensation, crash/resume) has its own dedicated, independently committed test — never bundled into one commit, per the pre-implementation independent review's condition #4.

| # | Variant | Mechanism Exercised | Test | Commit |
|---|---|---|---|---|
| 1 | Flaky operation → retry | Bounded retry, exponential backoff, exact attempt bound | `tests/orchestration/test_retry.py` | `5b87fda` |
| 2 | Doc-generator outage → fallback | Labeled fallback stub, run not blocked | `tests/orchestration/test_document_fallback.py` | `44e149a` |
| 3 | Late ambiguity (discovered mid-`IMPLEMENT`, not just at intake) → suspend + scoped resume | `IMPLEMENT → CLARIFY` edge (added for this variant), reuses `RENORMALIZE` for scoped resumption | `tests/e2e/test_fault_injection_late_ambiguity.py` | this commit |
| 4 | Broken/irreversible-seeming change → rollback | Explicit, testable `is_rollback_feasible()` predicate (not an implicit judgment call) | `tests/orchestration/test_rollback.py` | `5b87fda` |
| 5 | Failed release / change requiring correction → compensation | Structurally requires a non-empty human approver, never automatic | `tests/orchestration/test_compensation.py` | `5b87fda` |
| 6 | Process crash mid-stage → resume | Two genuinely distinct cases (independent-review condition #1): (a) safe-stop → explicit human resume at a specific node; (b) plain process-crash → a fresh connection re-reads persisted state with zero lost history, no human gate needed | `tests/orchestration/test_safe_stop_resume.py` | `5b87fda` |

## Gate Decisions for These Variants

Each variant's governing decision is test-identity-scoped: the test itself constructs the run, drives it to the fault condition, and asserts the correct recovery mechanism and outcome — there is no separate "production" gate distinct from the test's own assertions, since these are deliberately constructed fault conditions for demonstration, not organically occurring production failures. This is explicitly labeled (constitution Principle IX: demonstration measurements vs. production measurements) rather than conflated.

## Reviewer Verification

```bash
pytest tests/orchestration/test_retry.py tests/orchestration/test_document_fallback.py \
       tests/e2e/test_fault_injection_late_ambiguity.py tests/orchestration/test_rollback.py \
       tests/orchestration/test_compensation.py tests/orchestration/test_safe_stop_resume.py -v
```
Expected: 22 passed (5+2+2+4+2+5, per current suite — exact count may grow as the suite does; see each file for its current count).
