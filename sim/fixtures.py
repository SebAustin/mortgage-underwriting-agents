"""Deterministic mortgage personas used by the demo and the test-suite.

Each persona bundles the loan application, the canned external-service responses
(credit + AML, keyed by ssn_last4), the scripted human decisions for headless runs,
and the expected terminal decision. Together they exercise every case path and all
seven exception routes.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from mortgage_agents.ports.local_adapter import MockProfile
from mortgage_agents.state import (
    AmlResult,
    Applicant,
    CreditProfile,
    Decision,
    DocType,
    Document,
    EmploymentType,
    LoanApplication,
    LoanRequest,
)


@dataclass
class Persona:
    name: str
    description: str
    application: LoanApplication
    directory: dict[str, MockProfile]
    decisions: dict[str, str]  # gate -> choice for headless runs
    expected_decision: Decision
    expected_exceptions: list[str] = field(default_factory=list)


def _doc(doc_type: DocType, filename: str, confidence: float = 0.99, **payload) -> Document:
    return Document(
        doc_type=doc_type, filename=filename, payload=payload, extraction_confidence=confidence
    )


def _full_doc_set(name: str, employer: str, ssn: str, wages: float, balance: float,
                  appraised: float, paystub_employer: str | None = None) -> list[Document]:
    return [
        _doc(DocType.W2, "w2.pdf", name=name, ssn_last4=ssn, employer=employer, annual_wages=wages),
        _doc(DocType.PAY_STUB, "paystub.pdf", name=name, employer=paystub_employer or employer,
             monthly_gross=wages / 12, employment_months=36),
        _doc(DocType.BANK_STATEMENT, "bank.pdf", name=name, balance=balance),
        _doc(DocType.APPRAISAL, "appraisal.pdf", appraised_value=appraised),
    ]


def _clean_approve() -> Persona:
    ssn = "1111"
    app = LoanApplication(
        case_id="CASE-CLEAN",
        applicant=Applicant(full_name="Jordan Rivera", ssn_last4=ssn,
                            employment_type=EmploymentType.W2, employer="Acme Corp",
                            stated_annual_income=120000, monthly_debts=400,
                            email="jordan@example.com"),
        loan=LoanRequest(purchase_price=400000, loan_amount=320000, appraised_value=400000),
        documents=_full_doc_set("Jordan Rivera", "Acme Corp", ssn, 120000, 60000, 400000),
    )
    return Persona(
        name="clean_approve",
        description="Strong file: 760 score, 29% DTI, 80% LTV → straight-through approval.",
        application=app,
        directory={ssn: MockProfile(
            credit=CreditProfile(score=760, open_tradelines=6, derogatory_marks=0,
                                 monthly_debt_payments=400),
            aml=AmlResult(hit=False, risk_score=0.02))},
        decisions={"gate_b": "approve"},
        expected_decision=Decision.APPROVE,
    )


def _conditional_approve() -> Persona:
    ssn = "2222"
    app = LoanApplication(
        case_id="CASE-COND",
        applicant=Applicant(full_name="Sam Patel", ssn_last4=ssn,
                            employment_type=EmploymentType.W2, employer="Initech",
                            stated_annual_income=96000, monthly_debts=975,
                            email="sam@example.com"),
        loan=LoanRequest(purchase_price=400000, loan_amount=320000, appraised_value=400000),
        documents=_full_doc_set("Sam Patel", "Initech", ssn, 96000, 64000, 400000),
    )
    return Persona(
        name="conditional_approve",
        description="Borderline 44% DTI rescued by strong reserves & 760 score → Gate A then conditional.",
        application=app,
        directory={ssn: MockProfile(
            credit=CreditProfile(score=760, open_tradelines=7, derogatory_marks=0,
                                 monthly_debt_payments=975),
            aml=AmlResult(hit=False, risk_score=0.03))},
        decisions={"gate_a": "conditional_approve", "gate_b": "conditional_approve"},
        expected_decision=Decision.CONDITIONAL_APPROVE,
        expected_exceptions=["dti_exceeded"],
    )


def _decline() -> Persona:
    ssn = "3333"
    app = LoanApplication(
        case_id="CASE-DECLINE",
        applicant=Applicant(full_name="Casey Lin", ssn_last4=ssn,
                            employment_type=EmploymentType.W2, employer="Hooli",
                            stated_annual_income=72000, monthly_debts=1500,
                            email="casey@example.com"),
        loan=LoanRequest(purchase_price=400000, loan_amount=360000, appraised_value=400000),
        documents=_full_doc_set("Casey Lin", "Hooli", ssn, 72000, 5000, 400000),
    )
    return Persona(
        name="decline",
        description="Thin file: 580 score + 3 derogatories + high LTV → decline (human confirms).",
        application=app,
        directory={ssn: MockProfile(
            credit=CreditProfile(score=580, open_tradelines=2, derogatory_marks=3,
                                 monthly_debt_payments=1500),
            aml=AmlResult(hit=False, risk_score=0.10))},
        decisions={"gate_b": "decline"},
        expected_decision=Decision.DECLINE,
    )


def _fraud_exception() -> Persona:
    ssn = "4444"
    # Employer disagrees between W-2 (Acme) and pay stub (Globex) → conflicting data.
    docs = [
        _doc(DocType.W2, "w2.pdf", name="Morgan Gray", ssn_last4=ssn, employer="Acme Corp",
             annual_wages=110000),
        _doc(DocType.PAY_STUB, "paystub.pdf", name="Morgan Gray", employer="Globex Inc",
             monthly_gross=110000 / 12, employment_months=18),
        _doc(DocType.BANK_STATEMENT, "bank.pdf", name="Morgan Gray", balance=40000),
        _doc(DocType.APPRAISAL, "appraisal.pdf", appraised_value=400000),
    ]
    app = LoanApplication(
        case_id="CASE-FRAUD",
        applicant=Applicant(full_name="Morgan Gray", ssn_last4=ssn,
                            employment_type=EmploymentType.W2, employer="Acme Corp",
                            stated_annual_income=110000, monthly_debts=600,
                            email="morgan@example.com"),
        loan=LoanRequest(purchase_price=400000, loan_amount=320000, appraised_value=400000),
        documents=docs,
    )
    return Persona(
        name="fraud_exception",
        description="Conflicting employer (human verify) + AML watchlist hit → escalate to compliance.",
        application=app,
        directory={ssn: MockProfile(
            credit=CreditProfile(score=700, open_tradelines=5, derogatory_marks=1,
                                 monthly_debt_payments=600),
            aml=AmlResult(hit=True, risk_score=0.88, watchlists=["OFAC SDN"]))},
        decisions={"verify_field": "verified"},
        expected_decision=Decision.ESCALATED,
        expected_exceptions=["conflicting_data", "fraud_aml"],
    )


def _missing_docs() -> Persona:
    ssn = "5555"
    docs = [
        _doc(DocType.W2, "w2.pdf", name="Lee Brooks", ssn_last4=ssn, employer="Stark",
             annual_wages=130000),
        _doc(DocType.BANK_STATEMENT, "bank.pdf", name="Lee Brooks", balance=80000),
        # Missing PAY_STUB and APPRAISAL → request info.
    ]
    app = LoanApplication(
        case_id="CASE-MISSING",
        applicant=Applicant(full_name="Lee Brooks", ssn_last4=ssn,
                            employment_type=EmploymentType.W2, employer="Stark",
                            stated_annual_income=130000, monthly_debts=300,
                            email="lee@example.com"),
        loan=LoanRequest(purchase_price=420000, loan_amount=300000, appraised_value=420000),
        documents=docs,
    )
    return Persona(
        name="missing_docs",
        description="Required documents absent at intake → borrower request-info, case suspended.",
        application=app,
        directory={ssn: MockProfile(
            credit=CreditProfile(score=740, monthly_debt_payments=300),
            aml=AmlResult(hit=False, risk_score=0.02))},
        decisions={},
        expected_decision=Decision.INFO_REQUESTED,
        expected_exceptions=["missing_docs"],
    )


def _low_confidence_recovered() -> Persona:
    ssn = "6666"
    docs = _full_doc_set("Robin Vega", "Wayne Ent", ssn, 120000, 60000, 400000)
    # W-2 comes in at low confidence but a re-digitise pass recovers it (no human needed).
    docs[0] = _doc(DocType.W2, "w2.pdf", confidence=0.60, name="Robin Vega", ssn_last4=ssn,
                   employer="Wayne Ent", annual_wages=120000, reverify_confidence=0.95)
    app = LoanApplication(
        case_id="CASE-LOWCONF-OK",
        applicant=Applicant(full_name="Robin Vega", ssn_last4=ssn,
                            employment_type=EmploymentType.W2, employer="Wayne Ent",
                            stated_annual_income=120000, monthly_debts=400,
                            email="robin@example.com"),
        loan=LoanRequest(purchase_price=400000, loan_amount=320000, appraised_value=400000),
        documents=docs,
    )
    return Persona(
        name="low_confidence_recovered",
        description="Low OCR confidence auto-recovers on re-digitise → no human needed → approve.",
        application=app,
        directory={ssn: MockProfile(
            credit=CreditProfile(score=760, monthly_debt_payments=400),
            aml=AmlResult(hit=False, risk_score=0.02))},
        decisions={"gate_b": "approve"},
        expected_decision=Decision.APPROVE,
        expected_exceptions=["low_confidence"],
    )


def _low_confidence_human() -> Persona:
    ssn = "7777"
    docs = _full_doc_set("Avery Stone", "Cyberdyne", ssn, 120000, 60000, 400000)
    # Re-digitise does not improve confidence → human verification gate.
    docs[0] = _doc(DocType.W2, "w2.pdf", confidence=0.60, name="Avery Stone", ssn_last4=ssn,
                   employer="Cyberdyne", annual_wages=120000, reverify_confidence=0.60)
    app = LoanApplication(
        case_id="CASE-LOWCONF-HUMAN",
        applicant=Applicant(full_name="Avery Stone", ssn_last4=ssn,
                            employment_type=EmploymentType.W2, employer="Cyberdyne",
                            stated_annual_income=120000, monthly_debts=400,
                            email="avery@example.com"),
        loan=LoanRequest(purchase_price=400000, loan_amount=320000, appraised_value=400000),
        documents=docs,
    )
    return Persona(
        name="low_confidence_human",
        description="Low OCR confidence persists after re-digitise → human verify gate → approve.",
        application=app,
        directory={ssn: MockProfile(
            credit=CreditProfile(score=760, monthly_debt_payments=400),
            aml=AmlResult(hit=False, risk_score=0.02))},
        decisions={"verify_field": "verified", "gate_b": "approve"},
        expected_decision=Decision.APPROVE,
        expected_exceptions=["low_confidence"],
    )


def _appraisal_gap() -> Persona:
    ssn = "8888"
    app = LoanApplication(
        case_id="CASE-APPRAISAL",
        applicant=Applicant(full_name="Dana Frost", ssn_last4=ssn,
                            employment_type=EmploymentType.W2, employer="Umbrella",
                            stated_annual_income=120000, monthly_debts=400,
                            email="dana@example.com"),
        loan=LoanRequest(purchase_price=400000, loan_amount=340000, appraised_value=380000),
        documents=_full_doc_set("Dana Frost", "Umbrella", ssn, 120000, 60000, 380000),
    )
    return Persona(
        name="appraisal_gap",
        description="Appraisal $380k below $400k price → LTV recomputed on lesser value (89%), "
                    "appraisal-gap exception, still approvable.",
        application=app,
        directory={ssn: MockProfile(
            credit=CreditProfile(score=760, monthly_debt_payments=400),
            aml=AmlResult(hit=False, risk_score=0.02))},
        decisions={"gate_a": "approve", "gate_b": "approve"},
        expected_decision=Decision.APPROVE,
        expected_exceptions=["appraisal_gap"],
    )


_BUILDERS = [
    _clean_approve,
    _conditional_approve,
    _decline,
    _fraud_exception,
    _missing_docs,
    _low_confidence_recovered,
    _low_confidence_human,
    _appraisal_gap,
]

# The four "headline" personas shown in the demo.
HEADLINE = ["clean_approve", "conditional_approve", "decline", "fraud_exception"]


def all_personas() -> dict[str, Persona]:
    return {b().name: b() for b in _BUILDERS}


def get_persona(name: str) -> Persona:
    personas = all_personas()
    if name not in personas:
        raise KeyError(f"Unknown persona '{name}'. Available: {', '.join(personas)}")
    return personas[name]
