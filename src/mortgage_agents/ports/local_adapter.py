"""LocalAdapter — the no-tenant implementation of :class:`PlatformPort`.

Everything is deterministic so the simulation and tests are fully reproducible:

* ``request_human_decision`` surfaces a LangGraph ``interrupt``; the sim layer (CLI inbox
  or scripted persona) supplies the resume value — exactly mirroring how UiPath Action
  Center would complete the task.
* ``extract_document`` returns the canned payload carried on the fixture document.
* ``pull_credit`` / ``screen_aml`` look the applicant up in a per-persona mock directory,
  falling back to sensible defaults so arbitrary applications still run.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from datetime import UTC, datetime

from pydantic import BaseModel

from ..config import Settings
from ..state import (
    AmlResult,
    Applicant,
    CreditProfile,
    Document,
    DocumentExtraction,
    HumanDecision,
    HumanTaskRequest,
)


class MockProfile(BaseModel):
    """Canned external-service responses for one applicant (keyed by ssn_last4)."""

    credit: CreditProfile
    aml: AmlResult


class LocalAdapter:
    """Deterministic, offline platform port."""

    def __init__(
        self,
        settings: Settings,
        directory: dict[str, MockProfile] | None = None,
        clock: Callable[[], str] | None = None,
    ) -> None:
        self.settings = settings
        self.directory: dict[str, MockProfile] = directory or {}
        self._clock = clock
        self.sent_emails: list[dict[str, str]] = []
        self.artifacts: list[str] = []

    # — Clock —
    def now(self) -> str:
        if self._clock is not None:
            return self._clock()
        return datetime.now(UTC).isoformat()

    # — Human-in-the-loop —
    def request_human_decision(self, request: HumanTaskRequest) -> HumanDecision:
        # Lazy import keeps the port usable outside a graph execution context in tests.
        from langgraph.types import interrupt

        resumed = interrupt(request.model_dump())
        if isinstance(resumed, HumanDecision):
            return resumed
        if isinstance(resumed, dict):
            data = {"gate": request.gate, **resumed}
            return HumanDecision(**data)
        raise TypeError(f"Unexpected resume value for human decision: {type(resumed)!r}")

    # — Document Understanding (canned) —
    def extract_document(self, document: Document) -> DocumentExtraction:
        return DocumentExtraction(
            doc_type=document.doc_type,
            fields=dict(document.payload),
            confidence=document.extraction_confidence,
        )

    # — External enterprise services —
    def pull_credit(self, applicant: Applicant) -> CreditProfile:
        profile = self.directory.get(applicant.ssn_last4)
        if profile is not None:
            return profile.credit
        # Deterministic fallback derived from stated profile.
        return CreditProfile(
            score=720,
            open_tradelines=5,
            derogatory_marks=0,
            monthly_debt_payments=applicant.monthly_debts,
        )

    def screen_aml(self, applicant: Applicant) -> AmlResult:
        profile = self.directory.get(applicant.ssn_last4)
        if profile is not None:
            return profile.aml
        return AmlResult(hit=False, risk_score=0.05, watchlists=[])

    def send_borrower_email(self, to: str, subject: str, body: str) -> None:
        record = {"to": to, "subject": subject, "body": body, "ts": self.now()}
        self.sent_emails.append(record)
        self._write("emails", f"email-{len(self.sent_emails)}.json", json.dumps(record, indent=2))

    def emit_artifact(self, case_id: str, name: str, content: str) -> str:
        path = self._write(os.path.join("artifacts", case_id), name, content)
        self.artifacts.append(path)
        return path

    def get_asset(self, name: str) -> str | None:
        return os.environ.get(name)

    # — helpers —
    def _write(self, subdir: str, name: str, content: str) -> str:
        base = os.path.join(self.settings.runtime_dir, subdir)
        os.makedirs(base, exist_ok=True)
        path = os.path.join(base, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        return path
