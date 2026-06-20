"""AdjudicationAgent — the reasoning centerpiece.

Pulls credit (with transient-failure retry), computes DTI/LTV/front-end DTI, applies the
underwriting policy matrix, runs a self-critique deliberation over compensating factors,
and emits a recommendation with rationale, confidence, conditions, and policy citations.
Flags borderline files for the human decision-support gate (Gate A).
"""

from __future__ import annotations

from collections.abc import Callable

from ..llm import LLMProvider
from ..policy.exception_policy import route_for
from ..policy.underwriting_policy import (
    DEFAULT_POLICY,
    compensating_factors,
    evaluate,
)
from ..ports import PlatformPort
from ..state import (
    Actor,
    CaseState,
    ExceptionEvent,
    ExceptionType,
    Metrics,
    Recommendation,
    Stage,
)
from ..tools.finance import (
    compute_back_end_dti,
    compute_front_end_dti,
    compute_ltv,
    lesser_of_value,
    monthly_payment,
)
from ..tools.resilience import RetryExhausted, call_with_retries
from ._helpers import timeline_entry
from .self_critique import deliberate

# Annual taxes + insurance as a fraction of value, used to estimate the escrow portion
# of the housing payment.
ESCROW_RATE_ANNUAL = 0.0125


def make_adjudication_agent(
    port: PlatformPort, llm: LLMProvider, use_crew: bool = False
) -> Callable[[CaseState], dict]:
    def adjudication(state: CaseState) -> dict:
        app = state["application"]
        fin = state["financials"]
        assert fin is not None, "income analysis must run before adjudication"

        # — Credit pull with transient-failure retry —
        retries = route_for(ExceptionType.TRANSIENT_FAILURE).max_retries
        try:
            credit = call_with_retries(
                lambda: port.pull_credit(app.applicant),
                max_retries=retries,
                base_delay=0.0,
            )
        except RetryExhausted as exc:
            route = route_for(ExceptionType.TRANSIENT_FAILURE)
            return {
                "stage": Stage.CONDITIONS,
                "exceptions": [
                    ExceptionEvent(
                        type=ExceptionType.TRANSIENT_FAILURE,
                        severity=route.severity,
                        detail=f"Credit bureau unavailable: {exc}",
                        route=route.route,
                        stage=Stage.ADJUDICATION,
                    )
                ],
                "timeline": [
                    timeline_entry(
                        port,
                        Stage.ADJUDICATION,
                        Actor.SYSTEM,
                        "Credit pull failed after retries",
                        str(exc),
                    )
                ],
            }

        # — Metrics —
        value = lesser_of_value(app.loan.appraised_value, app.loan.purchase_price)
        pni = monthly_payment(app.loan.loan_amount, app.loan.interest_rate, app.loan.term_months)
        escrow = value * ESCROW_RATE_ANNUAL / 12.0
        housing_payment = pni + escrow
        # Use the bureau-reported obligations as authoritative (avoids double-counting the
        # applicant-declared figure, which is collected at intake for reference only).
        total_monthly_debts = max(credit.monthly_debt_payments, fin.monthly_debts)

        income = fin.qualifying_monthly_income
        metrics = Metrics(
            dti=round(compute_back_end_dti(total_monthly_debts, housing_payment, income), 4),
            front_end_dti=round(compute_front_end_dti(housing_payment, income), 4),
            ltv=round(compute_ltv(app.loan.loan_amount, value), 4),
        )

        # — Exceptions surfaced during adjudication —
        exceptions: list[ExceptionEvent] = []
        if metrics.dti > DEFAULT_POLICY.max_back_end_dti:
            r = route_for(ExceptionType.DTI_EXCEEDED)
            exceptions.append(
                ExceptionEvent(
                    type=ExceptionType.DTI_EXCEEDED,
                    severity=r.severity,
                    detail=f"Back-end DTI {metrics.dti:.0%} over {DEFAULT_POLICY.max_back_end_dti:.0%}",
                    route=r.route,
                    stage=Stage.ADJUDICATION,
                )
            )
        if app.loan.appraised_value is not None and app.loan.appraised_value < app.loan.purchase_price:
            r = route_for(ExceptionType.APPRAISAL_GAP)
            exceptions.append(
                ExceptionEvent(
                    type=ExceptionType.APPRAISAL_GAP,
                    severity=r.severity,
                    detail=(
                        f"Appraised ${app.loan.appraised_value:,.0f} below price "
                        f"${app.loan.purchase_price:,.0f}; LTV recomputed on lesser value"
                    ),
                    route=r.route,
                    stage=Stage.ADJUDICATION,
                )
            )

        # — Policy evaluation + self-critique deliberation —
        evaluation = evaluate(metrics, credit, fin, income)
        factors = compensating_factors(metrics, credit, fin, income)
        verdict = deliberate(evaluation, metrics, credit, fin, factors, llm, use_crew=use_crew)

        recommendation = Recommendation(
            decision=verdict.decision,
            confidence=verdict.confidence,
            rationale=verdict.rationale,
            conditions=verdict.conditions,
            policy_citations=evaluation.citations,
            borderline=evaluation.borderline,
            compensating_factors=verdict.compensating_factors,
        )

        return {
            "stage": Stage.CONDITIONS,
            "credit_profile": credit,
            "metrics": metrics,
            "recommendation": recommendation,
            "exceptions": exceptions,
            "timeline": [
                timeline_entry(
                    port,
                    Stage.ADJUDICATION,
                    Actor.AGENT,
                    f"Adjudicated: {verdict.decision.value}",
                    f"DTI {metrics.dti:.0%}, LTV {metrics.ltv:.0%}, score {credit.score}, "
                    f"borderline={evaluation.borderline}",
                )
            ],
        }

    return adjudication
