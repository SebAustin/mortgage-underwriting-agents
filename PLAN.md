# PLAN — Mortgage Underwriting Agents (UiPath Maestro Case)

Full architecture: [README.md](README.md) · [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
Assumptions: [ASSUMPTIONS.md](ASSUMPTIONS.md). This file records the approach and the
measurable success criteria used to judge "done."

## Approach
Five LangGraph **coded agents** sequenced by a supervisor graph across six Maestro Case
stages, with two human gates and a 7-route exception policy. A `PlatformPort` interface with
`LocalAdapter` (offline mocks + SQLite Action Inbox + durable checkpointer) and
`UiPathAdapter` (Action Center, Orchestrator assets, Document Understanding, LLM Gateway)
lets the same code run locally and on UiPath. Decisions are deterministic/policy-driven;
the LLM only narrates. CrewAI provides an optional borderline-deliberation panel inside the
governed graph.

## Success criteria
1. All 4 headline personas (clean approve, conditional approve, decline, fraud/escalation)
   run end-to-end with one command and reach the correct terminal state.
2. Both human gates (A decision-support, B final authority) demonstrably pause and resume
   the case — including **cross-process** via the Action Inbox.
3. All 7 exception routes behave per `exception_policy` (covered by tests).
4. `uipath init` + `uipath pack` succeed → valid `.nupkg` **without a tenant**;
   `docs/DEPLOY_UIPATH.md` reduces go-live to a short command list.
5. ≥80% test coverage; lint + type-check clean; deterministic (LLM stubbed).
6. The same agent source runs under `LocalAdapter` and the cloud `UiPathAdapter` (one env var).
7. Submission assets complete: README with verifiable Claude Code evidence, ARCHITECTURE,
   deploy guide, deck outline, Devpost copy, 5-min demo script, Apache-2.0 license.

## Status
Built across milestones M0–M6 (see `evidence/CODING_AGENT_LOG.md`). Security audited
(`SECURITY.md`, 0 open Critical/High after mitigation). Verified per the solution rubric —
see `ACCEPTANCE.md`.
