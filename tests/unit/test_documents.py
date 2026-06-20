from mortgage_agents.state import DocType, Document, DocumentExtraction
from mortgage_agents.tools.documents import (
    build_checklist,
    classify_document,
    cross_check_fields,
    min_confidence,
)


def test_classify_by_declared_type():
    doc = Document(doc_type=DocType.W2, filename="anything.pdf")
    assert classify_document(doc) == DocType.W2


def test_classify_by_filename_when_unknown():
    doc = Document(doc_type=DocType.UNKNOWN, filename="2024_paystub_march.pdf")
    assert classify_document(doc) == DocType.PAY_STUB


def test_classify_falls_back_to_unknown():
    doc = Document(doc_type=DocType.UNKNOWN, filename="mystery.bin")
    assert classify_document(doc) == DocType.UNKNOWN


def test_build_checklist_flags_missing():
    required = [DocType.W2, DocType.PAY_STUB, DocType.APPRAISAL]
    present = [DocType.W2, DocType.PAY_STUB]
    checklist, missing = build_checklist(required, present)
    assert checklist == {"w2": True, "pay_stub": True, "appraisal": False}
    assert missing == ["appraisal"]


def test_cross_check_detects_employer_conflict():
    extractions = [
        DocumentExtraction(doc_type=DocType.W2, fields={"employer": "Acme"}, confidence=0.99),
        DocumentExtraction(
            doc_type=DocType.PAY_STUB, fields={"employer": "Globex"}, confidence=0.99
        ),
    ]
    findings = cross_check_fields(extractions)
    assert any("employer" in f for f in findings)


def test_cross_check_passes_when_consistent():
    extractions = [
        DocumentExtraction(doc_type=DocType.W2, fields={"employer": "Acme", "name": "A"}, confidence=0.99),
        DocumentExtraction(doc_type=DocType.PAY_STUB, fields={"employer": "Acme", "name": "A"}, confidence=0.99),
    ]
    assert cross_check_fields(extractions) == []


def test_min_confidence():
    extractions = [
        DocumentExtraction(doc_type=DocType.W2, fields={}, confidence=0.6),
        DocumentExtraction(doc_type=DocType.PAY_STUB, fields={}, confidence=0.95),
    ]
    assert min_confidence(extractions) == 0.6
    assert min_confidence([]) == 1.0
