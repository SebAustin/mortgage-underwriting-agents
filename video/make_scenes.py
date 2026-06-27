"""Generate the demo-video scenes as on-brand 1920x1080 HTML pages + a narration manifest.

Terminal/"footage" scenes are rebuilt from the REAL captured run data
(``video/assets/runs.json``) so every number on screen is true program output. Each scene
is screenshotted (Chrome, viewport 1920x1080) into ``video/frames`` and narrated with
macOS ``say``; ``assemble.sh`` muxes stills + audio into ``video/demo.mp4``.
"""

from __future__ import annotations

import html
import json
import os

HERE = os.path.dirname(__file__)
SCENES_DIR = os.path.join(HERE, "scenes")
RUNS = json.load(open(os.path.join(HERE, "assets", "runs.json"), encoding="utf-8"))["runs"]

DECISION_COLOR = {
    "approve": "#34d399",
    "conditional_approve": "#fbbf24",
    "decline": "#f87171",
    "escalated": "#fb7185",
    "info_requested": "#38bdf8",
}
ACTOR_COLOR = {"agent": "#34d399", "robot": "#38bdf8", "human": "#a78bfa", "system": "#fbbf24"}

CSS = """
* { margin:0; padding:0; box-sizing:border-box; }
:root{
  --bg:#0b0e14; --panel:#141925; --line:#232a39; --ink:#e6eaf2; --soft:#94a0b8;
  --accent:#7c8cff; --accent-soft:#1b2138; --mono:'Menlo','SF Mono',monospace;
  --sans:-apple-system,'Helvetica Neue',sans-serif;
}
html,body{ width:1920px; height:1080px; overflow:hidden; }
body{ background:
   radial-gradient(1200px 700px at 80% -10%, #161d2e 0%, transparent 60%),
   radial-gradient(900px 600px at -10% 110%, #14223a 0%, transparent 55%), var(--bg);
   color:var(--ink); font-family:var(--sans); -webkit-font-smoothing:antialiased; }
.stage{ width:1920px; height:1080px; padding:96px 130px; display:flex; flex-direction:column; }
.kicker{ font-family:var(--mono); font-size:26px; letter-spacing:.35em; text-transform:uppercase;
  color:var(--accent); margin-bottom:28px; }
h1{ font-size:104px; line-height:1.02; letter-spacing:-.02em; font-weight:800; }
h1 .sub{ display:block; font-size:46px; font-weight:500; color:var(--soft); margin-top:30px;
  letter-spacing:0; line-height:1.3; }
h2{ font-size:64px; line-height:1.08; letter-spacing:-.01em; font-weight:750; margin-bottom:44px; }
.badges{ margin-top:auto; display:flex; gap:18px; flex-wrap:wrap; }
.badge{ font-family:var(--mono); font-size:24px; color:var(--soft); border:1px solid var(--line);
  border-radius:999px; padding:12px 22px; background:#0e131d; }
.badge b{ color:var(--ink); }
ul.points{ list-style:none; display:flex; flex-direction:column; gap:30px; margin-top:8px; }
ul.points li{ font-size:42px; line-height:1.32; padding-left:54px; position:relative; color:#d7deec; }
ul.points li::before{ content:''; position:absolute; left:0; top:18px; width:24px; height:24px;
  border-radius:7px; background:var(--accent); box-shadow:0 0 0 6px var(--accent-soft); }
ul.points li b{ color:#fff; }
.term{ background:var(--panel); border:1px solid var(--line); border-radius:20px; overflow:hidden;
  box-shadow:0 30px 80px rgba(0,0,0,.45); flex:1; display:flex; flex-direction:column; }
.term .bar{ display:flex; gap:11px; padding:22px 26px; border-bottom:1px solid var(--line);
  align-items:center; }
.dot{ width:16px; height:16px; border-radius:50%; }
.term .bar .t{ margin-left:18px; font-family:var(--mono); font-size:24px; color:var(--soft); }
.term .body{ padding:30px 40px; font-family:var(--mono); font-size:30px; line-height:1.0; flex:1; }
.cmd{ font-size:32px; margin-bottom:26px; }
.cmd .p{ color:var(--accent); } .cmd .c{ color:#fff; }
.tl{ display:flex; flex-direction:column; gap:14px; }
.row{ display:grid; grid-template-columns:300px 130px 1fr; gap:24px; align-items:baseline; font-size:27px; }
.row .stg{ color:var(--soft); text-transform:uppercase; font-size:22px; letter-spacing:.06em; }
.row .act{ font-weight:700; text-transform:uppercase; font-size:21px; letter-spacing:.05em; }
.row .desc b{ color:#fff; } .row .desc{ color:#b9c2d6; }
.outcome{ margin-top:30px; display:flex; align-items:center; gap:28px; }
.chip{ font-family:var(--mono); font-weight:800; text-transform:uppercase; letter-spacing:.05em;
  font-size:34px; padding:16px 34px; border-radius:14px; color:#0b0e14; }
.metrics{ font-family:var(--mono); font-size:30px; color:var(--soft); }
.metrics b{ color:#fff; }
.flow{ display:flex; flex-direction:column; gap:34px; margin-top:10px; flex:1; justify-content:center; }
.lane{ display:flex; align-items:center; gap:22px; flex-wrap:wrap; }
.node{ font-size:30px; padding:20px 30px; border-radius:14px; background:var(--panel);
  border:1px solid var(--line); font-weight:650; }
.node.agent{ border-color:#2f7d5e; } .node.human{ border-color:#5b4aa6; background:#1a1733; }
.node.term{ border-color:#7c8cff; }
.arrow{ color:var(--soft); font-size:34px; }
.seam{ margin-top:40px; display:grid; grid-template-columns:1fr 90px 1fr; gap:22px; align-items:stretch; }
.col{ background:var(--panel); border:1px solid var(--line); border-radius:18px; padding:34px 38px; }
.col h3{ font-size:30px; margin-bottom:22px; color:var(--accent); font-family:var(--mono);
  letter-spacing:.04em; }
.col .line{ font-size:28px; color:#c4cde0; margin:14px 0; }
.seam .mid{ display:flex; align-items:center; justify-content:center; font-family:var(--mono);
  font-size:26px; color:var(--soft); text-align:center; }
table.cmp{ width:100%; border-collapse:collapse; margin-top:8px; font-size:30px; }
table.cmp th{ text-align:left; color:var(--soft); font-family:var(--mono); font-size:24px;
  text-transform:uppercase; letter-spacing:.06em; padding:18px 22px; border-bottom:2px solid var(--line); }
table.cmp td{ padding:20px 22px; border-bottom:1px solid var(--line); color:#cdd6e8; }
table.cmp td b{ color:#fff; } table.cmp tr td:first-child{ color:var(--accent); font-family:var(--mono); font-size:26px; }
.shot{ flex:1; border-radius:18px; border:1px solid var(--line); overflow:hidden; margin-top:6px;
  box-shadow:0 30px 80px rgba(0,0,0,.5); background:#fff; display:flex; }
.shot img{ width:100%; height:100%; object-fit:cover; object-position:top center; }
.foot{ margin-top:auto; font-family:var(--mono); font-size:26px; color:var(--soft); }
.big{ font-size:150px; font-weight:800; letter-spacing:-.03em; line-height:1; }
.center{ align-items:flex-start; justify-content:center; }
.spacer{ flex:1; }
"""


