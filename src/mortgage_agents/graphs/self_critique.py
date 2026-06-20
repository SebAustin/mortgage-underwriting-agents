"""Self-critique deliberation for the AdjudicationAgent.

Given a preliminary policy evaluation, decide the final recommendation — crucially, how
to treat *borderline* files in light of compensating factors. This is where a marginal
DTI is either rescued (conditional approve) or declined.

The default implementation is deterministic. M5 swaps in a CrewAI "Credit Analyst vs
Risk Officer" debate behind the ``use_crew`` flag, returning the same structured verdict
so the graph is unaffected.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..llm import LLMProvider
from ..policy.underwriting_policy import PolicyEvaluation
from ..state import (
    Condition,
    CreditProfile,
    Decision,
    Financials,
    Metrics,
)


@dataclass
class Deliberation:
    decision: Decision
    confidence: float
    rationale: str
    conditions: list[Condition]
    compensating_factors: list[str]


def _conditions_for(evaluation: PolicyEvaluation, factors: list[str]) -> list[Condition]:
    conditions: list[Condition] = []
    for citation in evaluation.citations:
        if "(condition)" in citation:
            conditions.append(Condition(code="RESERVES", description=citation))
    if not conditions:
        conditions.append(
            Condition(code="VERIFY", description="Verify final income and asset documentation")
        )
    return conditions


def deliberate(
    evaluation: PolicyEvaluation,
    metrics: Metrics,
    credit: CreditProfile,
    financials: Financials,
    factors: list[str],
    llm: LLMProvider,
    use_crew: bool = False,
) -> Deliberation:
    """Produce the final recommendation from the preliminary policy evaluation."""

    if use_crew:
        try:
            from .crew_panel import run_credit_panel  # lazy: only if the crew extra is installed

            return run_credit_panel(evaluation, metrics, credit, financials, factors, llm)
        except Exception:
            # If CrewAI is unavailable or errors, fall back to the deterministic path.
            pass

    base = evaluation.preliminary_decision

    if base == Decision.APPROVE:
        rationale = "Clean file — all policy gates satisfied: " + "; ".join(evaluation.citations)
        return Deliberation(Decision.APPROVE, 0.92, rationale, [], factors)

    if base == Decision.DECLINE:
        rationale = "Hard policy breach — " + "; ".join(evaluation.failed_rules)
        return Deliberation(Decision.DECLINE, 0.85, rationale, [], factors)

    # Borderline / conditional — the interesting case.
    if factors:
        conditions = _conditions_for(evaluation, factors)
        rationale = (
            "Borderline metrics offset by compensating factors ("
            + "; ".join(factors)
            + "). Recommend conditional approval subject to: "
            + "; ".join(c.description for c in conditions)
        )
        return Deliberation(Decision.CONDITIONAL_APPROVE, 0.72, rationale, conditions, factors)

    rationale = (
        "Borderline metrics with no compensating factors ("
        + "; ".join(evaluation.citations)
        + ") — recommend decline."
    )
    return Deliberation(Decision.DECLINE, 0.6, rationale, [], factors)
