# Devpost Submission — Mortgage Underwriting Agents

**Track:** Track 1 — UiPath Maestro Case
**License:** Apache-2.0
**Repo:** <add public GitHub URL> · **Demo video:** <upload `video/demo.mp4` to YouTube/Vimeo, add URL> · **Deck:** <add link>

## Elevator pitch
An agentic, exception-heavy **mortgage underwriting case** built as **UiPath Coded Agents**
(Python + LangGraph), orchestrated as a **UiPath Maestro Case**, with humans in charge of
every credit decision. The same agent code runs locally (fully mocked) and on UiPath
Automation Cloud through one swappable port.

## The business problem it solves
Mortgage underwriting is the canonical dynamic, exception-heavy process: most files are
routine, but the tail needs document chasing, re-verification, compensating-factor
judgement, fraud/AML escalation, and appraisal reconciliation — and a human must remain
accountable for the credit decision. Rigid RPA can't handle the exceptions; an autonomous
LLM is unacceptable for a regulated decision. This solution shows the right shape: agents
reason and coordinate, robots do mechanical work, and humans hold authority — governed,
audited, and durable.

## What it does
A Maestro Case moves each loan through **intake → document verification → income analysis →
credit & risk adjudication → conditions/compliance → human-approved decision**, driven by
**five coded agents**, with **two human gates** (underwriter decision support + final
authority), **durable cross-process suspend/resume**, and **seven exception routes** in one
auditable policy table (missing docs, low-confidence OCR with auto re-digitise, conflicting
data, DTI breaches, appraisal gaps, AML/fraud escalation, transient-failure retry). Five
personas demonstrate every path: clean approve, conditional approve (borderline → both
gates), decline, and a fraud case (human verify + AML escalation to compliance).

## How it works
Agents depend only on a `PlatformPort` interface. `RUNTIME_MODE=local` injects deterministic
mocks + a local "Action Inbox" (SQLite) so the whole flow runs offline; `RUNTIME_MODE=uipath`
injects the real UiPath SDK — Action Center tasks/escalations (`CreateTask`/`CreateEscalation`
interrupts), Orchestrator asset secrets, Document Understanding, API-Workflow services, and
the LLM Gateway. The graph code is identical in both. Credit decisions are deterministic and
policy-driven (auditable); the LLM only narrates, with a deterministic offline fallback. A
borderline file can be escalated to an optional **CrewAI** "Credit Analyst vs Risk Officer"
panel running *inside* the governed graph.

## UiPath components used
UiPath **Maestro Case** (orchestration), **Coded Agents** (Python SDK; packaged via
`uipath pack`), **Action Center** (human gates), **Document Understanding** (IDP),
**Orchestrator** (package feed + governed asset secrets), **API Workflows / connectors**
(credit bureau + AML), **UiPath LLM Gateway**, plus an **external framework (CrewAI)** inside
the governed layer.

## Agent type
**Coded Agents** (Python / LangGraph) as the core, combined with an **external framework
(CrewAI)** inside the governed orchestration layer, and built to host **low-code** agents in
the Maestro Case. (Statement per the rules: this solution uses **Coded Agents** primarily,
plus an external agent framework.)

## Built with a coding agent (bonus)
The entire solution was built by **Claude Code (Claude Opus 4.8)** via UiPath for Coding
Agents — including `uipath init`/`uipath pack`. Evidence: every git commit is
`Co-Authored-By: Claude`, plus a phase-by-phase build log in `evidence/CODING_AGENT_LOG.md`
and the UiPath-generated coding-agent guidance (`AGENTS.md`, `.agent/`) committed in the repo.

## Run it
`uv pip install -e ".[dev]"` then `mua-sim run conditional_approve` (no tenant/API key
needed). Cloud deploy steps in `docs/DEPLOY_UIPATH.md`. 72 tests, ~94% coverage,
security-audited.

## Screenshots to attach
1. `mua-sim run conditional_approve` timeline (terminal) showing the agent stages + both gates.
2. `mua-sim inbox` + `mua-sim approve` (durable human-in-the-loop).
3. The loan-officer desk web UI (`mua-sim serve`) on a borderline case (Gate A panel).
4. `uipath pack` success + the generated `.nupkg` / `entry-points.json`.
5. `pytest --cov` green + `git log` co-authored commits.
