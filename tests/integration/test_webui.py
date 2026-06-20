"""Smoke tests for the optional FastAPI loan-officer desk."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402
from sim.inbox import InboxStore  # noqa: E402
from sim.webui.app import create_app  # noqa: E402

from mortgage_agents.config import Settings  # noqa: E402


@pytest.fixture
def client(tmp_path):
    settings = Settings(runtime_mode="local", llm_mode="stub", runtime_dir=str(tmp_path))
    app = create_app(settings)
    return TestClient(app), settings


def test_index_lists_personas(client):
    tc, _ = client
    resp = tc.get("/")
    assert resp.status_code == 200
    assert "Underwriting Desk" in resp.text
    assert "clean_approve" in resp.text


def test_start_then_resolve_to_approval(client):
    tc, settings = client

    # Start a clean case → suspends at Gate B.
    resp = tc.post("/start", data={"persona": "clean_approve"}, follow_redirects=True)
    assert resp.status_code == 200
    assert "CASE-CLEAN" in resp.text

    store = InboxStore(f"{settings.runtime_dir}/inbox.sqlite")
    pending = store.list_pending()
    assert len(pending) == 1
    task = pending[0]
    assert task.gate == "gate_b"
    store.close()

    # Resolve Gate B with approve → case closes approved.
    resp = tc.post(
        "/resolve",
        data={"task_id": task.task_id, "choice": "approve", "note": "ok", "case_id": task.case_id},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "approve" in resp.text.lower()

    store = InboxStore(f"{settings.runtime_dir}/inbox.sqlite")
    case = store.get_case("CASE-CLEAN")
    assert case.status == "closed"
    assert case.terminal_decision == "approve"
    store.close()
