# 🏦 Mortgage Underwriting Agents — UiPath Maestro Case

> An **agentic, exception-heavy mortgage underwriting case** built as **UiPath Coded Agents**
> (Python + LangGraph), orchestrated as a **UiPath Maestro Case**, with **humans in charge**
> of every credit decision.
>
> **AgentHack 2026 — Track 1: UiPath Maestro Case** · License: Apache-2.0

🎬 **Demo video:** [`video/demo.mp4`](video/demo.mp4) — a narrated 3-minute walkthrough
assembled from real captured runs (see [`video/README.md`](video/README.md)). Upload it to
YouTube/Vimeo and drop the link into the Devpost submission.

A loan application enters; five coordinated agents move it through intake, document
verification, income analysis, credit & risk adjudication, and compliance — pausing for
human judgement at the moments that matter, escalating true exceptions, and recovering
from failures — until a human signs the final decision. The **same agent code** runs
locally (fully mocked, no tenant) and on **UiPath Automation Cloud**, because every side
effect goes through one swappable port.

---

## The business problem

Mortgage underwriting is the textbook "dynamic, exception-heavy" process: most files are
routine, but a long tail need document chasing, re-verification, compensating-factor
judgement, fraud/AML escalation, and appraisal reconciliation — and a human must remain
accountable for the credit decision. Pure RPA is too rigid for the exceptions; a pure LLM
is unacceptable for a regulated credit decision. **Agentic case management** is the right
shape: agents do the reasoning and coordination, robots do the mechanical work, and humans
hold authority at the decision points — all governed, audited, and durable.

This solution shows that shape end to end, with the failure handling and human-in-the-loop
control the hackathon asks for.

---

## What it does

A **Maestro Case** moves each loan through six stages with two human gates and a
table-driven exception lane:

| # | Stage | Actor | Human / exception |
|---|-------|-------|-------------------|
| 1 | **Intake** | `IntakeAgent` + RPA | Missing docs → email borrower, suspend |
| 2 | **Document verification** | `DocVerifyAgent` + Document Understanding | Low confidence → auto re-digitise → **human verify gate**; conflicting data → human |
| 3 | **Income / asset analysis** | `UnderwritingAgent` | W-2 vs self-employed income branching |
| 4 | **Credit & risk adjudication** | `AdjudicationAgent` (+ optional CrewAI panel) | Borderline → **Gate A** (underwriter decision support) |
| 5 | **Conditions / compliance** | `ExceptionAgent` | AML hit → **hard escalate to compliance** |
| 6 | **Decision & closing** | Human + RPA | **Gate B** — final credit decision (human authority, every case) |

**Five personas** demonstrate every path end to end:

| Persona | Outcome | What it shows |
|---------|---------|---------------|
| `clean_approve` | ✅ Approve | Straight-through; only the final human sign-off |
| `conditional_approve` | 🟡 Conditional | Borderline 44% DTI rescued by reserves → **Gate A** then **Gate B** |
| `decline` | 🔴 Decline | Hard policy breach; human confirms |
| `fraud_exception` | ⛔ Escalated | Conflicting employer (human verify) **+** AML hit → compliance escalation |
| `missing_docs` / `low_confidence_*` / `appraisal_gap` | — | The remaining exception routes |

All **seven exception routes** are centralized in one auditable policy table and covered
by tests.

---

## Architecture at a glance

```
                       ┌──────────────────────────────────────────────┐
   LoanApplication ──▶ │   Maestro Case  (LangGraph supervisor graph)   │ ──▶ Decision + audit trail
                       │  intake→docs→income→adjudication→conditions→…  │
                       └───────────────┬────────────────────────────────┘
                                       │ every side-effect call
                                       ▼
                          ┌──────────  PlatformPort  ──────────┐
                          │                                    │
                  LocalAdapter (no tenant)          UiPathAdapter (cloud)
            mocks · SQLite Action Inbox       Action Center · Orchestrator assets
            · SQLite durable checkpointer      · Document Understanding · LLM Gateway
```

**The one idea that makes this real:** agents depend only on a `PlatformPort` interface.
`RUNTIME_MODE=local` injects deterministic mocks + a local "Action Inbox" so the whole
multi-agent flow runs offline today; `RUNTIME_MODE=uipath` injects the real UiPath SDK.
The graph code is identical in both — so the local run is a faithful preview of Maestro,
and the cloud port is a small, reviewable shim.

See **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** for the deep dive and
**[mortgage-case.mermaid](mortgage-case.mermaid)** for the generated graph diagram.

---

## UiPath components used

| Component | How it's used |
|-----------|---------------|
| **UiPath Maestro Case** | The case lifecycle / orchestration (see [`case_definition.yaml`](case_definition.yaml)) |
| **Coded Agents (Python SDK)** | All five agents are LangGraph coded agents; packaged via `uipath pack` → `.nupkg` |
| **Action Center** | The two human gates + verify gate (`CreateTask` / `CreateEscalation` interrupts) |
| **Document Understanding (IDP)** | Document field extraction in `DocVerifyAgent` (cloud) |
| **Orchestrator** | Package feed + governed **assets** (secrets) for external service URLs |
| **API Workflows / connectors** | Credit-bureau and AML screening calls in the cloud adapter |
| **UiPath LLM Gateway** | LLM access in cloud mode (no API keys in code) |
| **External framework — CrewAI** | A "Credit Analyst vs Risk Officer" deliberation panel for borderline files, run *inside* the governed graph (optional, feature-flagged) |

