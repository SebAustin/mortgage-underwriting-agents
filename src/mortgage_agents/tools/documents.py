"""Document classification and cross-document consistency checks.

The classifier is a deterministic heuristic (filename + payload hints) with an optional
LLM assist; the cross-check reconciles identity/employer fields across documents — the
kind of mismatch that signals fraud or data-entry error in real underwriting.
"""

from __future__ import annotations

from ..state import DocType, Document, DocumentExtraction

_FILENAME_HINTS: dict[str, DocType] = {
    "paystub": DocType.PAY_STUB,
    "pay_stub": DocType.PAY_STUB,
    "payslip": DocType.PAY_STUB,
    "w2": DocType.W2,
    "w-2": DocType.W2,
    "bank": DocType.BANK_STATEMENT,
    "statement": DocType.BANK_STATEMENT,
    "tax": DocType.TAX_RETURN,
    "1040": DocType.TAX_RETURN,
    "appraisal": DocType.APPRAISAL,
    "id": DocType.ID,
    "license": DocType.ID,
    "passport": DocType.ID,
}


def classify_document(document: Document) -> DocType:
    """Classify a document by its declared type, else by filename heuristics."""

    if document.doc_type and document.doc_type != DocType.UNKNOWN:
        return document.doc_type
    name = document.filename.lower()
    for hint, doc_type in _FILENAME_HINTS.items():
        if hint in name:
            return doc_type
    return DocType.UNKNOWN


def build_checklist(
    required: list[DocType], present: list[DocType]
) -> tuple[dict[str, bool], list[str]]:
    """Return (checklist, missing) for a required-vs-present document comparison."""

    present_set = set(present)
    checklist = {dt.value: (dt in present_set) for dt in required}
    missing = [dt.value for dt in required if dt not in present_set]
    return checklist, missing


# Fields that must agree across documents for the same applicant.
_IDENTITY_FIELDS = ("name", "ssn_last4", "employer")


def cross_check_fields(extractions: list[DocumentExtraction]) -> list[str]:
    """Reconcile identity/employer fields across extractions; return mismatch findings."""

    findings: list[str] = []
    for key in _IDENTITY_FIELDS:
        values = {
            str(e.fields[key]).strip().lower()
            for e in extractions
            if key in e.fields and e.fields[key] not in (None, "")
        }
        if len(values) > 1:
            findings.append(
                f"Conflicting '{key}' across documents: {sorted(values)}"
            )
    return findings


def min_confidence(extractions: list[DocumentExtraction]) -> float:
    """Lowest extraction confidence across all documents (1.0 if none)."""

    if not extractions:
        return 1.0
    return min(e.confidence for e in extractions)
