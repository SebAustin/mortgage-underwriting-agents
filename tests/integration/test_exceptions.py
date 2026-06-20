"""Integration tests for the exception routes that need injected failures."""

from __future__ import annotations

import pytest
from langgraph.types import Command
from sim import runner
from sim.fixtures import get_persona

from mortgage_agents.config import Settings
from mortgage_agents.graphs.case_orchestrator import build_case_graph
from mortgage_agents.persistence import make_memory_checkpointer
from mortgage_agents.ports.local_adapter import LocalAdapter
from mortgage_agents.state import new_case_state


@pytest.fixture
def settings(tmp_path):
    return Settings(runtime_mode="local", llm_mode="stub", runtime_dir=str(tmp_path))


def _drive(port, application, decisions, settings):
    graph = build_case_graph(port, checkpointer=make_memory_checkpointer())
    cfg = {"configurable": {"thread_id": application.case_id}}
    out = graph.invoke(new_case_state(application), cfg)
    safety = 0
    while "__interrupt__" in out and safety < 12:
        gate = out["__interrupt__"][0].value["gate"]
        choice = decisions.get(gate, "approve")
        out = graph.invoke(Command(resume={"choice": choice, "note": "test"}), cfg)
        safety += 1
    return out


class _FlakyRecoverAdapter(LocalAdapter):
    """Credit bureau fails a few times, then recovers (within retry budget)."""

    def __init__(self, *args, fail_times: int = 2, **kwargs):
        super().__init__(*args, **kwargs)
        self._fail_times = fail_times
        self._calls = 0

    def pull_credit(self, applicant):
        self._calls += 1
        if self._calls <= self._fail_times:
            raise ConnectionError("bureau timeout")
        return super().pull_credit(applicant)


class _AlwaysDownAdapter(LocalAdapter):
    def pull_credit(self, applicant):
        raise ConnectionError("bureau down")


def test_transient_failure_recovers_via_retry(settings):
    persona = get_persona("clean_approve")
    port = _FlakyRecoverAdapter(settings, directory=persona.directory, fail_times=2)
    out = _drive(port, persona.application, {"gate_b": "approve"}, settings)
    emitted = {e.type.value for e in out.get("exceptions", [])}
    assert "transient_failure" not in emitted  # retry absorbed it
    assert out["terminal_decision"].value == "approve"


def test_transient_failure_exhausts_and_escalates(settings):
    persona = get_persona("clean_approve")
    port = _AlwaysDownAdapter(settings, directory=persona.directory)
    out = _drive(port, persona.application, {"gate_b": "approve"}, settings)
    emitted = {e.type.value for e in out.get("exceptions", [])}
    assert "transient_failure" in emitted
    assert out["terminal_decision"].value == "escalated"


def test_appraisal_gap_recomputes_ltv_on_lesser_value(settings):
    persona = get_persona("appraisal_gap")
    final, _ = runner.run_auto(persona, settings=settings)
    emitted = {e.type.value for e in final.get("exceptions", [])}
    assert "appraisal_gap" in emitted
    metrics = final["metrics"]
    loan = persona.application.loan.loan_amount
    appraised = persona.application.loan.appraised_value
    assert metrics.ltv == pytest.approx(loan / appraised, abs=0.001)


def test_low_confidence_auto_recovers_without_human(settings):
    persona = get_persona("low_confidence_recovered")
    final, _ = runner.run_auto(persona, settings=settings)
    gates = [d.gate for d in final.get("human_decisions", [])]
    assert "verify_field" not in gates  # re-digitise fixed it
    assert final.get("verify_retry_count", 0) == 1
    assert final["terminal_decision"].value == "approve"


def test_low_confidence_falls_through_to_human(settings):
    persona = get_persona("low_confidence_human")
    final, _ = runner.run_auto(persona, settings=settings)
    gates = [d.gate for d in final.get("human_decisions", [])]
    assert "verify_field" in gates  # re-digitise didn't help → human verified
    assert final["terminal_decision"].value == "approve"