**Agent type:** **Coded Agents** (Python/LangGraph) are the core, combined with an
**external framework** (CrewAI) inside the governed layer, and designed to slot into
**Maestro Case** low-code orchestration. (No UiPath low-code Agent Builder agent is
required, but the case is built to host them.)

---

## 🤖 Built with Claude Code (UiPath for Coding Agents)

**This entire solution was built by [Claude Code](https://claude.com/claude-code)
(Claude Opus 4.8)** driving a multi-agent "AI project agency" workflow — exactly the
"UiPath for Coding Agents" capability the hackathon highlights.

**How the coding agent contributed (specific, verifiable):**

- **Architecture** — designed the dual-mode `PlatformPort` seam that lets one agent
  codebase run locally and on UiPath.
- **All five coded agents + the supervisor graph**, the policy tables, and the finance/
  document tools.
- **Durable human-in-the-loop** — researched the LangGraph `interrupt`/`Command` API and
  the cross-process SQLite checkpointer live before building on them.
- **Cloud port mapped to the *real* UiPath SDK** — inspected the installed `uipath`
  2.11.x package to use the actual `CreateTask`/`CreateEscalation` interrupt models and
  `sdk.assets.retrieve_secret`, rather than guessing.
- **Validated `uipath init` + `uipath pack`** against the real CLI, producing a valid
  `.nupkg` and a clean agent I/O contract — without a tenant.
- **Tests, security audit, and this documentation.**

**Evidence (independently verifiable):**
- The git history — every commit is `Co-Authored-By: Claude`. Run `git log`.
- **[evidence/CODING_AGENT_LOG.md](evidence/CODING_AGENT_LOG.md)** — a phase-by-phase build
  log with the decisions and commit hashes.
- The UiPath-generated coding-agent guidance ([`AGENTS.md`](AGENTS.md), [`.agent/`](.agent))
  produced by `uipath init` is committed as part of the workflow.

---

## Quickstart

> Requires **Python 3.11+** and [`uv`](https://docs.astral.sh/uv/) (or pip). Runs fully
> offline — **no UiPath tenant and no API key needed** (LLM defaults to a deterministic stub).

```bash
# 1. Install (base + dev). Use the matching Python.
uv venv --python 3.12 && source .venv/bin/activate
uv pip install -e ".[dev]"

# 2. See the personas
mua-sim personas

# 3. Run a case end-to-end (auto-resolves the human gates from the persona script)
mua-sim run clean_approve
mua-sim run conditional_approve     # borderline → Gate A + Gate B
mua-sim run fraud_exception         # human verify + AML escalation

# 4. Or drive the human gates yourself (durable, cross-process — like Action Center):
mua-sim run conditional_approve --interactive   # runs until the first gate, then suspends
mua-sim inbox                                    # list pending human tasks
mua-sim approve <task_id> --choice conditional_approve --note "underwriter ok"
mua-sim cases                                    # see case status
```

### Optional: the loan-officer desk (web UI)

```bash
uv pip install -e ".[web]"
mua-sim serve            # http://127.0.0.1:8000  (local demo only; see SECURITY.md)
```

### Optional: live LLM narration / CrewAI panel

```bash
uv pip install -e ".[live,crew]"
export LLM_MODE=live ANTHROPIC_API_KEY=sk-ant-...
mua-sim run conditional_approve --crew      # CrewAI debates the borderline file
```

### Deploy to UiPath Automation Cloud

Everything is cloud-ready. The coded agent already packages with `uipath pack` **without a
tenant**. The full path (`uipath auth → init → pack → publish → invoke`), asset setup, and
Maestro Case wiring are in **[docs/DEPLOY_UIPATH.md](docs/DEPLOY_UIPATH.md)**.

---

## Testing

```bash
pytest --cov                 # 72 tests, ~94% coverage, deterministic (LLM stubbed)
ruff check src sim tests     # lint
mypy src                     # types
```

Tests cover the finance math, document checks, the policy matrix, the deliberation logic,
the retry/resilience helper, the port contract, all 8 personas, every exception route
(including injected transient failures), the cross-process durable suspend/resume, and the
web UI.

---

## Project structure

```
src/mortgage_agents/
├── state.py            # domain models, CaseState, clean CaseInput/CaseOutput contract
├── config.py           # RUNTIME_MODE / LLM_MODE settings
├── ports/              # PlatformPort + LocalAdapter (mocks) + UiPathAdapter (cloud)
├── policy/             # underwriting_policy (DTI/LTV/score) + exception_policy (routes)
├── tools/              # finance math, document checks, retry/backoff
├── llm/                # stub (default) / Anthropic provider
├── graphs/             # 5 agents + case_orchestrator (the deployable graph) + CrewAI panel
└── persistence.py      # SQLite durable checkpointer (allowlisted serde)
sim/                    # local runner, Action Inbox, personas/fixtures, CLI, web UI
tests/                  # unit + integration + e2e
docs/                   # ARCHITECTURE, DEPLOY_UIPATH, DEMO_SCRIPT, DECK_OUTLINE
case_definition.yaml    # the Maestro Case source of truth
langgraph.json          # coded-agent entry point for uipath init/pack
```

---

## License

[Apache-2.0](LICENSE). The license applies to this solution's original code; UiPath tools,
SDKs, and platform components remain under their own license terms.
