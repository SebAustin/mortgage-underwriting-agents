"""ExceptionAgent — conditions stage: AML/fraud screen, condition assembly, escalation.

Runs the compliance screen before the final human decision. An AML hit is a hard stop
that escalates to compliance (the orchestrator routes to the escalate node); otherwise
the case proceeds to the final human credit decision (Gate B) with its condition list.
"""

from __future__ import annotations

from collections.abc import Callable

from ..llm import LLMProvider
from ..policy.exception_policy import route_for
from ..ports import PlatformPort
from ..state import (
    Actor,
    CaseState,
    ExceptionEvent,
    ExceptionType,
    Stage,
)
from ._helpers import timeline_entry


def make_exception_agent(port: PlatformPort, llm: LLMProvider) -> Callable[[CaseState], dict]:
    def conditions(state: CaseState) -> dict:
        app = state["application"]
        aml = port.screen_aml(app.applicant)
        recommendation = state.get("recommendation")
        case_conditions = recommendation.conditions if recommendation else []

        updates: dict = {
            "stage": Stage.DECISION,
            "aml_result": aml,
            "conditions": case_conditions,
            "timeline": [
                timeline_entry(
                    port,
                    Stage.CONDITIONS,
                    Actor.AGENT,
                    "Screened AML & assembled conditions",
                    f"aml_hit={aml.hit} (risk {aml.risk_score:.2f}); "
                    f"{len(case_conditions)} condition(s)",
                )
            ],
        }

        if aml.hit:
            route = route_for(ExceptionType.FRAUD_AML)
            updates["exceptions"] = [
                ExceptionEvent(
                    type=ExceptionType.FRAUD_AML,
                    severity=route.severity,
                    detail=f"AML watchlist hit: {', '.join(aml.watchlists) or 'flagged'}",
                    route=route.route,
                    stage=Stage.CONDITIONS,
                )
            ]

        return updates

    return conditions
