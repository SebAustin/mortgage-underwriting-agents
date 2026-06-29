// Builds CaseWeaver-Deck.pptx — a 13-slide, on-brand dark deck for the AgentHack submission.
// Native design throughout, with two real product screenshots embedded as evidence.
const P = require("pptxgenjs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..", ".."); // repo root
const GAL = path.join(ROOT, "devpost", "gallery");

const C = {
  bg: "0B0E14", panel: "141925", panel2: "0E131D", ink: "F2F5FB", soft: "9AA6BF",
  accent: "7C8CFF", accentSoft: "1B2138", line: "232A39",
  green: "34D399", amber: "FBBF24", red: "FB7185", blue: "38BDF8", violet: "A78BFA",
};
const HF = "Trebuchet MS";   // headers
const BF = "Calibri";        // body
const MF = "Consolas";       // mono / kickers

const pres = new P();
pres.defineLayout({ name: "W", width: 13.333, height: 7.5 });
pres.layout = "W";
pres.author = "Sebastien Henry";
pres.title = "CaseWeaver — Mortgage Underwriting Agents";

const W = 13.333, H = 7.5, MX = 0.75, CW = W - 2 * MX;
const sh = () => ({ type: "outer", color: "000000", blur: 9, offset: 4, angle: 135, opacity: 0.45 });

function base(dark = true) {
  const s = pres.addSlide();
  s.background = { color: dark ? C.bg : C.bg };
  // faint accent glow top-right for depth
  s.addShape(pres.shapes.OVAL, { x: W - 4.5, y: -2.6, w: 6.5, h: 5, fill: { color: "1B2740", transparency: 35 }, line: { type: "none" } });
  return s;
}
function kicker(s, t) {
  s.addText(t.toUpperCase(), { x: MX, y: 0.46, w: CW, h: 0.36, fontFace: MF, fontSize: 12.5, color: C.accent, bold: true, charSpacing: 3, margin: 0 });
}
function title(s, t, size = 30) {
  s.addText(t, { x: MX, y: 0.86, w: CW, h: 1.15, fontFace: HF, fontSize: size, bold: true, color: C.ink, margin: 0, lineSpacingMultiple: 1.02 });
}
function panel(s, x, y, w, h, fill = C.panel) {
  s.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { color: fill }, line: { color: C.line, width: 1 }, shadow: sh() });
}
function chip(s, x, y, w, h, t, color, txtColor) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: h / 2, fill: { color }, line: { type: "none" } });
  s.addText(t, { x, y, w, h, fontFace: MF, fontSize: 12.5, bold: true, color: txtColor || "0B0E14", align: "center", valign: "middle", margin: 0 });
}
function footer(s, n) {
  s.addText("CaseWeaver · UiPath AgentHack 2026", { x: MX, y: H - 0.46, w: 8, h: 0.3, fontFace: MF, fontSize: 9.5, color: "5b6party".slice(0,0) + "5B6680", margin: 0 });
  s.addText(String(n), { x: W - MX - 1, y: H - 0.46, w: 1, h: 0.3, fontFace: MF, fontSize: 9.5, color: "5B6680", align: "right", margin: 0 });
}

// ── 1. Title ────────────────────────────────────────────────────────────────
(() => {
  const s = base();
  s.addText("UIPATH AGENTHACK 2026  ·  TRACK 1 — MAESTRO CASE", { x: MX, y: 1.5, w: CW, h: 0.4, fontFace: MF, fontSize: 14, color: C.accent, bold: true, charSpacing: 3, margin: 0 });
  s.addText("CaseWeaver", { x: MX, y: 2.0, w: CW, h: 1.5, fontFace: HF, fontSize: 76, bold: true, color: C.ink, margin: 0 });
  s.addText("Agentic Mortgage Underwriting Agents", { x: MX, y: 3.5, w: CW, h: 0.7, fontFace: HF, fontSize: 30, color: C.soft, margin: 0 });
  s.addText("Agents underwrite.  Humans decide.  UiPath governs.", { x: MX, y: 4.25, w: CW, h: 0.6, fontFace: BF, fontSize: 20, italic: true, color: C.ink, margin: 0 });
  chip(s, MX, 5.5, 3.2, 0.55, "Built with Claude Code", C.accent);
  chip(s, MX + 3.4, 5.5, 2.0, 0.55, "5 coded agents", C.panel, C.ink);
  chip(s, MX + 5.6, 5.5, 2.6, 0.55, "durable human-in-the-loop", C.panel, C.ink);
  s.addText("github.com/SebAustin/mortgage-underwriting-agents", { x: MX, y: 6.6, w: CW, h: 0.35, fontFace: MF, fontSize: 13, color: C.soft, margin: 0 });
})();

