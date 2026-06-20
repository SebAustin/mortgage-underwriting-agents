# Presentation Deck Outline

Fill the official AgentHack template with these slides. Each bullet is speaker-ready.

**1 — Title.** "Mortgage Underwriting Agents — an agentic UiPath Maestro Case." Track 1.
Team / author. Tagline: *coded agents that underwrite, humans who decide.*

**2 — The problem.** Mortgage underwriting is dynamic & exception-heavy; RPA is too rigid
for the tail, a raw LLM is unacceptable for a regulated credit decision. Cost of manual
exception handling + the compliance need for human accountability.

**3 — The idea.** Agentic case management: agents reason & coordinate, robots do mechanical
work, humans hold authority. Map to UiPath Maestro Case.

**4 — Architecture.** The diagram: 5 coded agents → 6 stages → 2 human gates → 1 exception
lane. Highlight the `PlatformPort` seam (local ⇄ UiPath, one env var).

**5 — The agents.** One line each: Intake, DocVerify (+IDP), Underwriting, Adjudication
(+ CrewAI panel), Exception/Compliance. Note the deterministic decision + LLM-narrates split.

**6 — Humans in the loop.** Gate A (underwriter decision support, borderline only) and
Gate B (final authority, every case); durable suspend/resume = Action Center + Maestro.

**7 — Exceptions & resilience.** The 7-route policy table; auto re-digitise retry, AML hard
escalation, transient-failure backoff. "Exception handling is the product."

**8 — Live demo.** (Embed/transition to the 5-min video.) Clean → borderline (gates) →
fraud (escalation) → `uipath pack`.

**9 — UiPath platform usage.** Maestro Case, Coded Agents, Action Center, Document
Understanding, Orchestrator assets, API Workflows, LLM Gateway, + CrewAI inside the
governed layer. Validated `uipath pack`.

**10 — Built with Claude Code.** UiPath for Coding Agents: the whole solution authored by
Claude Code; git history co-authored; `uipath init`/`pack` in the loop. (Bonus.)

**11 — Production readiness.** 72 tests / ~94% coverage, ruff + mypy clean, STRIDE security
audit (0 open Critical/High), deterministic & reproducible. Deploy guide reduces go-live to
a command list.

**12 — Impact & next steps.** Faster cycle time, fewer manual touches, full auditability,
humans accountable. Next: real IDP project + bureau connector + Maestro Case canvas wiring
(all scaffolded in `case_definition.yaml`).

**13 — Thank you / links.** GitHub repo, demo video, this deck.
