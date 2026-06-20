from mortgage_agents.graphs.self_critique import deliberate
from mortgage_agents.llm.provider import StubLLM
from mortgage_agents.policy.underwriting_policy import PolicyEvaluation
from mortgage_agents.state import (
    CreditProfile,
    Decision,
    Financials,
    Metrics,
)

_LLM = StubLLM()
_METRICS = Metrics(dti=0.40, front_end_dti=0.30, ltv=0.85)
_CREDIT = CreditProfile(score=740, monthly_debt_payments=400)
_FIN = Financials(qualifying_monthly_income=10_000, liquid_reserves=60_000, monthly_debts=400,
                  employment_stability_months=36, income_method="W-2 annual wages / 12")


def _eval(decision, borderline, citations=None, failed=None):
    return PolicyEvaluation(
        preliminary_decision=decision,
        citations=citations or [],
        failed_rules=failed or [],
        borderline=borderline,
    )


def test_approve_passthrough():
    d = deliberate(_eval(Decision.APPROVE, False, ["all gates ok"]), _METRICS, _CREDIT, _FIN, [], _LLM)
    assert d.decision == Decision.APPROVE
    assert d.conditions == []


def test_hard_decline():
    d = deliberate(_eval(Decision.DECLINE, False, failed=["score too low"]), _METRICS, _CREDIT,
                   _FIN, [], _LLM)
    assert d.decision == Decision.DECLINE


def test_borderline_with_factors_is_conditional():
    d = deliberate(_eval(Decision.CONDITIONAL_APPROVE, True, ["DTI over (condition)"]),
                   _METRICS, _CREDIT, _FIN, ["Strong reserves (8 months)"], _LLM)
    assert d.decision == Decision.CONDITIONAL_APPROVE
    assert d.conditions  # at least one condition attached


def test_borderline_without_factors_declines():
    d = deliberate(_eval(Decision.CONDITIONAL_APPROVE, True, ["DTI over"]),
                   _METRICS, _CREDIT, _FIN, [], _LLM)
    assert d.decision == Decision.DECLINE


def test_use_crew_falls_back_when_unavailable():
    # In stub mode the CrewAI panel raises (no live LLM); deliberate must fall back cleanly.
    d = deliberate(_eval(Decision.CONDITIONAL_APPROVE, True, ["DTI over (condition)"]),
                   _METRICS, _CREDIT, _FIN, ["Strong reserves (8 months)"], _LLM, use_crew=True)
    assert d.decision == Decision.CONDITIONAL_APPROVE  # deterministic fallback still works