// ── 2. Problem ────────────────────────────────────────────────────────────────
(() => {
  const s = base(); kicker(s, "The problem");
  title(s, "Underwriting is exception-heavy — and a human must own the decision.", 28);
  const pts = [
    ["Most loans are routine", "the long tail needs document chasing, re-verification, judgement, and fraud checks."],
    ["RPA is too brittle", "rigid scripts snap on the exceptions that actually matter."],
    ["A raw LLM is unacceptable", "no autonomous model should make a regulated credit decision."],
  ];
  let y = 2.5;
  pts.forEach(([h, b]) => {
    s.addShape(pres.shapes.RECTANGLE, { x: MX, y: y + 0.05, w: 0.12, h: 0.95, fill: { color: C.accent }, line: { type: "none" } });
    s.addText(h, { x: MX + 0.35, y, w: 6.6, h: 0.5, fontFace: HF, fontSize: 21, bold: true, color: C.ink, margin: 0 });
    s.addText(b, { x: MX + 0.35, y: y + 0.5, w: 6.6, h: 0.6, fontFace: BF, fontSize: 15.5, color: C.soft, margin: 0 });
    y += 1.35;
  });
  panel(s, 8.1, 2.45, 4.45, 4.1, C.panel);
  s.addText("THE EXCEPTION TAIL", { x: 8.45, y: 2.75, w: 3.8, h: 0.35, fontFace: MF, fontSize: 12, color: C.accent, bold: true, charSpacing: 2, margin: 0 });
  const tags = ["Missing documents", "Low-confidence OCR", "Conflicting data", "Debt-ratio over policy", "Appraisal gaps", "Fraud / AML"];
  let ty = 3.25;
  tags.forEach((t) => {
    s.addText(t, { x: 8.45, y: ty, w: 3.8, h: 0.45, fontFace: BF, fontSize: 16, color: C.ink, bullet: { code: "2022", indent: 14 }, margin: 0 });
    ty += 0.5;
  });
  s.addText("Agentic case management: agents reason, robots act, humans hold authority.", { x: 8.45, y: 6.0, w: 3.85, h: 0.5, fontFace: BF, fontSize: 13.5, italic: true, color: C.amber, margin: 0 });
  footer(s, 2);
})();

// ── 3. The idea ──────────────────────────────────────────────────────────────
(() => {
  const s = base(); kicker(s, "The approach");
  title(s, "Agentic case management on UiPath Maestro Case");
  const cols = [
    [C.green, "Agents", "reason, coordinate, and recommend — five coded LangGraph agents."],
    [C.blue, "Robots", "do the mechanical work — ingest, re-digitise, generate letters."],
    [C.violet, "Humans", "hold authority — decision support, then the final credit call."],
  ];
  const w = 3.75, gap = 0.5; let x = MX;
  cols.forEach(([col, h, b]) => {
    panel(s, x, 2.5, w, 3.2, C.panel);
    s.addShape(pres.shapes.RECTANGLE, { x, y: 2.5, w, h: 0.14, fill: { color: col }, line: { type: "none" } });
    s.addText(h, { x: x + 0.35, y: 2.95, w: w - 0.7, h: 0.6, fontFace: HF, fontSize: 26, bold: true, color: C.ink, margin: 0 });
    s.addText(b, { x: x + 0.35, y: 3.65, w: w - 0.7, h: 1.7, fontFace: BF, fontSize: 16, color: C.soft, margin: 0, lineSpacingMultiple: 1.1 });
    x += w + gap;
  });
  chip(s, MX, 6.2, CW, 0.6, "ORCHESTRATED, GOVERNED, AND AUDITED AS ONE MAESTRO CASE", C.accentSoft, C.accent);
  footer(s, 3);
})();

