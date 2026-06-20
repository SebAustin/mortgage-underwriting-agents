"""The :class:`PlatformPort` protocol — every side-effecting capability an agent needs.

This is the single interface that decouples agent reasoning from the platform. The
exact same agent graph runs against a mocked ``LocalAdapter`` or a real ``UiPathAdapter``
because both honour this contract.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..state import (
    AmlResult,
    Applicant,
    CreditProfile,
    Document,
    DocumentExtraction,
    HumanDecision,
    HumanTaskRequest,
)


@runtime_checkable
class PlatformPort(Protocol):
    """Capabilities the underwriting agents call out to.

    Implementations MUST be deterministic given the same inputs in local mode so the
    simulation and tests are reproducible.
    """

    # — Clock (injected so timelines are testable) —
    def now(self) -> str:
        """Return an ISO-8601 timestamp string."""
        ...

    # — Human-in-the-loop —
    def request_human_decision(self, request: HumanTaskRequest) -> HumanDecision:
        """Pause the case and route a decision to a human.

        Local: surfaces a LangGraph ``interrupt`` that the Action Inbox resolves.
        Cloud: creates a UiPath Action Center task/escalation and resumes on completion.
        The returned :class:`HumanDecision` carries the human's choice and notes.
        """
        ...

    # — Document Understanding (IDP) —
    def extract_document(self, document: Document) -> DocumentExtraction:
        """Digitise/extract structured fields from a document, with a confidence score."""
        ...

    # — External enterprise services —
    def pull_credit(self, applicant: Applicant) -> CreditProfile:
        """Pull a credit profile from the bureau."""
        ...

    def screen_aml(self, applicant: Applicant) -> AmlResult:
        """Run an AML / fraud watchlist screen."""
        ...

    def send_borrower_email(self, to: str, subject: str, body: str) -> None:
        """Notify the borrower (e.g. request missing documents)."""
        ...

    def emit_artifact(self, case_id: str, name: str, content: str) -> str:
        """Persist a generated artifact (e.g. a commitment/decline letter). Returns a ref."""
        ...

    # — Governed secrets/config (Orchestrator assets in cloud) —
    def get_asset(self, name: str) -> str | None:
        """Fetch a governed configuration value / secret by name."""
        ...
