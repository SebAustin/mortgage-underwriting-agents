# Architecture

## Overview

The solution is a single LangGraph **supervisor graph** (`case_orchestrator`) that
sequences five coded agents across the six Maestro Case stages, with two human gates and a
table-driven exception lane. It is designed around one seam — the `PlatformPort` — so the
identical graph runs locally (mocked, offline) and on UiPath Automation Cloud.

```
START → intake → doc_verify ⇄ redigitize → [verify_gate] → income_analysis
      → adjudication → [gate_a?] → conditions → [gate_b] → closing → END
                         │                         │
                         └── transient fail ──▶ escalate ◀── AML hit
   intake (missing docs) ─────────────────────▶ request_info
```

## Components

### `PlatformPort` (the seam) — `ports/platform_port.py`
A `Protocol` with every side-effecting capability the agents need: `request_human_decision`,
`extract_document`, `pull_credit`, `screen_aml`, `send_borrower_email`, `emit_artifact`,
`get_asset`, `now`. Agents/graph code never import the UiPath SDK directly.

- **`LocalAdapter`** — deterministic mocks keyed by persona (`ssn_last4`), a local Action
  Inbox (SQLite), artifacts/emails written under `.runtime/`. Human gates surface a
  LangGraph `interrupt`; the sim layer resolves it (scripted persona decision, CLI
  `approve`, or web UI).
- **`UiPathAdapter`** — `interrupt(CreateTask|CreateEscalation)` for Action Center,
  `sdk.assets.retrieve_secret` for governed secrets, Document Understanding fields, and
  `httpx` calls to API-Workflow-backed services whose URLs come from Orchestrator assets.

Selection is one env var (`RUNTIME_MODE`) via `ports.get_port()`; the cloud adapter is
imported lazily so the heavy SDK is only required in cloud mode.

### State — `state.py`
`CaseState` (a `TypedDict`) is the internal graph state; list fields that accumulate
(`timeline`, `exceptions`, `human_decisions`) use `operator.add` reducers. The deployed
agent exposes a **clean contract** via `input_schema=CaseInput` (just the `application`)
and `output_schema=CaseOutput` (decision + recommendation + metrics + audit trail) — so the
UiPath entry-points schema is meaningful rather than the full internal state.

### The five agents — `graphs/`
1. **IntakeAgent** — classify documents, build the required-docs checklist, emit
   `MISSING_DOCS` when incomplete.
2. **DocVerifyAgent** — run extraction (port), cross-check identity/employer across docs,
   emit `LOW_CONFIDENCE` / `CONFLICTING_DATA`. A `redigitize` node retries extraction once.
3. **UnderwritingAgent** — qualifying income (W-2 wages/12 vs self-employed averaging),
   reserves, employment stability.
4. **AdjudicationAgent** *(centerpiece)* — credit pull (with transient-failure retry),
   DTI/LTV/front-end DTI, the policy matrix, and a **self-critique deliberation** over
   compensating factors. Borderline files are flagged for Gate A. Optionally delegates the
   borderline judgement to a **CrewAI** panel (`crew_panel.py`).
5. **ExceptionAgent** — AML/fraud screen, condition assembly; an AML hit routes to the
   compliance escalation.

### Human gates
- **`verify_gate`** — loan processor verifies low-confidence/conflicting extraction.
- **Gate A** — *decision support* on borderline files only (underwriter can steer
  approve/conditional/decline).
- **Gate B** — *final authority*; **every** approved/declined case requires it.

All three are `port.request_human_decision(...)` calls → a LangGraph `interrupt` that
pauses the case durably and resumes with the human's choice.

### Policy — `policy/`
- `underwriting_policy.py` — thresholds (DTI 43% + 3% borderline band, LTV 97%, score 620),
  required-docs matrix, `evaluate()` (preliminary decision + citations + borderline flag),
  and `compensating_factors()`.
- `exception_policy.py` — the single table mapping each of the 7 `ExceptionType`s to a
  route, retry budget, and escalation target.

### Durability — `persistence.py`
A SQLite-backed LangGraph checkpointer gives cross-process suspend/resume (the local
equivalent of Maestro's durable execution): a case can pause at a gate in one process
(`mua-sim run --interactive`) and resume in another (`mua-sim approve`). The msgpack serde
uses a **module-scoped allowlist** derived from our own model modules (no arbitrary-type
deserialization).

---

## Architectural Decision Records (ADRs)

**ADR-1 — LangGraph as the orchestration spine.** It is UiPath's first-class coded-agent
pattern (`uipath-langchain`), its `interrupt`/`Command` durability maps directly to Maestro
suspend/resume, and `uipath init` understands it. *Alternatives:* CrewAI/AutoGen as the
spine — rejected because they don't port to UiPath's runtime as cleanly; CrewAI is used only
as a sandboxed sub-node.

**ADR-2 — `PlatformPort` dependency injection over `if cloud:` branching.** A single
interface + two adapters keeps agent code identical and testable and confines all SDK
coupling to one reviewable file. *Cost:* one indirection layer — the project's core
credibility argument, worth it.

**ADR-3 — Deterministic decisions; the LLM only narrates.** Credit decisions are
policy-driven and reproducible; the LLM (stub by default) generates rationale/classification
with a deterministic fallback. This makes the whole system runnable offline, testable
without flakiness, and safe (no LLM authority over a regulated decision). *Trade-off:* less
"magic," but correct for the domain.

**ADR-4 — SQLite checkpointer for durable HITL.** Chosen over an in-memory checkpointer so
the inbox/approve story survives process boundaries, mirroring Maestro. *Cost:* serde
allowlist maintenance, handled generically.

**ADR-5 — Clean `CaseInput`/`CaseOutput` contract.** Chosen over exposing the full
`CaseState` so the deployed agent's I/O schema (and `entry-points.json`) is meaningful.
*Trade-off:* the runner/tests read final results via `get_state` (full internal state)
rather than the invoke return.

**ADR-6 — CrewAI behind a feature flag with a deterministic fallback.** The external-
framework showcase can't destabilize the deployable graph: it's a single node, lazily
imported, and `deliberate()` falls back to the deterministic path on any error.