// ── 4. Architecture ──────────────────────────────────────────────────────────
(() => {
  const s = base(); kicker(s, "Architecture");
  title(s, "Five agents · six stages · two gates · one swappable port");
  const stages = [
    ["Intake", C.line], ["Doc Verify", C.line], ["Income", C.line], ["Adjudication", C.line],
    ["Gate A", C.violet], ["Compliance", C.line], ["Gate B", C.violet], ["Decision", C.blue],
  ];
  const n = stages.length, gap = 0.12, cw = (CW - gap * (n - 1)) / n; let x = MX;
  stages.forEach(([t, col]) => {
    const human = col === C.violet, term = col === C.blue;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 2.45, w: cw, h: 0.7, rectRadius: 0.1,
      fill: { color: human ? "1A1733" : C.panel }, line: { color: human ? C.violet : (term ? C.blue : C.line), width: 1.3 } });
    s.addText(t, { x, y: 2.45, w: cw, h: 0.7, fontFace: MF, fontSize: 12, bold: true, color: C.ink, align: "center", valign: "middle", margin: 0 });
    x += cw + gap;
  });
  s.addText("one PlatformPort interface — the same graph runs locally and on UiPath, selected by RUNTIME_MODE", { x: MX, y: 3.35, w: CW, h: 0.4, fontFace: BF, fontSize: 14, italic: true, color: C.soft, align: "center", margin: 0 });
  // PlatformPort seam
  panel(s, MX, 4.0, 5.5, 2.6, C.panel);
  s.addText("LocalAdapter — no tenant", { x: MX + 0.35, y: 4.25, w: 4.8, h: 0.5, fontFace: HF, fontSize: 19, bold: true, color: C.green, margin: 0 });
  s.addText([
    { text: "deterministic mocks + SQLite Action Inbox", options: { bullet: { code: "2022", indent: 14 }, breakLine: true } },
    { text: "durable checkpointer (suspend / resume)", options: { bullet: { code: "2022", indent: 14 }, breakLine: true } },
    { text: "runs offline, no API key", options: { bullet: { code: "2022", indent: 14 } } },
  ], { x: MX + 0.35, y: 4.9, w: 4.8, h: 1.5, fontFace: BF, fontSize: 14.5, color: C.ink, margin: 0, paraSpaceAfter: 6 });

  chip(s, 6.34, 5.05, 0.65, 0.55, "⇄", C.accent);

  panel(s, 7.05, 4.0, 5.5, 2.6, C.panel);
  s.addText("UiPathAdapter — cloud", { x: 7.4, y: 4.25, w: 4.8, h: 0.5, fontFace: HF, fontSize: 19, bold: true, color: C.blue, margin: 0 });
  s.addText([
    { text: "Action Center tasks & escalations", options: { bullet: { code: "2022", indent: 14 }, breakLine: true } },
    { text: "Orchestrator assets · Document Understanding", options: { bullet: { code: "2022", indent: 14 }, breakLine: true } },
    { text: "UiPath LLM Gateway · Maestro durability", options: { bullet: { code: "2022", indent: 14 } } },
  ], { x: 7.4, y: 4.9, w: 4.8, h: 1.5, fontFace: BF, fontSize: 14.5, color: C.ink, margin: 0, paraSpaceAfter: 6 });
  footer(s, 4);
})();

// ── 5. The agents ────────────────────────────────────────────────────────────
(() => {
  const s = base(); kicker(s, "The agents — coded (Python · LangGraph)");
  title(s, "What each agent does");
  const rows = [
    ["IntakeAgent", "classify the document set, build the required-docs checklist, triage."],
    ["DocVerifyAgent", "extract fields, cross-check identity across documents, gate on confidence."],
    ["UnderwritingAgent", "compute qualifying income (W-2 vs self-employed), reserves, stability."],
    ["AdjudicationAgent", "DTI / LTV, policy matrix, self-critique — with a CrewAI debate for borderline files."],
    ["ExceptionAgent", "AML / fraud screen, assemble conditions, route every exception."],
  ];
  let y = 2.4;
  rows.forEach(([h, b]) => {
    panel(s, MX, y, CW, 0.74, C.panel);
    s.addText(h, { x: MX + 0.3, y, w: 3.4, h: 0.74, fontFace: MF, fontSize: 16, bold: true, color: C.accent, valign: "middle", margin: 0 });
    s.addText(b, { x: MX + 3.8, y, w: CW - 4.1, h: 0.74, fontFace: BF, fontSize: 15.5, color: C.ink, valign: "middle", margin: 0 });
    y += 0.82;
  });
  s.addText("Decisions are deterministic and policy-driven — the LLM only narrates.", { x: MX, y: y + 0.0, w: CW, h: 0.36, fontFace: BF, fontSize: 14, italic: true, color: C.amber, margin: 0 });
  footer(s, 5);
})();

