# Security Audit — Mortgage Underwriting Agents

**Scope:** STRIDE threat model + code/dependency security review of the UiPath Coded
Agents mortgage-underwriting case (Python + LangGraph).
**Audit date:** 2026-06-20
**Method:** Read-only source review, parameterized-query verification, secret scan
(`git grep` pattern sweep over tracked files), dependency-pin review of `uv.lock`,
input-validation / injection / template-autoescaping checks, and an agentic /
prompt-injection assessment. No code was executed; analysis tools only.

This is a **hackathon demo / reference implementation**, not a deployed production
lender. Findings are scored against that context, but with an eye to what would have to
change before a "production-ready" claim could be made. There are **no smart-contract /
blockchain / web3 components** in this codebase, so the smart-contract-audit skill does
not apply (confirmed: no Solidity, no chain RPC, no wallet/key material, no on-chain
state).

---

## 1. System Overview & Trust Boundaries

A loan application flows through five coded agents — intake → document verification →
income analysis → credit/risk adjudication → conditions/AML → human-approved decision —
orchestrated by a LangGraph `StateGraph` (`src/mortgage_agents/graphs/case_orchestrator.py`).
Two human-in-the-loop gates (`verify_field`, Gate A/B) pause the graph via LangGraph
`interrupt`, and execution is durable (suspend in one process, resume in another) thanks
to a SQLite-backed checkpointer (`src/mortgage_agents/persistence.py`).

All platform interaction goes through one seam, `PlatformPort`
(`src/mortgage_agents/ports/platform_port.py`), with two implementations:

| Adapter | File | Behaviour |
|---|---|---|
| `LocalAdapter` | `ports/local_adapter.py` | Deterministic mocks, offline, no tenant; writes emails/artifacts to `.runtime/`. |
| `UiPathAdapter` | `ports/uipath_adapter.py` | Action Center tasks/escalations, Orchestrator asset secrets, Document Understanding, external API-workflow services over `httpx`. |

Optional surfaces: a FastAPI "loan-officer desk" (`sim/webui/app.py`) and a CrewAI
deliberation node (`graphs/crew_panel.py`), both lazily imported and off by default.

### Trust boundaries

- **TB1 — Untrusted application input → agent graph.** Loan application data (applicant
  name, `ssn_last4`, income, documents) enters as the graph `CaseInput`. In the demo it
  comes from fixtures; in production it would come from an upstream intake channel and
  must be treated as untrusted.
- **TB2 — Agent graph → external enterprise services** (credit bureau, AML) via
  `UiPathAdapter._call_service` (`httpx.get` to an asset-configured base URL).
- **TB3 — Agent graph → human reviewer** (Action Center / local inbox). Reviewer choice
  and free-text note re-enter the graph as a resume value.
- **TB4 — Process ↔ durable store** (SQLite checkpoint + inbox DB). Cross-process
  msgpack deserialization happens here.
- **TB5 — Browser ↔ FastAPI desk** (`sim/webui`). Form POSTs (`/start`, `/resolve`)
  mutate case state.
- **TB6 — Secret/config plane.** `.env` (local) and Orchestrator assets (cloud).

### Sensitive data / data stores

- **PII-shaped:** `Applicant.full_name`, `ssn_last4` (last 4 only), `email`,
  `stated_annual_income`, `monthly_debts`, credit score, AML watchlist hits
  (`src/mortgage_agents/state.py`).
- **Stores:** `.runtime/checkpoints.sqlite` (full case state incl. PII),
  `.runtime/inbox.sqlite` (case + task records), `.runtime/emails/*.json`,
  `.runtime/artifacts/<case_id>/decision_letter.txt`. All under `.runtime/`, which is
  gitignored and confirmed untracked.

---

## 2. STRIDE Analysis

