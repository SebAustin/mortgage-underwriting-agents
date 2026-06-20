# Deploying to UiPath Automation Cloud

This guide takes the solution from the local simulation to a running **UiPath Maestro
Case** with **coded agents**, **Action Center** human gates, and governed external
services. It is written so deployment is a short, mechanical command list once you have a
UiPath Labs / Automation Cloud tenant.

> **Status:** the repo is fully *cloud-ready*. The coded agent already packages into a
> valid `.nupkg` with `uipath pack` **without a tenant** (proof below). The steps that
> need a live tenant (publish, asset config, Maestro Case wiring) are marked **[tenant]**.

---

## 1. Prerequisites

- A UiPath Automation Cloud tenant (UiPath Labs for AgentHack).
- Python 3.11+ and [`uv`](https://docs.astral.sh/uv/) (or pip).
- Node.js (only if you also use the `@uipath/cli` `uip` command for coding-agent skills).

## 2. Install with the cloud extra

```bash
uv venv --python 3.12 && source .venv/bin/activate
uv pip install -e ".[cloud]"      # adds uipath + uipath-langchain
```

## 3. Authenticate **[tenant]**

```bash
uipath auth            # opens a browser; stores a token for your org/tenant
# Set RUNTIME_MODE=uipath and your tenant URL in .env (never commit real values):
#   RUNTIME_MODE=uipath
#   UIPATH_URL=https://cloud.uipath.com/<org>/<tenant>
```

## 4. Generate the coded-agent config (no tenant needed)

```bash
uipath init     # imports the graph from langgraph.json, writes uipath.json,
                # bindings.json and entry-points.json (the agent's I/O contract)
```

`langgraph.json` points at the deployable case graph:

```json
{ "graphs": { "mortgage-case": "./src/mortgage_agents/graphs/case_orchestrator.py:graph" } }
```

## 5. Package — **validated without a tenant**

```bash
uipath pack     # → .uipath/mortgage-underwriting-agents.<version>.nupkg
```

This repo has been verified end-to-end through `uipath pack`: the package contains the
agent source, `pyproject.toml`, `uv.lock`, and the generated `entry-points.json`, and it
**excludes `.env`** (secrets never ship in the package).

## 6. Publish & run **[tenant]**

```bash
uipath publish                       # upload to the Orchestrator package feed
uipath invoke mortgage-case --input '{"application": { ... }}'   # run on the cloud
```

## 7. Configure governed services (Orchestrator assets) **[tenant]**

The `UiPathAdapter` (`src/mortgage_agents/ports/uipath_adapter.py`) reads these assets:

| Asset name              | Type        | Purpose                                  |
|-------------------------|-------------|------------------------------------------|
| `mua_credit_bureau_url` | Text/Secret | Credit bureau API Workflow / connector   |
| `mua_aml_url`           | Text/Secret | AML / watchlist screening service        |

Create them under your folder (default `Shared`). LLM calls route through the **UiPath
LLM Gateway** in cloud mode (no API keys in code).

## 8. Build the Maestro Case **[tenant]**

`case_definition.yaml` is the **single source of truth** for the case lifecycle — recreate
it 1:1 in the Maestro Case designer:

- **Stages**: intake → doc_verification → income_analysis → adjudication → conditions →
  decision → closing (plus `request_info` and `escalate` terminals).
- **Agents**: add the published `mortgage-case` coded agent as the Service Task in each
  agent-owned stage (or one published agent per stage if you split them).
- **Human gates**: `verify_gate`, `gate_a`, and `gate_b` map to **Action Center** tasks /
  escalations — the adapter already raises `CreateTask` / `CreateEscalation` interrupts, so
  Maestro renders them as human tasks automatically.
- **Exception routes**: mirror the `exception_routes` block (re-digitise retry, request-info,
  compliance escalation, transient-failure retry).

## 9. Document Understanding **[tenant]**

For real documents, run UiPath **Document Understanding (IDP)** in an upstream RPA/API step
and pass the extracted fields to the agent. `UiPathAdapter.extract_document` surfaces those
fields with their confidence; the `redigitize` retry and `verify_gate` handle low-confidence
and conflicting extractions exactly as in the local simulation.

---

## How the same code runs in both places

Nothing in the agents changes between local and cloud — only the injected
[`PlatformPort`](../src/mortgage_agents/ports/platform_port.py):

| Capability            | `LocalAdapter` (no tenant)        | `UiPathAdapter` (cloud)                     |
|-----------------------|-----------------------------------|---------------------------------------------|
| Human gate            | local Action Inbox (SQLite)       | Action Center `CreateTask`/`CreateEscalation` |
| Durable suspend/resume| SQLite checkpointer               | Maestro durable execution                   |
| Document Understanding| canned fixture payloads           | UiPath IDP fields                           |
| Credit / AML          | deterministic mocks               | API Workflow / connector via asset URL      |
| Secrets               | `.env`                            | Orchestrator assets                         |
| LLM                   | stub (default) / Anthropic        | UiPath LLM Gateway                          |

Selected by one variable: `RUNTIME_MODE=local|uipath`.
