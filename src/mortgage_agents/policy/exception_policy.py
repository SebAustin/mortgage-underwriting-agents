"""Exception policy: the single table that maps every exception type to its route.

Track 1 (Maestro Case) is about exception-heavy work, so routing lives here as data —
auditable and unit-testable — rather than scattered through the agents. Each agent
*detects* an exception and records an :class:`ExceptionEvent`; the orchestrator's
routers consult this table to decide where the case goes next.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..state import ExceptionType, Severity


@dataclass(frozen=True)
class ExceptionRoute:
    type: ExceptionType
    severity: Severity
    route: str  # destination keyword the orchestrator understands
    max_retries: int
    escalate_to: str | None
    description: str


# Route keywords used by the orchestrator's conditional edges:
#   request_info        → email borrower for missing items, suspend case (terminal: info_requested)
#   reverify_then_human → automatic re-extraction once, then a human verify gate
#   adjudicate          → continue into adjudication (handled by policy/compensating factors)
#   recompute_then_human→ recompute affected metric, then a human review gate
#   escalate_compliance → hard stop, route to compliance human (terminal: escalated)
#   retry_backoff       → automatic exponential-backoff retry, then system escalation
EXCEPTION_ROUTES: dict[ExceptionType, ExceptionRoute] = {
    ExceptionType.MISSING_DOCS: ExceptionRoute(
        type=ExceptionType.MISSING_DOCS,
        severity=Severity.MEDIUM,
        route="request_info",
        max_retries=0,
        escalate_to=None,
        description="Required documents missing — request from borrower and suspend.",
    ),
    ExceptionType.LOW_CONFIDENCE: ExceptionRoute(
        type=ExceptionType.LOW_CONFIDENCE,
        severity=Severity.MEDIUM,
        route="reverify_then_human",
        max_retries=1,
        escalate_to="loan_processor",
        description="Extraction confidence below threshold — re-digitise once, then human verify.",
    ),
    ExceptionType.DTI_EXCEEDED: ExceptionRoute(
        type=ExceptionType.DTI_EXCEEDED,
        severity=Severity.MEDIUM,
        route="adjudicate",
        max_retries=0,
        escalate_to=None,
        description="DTI over policy — apply compensating factors → conditional or decline.",
    ),
    ExceptionType.FRAUD_AML: ExceptionRoute(
        type=ExceptionType.FRAUD_AML,
        severity=Severity.CRITICAL,
        route="escalate_compliance",
        max_retries=0,
        escalate_to="compliance",
        description="AML/fraud hit — hard escalate to compliance; case paused.",
    ),
    ExceptionType.APPRAISAL_GAP: ExceptionRoute(
        type=ExceptionType.APPRAISAL_GAP,
        severity=Severity.HIGH,
        route="recompute_then_human",
        max_retries=0,
        escalate_to="loan_officer",
        description="Appraised value below price — recompute LTV, then human review.",
    ),
    ExceptionType.CONFLICTING_DATA: ExceptionRoute(
        type=ExceptionType.CONFLICTING_DATA,
        severity=Severity.HIGH,
        route="reverify_then_human",
        max_retries=1,
        escalate_to="loan_processor",
        description="Cross-document mismatch — re-verify once, then human resolution.",
    ),
    ExceptionType.TRANSIENT_FAILURE: ExceptionRoute(
        type=ExceptionType.TRANSIENT_FAILURE,
        severity=Severity.LOW,
        route="retry_backoff",
        max_retries=3,
        escalate_to="system",
        description="Transient tool/API failure — exponential-backoff retry, then escalate.",
    ),
}


def route_for(exc_type: ExceptionType) -> ExceptionRoute:
    """Look up the route for an exception type."""

    return EXCEPTION_ROUTES[exc_type]