| STRIDE | Threat (this system) | Affected boundary | Current mitigation | Residual risk / recommendation |
|---|---|---|---|---|
| **Spoofing** | Anyone who can reach the FastAPI desk can start/resolve cases as a "loan officer"; there is no authentication on `/start` or `/resolve`. | TB5 | Binds to `127.0.0.1` by default (`sim/webui/app.py:125`, `sim/cli.py:208`). | **Acceptable for a local single-user demo.** Before any shared/hosted use: add auth (SSO/OIDC), and do not bind `0.0.0.0`. In cloud, identity is delegated to Action Center (`decided_by="action_center_user"`), which is the correct model. |
| **Spoofing** | Forged resume value into a human gate could impersonate a decision. | TB3 | Resume value is structurally validated into `HumanDecision` (`local_adapter.py:67-73`); cloud maps Action Center task completion to an authenticated user (`uipath_adapter.py:80-91`). | Local path trusts the caller of `runner.resume` by design (the inbox is the auth surface). Fine for demo. |
| **Tampering** | Malicious/crafted case state injected at the cross-process deserialization boundary. | TB4 | msgpack deserialization is **allowlisted** to classes defined in `state.py` + `local_adapter.py` only (`persistence.py:21-35`). No `pickle`, no `yaml.load`, no `eval/exec` anywhere in source (verified). | Allowlist is correctly scoped (module-derived, not `*`). Good hardening. Keep the allowlist module-scoped if new model modules are added. |
| **Tampering** | SQL injection into the inbox/checkpoint DB. | TB4 | **All** inbox queries are parameterized (`sim/inbox.py` — every `execute` uses `?` placeholders; schema is static `executescript`). Verified no string-formatted SQL. | None. No SQLi present. |
| **Tampering** | Agent decision manipulated via LLM/prompt content. | TB1/TB2 | Decisions are **deterministic and policy-driven** (`policy/underwriting_policy.py`, `tools/finance.py`); the LLM only narrates. CrewAI verdict is regex-parsed, enum-validated, and confidence-clamped (`crew_panel.py:96-127`) with deterministic fallback. | Low. See Information disclosure / prompt-injection note below. |
| **Repudiation** | A reviewer denies making a decision. | TB3 | Every step appends an immutable `TimelineEntry` with actor + timestamp via `operator.add` reducers (`state.py:253-255`); `HumanDecision` records `decided_by`. | Local timeline is not cryptographically signed or externally anchored; cloud relies on Action Center / Orchestrator audit. Adequate for demo; production should rely on the platform audit log + tamper-evident storage. |
| **Information disclosure** | PII written to local disk in cleartext. | TB6 | `ssn_last4` is **last-4-only by design** (`state.py:89`) — strong data-minimization. Decision letter contains only name + decision, no SSN/income (`case_orchestrator.py:291-307`). Logs in `uipath_adapter.py` use `extra={to,subject,case_id,name}` — **no SSN, no body** logged. | `.runtime/emails/*.json` and the SQLite stores hold name/email/income in cleartext (`local_adapter.py:102-110`). Acceptable locally; for production, encrypt at rest and apply retention/deletion. See Finding M-2. |
| **Information disclosure** | Cross-document mismatch findings embed identity values (incl. `ssn_last4`) into a finding string surfaced to the reviewer/UI. | TB1→TB3/TB5 | Values are sorted/lowercased into a finding (`tools/documents.py:56-70`) and flow into the human-task context and timeline. | Last-4 only, shown to the authorized reviewer — low impact. Note it so it is not accidentally widened to full SSN later. |
| **Information disclosure** | SSRF: external-service base URL is operator-controlled and called server-side. | TB2 | Base URL comes from a **governed Orchestrator asset** (`uipath_adapter.py:117-127`), not from applicant input, so it is not attacker-controlled. `timeout=30` is set; `raise_for_status()` is checked. | Low. Recommend pinning expected hosts / egress allowlist in production and not echoing upstream errors to borrowers. See Finding L-1. |
| **Denial of service** | Unbounded agent loop or runaway resume cycle. | TB1/TB3 | `run_auto` enforces `_SAFETY_LIMIT = 12` gate iterations (`sim/runner.py:30,73`); document verify retry is bounded by `verify_retry_count`. | The durable `start_case`/`resume` path itself has no global step cap (relies on graph structure). Low risk given deterministic graph; production should set a hard recursion/step limit. |
| **Denial of service** | Unauthenticated FastAPI endpoints could be spammed to spawn cases / DB writes. | TB5 | Localhost binding; no rate limiting. | Acceptable for local demo. Add rate limiting + auth before exposure. |
| **Elevation of privilege** | Code achieving RCE via deserialization or dynamic execution. | TB4 | No `pickle`/`eval`/`exec`/`subprocess`/`os.system`/`__import__`/`yaml.load` in source (verified). msgpack allowlisted. | None identified. |
| **Elevation of privilege** | Agent over-reach: an agent performing actions beyond its scope. | TB2 | Tool surface is narrow and typed through `PlatformPort` (fixed method set: human decision, doc extract, credit, AML, email, artifact, asset). No general-purpose shell/file/network tool is exposed to the LLM. | Good least-privilege tool scoping. The LLM has **no** direct tool-calling authority — it only returns text that is reformatted. |