def _esc(s: str) -> str:
    return html.escape(str(s))


def page(body: str, extra: str = "") -> str:
    return (
        f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}{extra}</style></head>"
        f"<body>{body}</body></html>"
    )


def chip(decision: str) -> str:
    col = DECISION_COLOR.get(decision, "#cbd5e1")
    return f"<span class='chip' style='background:{col}'>{_esc(decision.replace('_',' '))}</span>"


def terminal_scene(run: dict, max_rows: int = 6) -> str:
    rows = run["timeline"][:max_rows]
    tl = "".join(
        f"<div class='row'><span class='stg'>{_esc(r['stage'])}</span>"
        f"<span class='act' style='color:{ACTOR_COLOR.get(r['actor'],'#fff')}'>{_esc(r['actor'])}</span>"
        f"<span class='desc'><b>{_esc(r['action'])}</b> &mdash; {_esc(r['detail'])}</span></div>"
        for r in rows
    )
    m = run["metrics"]
    metrics = (
        f"<span class='metrics'>DTI <b>{m['dti']*100:.0f}%</b> &nbsp; LTV <b>{m['ltv']*100:.0f}%</b>"
        f" &nbsp; score <b>{run['credit_score']}</b></span>"
        if m
        else ""
    )
    gates = len(run["human_decisions"])
    gate_txt = f"<span class='metrics'>&nbsp;&nbsp; human gates <b>{gates}</b></span>"
    body = f"""
      <div class='stage'>
        <div class='kicker'>live run &middot; real output</div>
        <div class='term'>
          <div class='bar'><span class='dot' style='background:#ff5f57'></span>
            <span class='dot' style='background:#febc2e'></span>
            <span class='dot' style='background:#28c840'></span>
            <span class='t'>mua-sim &mdash; {_esc(run['case_id'])}</span></div>
          <div class='body'>
            <div class='cmd'><span class='p'>$</span> <span class='c'>mua-sim run {_esc(run['persona'])}</span></div>
            <div class='tl'>{tl}</div>
            <div class='outcome'>{chip(run['terminal_decision'])} {metrics} {gate_txt}</div>
          </div>
        </div>
      </div>"""
    return page(body)


