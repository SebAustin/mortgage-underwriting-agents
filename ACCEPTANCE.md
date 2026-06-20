# Acceptance

Final acceptance record for the AgentHack 2026 (Track 1) build. Verdict from the
independent solution-verifier: **SOLID — 4.90 / 5**.

## Success criteria — pass/fail

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | 4 personas reach correct terminal states | ✅ PASS | clean→APPROVE, conditional→CONDITIONAL_APPROVE, decline→DECLINE, fraud→ESCALATED (verifier ran all four) |
| 2 | Both gates pause/resume cross-process via Action Inbox | ✅ PASS | `run --interactive` → `inbox` → `approve` ×2 across processes → closes CONDITIONAL_APPROVE; tasks persisted/resolved in SQLite |
| 3 | All 7 exception routes per policy, tested | ✅ PASS | `exception_policy.py` (7 routes) + parametrized + behavior tests |
| 4 | `uipath init`/`pack` → valid `.nupkg` without a tenant | ✅ PASS | Produced `.uipath/mortgage-underwriting-agents.0.1.0.nupkg` during M6; config artifacts committed; path in `docs/DEPLOY_UIPATH.md` |
| 5 | ≥80% coverage; lint + types clean; deterministic | ✅ PASS | 72 tests, **93%** coverage; ruff clean; mypy clean; identical outcomes across runs (LLM stubbed) |
| 6 | Same source under Local + cloud port (one env var) | ✅ PASS | graphs/ & `local_adapter.py` do not import the SDK; only `uipath_adapter.py` does (lazy); `RUNTIME_MODE` selects |
| 7 | Submission assets complete | ✅ PASS | README (+ Claude Code evidence), ARCHITECTURE, DEPLOY_UIPATH, DEMO_SCRIPT, DECK_OUTLINE, devpost/SUBMISSION, Apache-2.0 LICENSE, SECURITY |

## Build log
- `pytest --cov` → **72 passed, 93% coverage** (threshold 80%).
- `ruff check src sim tests` → clean. `mypy src` → clean (27 files).
- Security (`SECURITY.md`, STRIDE + deps) → **0 open Critical/High** (H-1 mitigated via loopback-bind guard; verified by running it).
- `uipath init` + `uipath pack` (in an isolated `.[cloud]` env) → valid `.nupkg`; clean agent I/O contract (`entry-points.json` input=application, output=decision+audit).

## Built
Five coded LangGraph agents + supervisor; dual-mode `PlatformPort` (LocalAdapter / UiPathAdapter);
two human gates + verify gate via durable LangGraph interrupts; SQLite cross-process
suspend/resume; 7-route exception policy; 8 personas; deterministic finance/policy engine;
optional CrewAI deliberation panel; FastAPI loan-officer desk; CLI (`run`/`inbox`/`approve`/
`cases`/`personas`/`serve`); validated UiPath packaging; full test suite + docs + submission assets.

## Deferred (need a UiPath Labs tenant or out of demo scope)
- **Live cloud publish/run** (`uipath publish` / `invoke`) and Maestro Case canvas wiring —
  gated on tenant access; the command list and `case_definition.yaml` make this mechanical
  (`docs/DEPLOY_UIPATH.md`).
- **Real connectors** for the credit bureau, AML, and Document Understanding (currently
  mocked locally; cloud adapter calls API-Workflow URLs from Orchestrator assets).
- Live CrewAI panel / LLM-Gateway narration (optional `.[live,crew]` extras).

## Next steps for the team
1. **Request UiPath Labs access now** (≤3 business days) — the top blocker for the platform demo.
2. Follow `docs/DEPLOY_UIPATH.md`: `uipath auth → init → pack → publish`, set the two
   Orchestrator assets, wire the Maestro Case from `case_definition.yaml`.
3. Record the ≤5-min demo per `docs/DEMO_SCRIPT.md`; fill the deck from `docs/DECK_OUTLINE.md`;
   paste `devpost/SUBMISSION.md` into Devpost; push the repo public with the Apache-2.0 license.
