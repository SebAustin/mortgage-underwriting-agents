"""IntakeAgent — classify the document set, build the required-docs checklist, triage.

First stage of the case. Emits a MISSING_DOCS exception when required documents are
absent so the orchestrator can route to the borrower request-info path.
"""

from __future__ import annotations

from collections.abc import Callable

from ..llm import LLMProvider
from ..policy.exception_policy import route_for
from ..policy.underwriting_policy import required_docs_for
from ..ports import PlatformPort
from ..state import (
    Actor,
    CaseState,
    ExceptionEvent,
    ExceptionType,
    Stage,
)
from ..tools.documents import build_checklist, classify_document
from ._helpers import timeline_entry


def make_intake_agent(port: PlatformPort, llm: LLMProvider) -> Callable[[CaseState], dict]:
    def intake(state: CaseState) -> dict:
        app = state["application"]
        present = [classify_document(doc) for doc in app.documents]
        required = required_docs_for(app.loan.loan_program)
        checklist, missing = build_checklist(required, present)

        updates: dict = {
            "stage": Stage.DOC_VERIFICATION,
            "doc_checklist": checklist,
            "missing_docs": missing,
            "timeline": [
                timeline_entry(
                    port,
                    Stage.INTAKE,
                    Actor.AGENT,
                    "Triaged application",
                    f"{len(app.documents)} docs received; missing={missing or 'none'}",
                )
            ],
        }

        if missing:
            route = route_for(ExceptionType.MISSING_DOCS)
            updates["exceptions"] = [
                ExceptionEvent(
                    type=ExceptionType.MISSING_DOCS,
                    severity=route.severity,
                    detail=f"Missing required documents: {', '.join(missing)}",
                    route=route.route,
                    stage=Stage.INTAKE,
                )
            ]

        return updates

    return intake