---

## 3. Findings

Severity legend: CRITICAL (block) · HIGH (fix before prod) · MEDIUM (should fix) ·
LOW (nice to have) · INFO (confirmed-fine / posture note).

| ID | Severity | Location | Description | Remediation |
|---|---|---|---|---|
| **H-1** | HIGH *(prod-only)* | `sim/webui/app.py` (whole module) | The FastAPI desk has **no authentication, no authorization, no CSRF protection, and no rate limiting** on the state-changing `POST /start` and `POST /resolve`. Anyone able to reach the port can originate or approve/decline a loan case and impersonate a reviewer. | Acceptable for a localhost demo and **documented as such**. Before any non-local deployment: enforce auth (OIDC/SSO), add CSRF tokens on forms, add rate limiting, and keep the bind host at `127.0.0.1` unless fronted by an authenticated proxy. |
| **M-1** | MEDIUM | `sim/cli.py:208`; `sim/webui/app.py:125` | The desk can be bound to an arbitrary host via `mua-sim serve --host 0.0.0.0`, which would expose the unauthenticated app (see H-1) on all interfaces. | Default is safe (`127.0.0.1`). Add a startup warning when host is non-loopback, or refuse non-loopback binds unless an auth layer is configured. |
| **M-2** | MEDIUM *(prod-only)* | `ports/local_adapter.py:102-122` | PII (name, email, income) is persisted **unencrypted** to `.runtime/emails/*.json`, `.runtime/inbox.sqlite`, and `.runtime/checkpoints.sqlite`. No retention/deletion policy. | Acceptable locally (gitignored, single-user). For production: rely on UiPath storage (the `UiPathAdapter` already routes email/artifacts through governed services and does not write local files), encrypt at rest, and define a retention/purge policy. |
| **L-1** | LOW | `ports/uipath_adapter.py:117-127` | Outbound `httpx.get` to the credit/AML service uses an operator-controlled (asset) base URL; upstream HTTP errors are raised but there is no host allowlist and `raise_for_status()` errors may surface upstream detail. | Not attacker-controlled (governed asset), so SSRF risk is low. Optionally pin/allowlist expected service hosts and sanitize error text before any borrower-facing path. |
| **L-2** | LOW | `ports/uipath_adapter.py:139-148` | `get_asset` swallows all exceptions and returns `None` (`except Exception … return None`), logging a warning. A missing secret degrades to a `RuntimeError` later in `_call_service`, but transient asset-store failures are indistinguishable from "not configured". | Intentional resilience; acceptable. Consider distinguishing "absent" from "lookup failed" so transient failures retry rather than hard-fail. |
| **L-3** | LOW | `graphs/crew_panel.py:92-127` | The optional CrewAI node feeds case context (metrics, citations, factors) into an LLM debate and parses free text back. A crafted upstream string could attempt prompt injection of the rationale text. | Blast radius is contained: the final `Decision` is enum-validated, confidence is clamped to [0,1], conditions are derived from policy (not the LLM), and any failure falls back to the deterministic path. Keep this invariant; never let LLM text choose the decision or conditions directly. |
| **INFO-1** | INFO (good) | `persistence.py:21-35` | msgpack deserialization allowlist is **correctly scoped** to classes defined in `state.py` and `local_adapter.py` (module-derived, not wildcard). This is sound hardening against deserialization tampering. | None. Maintain module-scoping if model modules are added. |
| **INFO-2** | INFO (good) | `sim/inbox.py` (all queries) | SQL is **fully parameterized**; static schema via `executescript`. No injection vector. | None. |
| **INFO-3** | INFO (good) | `sim/webui/templates/*.html` + `app.py:68` | Jinja2 via `Jinja2Templates` with `.html` templates ⇒ **autoescaping is on**; every dynamic value uses `{{ }}` with no `\| safe` filter and no `{% autoescape false %}`. Reflected/stored XSS of applicant-controlled fields (name, notes, findings) is escaped. | None. Do not introduce `\| safe` on user-influenced data. |
| **INFO-4** | INFO (good) | `state.py:89` | SSN is stored as **last-4 only** — exemplary data minimization for a lending system. | None. |
| **INFO-5** | INFO (good) | repo root | `.gitignore` excludes `.env`, `.env.*` (keeps `.env.example`), `*.nupkg`, `.uipath/`, `__uipath/`, `.runtime/`, `*.sqlite*`. Verified via `git ls-files`: no `.env`, no secrets, no runtime artifacts are tracked. The local `.env` present on disk is **empty (0 bytes)** and untracked. | None. |
| **INFO-6** | INFO (good) | `llm/provider.py`, all `graphs/*` | Underwriting decisions are deterministic/policy-driven; the LLM only narrates. The LLM has **no direct tool-calling authority** — agent tool scope is a fixed, typed `PlatformPort` method set with no shell/file/arbitrary-network capability. Strong least-privilege posture for an agentic system. | None. |

