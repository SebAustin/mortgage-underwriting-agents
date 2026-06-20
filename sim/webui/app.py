"""The loan-officer desk — a small FastAPI app over the durable case runner.

Lets you start cases, watch the agent timeline, and act on the human gates (Gate A / B)
from a browser — the visual equivalent of the CLI inbox, useful for the demo video and
screenshots. Backed by the same ``runner`` + ``InboxStore`` as everything else.
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from mortgage_agents.config import Settings

from .. import runner
from ..fixtures import all_personas, get_persona
from ..inbox import InboxStore

_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")


def _state_view(state: dict | None) -> dict[str, Any]:
    """Flatten a CaseState into template-friendly primitives."""

    if not state:
        return {}
    rec = state.get("recommendation")
    metrics = state.get("metrics")
    credit = state.get("credit_profile")
    decision = state.get("terminal_decision")
    return {
        "applicant": state["application"].applicant.full_name,
        "loan_amount": state["application"].loan.loan_amount,
        "purchase_price": state["application"].loan.purchase_price,
        "stage": state.get("stage").value if state.get("stage") else "—",
        "terminal": state.get("terminal", False),
        "decision": decision.value if decision else None,
        "recommendation": {
            "decision": rec.decision.value,
            "confidence": rec.confidence,
            "rationale": rec.rationale,
            "borderline": rec.borderline,
            "citations": rec.policy_citations,
            "factors": rec.compensating_factors,
            "conditions": [c.description for c in rec.conditions],
        }
        if rec
        else None,
        "metrics": {"dti": metrics.dti, "front": metrics.front_end_dti, "ltv": metrics.ltv}
        if metrics
        else None,
        "credit_score": credit.score if credit else None,
        "exceptions": [{"type": e.type.value, "severity": e.severity.value, "detail": e.detail}
                       for e in state.get("exceptions", [])],
        "timeline": [{"stage": t.stage.value, "actor": t.actor.value, "action": t.action,
                      "detail": t.detail} for t in state.get("timeline", [])],
        "human_decisions": [{"gate": d.gate, "choice": d.choice, "by": d.decided_by}
                            for d in state.get("human_decisions", [])],
    }


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings(runtime_mode="local", llm_mode="stub")
    templates = Jinja2Templates(directory=_TEMPLATES_DIR)
    app = FastAPI(title="Mortgage Underwriting Desk")

    def store() -> InboxStore:
        return InboxStore(f"{settings.runtime_dir}/inbox.sqlite")

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request):
        st = store()
        ctx = {
            "personas": list(all_personas().values()),
            "cases": st.list_cases(),
            "pending": st.list_pending(),
        }
        st.close()
        return templates.TemplateResponse(request, "index.html", ctx)

    @app.post("/start")
    def start(persona: str = Form(...)):
        st = store()
        p = get_persona(persona)
        runner.start_case(p, st, settings=settings)
        st.close()
        return RedirectResponse(f"/case/{p.application.case_id}", status_code=303)

    @app.get("/case/{case_id}", response_class=HTMLResponse)
    def case_detail(request: Request, case_id: str):
        st = store()
        record = st.get_case(case_id)
        pending = [t for t in st.list_pending() if t.case_id == case_id]
        st.close()
        view = _state_view(runner.load_state(case_id, settings=settings))
        ctx = {
            "case_id": case_id,
            "record": record,
            "pending": pending[0] if pending else None,
            "view": view,
        }
        return templates.TemplateResponse(request, "case.html", ctx)

    @app.post("/resolve")
    def resolve(task_id: str = Form(...), choice: str = Form(...), note: str = Form(""),
                case_id: str = Form(...)):
        st = store()
        runner.resume(task_id, choice, note, st, settings=settings)
        st.close()
        return RedirectResponse(f"/case/{case_id}", status_code=303)

    return app


app = create_app()


def main() -> None:  # pragma: no cover - convenience launcher
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
