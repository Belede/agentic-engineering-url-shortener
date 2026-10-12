# Agentic Software Engineering System: URL Shortener

Interview assignment submission — a URL shortener built as the demonstration domain for a **governed, stateful, non-linear agentic SDLC orchestration system**, following the complete SpecKit lifecycle with real human approval gates throughout.

**Release status**: `READY WITH ACCEPTED LIMITATIONS` — tag [`assessment-submission-v1.0`](https://github.com/Belede/agentic-engineering-url-shortener/tree/assessment-submission-v1.0) (git tag, no formal GitHub Release object created). 172/172 tests passing, clean-clone verified in 15.4s.

## Start Here

- **[Reviewer Navigation Guide](docs/traceability/reviewer-navigation.md)** — the fastest path through this repo: every claim links to an exact path/command and expected result.
- **[Final Engineering Summary](docs/assessment/final-engineering-summary.md)** — the 21-section executive summary (outcome, architecture, scenarios, limitations, judgment).
- **[Assignment Brief](docs/assessment/assignment.md)** — the original requirement this repo answers.

## Quickstart

```bash
git clone https://github.com/Belede/agentic-engineering-url-shortener.git
cd agentic-engineering-url-shortener
python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"
pytest -v        # expect 172 passed
uvicorn shortener.api.app:app --reload
```
Full walkthrough: [`specs/001-agentic-url-shortener/quickstart.md`](specs/001-agentic-url-shortener/quickstart.md).

## What's Here

| | |
|---|---|
| **Governance process** | `.specify/memory/constitution.md`, `specs/001-agentic-url-shortener/{spec,plan,tasks}.md`, `docs/adr/` (11 accepted ADRs) |
| **Orchestration engine** | `src/orchestration/` — 16-node explicit graph, human-gated approvals, retry/fallback/rollback/compensation/safe-stop/resume, dynamic replanning |
| **URL shortener (demo domain)** | `src/shortener/` — create/redirect/analytics/expiry/rate-limiting/click-limits |
| **Three required scenarios** | `docs/scenarios/{greenfield,brownfield,ambiguous}.md`, each with a real human decision and a full orchestration-run trace |
| **Evidence & assessment** | `docs/assessment/` — pre/post-implementation analysis, independent reviews, convergence report, final summary |
| **Traceability** | `docs/traceability/matrix.md` — every requirement mapped to scenario, ADR, task, code, and test |

## Every Human Decision, Logged

`docs/governance/decision-log.md` — 20 real decisions made by the candidate during this build (not fabricated or inferred from silence), each cross-referenced to this repository's commit history and the orchestration engine's own `approval_records`.

## License

Private submission for interview assessment purposes — not licensed for reuse.
