import math

import pytest

from mortgage_agents.tools.finance import (
    compute_back_end_dti,
    compute_dscr,
    compute_front_end_dti,
    compute_ltv,
    lesser_of_value,
    monthly_payment,
    qualifying_monthly_income_self_employed,
    qualifying_monthly_income_w2,
)


def test_monthly_payment_amortizes():
    # 320k @ 7% over 30 years ≈ $2,129/mo
    assert monthly_payment(320_000, 0.07, 360) == pytest.approx(2129.30, abs=1.0)


def test_monthly_payment_zero_rate_is_straight_line():
    assert monthly_payment(120_000, 0.0, 120) == pytest.approx(1000.0)


def test_monthly_payment_zero_principal():
    assert monthly_payment(0, 0.07, 360) == 0.0


def test_monthly_payment_rejects_bad_term():
    with pytest.raises(ValueError):
        monthly_payment(100_000, 0.05, 0)


def test_qualifying_income_w2():
    assert qualifying_monthly_income_w2(120_000) == pytest.approx(10_000)


def test_qualifying_income_self_employed_averages_years():
    assert qualifying_monthly_income_self_employed([90_000, 110_000]) == pytest.approx(
        (100_000) / 12
    )


def test_qualifying_income_self_employed_empty():
    assert qualifying_monthly_income_self_employed([]) == 0.0


def test_back_end_dti():
    assert compute_back_end_dti(500, 2000, 10_000) == pytest.approx(0.25)


def test_dti_infinite_without_income():
    assert math.isinf(compute_back_end_dti(500, 2000, 0))
    assert math.isinf(compute_front_end_dti(2000, 0))


def test_front_end_dti():
    assert compute_front_end_dti(3100, 10_000) == pytest.approx(0.31)


def test_ltv():
    assert compute_ltv(320_000, 400_000) == pytest.approx(0.8)


def test_ltv_infinite_without_value():
    assert math.isinf(compute_ltv(100_000, 0))


def test_dscr():
    assert compute_dscr(3000, 2000) == pytest.approx(1.5)


def test_lesser_of_value_uses_minimum():
    assert lesser_of_value(360_000, 400_000) == 360_000
    assert lesser_of_value(420_000, 400_000) == 400_000
    assert lesser_of_value(None, 400_000) == 400_000
