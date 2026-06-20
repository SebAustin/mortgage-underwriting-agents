from mortgage_agents.config import Settings
from mortgage_agents.ports import PlatformPort
from mortgage_agents.ports.local_adapter import LocalAdapter, MockProfile
from mortgage_agents.state import (
    AmlResult,
    Applicant,
    CreditProfile,
    DocType,
    Document,
    EmploymentType,
)


def _settings(tmp_path) -> Settings:
    return Settings(runtime_mode="local", llm_mode="stub", runtime_dir=str(tmp_path))


def _applicant(ssn="9999") -> Applicant:
    return Applicant(
        full_name="Pat Doe",
        ssn_last4=ssn,
        employment_type=EmploymentType.W2,
        stated_annual_income=100_000,
    )


def test_local_adapter_satisfies_port(tmp_path):
    adapter = LocalAdapter(_settings(tmp_path))
    assert isinstance(adapter, PlatformPort)


def test_extract_document_returns_payload(tmp_path):
    adapter = LocalAdapter(_settings(tmp_path))
    doc = Document(doc_type=DocType.W2, filename="w2.pdf", payload={"annual_wages": 100_000},
                   extraction_confidence=0.91)
    extraction = adapter.extract_document(doc)
    assert extraction.doc_type == DocType.W2
    assert extraction.fields["annual_wages"] == 100_000
    assert extraction.confidence == 0.91


def test_credit_and_aml_use_directory(tmp_path):
    directory = {
        "1212": MockProfile(
            credit=CreditProfile(score=801, monthly_debt_payments=100),
            aml=AmlResult(hit=True, risk_score=0.9, watchlists=["X"]),
        )
    }
    adapter = LocalAdapter(_settings(tmp_path), directory=directory)
    applicant = _applicant(ssn="1212")
    assert adapter.pull_credit(applicant).score == 801
    assert adapter.screen_aml(applicant).hit is True


def test_credit_falls_back_when_unknown(tmp_path):
    adapter = LocalAdapter(_settings(tmp_path))
    profile = adapter.pull_credit(_applicant())
    assert profile.score == 720  # deterministic default
    assert adapter.screen_aml(_applicant()).hit is False


def test_email_and_artifact_persist(tmp_path):
    adapter = LocalAdapter(_settings(tmp_path))
    adapter.send_borrower_email("a@b.com", "subj", "body")
    assert adapter.sent_emails[0]["to"] == "a@b.com"
    ref = adapter.emit_artifact("CASE-1", "letter.txt", "Decision: APPROVE")
    assert ref.endswith("letter.txt")
    with open(ref, encoding="utf-8") as fh:
        assert "APPROVE" in fh.read()


def test_clock_is_injectable(tmp_path):
    adapter = LocalAdapter(_settings(tmp_path), clock=lambda: "2026-01-01T00:00:00Z")
    assert adapter.now() == "2026-01-01T00:00:00Z"
