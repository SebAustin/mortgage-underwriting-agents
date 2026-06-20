import pytest
from sim import runner
from sim.fixtures import all_personas

from mortgage_agents.config import Settings

PERSONAS = list(all_personas().values())


@pytest.fixture
def settings(tmp_path):
    return Settings(runtime_mode="local", llm_mode="stub", runtime_dir=str(tmp_path))


@pytest.mark.parametrize("persona", PERSONAS, ids=[p.name for p in PERSONAS])
def test_persona_reaches_expected_decision(persona, settings):
    final, port = runner.run_auto(persona, settings=settings)

    assert final.get("terminal") is True
    decision = final.get("terminal_decision")
    assert decision is not None
    assert decision.value == persona.expected_decision.value

    emitted = {e.type.value for e in final.get("exceptions", [])}
    for expected in persona.expected_exceptions:
        assert expected in emitted, f"{persona.name} missing exception {expected} (got {emitted})"

    # Every case keeps an audit timeline (short-circuit cases like missing-docs have ≥2).
    assert len(final.get("timeline", [])) >= 2


def test_clean_file_needs_only_final_human_gate(settings):
    final, _ = runner.run_auto(all_personas()["clean_approve"], settings=settings)
    gates = [d.gate for d in final.get("human_decisions", [])]
    assert gates == ["gate_b"]  # no Gate A for a clean file


def test_borderline_uses_both_gates(settings):
    final, _ = runner.run_auto(all_personas()["conditional_approve"], settings=settings)
    gates = [d.gate for d in final.get("human_decisions", [])]
    assert gates == ["gate_a", "gate_b"]


def test_fraud_case_escalates_without_final_gate(settings):
    final, _ = runner.run_auto(all_personas()["fraud_exception"], settings=settings)
    gates = [d.gate for d in final.get("human_decisions", [])]
    assert "verify_field" in gates  # human verified the conflict
    assert "gate_b" not in gates  # but it escalated before final sign-off
    assert final["terminal_decision"].value == "escalated"


def test_missing_docs_sends_borrower_email(settings):
    final, port = runner.run_auto(all_personas()["missing_docs"], settings=settings)
    assert final["terminal_decision"].value == "info_requested"
    assert len(port.sent_emails) == 1
    assert "appraisal" in port.sent_emails[0]["body"] or "pay_stub" in port.sent_emails[0]["body"]
