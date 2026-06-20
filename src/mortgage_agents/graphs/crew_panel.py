"""CrewAI deliberation panel — the external-framework showcase node.

Runs a two-agent debate (Credit Analyst vs Risk Officer) inside the governed UiPath
graph to decide borderline files. This is the "external framework inside a governed
orchestration layer" pattern the hackathon rewards.

It is fully sandboxed: imported lazily, requires the ``crew`` + ``live`` extras and a
live LLM, and raises on any problem so :func:`self_critique.deliberate` falls back to the
deterministic path. The deployable graph is never at risk if CrewAI is absent.
"""

from __future__ import annotations

import re

from ..config import get_settings
from ..llm import LLMProvider
from ..policy.underwriting_policy import PolicyEvaluation
from ..state import Condition, CreditProfile, Decision, Financials, Metrics
from .self_critique import Deliberation, _conditions_for

_PANEL_BACKSTORY_ANALYST = (
    "You are a seasoned mortgage credit analyst. You advocate for creditworthy borrowers "
    "by weighing compensating factors (reserves, credit depth, stable employment, equity) "
    "against marginal metrics, within agency guidelines."
)
_PANEL_BACKSTORY_RISK = (
    "You are a conservative risk officer. You stress-test optimistic readings, surface "
    "default risk, and insist that any approval be defensible and properly conditioned."
)


def run_credit_panel(
    evaluation: PolicyEvaluation,
    metrics: Metrics,
    credit: CreditProfile,
    financials: Financials,
    factors: list[str],
    llm: LLMProvider,
) -> Deliberation:
    """Run the CrewAI panel and map its verdict onto a :class:`Deliberation`.

    Raises if CrewAI / a live LLM is unavailable so the caller can fall back.
    """

    settings = get_settings()
    if settings.llm_mode != "live" or not settings.anthropic_api_key:
        raise RuntimeError("CrewAI panel requires LLM_MODE=live and an Anthropic API key")

    from crewai import LLM as CrewLLM
    from crewai import Agent, Crew, Process, Task  # noqa: F401 — lazy, optional dep

    crew_llm = CrewLLM(model=f"anthropic/{settings.llm_model}", api_key=settings.anthropic_api_key)

    context = (
        f"Metrics: back-end DTI {metrics.dti:.0%}, front-end {metrics.front_end_dti:.0%}, "
        f"LTV {metrics.ltv:.0%}. Credit score {credit.score}, "
        f"{credit.derogatory_marks} derogatories. "
        f"Reserves ${financials.liquid_reserves:,.0f}, employment "
        f"{financials.employment_stability_months} months. "
        f"Preliminary policy read: {evaluation.preliminary_decision.value}. "
        f"Compensating factors: {factors or 'none'}. "
        f"Policy citations: {evaluation.citations}."
    )

    analyst = Agent(role="Credit Analyst", goal="Argue the fair credit case for this borrower.",
                    backstory=_PANEL_BACKSTORY_ANALYST, llm=crew_llm, verbose=False)
    risk = Agent(role="Risk Officer", goal="Stress-test the file and protect the portfolio.",
                 backstory=_PANEL_BACKSTORY_RISK, llm=crew_llm, verbose=False)

    debate = Task(
        description=(
            "Debate this borderline mortgage file and reach a recommendation.\n" + context
        ),
        expected_output="A short paragraph capturing both viewpoints and a leaning.",
        agent=analyst,
    )
    verdict = Task(
        description=(
            "Synthesise the debate into a final verdict. Respond in EXACTLY this format:\n"
            "DECISION: <approve|conditional_approve|decline>\n"
            "CONFIDENCE: <0.0-1.0>\n"
            "RATIONALE: <one or two sentences>"
        ),
        expected_output="The structured DECISION/CONFIDENCE/RATIONALE block.",
        agent=risk,
        context=[debate],
    )

    crew = Crew(agents=[analyst, risk], tasks=[debate, verdict], process=Process.sequential,
                verbose=False)
    raw = str(crew.kickoff())
    return _parse_verdict(raw, evaluation, factors)


def _parse_verdict(raw: str, evaluation: PolicyEvaluation, factors: list[str]) -> Deliberation:
    """Map the panel's free-text verdict to a structured :class:`Deliberation`."""

    decision_match = re.search(r"DECISION:\s*(\w+)", raw, re.IGNORECASE)
    conf_match = re.search(r"CONFIDENCE:\s*([0-9.]+)", raw)
    rationale_match = re.search(r"RATIONALE:\s*(.+)", raw, re.IGNORECASE | re.DOTALL)

    try:
        decision = Decision(decision_match.group(1).strip().lower()) if decision_match else None
    except ValueError:
        decision = None
    if decision not in (Decision.APPROVE, Decision.CONDITIONAL_APPROVE, Decision.DECLINE):
        decision = Decision.CONDITIONAL_APPROVE if factors else Decision.DECLINE

    confidence = float(conf_match.group(1)) if conf_match else 0.7
    rationale = (
        rationale_match.group(1).strip()
        if rationale_match
        else "CrewAI panel deliberation (see debate transcript)."
    )
    conditions: list[Condition] = (
        _conditions_for(evaluation, factors)
        if decision == Decision.CONDITIONAL_APPROVE
        else []
    )
    return Deliberation(
        decision=decision,
        confidence=max(0.0, min(1.0, confidence)),
        rationale=f"[CrewAI panel] {rationale}",
        conditions=conditions,
        compensating_factors=factors,
    )
