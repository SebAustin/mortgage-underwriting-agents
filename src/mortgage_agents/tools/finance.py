"""Finance math used by the underwriting and adjudication agents.

Pure, deterministic functions — every number the agents reason over is computed here,
so the math is unit-testable independently of any LLM or platform.
"""

from __future__ import annotations


def monthly_payment(principal: float, annual_rate: float, term_months: int) -> float:
    """Fully-amortising monthly principal & interest payment."""

    if term_months <= 0:
        raise ValueError("term_months must be positive")
    if principal <= 0:
        return 0.0
    r = annual_rate / 12.0
    if r == 0:
        return principal / term_months
    factor = (1 + r) ** term_months
    return principal * r * factor / (factor - 1)


def qualifying_monthly_income_w2(annual_wages: float) -> float:
    """W-2 qualifying income: annual base wages / 12."""

    return max(annual_wages, 0.0) / 12.0


def qualifying_monthly_income_self_employed(annual_net_incomes: list[float]) -> float:
    """Self-employed qualifying income: average of available years / 12 (FNMA-style)."""

    vals = [v for v in annual_net_incomes if v is not None]
    if not vals:
        return 0.0
    return (sum(vals) / len(vals)) / 12.0


def compute_back_end_dti(
    monthly_debts: float, proposed_housing_payment: float, monthly_income: float
) -> float:
    """Back-end DTI = (all monthly debts + new housing payment) / monthly income."""

    if monthly_income <= 0:
        return float("inf")
    return (monthly_debts + proposed_housing_payment) / monthly_income


def compute_front_end_dti(proposed_housing_payment: float, monthly_income: float) -> float:
    """Front-end DTI = housing payment / monthly income."""

    if monthly_income <= 0:
        return float("inf")
    return proposed_housing_payment / monthly_income


def compute_ltv(loan_amount: float, property_value: float) -> float:
    """Loan-to-value = loan / value. Uses the value the caller supplies (typically the
    *lesser* of appraised value and purchase price)."""

    if property_value <= 0:
        return float("inf")
    return loan_amount / property_value


def compute_dscr(net_operating_income_monthly: float, debt_service_monthly: float) -> float:
    """Debt-service-coverage ratio (used for investment properties)."""

    if debt_service_monthly <= 0:
        return float("inf")
    return net_operating_income_monthly / debt_service_monthly


def lesser_of_value(appraised_value: float | None, purchase_price: float) -> float:
    """LTV must use the lesser of appraised value and purchase price."""

    if appraised_value is None:
        return purchase_price
    return min(appraised_value, purchase_price)
