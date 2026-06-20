"""End-to-end: a case survives a simulated process restart between human gates.

Each ``InboxStore`` / ``resume`` call uses a fresh SQLite connection, mimicking a
separate process — the same durability UiPath Maestro provides in the cloud.
"""

from __future__ import annotations

import pytest
from sim import runner
from sim.fixtures import get_persona
from sim.inbox import InboxStore

from mortgage_agents.config import Settings


@pytest.fixture
def settings(tmp_path):
    return Settings(runtime_mode="local", llm_mode="stub", runtime_dir=str(tmp_path))


def _fresh_store(settings: Settings) -> InboxStore:
    # A new store object == a new process touching the same on-disk DB.
    return InboxStore(f"{settings.runtime_dir}/inbox.sqlite")


def test_case_suspends_and_resumes_across_processes(settings):
    persona = get_persona("conditional_approve")

    # Process 1: start → suspends at Gate A.
    store1 = _fresh_store(settings)
    start = runner.start_case(persona, store1, settings=settings)
    store1.close()
    assert start["status"] == "suspended"
    assert start["gate"] == "gate_a"
    task_a = start["task_id"]

    # Process 2: a fresh store sees the pending task.
    store2 = _fresh_store(settings)
    pending = store2.list_pending()
    assert [t.task_id for t in pending] == [task_a]
    store2.close()

    # Process 3: resolve Gate A → suspends at Gate B.
    store3 = _fresh_store(settings)
    mid = runner.resume(task_a, "conditional_approve", "underwriter ok", store3, settings=settings)
    store3.close()
    assert mid["status"] == "suspended"
    assert mid["gate"] == "gate_b"
    task_b = mid["task_id"]

    # Process 4: resolve Gate B → case closes with the human's final decision.
    store4 = _fresh_store(settings)
    final = runner.resume(task_b, "conditional_approve", "manager signs", store4, settings=settings)
    assert final["status"] == "closed"
    assert final["decision"] == "conditional_approve"

    # The Gate A task is resolved; no tasks remain pending.
    assert store4.get_task(task_a).status == "resolved"
    assert store4.list_pending() == []
    case = store4.get_case(persona.application.case_id)
    assert case.status == "closed"
    store4.close()


def test_resume_rejects_unknown_task(settings):
    store = _fresh_store(settings)
    with pytest.raises(KeyError):
        runner.resume("nope", "approve", "", store, settings=settings)
    store.close()


def test_double_resolve_is_rejected(settings):
    persona = get_persona("clean_approve")
    store = _fresh_store(settings)
    start = runner.start_case(persona, store, settings=settings)
    task = start["task_id"]
    runner.resume(task, "approve", "", store, settings=settings)
    with pytest.raises(ValueError):
        runner.resume(task, "approve", "", store, settings=settings)
    store.close()
