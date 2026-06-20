"""UnderwritingAgent — turn verified documents into qualifying income, reserves, stability.

Branches on employment type (W-2 vs self-employed averaging) — the kind of multi-branch
calculation real underwriting requires — and produces the structured financials the
adjudication stage reasons over.
"""

from __future__ import annotations

from collections.abc import Callable

from ..llm import LLMProvider
from ..ports import PlatformPort
from ..state import (
    Actor,
    CaseState,
    DocType,
    EmploymentType,
    Financials,
    Stage,
)
from ..tools.finance import (
    qualifying_monthly_income_self_employed,
    qualifying_monthly_income_w2,
)
from ._helpers import field, find_extraction, timeline_entry


def make_underwriting_agent(port: PlatformPort, llm: LLMProvider) -> Callable[[CaseState], dict]:
    def income_analysis(state: CaseState) -> dict:
        app = state["application"]
        extractions = state.get("extractions", [])

        if app.applicant.employment_type == EmploymentType.W2:
            annual_wages = field(extractions, DocType.W2, "annual_wages")
            if annual_wages is None:
                annual_wages = app.applicant.stated_annual_income
            monthly_income = qualifying_monthly_income_w2(float(annual_wages))
            income_method = "W-2 annual wages / 12"
        else:
            tax_incomes = [
                float(e.fields["net_income"])
                for e in extractions
                if e.doc_type == DocType.TAX_RETURN and "net_income" in e.fields
            ]
            if not tax_incomes:
                tax_incomes = [app.applicant.stated_annual_income]
            monthly_income = qualifying_monthly_income_self_employed(tax_incomes)
            income_method = f"Avg of {len(tax_incomes)} yr self-employed net / 12"

        reserves = field(extractions, DocType.BANK_STATEMENT, "balance", default=0.0)
        stability = field(extractions, DocType.PAY_STUB, "employment_months", default=12)
        if find_extraction(extractions, DocType.PAY_STUB) is None:
            stability = field(extractions, DocType.TAX_RETURN, "employment_months", default=24)

        financials = Financials(
            qualifying_monthly_income=round(monthly_income, 2),
            liquid_reserves=float(reserves),
            monthly_debts=app.applicant.monthly_debts,
            employment_stability_months=int(stability),
            income_method=income_method,
        )

        return {
            "stage": Stage.ADJUDICATION,
            "financials": financials,
            "timeline": [
                timeline_entry(
                    port,
                    Stage.INCOME_ANALYSIS,
                    Actor.AGENT,
                    "Computed qualifying income",
                    f"${financials.qualifying_monthly_income:,.0f}/mo ({income_method}); "
                    f"reserves ${financials.liquid_reserves:,.0f}",
                )
            ],
        }

    return income_analysis
