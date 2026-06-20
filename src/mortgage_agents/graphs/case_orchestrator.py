"""Case orchestrator — the supervisor graph that is the deployable Maestro Case.

Wires the five agents, the two human gates, the exception routes, and the terminal
nodes into one graph. Stage transitions here mirror the Maestro case definition 1:1
(see ``case_definition.yaml``). The same graph runs locally (mocked) and on UiPath,
because every side effect goes through the injected :class:`PlatformPort`.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

# NOTE: absolute imports (not relative) so this entry module loads both as a normal package
# module AND when the UiPath graph loader imports it by file path (no package context).
from mortgage_agents.graphs._helpers import timeline_entry
from mortgage_agents.graphs.adjudication_agent import make_adjudication_agent
from mortgage_agents.graphs.doc_verify_agent import (
    CONFIDENCE_THRESHOLD,
    make_doc_verify_agent,
    make_redigitize_node,
)
from mortgage_agents.graphs.exception_agent import make_exception_agent
from mortgage_agents.graphs.intake_agent import make_intake_agent
from mortgage_agents.graphs.underwriting_agent import make_underwriting_agent
from mortgage_agents.llm import LLMProvider, get_llm
from mortgage_agents.ports import PlatformPort
from mortgage_agents.state import (
    Actor,
    CaseInput,
    CaseOutput,
    CaseState,
    Condition,
    Decision,
    ExceptionType,
    HumanTaskRequest,
    Stage,
)

_MAX_VERIFY_RETRIES = 1


def _has_exception(state: CaseState, exc_type: ExceptionType) -> bool:
    return any(e.type == exc_type for e in state.get("exceptions", []))


def _decision_from_choice(choice: str, fallback: Decision) -> Decision:
    try:
        return Decision(choice)
    except ValueError:
        return fallback


def build_case_graph(
    port: PlatformPort,
    llm: LLMProvider | None = None,
    checkpointer=None,
    use_crew: bool = False,
):
    """Build (and compile) the mortgage underwriting case graph for a given port."""

    llm = llm or get_llm()

    intake = make_intake_agent(port, llm)
    doc_verify = make_doc_verify_agent(port, llm)
    redigitize = make_redigitize_node(port)
    income_analysis = make_underwriting_agent(port, llm)
    adjudication = make_adjudication_agent(port, llm, use_crew=use_crew)
    conditions = make_exception_agent(port, llm)

    # — Human gates —
    def gate_a(state: CaseState) -> dict:
        rec = state["recommendation"]
        assert rec is not None
        request = HumanTaskRequest(
            gate="gate_a",
            title="Underwriting decision support (borderline case)",
            summary=rec.rationale,
            options=[Decision.APPROVE.value, Decision.CONDITIONAL_APPROVE.value, Decision.DECLINE.value],
            context={
                "agent_recommendation": rec.decision.value,
                "confidence": rec.confidence,
                "policy_citations": rec.policy_citations,
                "compensating_factors": rec.compensating_factors,
            },
        )
        decision = port.request_human_decision(request)
        decision.decided_by = decision.decided_by or "underwriter"
        steered = _decision_from_choice(decision.choice, rec.decision)
        rec2 = rec.model_copy(update={"decision": steered})
        return {
            "recommendation": rec2,
            "human_decisions": [decision],
            "timeline": [
                timeline_entry(
                    port,
                    Stage.ADJUDICATION,
                    Actor.HUMAN,
                    "Gate A — underwriter steer",
                    f"{decision.choice}{' — ' + decision.note if decision.note else ''}",
                )
            ],
        }

    def gate_b(state: CaseState) -> dict:
        rec = state["recommendation"]
        assert rec is not None
        request = HumanTaskRequest(
            gate="gate_b",
            title="Final credit decision (human authority)",
            summary=rec.rationale,
            options=[Decision.APPROVE.value, Decision.CONDITIONAL_APPROVE.value, Decision.DECLINE.value],
            context={
                "agent_recommendation": rec.decision.value,
                "conditions": [c.description for c in (state.get("conditions") or [])],
            },
        )
        decision = port.request_human_decision(request)
        final = _decision_from_choice(decision.choice, rec.decision)
        return {
            "terminal_decision": final,
            "human_decisions": [decision],
            "stage": Stage.DECISION,
            "timeline": [
                timeline_entry(
                    port,
                    Stage.DECISION,
                    Actor.HUMAN,
                    f"Gate B — final decision: {final.value}",
                    decision.note,
                )
            ],
        }

    def verify_gate(state: CaseState) -> dict:
        request = HumanTaskRequest(
            gate="verify_field",
            title="Verify document data",
            summary="; ".join(state.get("consistency_findings", []))
            or f"Low extraction confidence (<{CONFIDENCE_THRESHOLD}); please verify.",
            options=["verified", "rejected"],
            context={"findings": state.get("consistency_findings", [])},
        )
        decision = port.request_human_decision(request)
        return {
            # Human resolved the data issue → clear the transient flags so the case proceeds.
            "consistency_findings": [],
            "current_min_confidence": 1.0,
            "human_decisions": [decision],
            "timeline": [
                timeline_entry(
                    port,
                    Stage.DOC_VERIFICATION,
                    Actor.HUMAN,
                    "Verified document data",
                    decision.choice,
                )
            ],
        }

    # — Terminal nodes —
    def closing(state: CaseState) -> dict:
        rec = state.get("recommendation")
        final = state.get("terminal_decision") or (rec.decision if rec else Decision.PENDING)
        app = state["application"]
        conditions_list: list[Condition] = state.get("conditions") or []
        letter = _decision_letter(app.case_id, app.applicant.full_name, final, conditions_list)
        ref = port.emit_artifact(app.case_id, "decision_letter.txt", letter)
        return {
            "terminal": True,
            "terminal_decision": final,
            "stage": Stage.CLOSED,
            "timeline": [
                timeline_entry(
                    port, Stage.CLOSED, Actor.ROBOT, f"Closed: {final.value}", f"letter → {ref}"
                )
            ],
        }

    def request_info(state: CaseState) -> dict:
        app = state["application"]
        missing = state.get("missing_docs", [])
        port.send_borrower_email(
            to=app.applicant.email,
            subject=f"Additional documents needed — case {app.case_id}",
            body=f"To continue underwriting we need: {', '.join(missing)}.",
        )
        return {
            "terminal": True,
            "terminal_decision": Decision.INFO_REQUESTED,
            "stage": Stage.CLOSED,
            "timeline": [
                timeline_entry(
                    port,
                    Stage.INTAKE,
                    Actor.ROBOT,
                    "Requested missing documents",
                    ", ".join(missing),
                )
            ],
        }

    def escalate(state: CaseState) -> dict:
        reason = "compliance review"
        for exc in state.get("exceptions", []):
            if exc.type in (ExceptionType.FRAUD_AML, ExceptionType.TRANSIENT_FAILURE):
                reason = f"{exc.type.value}: {exc.detail}"
        return {
            "terminal": True,
            "terminal_decision": Decision.ESCALATED,
            "stage": Stage.CLOSED,
            "timeline": [
                timeline_entry(
                    port, Stage.CONDITIONS, Actor.SYSTEM, "Escalated out of automated flow", reason
                )
            ],
        }

    # — Routers —
    def route_after_intake(state: CaseState) -> str:
        return "request_info" if _has_exception(state, ExceptionType.MISSING_DOCS) else "doc_verify"

    def route_after_doc_verify(state: CaseState) -> str:
        low = state.get("current_min_confidence", 1.0) < CONFIDENCE_THRESHOLD
        conflict = bool(state.get("consistency_findings"))
        if low and state.get("verify_retry_count", 0) < _MAX_VERIFY_RETRIES:
            return "redigitize"
        if low or conflict:
            return "verify_gate"
        return "income_analysis"

    def route_after_adjudication(state: CaseState) -> str:
        if _has_exception(state, ExceptionType.TRANSIENT_FAILURE):
            return "escalate"
        rec = state.get("recommendation")
        if rec is not None and rec.borderline:
            return "gate_a"
        return "conditions"

    def route_after_conditions(state: CaseState) -> str:
        return "escalate" if _has_exception(state, ExceptionType.FRAUD_AML) else "gate_b"

    # — Assemble — clean cloud I/O contract: input is a loan application, output is the
    # decision plus the audit trail. Internal state remains the richer CaseState.
    g = StateGraph(CaseState, input_schema=CaseInput, output_schema=CaseOutput)
    g.add_node("intake", intake)
    g.add_node("doc_verify", doc_verify)
    g.add_node("redigitize", redigitize)
    g.add_node("verify_gate", verify_gate)
    g.add_node("income_analysis", income_analysis)
    g.add_node("adjudication", adjudication)
    g.add_node("gate_a", gate_a)
    g.add_node("conditions", conditions)
    g.add_node("gate_b", gate_b)
    g.add_node("closing", closing)
    g.add_node("request_info", request_info)
    g.add_node("escalate", escalate)

    g.add_edge(START, "intake")
    g.add_conditional_edges(
        "intake", route_after_intake, {"request_info": "request_info", "doc_verify": "doc_verify"}
    )
    g.add_conditional_edges(
        "doc_verify",
        route_after_doc_verify,
        {
            "redigitize": "redigitize",
            "verify_gate": "verify_gate",
            "income_analysis": "income_analysis",
        },
    )
    g.add_edge("redigitize", "doc_verify")
    g.add_edge("verify_gate", "income_analysis")
    g.add_edge("income_analysis", "adjudication")
    g.add_conditional_edges(
        "adjudication",
        route_after_adjudication,
        {"escalate": "escalate", "gate_a": "gate_a", "conditions": "conditions"},
    )
    g.add_edge("gate_a", "conditions")
    g.add_conditional_edges(
        "conditions", route_after_conditions, {"escalate": "escalate", "gate_b": "gate_b"}
    )
    g.add_edge("gate_b", "closing")
    g.add_edge("closing", END)
    g.add_edge("request_info", END)
    g.add_edge("escalate", END)

    return g.compile(checkpointer=checkpointer)


def _decision_letter(
    case_id: str, applicant: str, decision: Decision, conditions: list[Condition]
) -> str:
    header = f"Case {case_id} — {applicant}\nDecision: {decision.value.upper()}\n"
    if decision == Decision.CONDITIONAL_APPROVE and conditions:
        body = "Conditions:\n" + "\n".join(f"  - {c.description}" for c in conditions)
    elif decision == Decision.APPROVE:
        body = "Congratulations — your mortgage application is approved."
    elif decision == Decision.DECLINE:
        body = "We are unable to approve your application at this time."
    elif decision == Decision.ESCALATED:
        body = "Your application requires additional review and has been escalated."
    elif decision == Decision.INFO_REQUESTED:
        body = "Additional documentation is required to proceed."
    else:
        body = "Your application is under review."
    return header + body + "\n"


# Module-level graph for langgraph.json / UiPath packaging (no checkpointer — the platform
# injects durable execution). Guarded so importing never breaks packaging tooling.
try:  # pragma: no cover - exercised only by packaging/import probes
    from mortgage_agents.ports import get_port

    graph = build_case_graph(get_port())
except Exception:  # pragma: no cover
    graph = None
