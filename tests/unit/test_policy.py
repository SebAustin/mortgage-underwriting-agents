import pytest

from mortgage_agents.policy.exception_policy import EXCEPTION_ROUTES, route_for
from mortgage_agents.policy.underwriting_policy import (
    compensating_factors,
    evaluate,
)
from mortgage_agents.state import (
    CreditProfile,
    Decision,
    ExceptionType,
    Financials,
    Metrics,
)


def _fin(income=10_000, reserves=60_000, debts=400, stability=36):
    return Financials(
        qualifying_monthly_income=income,
        liquid_reserves=reserves,
        monthly_debts=debts,
        employment_stability_months=stability,
        income_method="W-2 annual wages / 12",
    )


def test_clean_file_approves():
    metrics = Metrics(dti=0.29, front_end_dti=0.25, ltv=0.80)
    credit = CreditProfile(score=760, monthly_debt_payments=400)
    result = evaluate(metrics, credit, _fin(), 10_000)
    assert result.preliminary_decision == Decision.APPROVE
    assert result.borderline is False
    assert result.failed_rules == []


def test_marginal_dti_is_borderline_conditional():
    metrics = Metrics(dti=0.44, front_end_dti=0.31, ltv=0.80)
    credit = CreditProfile(score=760, monthly_debt_payments=975)
    result = evaluate(metrics, credit, _fin(income=8000, reserves=64_000, debts=975), 8000)
    assert result.preliminary_decision == Decision.CONDITIONAL_APPROVE
    assert result.borderline is True


def test_hard_failure_declines_and_is_not_borderline():
    metrics = Metrics(dti=0.72, front_end_dti=0.5, ltv=0.90)
    credit = CreditProfile(score=580, derogatory_marks=3, monthly_debt_payments=1500)
    result = evaluate(metrics, credit, _fin(income=6000, reserves=5000, debts=1500), 6000)
    assert result.preliminary_decision == Decision.DECLINE
    assert result.borderline is False
    assert result.failed_rules  # at least one hard breach cited


def test_reserves_shortfall_makes_otherwise_clean_file_conditional():
    metrics = Metrics(dti=0.29, front_end_dti=0.25, ltv=0.80)
    credit = CreditProfile(score=760, monthly_debt_payments=400)
    # reserves of 1 month (< 2 month minimum)
    result = evaluate(metrics, credit, _fin(reserves=10_000), 10_000)
    assert result.preliminary_decision == Decision.CONDITIONAL_APPROVE
    assert result.borderline is True


def test_compensating_factors_detected():
    metrics = Metrics(dti=0.44, front_end_dti=0.31, ltv=0.80)
    credit = CreditProfile(score=760, monthly_debt_payments=975)
    factors = compensating_factors(metrics, credit, _fin(income=8000, reserves=64_000), 8000)
    assert any("reserves" in f.lower() for f in factors)
    assert any("credit score" in f.lower() for f in factors)


@pytest.mark.parametrize(
    "exc_type,expected_route,expected_retries",
    [
        (ExceptionType.MISSING_DOCS, "request_info", 0),
        (ExceptionType.LOW_CONFIDENCE, "reverify_then_human", 1),
        (ExceptionType.DTI_EXCEEDED, "adjudicate", 0),
        (ExceptionType.FRAUD_AML, "escalate_compliance", 0),
        (ExceptionType.APPRAISAL_GAP, "recompute_then_human", 0),
        (ExceptionType.CONFLICTING_DATA, "reverify_then_human", 1),
        (ExceptionType.TRANSIENT_FAILURE, "retry_backoff", 3),
    ],
)
def test_exception_route_table(exc_type, expected_route, expected_retries):
    route = route_for(exc_type)
    assert route.route == expected_route
    assert route.max_retries == expected_retries


def test_every_exception_type_has_a_route():
    for exc_type in ExceptionType:
        assert exc_type in EXCEPTION_ROUTES
