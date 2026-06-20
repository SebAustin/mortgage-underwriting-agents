# Coding-Agent Build Log — UiPath for Coding Agents

This file documents how **Claude Code (Claude Opus 4.8)** built this solution, as
verifiable evidence for the AgentHack "coding agents" bonus. The build ran through a
multi-agent "AI project agency" orchestration (requirements → plan → build/verify loop →
security → docs → acceptance), all driven by the coding agent.

> **Independently verifiable:** every commit below is `Co-Authored-By: Claude`. Run
> `git log --format='%H %an %s'`. The build also used the UiPath coding-agent CLI
> (`uipath init` / `uipath pack`), whose generated guidance (`AGENTS.md`, `.agent/`) is
> committed.

## What the coding agent did, phase by phase

**Research & grounding (before writing code).** Rather than guess APIs, the agent ran live
probes: it confirmed the LangGraph `interrupt`/`Command` suspend-resume semantics, verified
cross-process Pydantic-state persistence through a SQLite checkpointer, and **inspected the
installed `uipath` 2.11.x SDK** to discover the real interrupt models
(`CreateTask`/`CreateEscalation`) and asset API (`sdk.assets.retrieve_secret`) — so the
cloud adapter matches the actual SDK instead of documentation guesswork.

**`6600370` — Core (M0–M4).** Scaffolded the project; designed and built the `PlatformPort`
dual-mode architecture, all five LangGraph agents and the supervisor graph, the
underwriting + exception policy tables, the finance/document tools, the durable SQLite
checkpointer, the local Action Inbox, the CLI, 8 personas, and 65 tests. Verified all four
headline personas end-to-end and the cross-process suspend/resume by hand before locking it
in. Caught and fixed a real logic bug (a hard-decline file was being mis-flagged as
"borderline" and routed through Gate A).

**`a63e08e` — CrewAI panel + web UI (M5).** Added the sandboxed CrewAI "Credit Analyst vs
Risk Officer" deliberation node (lazy import, deterministic fallback, verified it resolves
cleanly alongside LangGraph 1.x in an isolated env) and a FastAPI loan-officer desk; fixed a
Starlette 1.3 `TemplateResponse` signature change surfaced by the smoke tests.

**`a55c76b` — UiPath cloud port + packaging (M6).** Wrote the `UiPathAdapter` against the
real SDK; created `langgraph.json` and `case_definition.yaml`; ran the real `uipath init`
+ `uipath pack` and **produced a valid `.nupkg` without a tenant**. Discovered the UiPath
graph loader imports the entry module by file path (no package context) and converted the
orchestrator to absolute imports to fix it. Introduced a clean `CaseInput`/`CaseOutput`
contract, shrinking the generated `entry-points.json` from 64 KB to 29 KB.

**Security & docs.** Ran an independent STRIDE + dependency audit (`SECURITY.md`), then
applied the one recommended mitigation (loopback-bind guard on the demo UI). Wrote the
documentation set and submission assets.

## How to reproduce / verify

```bash
git log --format='%H  %an  %s'        # co-authored commits
pytest --cov                           # 72 tests, ~94% coverage
uv pip install -e ".[cloud]" && uipath init && uipath pack   # → .uipath/*.nupkg
```

The full interactive session that produced this repo is itself the prompt log; this file
plus the git history are its durable, checkable summary.
