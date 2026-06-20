"""Underwriting policy: thresholds, required documents, and rule evaluation.

Keeping the policy in one place (a) makes the credit logic auditable and testable and
(b) lets the :class:`AdjudicationAgent` cite the exact rules behind every recommendation.
All functions here are pure and deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..state import (
    CreditProfile,
    Decision,
    DocType,
    Financials,
    Metrics,
)


@dataclass(frozen=True)
class UnderwritingPolicy:
    # Debt-to-income
    max_back_end_dti: float = 0.43
    max_front_end_dti: float = 0.31
    borderline_dti_band: float = 0.03  # within this *above* the cap → borderline, not auto-decline
    # Loan-to-value
    max_ltv: float = 0.97
    borderline_ltv_band: float = 0.03
    # Credit
    min_credit_score: int = 620
    borderline_score_band: int = 20
    max_derogatory_marks: int = 2
    # Reserves
    min_reserves_months: float = 2.0
    # Required documents by loan program
    required_docs: dict[str, list[DocType]] = field(
        default_factory=lambda: {
            "conventional_30yr": [
                DocType.PAY_STUB,
                DocType.W2,
                DocType.BANK_STATEMENT,
                DocType.APPRAISAL,
            ],
            "self_employed_30yr": [
                DocType.TAX_RETURN,
                DocType.BANK_STATEMENT,
                DocType.APPRAISAL,
            ],
        }
    )


DEFAULT_POLICY = UnderwritingPolicy()


def required_docs_for(program: str, policy: UnderwritingPolicy = DEFAULT_POLICY) -> list[DocType]:
    """Documents required for a loan program (falls back to the conventional set)."""

    return policy.required_docs.get(program, policy.required_docs["conventional_30yr"])


@dataclass
class PolicyEvaluation:
    """Outcome of applying the policy matrix to a case's metrics."""

    preliminary_decision: Decision
    citations: list[str]
    failed_rules: list[str]
    borderline: bool


def compensating_factors(
    metrics: Metrics,
    credit: CreditProfile,
    financials: Financials,
    monthly_income: float,
    policy: UnderwritingPolicy = DEFAULT_POLICY,
) -> list[str]:
    """Identify factors that can offset a marginal weakness (FNMA-style)."""

    factors: list[str] = []
    reserves_months = financials.liquid_reserves / monthly_income if monthly_income else 0.0
    if reserves_months >= 6:
        factors.append(f"Strong liquid reserves ({reserves_months:.1f} months)")
    if credit.score >= 740:
        factors.append(f"Excellent credit score ({credit.score})")
    if financials.employment_stability_months >= 24:
        factors.append(
            f"Stable employment ({financials.employment_stability_months} months)"
        )
    if metrics.ltv <= 0.80:
        factors.append(f"Substantial equity (LTV {metrics.ltv:.0%})")
    return factors


def evaluate(
    metrics: Metrics,
    credit: CreditProfile,
    financials: Financials,
    monthly_income: float,
    policy: UnderwritingPolicy = DEFAULT_POLICY,
) -> PolicyEvaluation:
    """Apply the underwriting matrix and return a preliminary decision with citations.

    The decision is conservative-but-fair: hard breaches decline, marginal breaches are
    flagged ``borderline`` (eligible for human decision-support and compensating factors),
    and clean files approve.
    """

    citations: list[str] = []
    failed: list[str] = []
    borderline = False

    # — Credit score —
    if credit.score < policy.min_credit_score:
        if credit.score >= policy.min_credit_score - policy.borderline_score_band:
            borderline = True
            citations.append(
                f"Credit score {credit.score} below min {policy.min_credit_score} "
                f"but within borderline band"
            )
        else:
            failed.append(f"Credit score {credit.score} < {policy.min_credit_score}")
    else:
        citations.append(f"Credit score {credit.score} ≥ {policy.min_credit_score}")

    # — Derogatory marks —
    if credit.derogatory_marks > policy.max_derogatory_marks:
        failed.append(
            f"{credit.derogatory_marks} derogatory marks > {policy.max_derogatory_marks}"
        )

    # — Back-end DTI —
    if metrics.dti > policy.max_back_end_dti:
        if metrics.dti <= policy.max_back_end_dti + policy.borderline_dti_band:
            borderline = True
            citations.append(
                f"Back-end DTI {metrics.dti:.0%} over {policy.max_back_end_dti:.0%} "
                f"but within borderline band"
            )
        else:
            failed.append(f"Back-end DTI {metrics.dti:.0%} > {policy.max_back_end_dti:.0%}")
    else:
        citations.append(f"Back-end DTI {metrics.dti:.0%} ≤ {policy.max_back_end_dti:.0%}")

    # — LTV —
    if metrics.ltv > policy.max_ltv:
        if metrics.ltv <= policy.max_ltv + policy.borderline_ltv_band:
            borderline = True
            citations.append(
                f"LTV {metrics.ltv:.0%} over {policy.max_ltv:.0%} but within borderline band"
            )
        else:
            failed.append(f"LTV {metrics.ltv:.0%} > {policy.max_ltv:.0%}")
    else:
        citations.append(f"LTV {metrics.ltv:.0%} ≤ {policy.max_ltv:.0%}")

    # — Reserves —
    reserves_months = financials.liquid_reserves / monthly_income if monthly_income else 0.0
    if reserves_months < policy.min_reserves_months:
        # Reserves shortfall is a condition (marginal), not an automatic decline.
        borderline = True
        citations.append(
            f"Reserves {reserves_months:.1f}mo < required {policy.min_reserves_months:.1f}mo "
            f"(condition)"
        )

    # — Roll up — a hard failure declines outright; "borderline" only applies to an
    # otherwise-passing file with a marginal breach (eligible for the human Gate A).
    if failed:
        decision = Decision.DECLINE
        borderline = False
    elif borderline:
        decision = Decision.CONDITIONAL_APPROVE
    else:
        decision = Decision.APPROVE

    return PolicyEvaluation(
        preliminary_decision=decision,
        citations=citations,
        failed_rules=failed,
        borderline=borderline,
    )
