# Assumptions

Decisions and constraints recorded during intake/build (AgentHack 2026, Track 1).

- **Track & domain:** UiPath Maestro Case; mortgage / loan underwriting (chosen with the user).
- **No UiPath tenant during the build.** The repo is built cloud-ready and verified through
  `uipath pack` (valid `.nupkg`) **without a tenant**; live publish/run, Orchestrator asset
  setup, and Maestro Case canvas wiring are staged in `docs/DEPLOY_UIPATH.md`.
  **Top external action for the team:** request UiPath Labs access (≤3 business days) before
  the submission deadline so the demo can show the solution running on the platform.
- **Maestro Case canvas + any low-code Agent Builder agents are authored in the cloud GUI**
  by the team; `case_definition.yaml` is the 1:1 source of truth so reconstruction is
  mechanical.
- **LLM is a deterministic stub by default** so the whole solution runs offline, with no API
  key, reproducibly (tests/CI and judges cloning the repo). A live Anthropic model and the
  CrewAI panel are optional (`LLM_MODE=live`, `.[live,crew]`); in cloud, LLM access routes
  through the UiPath LLM Gateway.
- **Data is synthetic; no real PII.** SSNs are represented as last-4 only. Credit bureau,
  AML, and Document Understanding are mocked locally; in cloud they are API Workflows /
  connectors / IDP.
- **UiPath SDK surface is pinned and isolated** in `ports/uipath_adapter.py`
  (`CreateTask`/`CreateEscalation`, `sdk.assets.retrieve_secret`), verified against the
  installed `uipath` 2.11.x. One file to update on SDK drift.
- **The web UI is a local demo aid**, not part of the deployable agent; it is unauthenticated
  by design and guarded to loopback-only binding (see `SECURITY.md`). Production human gates
  run through authenticated UiPath Action Center.
- **Python 3.12** for the dev/build environment (broad ecosystem compatibility);
  `requires-python = ">=3.11"`, matching UiPath coded-agent support.