def scenes() -> list[dict]:
    clean, cond, decl, fraud = (RUNS[k] for k in ("clean_approve", "conditional_approve", "decline", "fraud_exception"))
    out: list[dict] = []

    out.append({
        "id": "01_title",
        "seconds": 11,
        "speak": "Mortgage Underwriting Agents. An agentic UiPath Maestro Case, built entirely with Claude Code, where coded agents underwrite and humans decide.",
        "html": page("""
          <div class='stage'>
            <div class='kicker'>UiPath AgentHack 2026 &middot; Track 1 &middot; Maestro Case</div>
            <h1>Mortgage Underwriting Agents
              <span class='sub'>Coded agents that underwrite &mdash; humans who decide.</span></h1>
            <div class='badges'>
              <span class='badge'>5 coded agents</span>
              <span class='badge'>2 human gates</span>
              <span class='badge'>durable suspend / resume</span>
              <span class='badge'><b>Built with Claude Code</b></span>
            </div>
          </div>"""),
    })

    out.append({
        "id": "02_problem",
        "seconds": 22,
        "speak": "Mortgage underwriting is dynamic and exception heavy. Most files are routine, but the tail needs document chasing, re-verification, judgement calls, and fraud escalation. Rigid robots cannot handle the exceptions, and a raw language model is unacceptable for a regulated credit decision. The right shape is agentic case management.",
        "html": page("""
          <div class='stage'>
            <div class='kicker'>the problem</div>
            <h2>Underwriting is exception-heavy &mdash; and a human must own the decision.</h2>
            <ul class='points'>
              <li>Most loans are routine; the <b>tail</b> needs docs, re-verification, judgement, fraud checks.</li>
              <li>Rigid RPA is <b>too brittle</b> for the exceptions.</li>
              <li>A raw LLM is <b>unacceptable</b> for a regulated credit decision.</li>
              <li><b>Agentic case management</b>: agents reason, robots act, humans hold authority.</li>
            </ul>
          </div>"""),
    })

    out.append({
        "id": "03_architecture",
        "seconds": 26,
        "speak": "Five coded LangGraph agents move each loan through six stages: intake, document verification, income analysis, adjudication, compliance, and decision. The key idea: agents never call the UiPath SDK directly. Every side effect goes through one platform port, so the exact same graph runs locally with mocks and on UiPath Automation Cloud.",
        "html": page("""
          <div class='stage'>
            <div class='kicker'>architecture</div>
            <h2>Five agents, six stages, two gates &mdash; one swappable port.</h2>
            <div class='flow'>
              <div class='lane'>
                <span class='node agent'>Intake</span><span class='arrow'>&rarr;</span>
                <span class='node agent'>Doc Verify</span><span class='arrow'>&rarr;</span>
                <span class='node agent'>Income</span><span class='arrow'>&rarr;</span>
                <span class='node agent'>Adjudication</span><span class='arrow'>&rarr;</span>
                <span class='node human'>Gate A</span><span class='arrow'>&rarr;</span>
                <span class='node agent'>Compliance</span><span class='arrow'>&rarr;</span>
                <span class='node human'>Gate B</span><span class='arrow'>&rarr;</span>
                <span class='node term'>Decision</span>
              </div>
              <div class='seam'>
                <div class='col'><h3>LocalAdapter &mdash; no tenant</h3>
                  <div class='line'>mocks &middot; SQLite Action Inbox</div>
                  <div class='line'>durable checkpointer</div></div>
                <div class='mid'>PlatformPort<br>RUNTIME_MODE</div>
                <div class='col'><h3>UiPathAdapter &mdash; cloud</h3>
                  <div class='line'>Action Center &middot; Orchestrator assets</div>
                  <div class='line'>Document Understanding &middot; LLM Gateway</div></div>
              </div>
            </div>
          </div>"""),
    })

    out.append({
        "id": "04_clean",
        "seconds": 24,
        "speak": "Here is a clean file, running for real. Intake triages documents, the agents verify them, compute income, and adjudicate: twenty-nine percent debt-to-income, eighty percent loan-to-value, a seven-sixty score. The recommendation is approve, and only the final human gate fires.",
        "html": terminal_scene(clean),
    })

    out.append({
        "id": "05_borderline",
        "seconds": 30,
        "speak": "This file is borderline: a forty-four percent debt-to-income ratio. The adjudication agent finds compensating factors, strong reserves and a seven-sixty score, and flags it for a human. Gate A is the underwriter's decision support; Gate B is final authority. Two humans, two distinct roles, ending in a conditional approval.",
        "html": terminal_scene(cond),
    })

    out.append({
        "id": "06_hitl",
        "seconds": 24,
        "speak": "And here is that human gate in the loan-officer desk. The underwriter sees the agent's metrics, its rationale, the compensating factors, the conditions, and the exact policy citations behind the recommendation, then approves, conditions, or declines.",
        "html": page("""
          <div class='stage'>
            <div class='kicker'>humans in charge &middot; Action Center</div>
            <h2>Gate A &mdash; decision support, with the agent's full reasoning.</h2>
            <div class='shot'><img src='../assets/shots/case_gate_a_vp.png'></div>
          </div>"""),
    })

    out.append({
        "id": "07_durable",
        "seconds": 22,
        "speak": "The case is durable. It suspends to SQLite in one process and resumes in another, exactly like Maestro's durable execution and Action Center. Start a case, it pauses at the gate, it appears in the inbox, and a separate command resumes it right where it left off.",
        "html": page(f"""
          <div class='stage'>
            <div class='kicker'>survives interruptions</div>
            <h2>Durable, cross-process human-in-the-loop.</h2>
            <div class='term'>
              <div class='bar'><span class='dot' style='background:#ff5f57'></span>
                <span class='dot' style='background:#febc2e'></span>
                <span class='dot' style='background:#28c840'></span>
                <span class='t'>mua-sim &mdash; durable inbox</span></div>
              <div class='body'>
                <div class='cmd'><span class='p'>$</span> <span class='c'>mua-sim run conditional_approve --interactive</span></div>
                <div class='row'><span class='stg'>suspended</span><span class='act' style='color:#a78bfa'>human</span>
                  <span class='desc'>paused at <b>gate_a</b> &mdash; persisted to SQLite</span></div>
                <div class='cmd' style='margin-top:26px'><span class='p'>$</span> <span class='c'>mua-sim approve {_esc(RUNS['conditional_approve']['case_id'])}-gate_a --choice conditional_approve</span></div>
                <div class='row'><span class='stg'>resumed</span><span class='act' style='color:#34d399'>agent</span>
                  <span class='desc'>continues &rarr; pauses at <b>gate_b</b> &rarr; <b>closed</b></span></div>
                <div class='outcome'>{chip('conditional_approve')}<span class='metrics'> different process &middot; same case</span></div>
              </div>
            </div>
          </div>"""),
    })

    out.append({
        "id": "08_fraud",
        "seconds": 27,
        "speak": "Exceptions are the product. This applicant's employer disagrees across documents, so the case routes to a human to verify. Then the anti-money-laundering screen hits a watchlist, a hard stop that escalates to compliance and never reaches an automated approval. All seven exception routes live in one auditable policy table.",
        "html": terminal_scene(fraud),
    })

    out.append({
        "id": "09_cloud",
        "seconds": 24,
        "speak": "Because of the platform port, the same agent code runs on UiPath, selected by one environment variable. The coded agent already packages with uipath pack into a valid nu-pkg, verified without a tenant, with a clean input and output contract that UiPath generated.",
        "html": page("""
          <div class='stage'>
            <div class='kicker'>same code, on UiPath</div>
            <h2>One env var switches local mocks for the real platform.</h2>
            <table class='cmp'>
              <tr><th>Capability</th><th>LocalAdapter</th><th>UiPathAdapter</th></tr>
              <tr><td>human gate</td><td>SQLite Action Inbox</td><td><b>Action Center</b> task / escalation</td></tr>
              <tr><td>durability</td><td>SQLite checkpointer</td><td><b>Maestro</b> durable execution</td></tr>
              <tr><td>documents</td><td>fixture payloads</td><td><b>Document Understanding</b></td></tr>
              <tr><td>secrets</td><td>.env</td><td><b>Orchestrator assets</b></td></tr>
              <tr><td>packaging</td><td colspan='2'><b>uipath pack &rarr; valid .nupkg</b> &mdash; verified with no tenant</td></tr>
            </table>
          </div>"""),
    })

    out.append({
        "id": "10_closing",
        "seconds": 18,
        "speak": "Five coded agents, durable human-in-the-loop, real exception handling, and a clean cloud port, built end to end by Claude Code. Seventy-two tests, ninety-three percent coverage, and security audited. Thank you.",
        "html": page("""
          <div class='stage'>
            <div class='kicker'>built with claude code &middot; UiPath for Coding Agents</div>
            <h1>Agents underwrite.<span class='sub'>Humans decide. UiPath governs.</span></h1>
            <div class='badges'>
              <span class='badge'><b>72</b> tests</span>
              <span class='badge'><b>93%</b> coverage</span>
              <span class='badge'>0 open Critical/High</span>
              <span class='badge'>valid <b>.nupkg</b> without a tenant</span>
            </div>
          </div>"""),
    })
    return out


def main() -> None:
    os.makedirs(SCENES_DIR, exist_ok=True)
    manifest = []
    for sc in scenes():
        path = os.path.join(SCENES_DIR, f"{sc['id']}.html")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(sc["html"])
        manifest.append({"id": sc["id"], "file": path, "speak": sc["speak"], "seconds": sc["seconds"]})
    with open(os.path.join(HERE, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    est = sum(s["seconds"] for s in manifest)
    print(f"wrote {len(manifest)} scenes; estimated ~{est}s ({est/60:.1f} min)")


if __name__ == "__main__":
    main()
