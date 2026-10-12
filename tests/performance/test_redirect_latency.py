"""T034b: p95 redirect-resolution latency, demonstration-labeled. NFR-007, CL-09.

Added during /speckit-analyze after discovering NFR-007 had no validating
task (docs/assessment/pre-implementation-analysis.md). This result is a
local-hardware demonstration measurement, NOT a production SLA — see
ADR-008 and constitution Principle IX.
"""
import statistics
import time

import pytest
from fastapi.testclient import TestClient

from shortener.api.app import create_app
from shortener.persistence import api_keys_repository
from shortener.persistence.db import get_connection
from shortener.persistence.migrations_runner import MigrationRunner

N_SAMPLES = 50
P95_TARGET_SECONDS = 0.100  # CL-09: <100ms p95, demonstration-only


@pytest.fixture
def client_and_code(tmp_path):
    db_path = str(tmp_path / "perf.db")
    app = create_app(db_path=db_path)
    conn = get_connection(db_path)
    MigrationRunner(conn, app.state.migrations_dir).apply_all()
    api_keys_repository.create_key(conn, key_id="k1", label="perf caller")
    conn.close()
    client = TestClient(app)
    code = client.post(
        "/api/v1/links", json={"target_url": "https://example.com"},
        headers={"X-API-Key": "k1"},
    ).json()["code"]
    return client, code


def test_redirect_p95_latency_under_demonstration_target(client_and_code):
    client, code = client_and_code
    durations = []
    for _ in range(N_SAMPLES):
        start = time.perf_counter()
        client.get(f"/{code}", follow_redirects=False)
        durations.append(time.perf_counter() - start)

    durations.sort()
    p95_index = int(len(durations) * 0.95)
    p95 = durations[p95_index]

    # Explicit demonstration-data labeling (NFR-007, ADR-008) — printed so
    # it's visible in pytest -v output as part of the evidence trail, not
    # silently asserted and discarded.
    print(
        f"\n[demonstration measurement, not a production SLA] "
        f"p95={p95*1000:.2f}ms over {N_SAMPLES} samples, "
        f"mean={statistics.mean(durations)*1000:.2f}ms, "
        f"target<{P95_TARGET_SECONDS*1000:.0f}ms"
    )
    assert p95 < P95_TARGET_SECONDS
