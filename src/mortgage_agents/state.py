"""Domain models and the LangGraph case state.

These Pydantic models are the single source of truth for what a mortgage case
carries through the Maestro stages. The graph state (:class:`CaseState`) is a
``TypedDict`` so LangGraph nodes can return partial updates; list fields that
accumulate across nodes use ``operator.add`` reducers.
"""

from __future__ import annotations

import operator
from enum import Enum
from typing import Annotated, Any, TypedDict

from pydantic import BaseModel, Field

# ─────────────────────────────────────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────────────────────────────────────


class Stage(str, Enum):
    """The Maestro case stages, in order."""

    INTAKE = "intake"
    DOC_VERIFICATION = "doc_verification"
    INCOME_ANALYSIS = "income_analysis"
    ADJUDICATION = "adjudication"
    CONDITIONS = "conditions"
    DECISION = "decision"
    CLOSED = "closed"


class Decision(str, Enum):
    APPROVE = "approve"
    CONDITIONAL_APPROVE = "conditional_approve"
    DECLINE = "decline"
    ESCALATED = "escalated"
    INFO_REQUESTED = "info_requested"
    PENDING = "pending"


class Actor(str, Enum):
    ROBOT = "robot"
    AGENT = "agent"
    HUMAN = "human"
    SYSTEM = "system"


class ExceptionType(str, Enum):
    MISSING_DOCS = "missing_docs"
    LOW_CONFIDENCE = "low_confidence"
    DTI_EXCEEDED = "dti_exceeded"
    FRAUD_AML = "fraud_aml"
    APPRAISAL_GAP = "appraisal_gap"
    CONFLICTING_DATA = "conflicting_data"
    TRANSIENT_FAILURE = "transient_failure"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EmploymentType(str, Enum):
    W2 = "w2"
    SELF_EMPLOYED = "self_employed"


class DocType(str, Enum):
    PAY_STUB = "pay_stub"
    W2 = "w2"
    BANK_STATEMENT = "bank_statement"
    TAX_RETURN = "tax_return"
    APPRAISAL = "appraisal"
    ID = "id"
    UNKNOWN = "unknown"


# ─────────────────────────────────────────────────────────────────────────────
# Application & documents
# ─────────────────────────────────────────────────────────────────────────────


class Applicant(BaseModel):
    full_name: str
    ssn_last4: str
    employment_type: EmploymentType
    employer: str | None = None
    stated_annual_income: float
    monthly_debts: float = 0.0
    email: str = "borrower@example.com"


class LoanRequest(BaseModel):
    loan_program: str = "conventional_30yr"
    purchase_price: float
    loan_amount: float
    appraised_value: float | None = None
    interest_rate: float = 0.07
    term_months: int = 360
    occupancy: str = "primary"


class Document(BaseModel):
    doc_type: DocType
    filename: str
    # In local mode the document's "content" is a canned extraction payload that the
    # mock Document Understanding service returns. In cloud mode this would be a file ref.
    payload: dict[str, Any] = Field(default_factory=dict)
    extraction_confidence: float = 0.99


class LoanApplication(BaseModel):
    case_id: str
    applicant: Applicant
    loan: LoanRequest
    documents: list[Document] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Derived / analysis artifacts
# ─────────────────────────────────────────────────────────────────────────────


class DocumentExtraction(BaseModel):
    doc_type: DocType
    fields: dict[str, Any]
    confidence: float


class CreditProfile(BaseModel):
    score: int
    open_tradelines: int = 0
    derogatory_marks: int = 0
    monthly_debt_payments: float = 0.0


class AmlResult(BaseModel):
    hit: bool
    risk_score: float
    watchlists: list[str] = Field(default_factory=list)


class Financials(BaseModel):
    qualifying_monthly_income: float
    liquid_reserves: float
    monthly_debts: float
    employment_stability_months: int
    income_method: str


class Metrics(BaseModel):
    dti: float  # back-end debt-to-income ratio (fraction, e.g. 0.43)
    front_end_dti: float
    ltv: float  # loan-to-value (fraction)
    dscr: float | None = None


class Condition(BaseModel):
    code: str
    description: str
    cleared: bool = False


class Recommendation(BaseModel):
    decision: Decision
    confidence: float
    rationale: str
    conditions: list[Condition] = Field(default_factory=list)
    policy_citations: list[str] = Field(default_factory=list)
    borderline: bool = False
    compensating_factors: list[str] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Exceptions, human gates, audit timeline
# ─────────────────────────────────────────────────────────────────────────────


class ExceptionEvent(BaseModel):
    type: ExceptionType
    severity: Severity
    detail: str
    route: str
    stage: Stage
    resolved: bool = False


class HumanTaskRequest(BaseModel):
    """A request for a human decision — maps to a UiPath Action Center task/escalation."""

    gate: str
    title: str
    summary: str
    options: list[str]
    context: dict[str, Any] = Field(default_factory=dict)


class HumanDecision(BaseModel):
    gate: str
    choice: str
    note: str = ""
    decided_by: str = "loan_officer"
    decided_at: str = ""


class TimelineEntry(BaseModel):
    ts: str
    stage: Stage
    actor: Actor
    action: str
    detail: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Graph state
# ─────────────────────────────────────────────────────────────────────────────


class CaseState(TypedDict, total=False):
    """LangGraph state for a single mortgage case."""

    case_id: str
    application: LoanApplication
    stage: Stage

    # intake
    doc_checklist: dict[str, bool]
    missing_docs: list[str]

    # document verification
    extractions: list[DocumentExtraction]
    consistency_findings: list[str]
    current_min_confidence: float
    verify_retry_count: int

    # income / asset analysis
    financials: Financials | None

    # adjudication
    credit_profile: CreditProfile | None
    metrics: Metrics | None
    recommendation: Recommendation | None

    # conditions / exceptions
    aml_result: AmlResult | None
    conditions: list[Condition]

    # accumulating audit fields (reducers append)
    exceptions: Annotated[list[ExceptionEvent], operator.add]
    human_decisions: Annotated[list[HumanDecision], operator.add]
    timeline: Annotated[list[TimelineEntry], operator.add]

    # terminal
    terminal: bool
    terminal_decision: Decision | None


def new_case_state(application: LoanApplication) -> CaseState:
    """Build the initial state for a fresh case."""

    return CaseState(
        case_id=application.case_id,
        application=application,
        stage=Stage.INTAKE,
        doc_checklist={},
        missing_docs=[],
        extractions=[],
        consistency_findings=[],
        verify_retry_count=0,
        financials=None,
        credit_profile=None,
        metrics=None,
        recommendation=None,
        aml_result=None,
        conditions=[],
        exceptions=[],
        human_decisions=[],
        timeline=[],
        terminal=False,
        terminal_decision=None,
    )