// ── 6. Humans in the loop (real screenshot) ──────────────────────────────────
(() => {
  const s = base(); kicker(s, "Humans in charge · Action Center");
  title(s, "Two gates: decision support, then final authority");
  const items = [
    [C.violet, "Gate A — decision support", "borderline files only; the underwriter sees the agent's metrics, rationale, compensating factors and policy citations."],
    [C.accent, "Gate B — final authority", "every approve / decline is signed by a human."],
    [C.blue, "Durable", "the case suspends and resumes across processes — like Maestro + Action Center."],
  ];
  let y = 2.55;
  items.forEach(([col, h, b]) => {
    s.addShape(pres.shapes.RECTANGLE, { x: MX, y: y + 0.04, w: 0.12, h: 0.85, fill: { color: col }, line: { type: "none" } });
    s.addText(h, { x: MX + 0.32, y, w: 5.4, h: 0.45, fontFace: HF, fontSize: 18, bold: true, color: C.ink, margin: 0 });
    s.addText(b, { x: MX + 0.32, y: y + 0.44, w: 5.4, h: 0.8, fontFace: BF, fontSize: 14.5, color: C.soft, margin: 0, lineSpacingMultiple: 1.05 });
    y += 1.4;
  });
  // real UI screenshot (3:2)
  const iw = 6.2, ih = iw * (1200 / 1800);
  panel(s, 6.5, 2.5, iw + 0.2, ih + 0.2, C.panel2);
  s.addImage({ path: path.join(GAL, "06_loan_officer_desk_ui.png"), x: 6.6, y: 2.6, w: iw, h: ih });
  s.addText("The loan-officer desk (real UI)", { x: 6.6, y: 2.6 + ih + 0.18, w: iw, h: 0.3, fontFace: MF, fontSize: 11, color: C.soft, margin: 0 });
  footer(s, 6);
})();

// ── 7. Exceptions table ──────────────────────────────────────────────────────
(() => {
  const s = base(); kicker(s, "Exceptions are the product");
  title(s, "Seven routes, one auditable policy table");
  const head = (t) => ({ text: t, options: { bold: true, color: C.accent, fill: { color: C.panel2 }, fontFace: MF, fontSize: 13 } });
  const cell = (t, c) => ({ text: t, options: { color: c || C.ink, fontFace: BF, fontSize: 14.5, fill: { color: C.panel } } });
  const rows = [
    [head("Exception"), head("Route")],
    [cell("Missing documents"), cell("email borrower → suspend (info requested)")],
    [cell("Low-confidence OCR"), cell("auto re-digitise once → human verify")],
    [cell("Conflicting data"), cell("re-verify → human resolution")],
    [cell("DTI over policy"), cell("compensating factors → conditional / decline")],
    [cell("Appraisal gap"), cell("recompute LTV on lesser value → human review")],
    [cell("Fraud / AML hit", C.red), cell("hard stop → escalate to compliance", C.red)],
    [cell("Transient failure"), cell("exponential-backoff retry → system escalation")],
  ];
  s.addTable(rows, { x: MX, y: 2.45, w: CW, colW: [4.2, CW - 4.2], rowH: 0.5, border: { pt: 1, color: C.line }, valign: "middle", margin: [4, 8, 4, 8] });
  footer(s, 7);
})();

// ── 8. Live demo (real terminal screenshot) ──────────────────────────────────
(() => {
  const s = base(); kicker(s, "See it run");
  title(s, "A borderline file, end to end — real output");
  const iw = 6.0, ih = iw * (1200 / 1800);
  panel(s, MX, 2.5, iw + 0.2, ih + 0.2, C.panel2);
  s.addImage({ path: path.join(GAL, "04_borderline_conditional_run.png"), x: MX + 0.1, y: 2.6, w: iw, h: ih });
  const tx = MX + iw + 0.7;
  s.addText([
    { text: "44% DTI", options: { bold: true, color: C.amber, breakLine: true } },
    { text: "rescued by reserves & a 760 score", options: { color: C.soft, breakLine: true } },
  ], { x: tx, y: 2.7, w: 3.5, h: 0.9, fontFace: HF, fontSize: 22, margin: 0 });
  s.addText([
    { text: "Gate A → underwriter steers", options: { bullet: { code: "2022", indent: 14 }, breakLine: true } },
    { text: "Gate B → final sign-off", options: { bullet: { code: "2022", indent: 14 }, breakLine: true } },
    { text: "→ conditional approve", options: { bullet: { code: "2022", indent: 14 } } },
  ], { x: tx, y: 3.8, w: 3.7, h: 1.6, fontFace: BF, fontSize: 16, color: C.ink, margin: 0, paraSpaceAfter: 7 });
  chip(s, tx, 5.6, 3.3, 0.55, "▶  watch the 3-min demo", C.accent);
  footer(s, 8);
})();

