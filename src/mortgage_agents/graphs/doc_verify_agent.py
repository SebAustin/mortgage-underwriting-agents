"""DocVerifyAgent — extract document fields, cross-check consistency, gate on confidence.

Runs Document Understanding (via the port), reconciles identity/employer fields across
documents, and emits LOW_CONFIDENCE / CONFLICTING_DATA exceptions. The orchestrator
auto-retries extraction once (the ``redigitize`` node) before escalating to a human.
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
from ..tools.documents import cross_check_fields, min_confidence
from ._helpers import timeline_entry

CONFIDENCE_THRESHOLD = 0.85


def make_doc_verify_agent(port: PlatformPort, llm: LLMProvider) -> Callable[[CaseState], dict]:
    def doc_verify(state: CaseState) -> dict:
        app = state["application"]
        extractions = [port.extract_document(doc) for doc in app.documents]
        findings = cross_check_fields(extractions)
        confidence = min_confidence(extractions)

        exceptions: list[ExceptionEvent] = []
        if confidence < CONFIDENCE_THRESHOLD:
            route = route_for(ExceptionType.LOW_CONFIDENCE)
            exceptions.append(
                ExceptionEvent(
                    type=ExceptionType.LOW_CONFIDENCE,
                    severity=route.severity,
                    detail=f"Lowest extraction confidence {confidence:.2f} < {CONFIDENCE_THRESHOLD}",
                    route=route.route,
                    stage=Stage.DOC_VERIFICATION,
                )
            )
        if findings:
            route = route_for(ExceptionType.CONFLICTING_DATA)
            exceptions.append(
                ExceptionEvent(
                    type=ExceptionType.CONFLICTING_DATA,
                    severity=route.severity,
                    detail="; ".join(findings),
                    route=route.route,
                    stage=Stage.DOC_VERIFICATION,
                )
            )

        return {
            "stage": Stage.INCOME_ANALYSIS,
            "extractions": extractions,
            "consistency_findings": findings,
            "current_min_confidence": confidence,
            "exceptions": exceptions,
            "timeline": [
                timeline_entry(
                    port,
                    Stage.DOC_VERIFICATION,
                    Actor.AGENT,
                    "Verified documents",
                    f"min_confidence={confidence:.2f}; findings={len(findings)}",
                )
            ],
        }

    return doc_verify


def make_redigitize_node(port: PlatformPort) -> Callable[[CaseState], dict]:
    """Automatic re-extraction pass: bump confidence using each document's reverify hint.

    A genuine OCR re-run can lift a borderline-confidence extraction; it cannot invent
    agreement between conflicting fields, so true conflicts still fall through to a human.
    """

    def redigitize(state: CaseState) -> dict:
        app = state["application"]
        improved = 0
        for doc in app.documents:
            reverify = doc.payload.get("reverify_confidence")
            if reverify is not None and reverify > doc.extraction_confidence:
                doc.extraction_confidence = float(reverify)
                improved += 1
        return {
            "verify_retry_count": state.get("verify_retry_count", 0) + 1,
            "timeline": [
                timeline_entry(
                    port,
                    Stage.DOC_VERIFICATION,
                    Actor.ROBOT,
                    "Re-digitised documents",
                    f"retry #{state.get('verify_retry_count', 0) + 1}; improved {improved} docs",
                )
            ],
        }

    return redigitize