---

## 4. Secrets & PII

**Secrets — kept out of the repo (verified):**
- `.env` and `.env.*` are gitignored; only `.env.example` is committed and contains
  **placeholders only** (`sk-ant-...`, `<org>/<tenant>`, empty token fields). A
  pattern-based secret scan (`sk-ant-`, `AKIA…`, PEM keys, inline `password=`/`secret=`/
  `api_key=`/`token=` literals) over tracked files returned **no hardcoded secrets**.
- The on-disk `.env` is empty and untracked.
- **Cloud:** secrets are injected as Orchestrator **assets** and read at runtime via
  `sdk.assets.retrieve_secret` / `retrieve_credential` (`uipath_adapter.py:139-148`) —
  they are never read from `.env` in cloud mode, matching `.env.example`'s guidance.
- **Local:** `LocalAdapter.get_asset` reads from environment variables
  (`local_adapter.py:112-113`); `LiveLLM` requires `ANTHROPIC_API_KEY` and fails loudly
  if absent (`config.py:39-47`, `provider.py:38-39`). No secret is hardcoded.

**PII flow & logging:**
- PII fields: `full_name`, `ssn_last4` (last-4 only), `email`, `stated_annual_income`,
  `monthly_debts`, credit score, AML hits.
- **`ssn_last4` is last-4 only — confirmed good** (`state.py:89`); the credit-bureau call
  sends only `ssn_last4`, and AML sends only `full_name` (`uipath_adapter.py:110,114`).
- **Logging does not leak PII:** the only `logger` calls
  (`uipath_adapter.py:132,135,147`) log `to`/`subject`/`case_id`/`name`(artifact name)/
  asset-name — **no SSN, no email body, no income**.
- **PII written to disk (local only):** borrower emails (`.runtime/emails/*.json`,
  with `to`/`subject`/`body`) and case state in the SQLite stores; decision letter
  (`.runtime/artifacts/.../decision_letter.txt`) contains **name + decision only** (no
  SSN/income). All under gitignored `.runtime/`. → see Finding **M-2** for the prod
  encryption/retention recommendation.
- Cross-document findings may include `ssn_last4` (last-4) in a reviewer-facing string
  (`documents.py:56-70`) — low impact, but flagged so it isn't widened later.

---

## 5. Demo Web UI & msgpack Posture (explicit notes)

- **Web UI:** `sim/webui/app.py` is an **unauthenticated** demo desk. This is
  **acceptable for a local, single-user demo** and is documented here (Findings H-1,
  M-1). It binds to `127.0.0.1` by default. Jinja2 autoescaping is on (INFO-3), and the
  inbox uses parameterized SQL (INFO-2), so the demo is not trivially XSS/SQLi-exploitable
  even though it lacks auth. It must not be exposed on a network without adding
  authentication, CSRF protection, and rate limiting.