// ── 9. Platform usage ────────────────────────────────────────────────────────
(() => {
  const s = base(); kicker(s, "UiPath platform usage");
  title(s, "Deep, governed platform use");
  const comps = [
    "Maestro Case", "Coded Agents", "Action Center", "Document Understanding",
    "Orchestrator", "API Workflows", "LLM Gateway", "CrewAI (governed)",
  ];
  const cols = 4, gap = 0.35, w = (CW - gap * (cols - 1)) / cols, h = 1.1;
  comps.forEach((t, i) => {
    const r = Math.floor(i / cols), c = i % cols;
    const x = MX + c * (w + gap), y = 2.6 + r * (h + 0.45);
    panel(s, x, y, w, h, C.panel);
    s.addText(t, { x: x + 0.15, y, w: w - 0.3, h, fontFace: HF, fontSize: 16, bold: true, color: C.ink, align: "center", valign: "middle", margin: 0 });
  });
  chip(s, MX, 6.35, CW, 0.6, "EXTERNAL FRAMEWORK INSIDE A GOVERNED LAYER  ·  BUILT WITH CLAUDE CODE (BONUS)", C.accentSoft, C.accent);
  footer(s, 9);
})();

// ── 10. Built with Claude Code ───────────────────────────────────────────────
(() => {
  const s = base(); kicker(s, "UiPath for coding agents");
  title(s, "The whole solution, built by a coding agent");
  s.addText([
    { text: "Designed the dual-mode PlatformPort architecture", options: { bullet: { code: "2022", indent: 16 }, breakLine: true } },
    { text: "Built all five agents, the supervisor graph, and the policy engine", options: { bullet: { code: "2022", indent: 16 }, breakLine: true } },
    { text: "Probed the real LangGraph & UiPath SDK APIs before committing", options: { bullet: { code: "2022", indent: 16 }, breakLine: true } },
    { text: "Validated uipath init / pack → a valid .nupkg, with no tenant", options: { bullet: { code: "2022", indent: 16 }, breakLine: true } },
    { text: "Wrote the tests, the security audit, and the documentation", options: { bullet: { code: "2022", indent: 16 } } },
  ], { x: MX, y: 2.55, w: 7.4, h: 3.4, fontFace: BF, fontSize: 18, color: C.ink, margin: 0, paraSpaceAfter: 12 });
  panel(s, 8.3, 2.55, 4.25, 3.5, C.panel);
  s.addText("EVIDENCE", { x: 8.6, y: 2.8, w: 3.6, h: 0.35, fontFace: MF, fontSize: 12, color: C.accent, bold: true, charSpacing: 2, margin: 0 });
  s.addText([
    { text: "git history — every commit co-authored", options: { breakLine: true } },
    { text: "evidence/CODING_AGENT_LOG.md", options: { breakLine: true, color: C.accent } },
    { text: "uipath init / pack in the loop", options: { breakLine: true } },
    { text: "AGENTS.md from the UiPath CLI", options: {} },
  ], { x: 8.6, y: 3.3, w: 3.65, h: 2.6, fontFace: BF, fontSize: 15, color: C.ink, margin: 0, paraSpaceAfter: 12, lineSpacingMultiple: 1.05 });
  footer(s, 10);
})();

