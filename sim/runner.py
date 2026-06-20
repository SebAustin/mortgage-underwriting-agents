"""Case runner — drives a mortgage case through the graph.

Two modes:

* ``run_auto`` — single process, in-memory checkpoint, resolves gates from the persona's
  scripted decisions. Deterministic; used by tests and the headless demo.
* ``start_case`` / ``resume`` — durable, cross-process. ``start_case`` runs until the
  first human gate, persists the checkpoint, and records a pending Action Inbox task.
  ``resume`` (typically a separate process) resolves the task and continues the case.
"""

from __future__ import annotations

import json
import sqlite3
import uuid

from langgraph.types import Command

from mortgage_agents.config import Settings, get_settings
from mortgage_agents.graphs.case_orchestrator import build_case_graph
from mortgage_agents.llm import get_llm
from mortgage_agents.persistence import make_checkpointer, make_memory_checkpointer
from mortgage_agents.ports.local_adapter import LocalAdapter, MockProfile
from mortgage_agents.state import CaseState, new_case_state

from .fixtures import Persona
from .inbox import InboxStore

_SAFETY_LIMIT = 12


def _default_choice(gate: str) -> str:
    return "verified" if gate == "verify_field" else "approve"


def serialize_directory(directory: dict[str, MockProfile]) -> str:
    return json.dumps({ssn: prof.model_dump() for ssn, prof in directory.items()})


def deserialize_directory(directory_json: str) -> dict[str, MockProfile]:
    raw = json.loads(directory_json)
    return {ssn: MockProfile(**data) for ssn, data in raw.items()}


def _build_port(directory: dict[str, MockProfile], settings: Settings) -> LocalAdapter:
    return LocalAdapter(settings, directory=directory)


def _checkpoints_path(settings: Settings) -> str:
    import os

    os.makedirs(settings.runtime_dir, exist_ok=True)
    return f"{settings.runtime_dir}/checkpoints.sqlite"


def run_auto(
    persona: Persona,
    settings: Settings | None = None,
    use_crew: bool = False,
) -> tuple[CaseState, LocalAdapter]:
    """Run a persona to completion in one process, resolving gates from its script."""

    settings = settings or get_settings()
    port = _build_port(persona.directory, settings)
    graph = build_case_graph(
        port, llm=get_llm(settings), checkpointer=make_memory_checkpointer(), use_crew=use_crew
    )
    cfg = {"configurable": {"thread_id": persona.application.case_id}}

    out = graph.invoke(new_case_state(persona.application), cfg)
    safety = 0
    while "__interrupt__" in out and safety < _SAFETY_LIMIT:
        gate = out["__interrupt__"][0].value["gate"]
        choice = persona.decisions.get(gate) or _default_choice(gate)
        out = graph.invoke(
            Command(resume={"choice": choice, "note": f"auto:{persona.name}"}), cfg
        )
        safety += 1
    return out, port


def _advance_and_record(graph, cfg, out: dict, store: InboxStore, case_id: str, persona: str,
                        directory_json: str) -> dict:
    """Inspect a graph output: persist a pending task or close the case. Returns a summary."""

    if "__interrupt__" in out:
        req = out["__interrupt__"][0].value
        task_id = f"{case_id}-{req['gate']}-{uuid.uuid4().hex[:6]}"
        store.add_task(
            task_id=task_id,
            case_id=case_id,
            gate=req["gate"],
            title=req["title"],
            summary=req["summary"],
            options=req["options"],
            context=req.get("context", {}),
        )
        store.upsert_case(case_id, persona, "suspended", directory_json)
        return {"status": "suspended", "task_id": task_id, "gate": req["gate"],
                "title": req["title"], "summary": req["summary"], "options": req["options"]}

    decision = out.get("terminal_decision")
    decision_val = decision.value if decision is not None else None
    store.upsert_case(case_id, persona, "closed", directory_json, terminal_decision=decision_val)
    return {"status": "closed", "case_id": case_id, "decision": decision_val,
            "timeline": out.get("timeline", [])}


def start_case(
    persona: Persona,
    store: InboxStore,
    settings: Settings | None = None,
    use_crew: bool = False,
) -> dict:
    """Start a durable case; run until the first gate or completion."""

    settings = settings or get_settings()
    port = _build_port(persona.directory, settings)
    conn = sqlite3.connect(_checkpoints_path(settings), check_same_thread=False)
    graph = build_case_graph(
        port, llm=get_llm(settings), checkpointer=make_checkpointer(conn), use_crew=use_crew
    )
    case_id = persona.application.case_id
    directory_json = serialize_directory(persona.directory)
    store.upsert_case(case_id, persona.name, "running", directory_json)

    cfg = {"configurable": {"thread_id": case_id}}
    out = graph.invoke(new_case_state(persona.application), cfg)
    summary = _advance_and_record(graph, cfg, out, store, case_id, persona.name, directory_json)
    conn.close()
    return summary


def load_state(case_id: str, settings: Settings | None = None) -> CaseState | None:
    """Read the persisted state for a case from the durable checkpointer (read-only).

    ``get_state`` does not execute nodes, so a default port is sufficient here.
    """

    settings = settings or get_settings()
    conn = sqlite3.connect(_checkpoints_path(settings), check_same_thread=False)
    graph = build_case_graph(_build_port({}, settings), checkpointer=make_checkpointer(conn))
    snapshot = graph.get_state({"configurable": {"thread_id": case_id}})
    conn.close()
    return snapshot.values if snapshot and snapshot.values else None


def resume(
    task_id: str,
    choice: str,
    note: str,
    store: InboxStore,
    settings: Settings | None = None,
    use_crew: bool = False,
) -> dict:
    """Resolve a pending Action Inbox task and continue the case (cross-process safe)."""

    settings = settings or get_settings()
    task = store.get_task(task_id)
    if task is None:
        raise KeyError(f"No such task '{task_id}'")
    if task.status != "pending":
        raise ValueError(f"Task '{task_id}' is already {task.status}")

    case = store.get_case(task.case_id)
    assert case is not None, "task references a missing case"
    directory = deserialize_directory(case.directory_json)
    port = _build_port(directory, settings)
    conn = sqlite3.connect(_checkpoints_path(settings), check_same_thread=False)
    graph = build_case_graph(
        port, llm=get_llm(settings), checkpointer=make_checkpointer(conn), use_crew=use_crew
    )

    cfg = {"configurable": {"thread_id": task.case_id}}
    out = graph.invoke(Command(resume={"choice": choice, "note": note}), cfg)
    store.resolve_task(task_id, choice, note)
    summary = _advance_and_record(
        graph, cfg, out, store, task.case_id, case.persona, case.directory_json
    )
    conn.close()
    return summary