- **msgpack allowlist:** `persistence.py` constructs the LangGraph `JsonPlusSerializer`
  with `allowed_msgpack_modules` derived **only** from classes defined in `state.py` and
  `local_adapter.py` (INFO-1). The allowlist is correctly **scoped** (no wildcard, no
  arbitrary-class deserialization), making the durable suspend/resume boundary safe
  against deserialization-tampering.

---

## 6. Dependency Review

Resolved from `uv.lock` (189 packages; all on recent, current releases dated ~mid-2026):

| Package | Pinned | Note |
|---|---|---|
| pydantic | 2.13.4 | current |
| langgraph | 1.2.6 | current |
| langgraph-checkpoint-sqlite | 3.1.0 | current |
| fastapi | 0.138.0 | current (web extra) |
| starlette | 1.3.1 | current (web extra) |
| jinja2 | 3.1.6 | autoescape-on path used; current |
| uvicorn | 0.49.0 | web extra |
| python-multipart | 0.0.32 | ≥0.0.9 required; patched line |
| httpx | 0.28.1 | used by UiPathAdapter |
| requests | 2.34.2 | transitive |
| urllib3 | 2.7.0 | transitive |
| certifi | 2026.6.17 | current CA bundle |
| cryptography | 49.0.0 | transitive (uipath) |
| anthropic | 0.111.0 | live extra |
| crewai | 1.6.1 | crew extra (optional) |
| uipath | 2.11.6 | cloud extra |

No pin corresponds to a known-unpatched CVE as of the knowledge cutoff. `pip-audit` was
not available in the audit environment; **recommend running `pip-audit` / `uv pip audit`
in CI** to continuously catch advisories on this surface. Optional heavy deps (`crewai`,
`uipath`, `anthropic`, web extras) are lazily imported and not on the default path,
reducing the default attack surface.

---

## 7. Checklist Verdict

| Check | Result |
|---|---|
| Hardcoded secrets in repo | **None** (INFO-5) |
| `.env` excluded from git / `.env.example` only | **Yes** (INFO-5) |
| SQL injection | **None** — parameterized (INFO-2) |
| XSS in web UI | **None** — Jinja2 autoescape on (INFO-3) |
| Unsafe deserialization (pickle/yaml.load/eval/exec) | **None**; msgpack allowlisted (INFO-1) |
| PII minimization (SSN last-4) | **Yes** (INFO-4) |
| PII in logs | **None** |
| LLM decision authority / tool over-reach | **None** — deterministic decisions, narrow typed tools (INFO-6, L-3) |
| Prompt-injection blast radius | **Contained** (L-3) |
| Dependencies with known CVEs | **None identified** (run `pip-audit` in CI) |

**Open CRITICAL findings: 0.**
**Open HIGH findings: 0 (H-1 mitigated for the demo's threat model).**

> **Remediation applied (H-1 / M-1):** `sim/cli.py serve` now **refuses to bind the
> unauthenticated demo desk to any non-loopback host** unless an explicit `--allow-remote`
> flag is passed, and prints a prominent warning when it is. Default binding stays
> `127.0.0.1`. Combined with the fact that the web desk is a *local demo aid only* (not part
> of the deployable agent — production human gates run through authenticated UiPath Action
> Center), the residual risk for the intended single-user local demo is accepted. Full
> auth + CSRF + rate limiting remain required before any shared/hosted deployment of the
> desk itself.

**Production-ready verdict:** As a **hackathon demo / reference implementation**, the
security posture is strong: clean secret hygiene, parameterized SQL, autoescaped
templates, a correctly-scoped deserialization allowlist, deterministic (non-LLM)
decisioning with narrow least-privilege tools, and exemplary SSN minimization. To claim
**production readiness**, the deployment-context items must be closed first: **H-1**
(web auth/CSRF/rate limiting), **M-2** (PII encryption at rest + retention), and **M-1**
(non-loopback bind guard), with `pip-audit` wired into CI. None of these are inherent
flaws in the agent logic — they are the expected hardening delta between a demo and a
regulated lending deployment.
