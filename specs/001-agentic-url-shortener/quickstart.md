# Quickstart

> This file is validated verbatim from a clean clone before final submission (Final Step-by-Step Execution Sequence, step 61). Any command here that stops working is a documentation bug, not an acceptable drift.

## Prerequisites

- Python 3.11+
- No external services, accounts, or API keys required (deterministic mode is the default — `LLM_PROVIDER=none`)

## Setup

```bash
git clone https://github.com/Belede/agentic-engineering-url-shortener.git
cd agentic-engineering-url-shortener
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Run the application

```bash
uvicorn shortener.api.app:app --reload
```

- Health: `curl http://localhost:8000/healthz`
- Create a link: `curl -X POST http://localhost:8000/api/v1/links -H "X-API-Key: demo-key" -H "Content-Type: application/json" -d '{"target_url":"https://example.com"}'`
- Resolve: `curl -i http://localhost:8000/<code>`

## Run the tests

```bash
./scripts/validate.sh
# or directly:
pytest
```

## Exercise the orchestration engine

```bash
curl -X POST http://localhost:8000/api/v1/workflows -H "X-API-Key: demo-key" \
  -d '{"requirement": "Add batch link creation, 1-25 items per call"}'
# -> {"run_id": "...", "current_state": "QUALITY_CHECK", ...}

curl http://localhost:8000/api/v1/workflows/<run_id>
# inspect state history

curl -X POST http://localhost:8000/api/v1/workflows/<run_id>/approve \
  -d '{"gate": "ARCH_APPROVAL", "decided_by": "reviewer", "rationale": "..."}'
```

See `docs/traceability/reviewer-navigation.md` (generated post-implementation) for the full command-by-command guide to every orchestration capability.
