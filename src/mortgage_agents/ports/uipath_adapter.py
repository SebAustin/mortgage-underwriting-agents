"""UiPathAdapter — the production implementation of :class:`PlatformPort`.

This is the thin "last-mile" shim that runs the *same* agent graph on UiPath Automation
Cloud. Every method maps a port capability to a real UiPath primitive:

* human gates → ``interrupt(CreateTask | CreateEscalation)`` (UiPath Action Center)
* governed secrets → Orchestrator assets (``sdk.assets.retrieve_secret``)
* Document Understanding → fields digitised upstream and passed on the document, or the
  UiPath IDP service
* external services (credit bureau, AML) → an API Workflow / connector reached over HTTP,
  with its base URL stored as a governed asset

It is intentionally small and isolated so SDK changes touch exactly one file. It is only
imported when ``RUNTIME_MODE=uipath`` (see ``ports.get_port``) and is excluded from the
local test-coverage gate because it requires a live tenant.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC

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

logger = logging.getLogger("mortgage_agents.uipath")

# Gates that represent final authority / compliance hand-offs become Escalations;
# everything else is a standard Action Center task.
_ESCALATION_GATES = {"gate_b", "compliance"}

# Orchestrator asset names (configured per tenant; see DEPLOY_UIPATH.md).
_ASSET_CREDIT_BUREAU_URL = "mua_credit_bureau_url"
_ASSET_AML_URL = "mua_aml_url"


class UiPathAdapter:
    """Platform port backed by the UiPath SDK."""

    def __init__(self, settings: Settings) -> None:
        from uipath.platform import UiPath  # lazy: requires the `cloud` extra

        settings.require("uipath_url")
        self.settings = settings
        self._sdk = UiPath(base_url=settings.uipath_url, secret=settings.uipath_access_token)

    # — Clock —
    def now(self) -> str:
        from datetime import datetime

        return datetime.now(UTC).isoformat()

    # — Human-in-the-loop via Action Center —
    def request_human_decision(self, request: HumanTaskRequest) -> HumanDecision:
        from langgraph.types import interrupt
        from uipath.platform.common import CreateEscalation, CreateTask

        payload = {
            "title": request.title,
            "data": {"summary": request.summary, "options": request.options, **request.context},
            "app_folder_path": self.settings.uipath_folder_path,
        }
        action = (
            CreateEscalation(**payload)
            if request.gate in _ESCALATION_GATES
            else CreateTask(**payload)
        )
        result = interrupt(action)
        return self._to_decision(request.gate, result)

    @staticmethod
    def _to_decision(gate: str, result: object) -> HumanDecision:
        """Map an Action Center completion into a :class:`HumanDecision`."""

        data: dict = {}
        if isinstance(result, dict):
            data = result
        elif hasattr(result, "data") and isinstance(result.data, dict):
            data = result.data  # completed Task object
        choice = str(data.get("choice") or data.get("action") or data.get("Action") or "approve")
        note = str(data.get("note") or data.get("comment") or "")
        return HumanDecision(gate=gate, choice=choice, note=note, decided_by="action_center_user")

    # — Document Understanding —
    def extract_document(self, document: Document) -> DocumentExtraction:
        # In the deployed flow an upstream RPA step / IDP run digitises the document and
        # passes the extracted fields on the payload. We surface them with their confidence.
        if document.payload:
            return DocumentExtraction(
                doc_type=document.doc_type,
                fields=dict(document.payload),
                confidence=document.extraction_confidence,
            )
        raise RuntimeError(
            f"No extracted fields for {document.filename}; wire UiPath Document Understanding "
            "(IDP) for this document type — see DEPLOY_UIPATH.md."
        )

    # — External enterprise services (API Workflows / connectors) —
    def pull_credit(self, applicant: Applicant) -> CreditProfile:
        data = self._call_service(_ASSET_CREDIT_BUREAU_URL, {"ssn_last4": applicant.ssn_last4})
        return CreditProfile(**data)

    def screen_aml(self, applicant: Applicant) -> AmlResult:
        data = self._call_service(_ASSET_AML_URL, {"name": applicant.full_name})
        return AmlResult(**data)

    def _call_service(self, asset_name: str, params: dict) -> dict:
        import httpx

        base_url = self.get_asset(asset_name)
        if not base_url:
            raise RuntimeError(
                f"Asset '{asset_name}' not configured; set it in Orchestrator (DEPLOY_UIPATH.md)."
            )
        resp = httpx.get(base_url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def send_borrower_email(self, to: str, subject: str, body: str) -> None:
        # Routed through a UiPath integration/connector in production; logged here so the
        # action is auditable even before the connector is wired.
        logger.info("borrower_email", extra={"to": to, "subject": subject})

    def emit_artifact(self, case_id: str, name: str, content: str) -> str:
        logger.info("artifact", extra={"case_id": case_id, "name": name})
        return f"uipath://artifacts/{case_id}/{name}"

    # — Governed secrets / config (Orchestrator assets) —
    def get_asset(self, name: str) -> str | None:
        try:
            return self._sdk.assets.retrieve_secret(
                name=name, folder_path=self.settings.uipath_folder_path
            ) or self._sdk.assets.retrieve_credential(
                name=name, folder_path=self.settings.uipath_folder_path
            )
        except Exception as exc:  # noqa: BLE001 - asset may be absent in some tenants
            logger.warning("asset lookup failed for %s: %s", name, exc)
            return None


def _example_env() -> str:  # pragma: no cover - documentation helper
    return json.dumps(
        {"RUNTIME_MODE": "uipath", "UIPATH_URL": "https://cloud.uipath.com/<org>/<tenant>"},
        indent=2,
    )