// ── 11. Production readiness (stats) ─────────────────────────────────────────
(() => {
  const s = base(); kicker(s, "Production-ready");
  title(s, "Engineered, not hacked");
  const stats = [
    ["72", "tests", C.green], ["93%", "coverage", C.blue], ["0", "open Critical / High", C.amber], ["✓", "valid .nupkg, no tenant", C.accent],
  ];
  const cols = 4, gap = 0.4, w = (CW - gap * (cols - 1)) / cols;
  stats.forEach(([n, l, col], i) => {
    const x = MX + i * (w + gap);
    panel(s, x, 2.7, w, 2.4, C.panel);
    s.addText(n, { x, y: 3.0, w, h: 1.3, fontFace: HF, fontSize: 64, bold: true, color: col, align: "center", margin: 0 });
    s.addText(l, { x: x + 0.15, y: 4.35, w: w - 0.3, h: 0.6, fontFace: BF, fontSize: 14.5, color: C.soft, align: "center", margin: 0 });
  });
  s.addText("ruff + mypy clean · STRIDE security audit · deterministic & reproducible (LLM stubbed)", { x: MX, y: 5.6, w: CW, h: 0.5, fontFace: BF, fontSize: 16, italic: true, color: C.ink, align: "center", margin: 0 });
  footer(s, 11);
})();

// ── 12. Impact & next ────────────────────────────────────────────────────────
(() => {
  const s = base(); kicker(s, "Impact & what's next");
  title(s, "From demo to deployment");
  panel(s, MX, 2.55, 5.7, 3.9, C.panel);
  s.addText("IMPACT", { x: MX + 0.35, y: 2.8, w: 5, h: 0.4, fontFace: MF, fontSize: 13, color: C.green, bold: true, charSpacing: 2, margin: 0 });
  s.addText([
    { text: "Faster cycle time on routine files", options: { bullet: { code: "2022", indent: 16 }, breakLine: true } },
    { text: "Fewer manual touches; agents handle the tail", options: { bullet: { code: "2022", indent: 16 }, breakLine: true } },
    { text: "Full auditability — every step on the timeline", options: { bullet: { code: "2022", indent: 16 }, breakLine: true } },
    { text: "Humans accountable for every credit decision", options: { bullet: { code: "2022", indent: 16 } } },
  ], { x: MX + 0.35, y: 3.35, w: 5.1, h: 2.9, fontFace: BF, fontSize: 15.5, color: C.ink, margin: 0, paraSpaceAfter: 11 });
  panel(s, 6.95, 2.55, 5.6, 3.9, C.panel);
  s.addText("WHAT'S NEXT", { x: 7.3, y: 2.8, w: 5, h: 0.4, fontFace: MF, fontSize: 13, color: C.accent, bold: true, charSpacing: 2, margin: 0 });
  s.addText([
    { text: "Go live on UiPath Labs (publish + Maestro canvas)", options: { bullet: { code: "2022", indent: 16 }, breakLine: true } },
    { text: "Real connectors: credit bureau, AML, Document Understanding", options: { bullet: { code: "2022", indent: 16 }, breakLine: true } },
    { text: "Escalation memory — learn from underwriter decisions", options: { bullet: { code: "2022", indent: 16 }, breakLine: true } },
    { text: "More case templates: disputes, KYC, claims", options: { bullet: { code: "2022", indent: 16 } } },
  ], { x: 7.3, y: 3.35, w: 5.0, h: 2.9, fontFace: BF, fontSize: 15.5, color: C.ink, margin: 0, paraSpaceAfter: 11 });
  footer(s, 12);
})();

// ── 13. Close ────────────────────────────────────────────────────────────────
(() => {
  const s = base();
  s.addText("Thank you", { x: MX, y: 2.1, w: CW, h: 1.3, fontFace: HF, fontSize: 64, bold: true, color: C.ink, margin: 0 });
  s.addText("Agents underwrite.  Humans decide.  UiPath governs.", { x: MX, y: 3.5, w: CW, h: 0.6, fontFace: BF, fontSize: 22, italic: true, color: C.soft, margin: 0 });
  s.addText([
    { text: "Repo:  ", options: { color: C.soft } },
    { text: "github.com/SebAustin/mortgage-underwriting-agents", options: { color: C.accent } },
  ], { x: MX, y: 4.6, w: CW, h: 0.4, fontFace: MF, fontSize: 16, margin: 0 });
  s.addText("Demo video + this deck linked in the Devpost submission.", { x: MX, y: 5.1, w: CW, h: 0.4, fontFace: BF, fontSize: 15, color: C.soft, margin: 0 });
  chip(s, MX, 6.0, 3.2, 0.55, "Built with Claude Code", C.accent);
})();

pres.writeFile({ fileName: path.join(ROOT, "devpost", "CaseWeaver-Deck.pptx") }).then((f) => console.log("wrote", f));
