# 5-Minute Demo Script

Target: **≤ 5:00**. Show the solution *running*, the architecture, the agents + their
orchestration, and where humans fit. Record terminal + browser; voice-over in **bold**.

## 0:00–0:40 — Problem & framing
- **"Mortgage underwriting is dynamic and exception-heavy: most files are routine, but the
  tail needs document chasing, re-verification, judgement calls, and fraud escalation — and
  a human must own the credit decision. That's a Maestro Case."**
- Show the diagram in [README](../README.md) / [ARCHITECTURE](ARCHITECTURE.md): five coded
  agents, six stages, two human gates, one exception lane.
- **"Built entirely with Claude Code via UiPath for Coding Agents."**

## 0:40–1:40 — Clean path (straight-through)
```bash
mua-sim run clean_approve
```
- **"A loan application enters. IntakeAgent triages documents, DocVerifyAgent extracts and
  cross-checks them, UnderwritingAgent computes qualifying income, AdjudicationAgent pulls
  credit and applies policy — DTI 29%, LTV 80%, score 760 — and recommends approve."**
- Point at the timeline: agent / robot / human columns. **"Only the final human gate (Gate
  B) fires — the underwriter signs. A decision letter is generated."**

## 1:40–2:50 — Borderline path + human-in-the-loop (the heart)
```bash
mua-sim run conditional_approve --interactive    # suspends at Gate A
mua-sim inbox
mua-sim approve <task_id> --choice conditional_approve --note "reserves offset DTI"
```
- **"This file is borderline — 44% DTI. The AdjudicationAgent finds compensating factors
  (8 months reserves, 760 score) and flags it for a human. The case SUSPENDS — durably, to
  SQLite — and a task appears in the inbox, exactly like Action Center."**
- **"I resume it in a separate command — a different process — and it picks up right where
  it left off. Gate A is the underwriter's decision support; Gate B is final authority.
  Two humans, two roles."** (Resume Gate B too.)
- *(Optional, browser):* `mua-sim serve` → the loan-officer desk; click Approve on the gate.

## 2:50–3:50 — Exceptions & failure handling
```bash
mua-sim run fraud_exception
```
- **"This applicant's employer disagrees across the W-2 and pay stub — a conflict. The
  agent can't auto-resolve it, so it routes to a human verify gate. Then the AML screen
  hits a watchlist — a hard stop. The case escalates to compliance and never reaches an
  automated approval."**
- **"Every exception route — missing docs, low OCR confidence with an automatic re-digitise
  retry, DTI breaches, appraisal gaps, fraud, and transient API failures with backoff — is
  in one auditable policy table, and every one is tested."** (Show `policy/exception_policy.py`.)

## 3:50–4:30 — Same code, on UiPath
- Show `ports/` : **"The agents never call the SDK directly — they call a PlatformPort.
  Locally it's mocks and a SQLite inbox. In the cloud, the SAME graph runs against Action
  Center, Orchestrator assets, Document Understanding, and the LLM Gateway. One env var."**
```bash
uipath init && uipath pack          # (in the .[cloud] env)
```
- **"The coded agent packages into a valid .nupkg — verified without a tenant. Here's the
  clean input/output contract UiPath generated."** (Show `.uipath/*.nupkg`, `entry-points.json`.)

## 4:30–5:00 — Close
- **"Five coded agents, durable human-in-the-loop, exception handling, and a clean cloud
  port — built end to end by Claude Code. 72 tests, 94% coverage, security-audited."**
- Show `git log` (co-authored commits) and `pytest` green.

### Pre-record checklist
- `rm -rf .runtime` for a clean inbox before recording.
- Have the `.[web]` and `.[cloud]` envs ready if showing the UI / pack steps.
- Keep each command's output on screen long enough to read the decision panel.
