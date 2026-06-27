"""Capture REAL run data from the solution for the demo video.

Runs the headline personas through the actual agent graph and the durable inbox flow,
then writes the genuine results (decisions, metrics, timelines, gate tasks) to
``video/assets/runs.json``. The video renderer consumes this — so every number and line on
screen is real program output, not a mockup.
"""

from __future__ import annotations

import json
import os
import tempfile

from mortgage_agents.config import Settings
from sim import runner
from sim.fixtures import get_persona
from sim.inbox import InboxStore

HEADLINE = ["clean_approve", "conditional_approve", "decline", "fraud_exception"]
OUT = os.path.join(os.path.dirname(__file__), "assets", "runs.json")


def _metrics(m) -> dict | None:
    if not m:
        return None
    return {"dti": m.dti, "front_end_dti": m.front_end_dti, "ltv": m.ltv}


def _capture_run(name: str, settings: Settings) -> dict:
    persona = get_persona(name)
    final, port = runner.run_auto(persona, settings=settings)
    rec = final.get("recommendation")
    credit = final.get("credit_profile")
    return {
        "persona": name,
        "description": persona.description,
        "case_id": persona.application.case_id,
        "applicant": persona.application.applicant.full_name,
        "loan_amount": persona.application.loan.loan_amount,
        "purchase_price": persona.application.loan.purchase_price,
        "terminal_decision": final["terminal_decision"].value,
        "metrics": _metrics(final.get("metrics")),
        "credit_score": credit.score if credit else None,
        "recommendation": None
        if not rec
        else {
            "decision": rec.decision.value,
            "borderline": rec.borderline,
            "confidence": rec.confidence,
            "rationale": rec.rationale,
            "compensating_factors": rec.compensating_factors,
            "conditions": [c.description for c in rec.conditions],
            "policy_citations": rec.policy_citations,
        },
        "exceptions": [
            {"type": e.type.value, "severity": e.severity.value, "detail": e.detail}
            for e in final.get("exceptions", [])
        ],
        "human_decisions": [
            {"gate": d.gate, "choice": d.choice, "by": d.decided_by}
            for d in final.get("human_decisions", [])
        ],
        "timeline": [
            {"stage": t.stage.value, "actor": t.actor.value, "action": t.action, "detail": t.detail}
            for t in final.get("timeline", [])
        ],
        "emails_sent": len(port.sent_emails),
    }


def _capture_durable_gate(settings: Settings) -> dict:
    """Capture the real pending Gate-A task raised when a borderline case suspends."""
    persona = get_persona("conditional_approve")
    store = InboxStore(f"{settings.runtime_dir}/inbox.sqlite")
    start = runner.start_case(persona, store, settings=settings)
    pending = store.list_pending()
    task = pending[0] if pending else None
    snapshot = {
        "status": start["status"],
        "gate": start.get("gate"),
        "task_id": task.task_id if task else None,
        "title": task.title if task else None,
        "summary": task.summary if task else None,
        "options": task.options if task else [],
    }
    store.close()
    return snapshot


def main() -> None:
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    settings = Settings(runtime_mode="local", llm_mode="stub")
    runs = {name: _capture_run(name, settings) for name in HEADLINE}
    with tempfile.TemporaryDirectory() as tmp:
        durable = _capture_durable_gate(Settings(runtime_mode="local", llm_mode="stub", runtime_dir=tmp))
    payload = {"runs": runs, "durable_gate": durable}
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    print(f"wrote {OUT}")
    for name, r in runs.items():
        m = r["metrics"]
        ms = f"DTI {m['dti']:.0%} LTV {m['ltv']:.0%}" if m else "—"
        print(f"  {name:20} → {r['terminal_decision']:20} {ms}  gates={len(r['human_decisions'])}")
    print(f"  durable gate: {durable['gate']} task={durable['task_id']}")


if __name__ == "__main__":
    main()
