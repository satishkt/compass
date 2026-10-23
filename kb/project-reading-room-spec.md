# Project document: reading-room-spec

Source: research_val_personal/docs/reading-room-spec.md
Kind: design document; may describe planned rather than shipped features.

# Reading Room — a guided active-reading aid for 10-K / 10-Q filings

**Status:** Proposed (backlog item **C14**). Big, multi-phase feature. Author: session 2026-09-22.

## Problem
10-Ks and 10-Qs carry enormous signal but are written to bore or conceal — boilerplate padding,
hedged prose, negatives buried mid-paragraph, and the real disclosures tucked into the **notes to
the financial statements**. Reading them cold, end to end, is exhausting and passive. We want an
*active-reading* workspace that helps you go through a whole filing deliberately, organizes the text
so signal stands out, shows what changed vs the prior filing, surfaces the buried/footnote material,
and — only when asked — interprets (hedge radar, claim/novelty, narrative-vs-numbers).

This is deliberately **separate from the dossier**. The dossier answers "what do I think"; the
Reading Room is where you *form* that view from the primary text. A dedicated full-screen route.

## Locked design decisions (from the user)
1. **Unit of a session = a single filing**, read end to end. The full-doc walk is the spine; the
   YoY/QoQ diff rides alongside each section.
2. **Organize by default, interpret on demand.** The base experience is structural (navigation,
   diff, boilerplate dimming, footnote surfacing) — instant and free. An **"Interpret with AI"**
   button (per section and whole-doc) invokes the expensive LLM layers. Keeps it fast, cheap, and
   non-patronizing: you ask for a read when you want one.
3. **All sections** — MD&A, Risk Factors, Business, and the **notes to the financial statements**.
4. **Footnotes / buried content are first-class** (the user's key addition) — the notes lane gets
   dedicated treatment (below).

## The Reading Room — UX
Route: `/read/:ticker/:filing` (full-screen, its own window/tab). Layout:
- **Left rail:** the filing's structure (Part/Item → section → note), with a progress indicator and
  a per-section **reviewed tick** + **"My read"** note (reuse the Epic A3 per-section pattern).
- **Center:** the document, rendered by section and paragraph. A **reading-density toggle**:
  *Everything → Signal only → Just what changed.*
- **Right rail (contextual):** for the current section — the YoY/QoQ diff summary, footnote/cross-ref
  jumps, linked metric charts, and (once invoked) the AI interpretation.
- Keyboard-driven progression (next/prev section & claim); a session ends when you've walked the doc.

## Feature layers

### A. Structural — free, instant, on-disk (Phase 1)
- **Full-doc section walk** across all sections incl. notes, with a navigation rail + progress.
- **Boilerplate spotlight / dim** — heuristic scoring elevates sentences with numbers, causal claims
  ("driven by…"), new language, and tone shifts; dims legalese and zero-information filler.
- **YoY / QoQ redline diff** — added / removed / **reworded** vs the prior like-for-like filing. The
  single highest-value layer: for a 10-Q, *what changed* is ~80% of the signal.
- **Footnote / "buried but material" lane** (see below).
- **Per-section reviewed tick + "My read"** capture.

### B. The footnotes / "buried but material" lane
Notes to the financial statements are the richest hiding spot, so they get elevated, not skimmed:
- **Burial sites surfaced:** revenue recognition, **segment definition changes** (ties into C13
  KPI-evolution), contingencies & litigation, related-party transactions, income-tax reconciliation
  & valuation allowances, goodwill/impairment, debt covenants, leases, stock-based comp,
  **subsequent events**, and any **change in accounting policy or estimate**.
- **Cross-reference resolver:** "see Note 12" becomes a jump link; tiny table footnote markers
  (¹, *) get pulled inline so they aren't lost.
- **New/changed-note radar:** a note that's *new this year* (a fresh contingency, a changed rev-rec
  policy, a new valuation allowance) is a red flag — surfaced like C13's dropped KPIs.

### C. Interpretive — AI-on-demand button (Phase 2, needs warehouse)
- **Hedge & concealment radar** — flag vague/hedging language ("challenging environment,"
  "headwinds"), passive voice hiding the actor, euphemism, buried negatives, %-vs-absolute framing,
  "kitchen-sink" risk-factor batches.
- **Claim extraction + novelty** — material claims with source quote + novelty tag
  (new/worsening/improving/unchanged), each with a "record my read / push to thesis" action.
- **Narrative ↔ numbers reconciliation** — tie an MD&A claim to the actual metric/segment series
  and flag divergence ("says demand strong; growth decelerated 18%→9%").
- **Footnote materiality scoring** — rank which notes matter this filing.
- **2-minute pre-read brief** — synthesized "what changed / what's new / what's missing" so you read
  with a hypothesis; plus per-section Socratic prompts.

### D. Later (Phase 3)
- **Transcript cross-read** — MD&A beside the same-period earnings-call transcript (both on disk):
  do they tell analysts the same story they wrote?
- **Press-release vs filing gap** — what the 8-K/PR omitted that the 10-Q footnote admits.
- **Push-to-thesis** — a highlighted claim → Investment Case / watch item (closes the decision loop).

## Data & architecture

### Data-availability findings (verified 2026-09-22)
- `companies/<T>/filings/sections/` has clean **MD&A / Risk Factors / Business** per year, but
  **no notes/footnotes** section.
- `companies/<T>/filings/raw/<FILING>.txt` has the **full filing text** (notes content is present —
  ITEM 8, NOTE 1, contingencies, rev-rec, segments all found) **BUT it's a flattened blob**: zero
  newlines, embedded XBRL cruft, no paragraph/heading structure. **Not directly renderable.**
- Some filings have the **`.htm` original** (e.g. `isrg_10K_FY2025.htm`) with real structure, but
  it's not universally on disk.
- The doc pipeline's **warehouse parsed docs** (`parse.py` → `ai_parse_document`, DOCUMENTS table,
  page-structured text) are the cleanest structured source, but require warehouse access.

**⇒ Foundational task (Phase 0):** produce a **clean, structured full-filing source** — sections +
paragraphs + **notes** — that the Reading Room renders from. Candidate approaches, to decide:
(a) re-parse the `.htm` original into structured sections/paragraphs (fetch HTML where missing);
(b) extend `shared/docs/sections.py` to segment the raw blob and add a **notes** extractor;
(c) serve from the warehouse parsed-doc/page tables. Likely (a) where HTML exists, else (c).

### Reuse (already in the repo)
- `shared/docs/insights.py` — claim extraction + novelty (new/worsening/improving/unchanged) and
  `compare_to_prior` (like-for-like novelty) → powers the AI claim layer **and** the diff scoring.
- `shared/docs/chunk.py` embeddings; `filing_claims` / `filing_narratives` tables.
- `service.kpi_evolution` (C13) — dropped/redefined KPIs feed the notes new/changed radar.
- `filings/transcripts/*.txt` — Phase 3 cross-read.
- Epic A3 per-section **"My read" + reviewed** pattern; `MetricChart` for linked numbers.

### New to build
- Route `/read/:ticker/:filing` + `ReadingRoom` page and components (rail, doc renderer, diff view,
  footnote lane, density toggle, AI panel).
- Backend: a service that serves the **structured filing** (Phase 0 output) + the **diff** vs prior;
  a **notes extractor**; an **annotations store** (char-offset-anchored, like claims); Phase-2
  **AI-invoke endpoints** (hedge/claims/narrative-vs-numbers/materiality/brief).
- A `filings_index.json`-driven filing picker (which filing to open).

## Build progress
- **Phase 0 — DONE (2026-09-22).** `shared/docs/filing_reader.py`: `structure_html()` parses SEC
  inline-XBRL HTML (bs4/lxml) into sections (Part→Item→Note) of clean paragraph/heading/table blocks,
  filtering running-header/page-number noise; `list_filings()` / `build_structured()` /
  `load_structured()` locate the HTML (cached `html/<key>.htm` → on-disk `*.htm` → **fetch SEC
  sourceUrl** with a UA) and cache the structured doc to `filings/structured/<key>.json` (gitignored
  runtime cache, built on demand). Verified on ISRG 10-K (39 sections, **14 notes split out** incl.
  Revenue / Contingencies / Income Taxes / Segments) and a fetched 10-Q.
- **Phase 1 backend — DONE.** `service.reading_filings()` / `reading_doc()`; routes
  `GET /api/companies/{t}/filings` and `/api/companies/{t}/filing/{key}`.
- **Phase 1 frontend — v1 DONE (2026-09-22).** `pages/ReadingRoom.jsx` + routes `/read/:ticker`
  (filing picker) and `/read/:ticker/:key`. Section-nav rail (Items with notes broken out + scroll-spy
  + burial-site ● flags), clean document rendering (paragraphs / headings / tables), a **signal-
  spotlight** density toggle (Everything | Signal — heuristic: numbers + causal/comparison markers),
  per-section **reviewed ticks + progress** (localStorage for now), and a "📖 Read filings →" entry on
  the dossier header. **Still to come this phase:** the **YoY/QoQ redline diff** (deferred — needs
  prior-filing alignment), and folder-persisted reviewed/My-read notes (currently per-browser).
- **HTML sourcing (hardened 2026-09-22).** Filings without an on-disk `.htm` are fetched from the SEC
  `sourceUrl`. To not depend on read-time egress: `download_filings(ticker)` fetches + pre-builds the
  recent 10-K/10-Q and is wired as a **pipeline stage** (`download_filings`, after `sections`, in both
  `run_stage.py` and `pipeline.py`) — the research job (which has egress) populates
  `filings/html/` + `filings/structured/` so the app just reads from disk. Also on-demand:
  `POST /api/companies/{t}/filings/download` + a "⬇ Download / refresh filings" button and a
  "Download & retry" on a failed open. Fetch failures degrade gracefully (no 500s); the picker
  distinguishes "not indexed / not researched" from "not downloaded." `lxml` added to requirements
  with an `html.parser` fallback. ISRG 10-K FY2025 has an on-disk `.htm` (renders with no fetch).
  Foreign private issuers (**20-F/6-K**) and Canadian (**40-F**) filings are supported (`filing_key`);
  cover-page checkbox lines filtered. (20-F financial-statement notes often live in a separate exhibit
  → notes lane may be empty on a 20-F — v2: fetch the financials exhibit.)
- **Signal navigation (2026-09-22).** In Signal density, a `‹ n/N signal ›` control (and `j`/`k`
  keys) steps through the signal paragraphs, scrolling each to center with a Lava highlight — read the
  high-signal spine without scrolling.
- **Ask this filing (2026-09-22) — the AI-on-demand entry.** A "💬 Ask / explain" drawer answers
  questions scoped to the open filing from its indexed chunks (reuses the pipeline's `doc_chunks`
  vector search): `chat.retrieve(form_type, period)` + `chat.ask_filing()` → route
  `POST /api/companies/{t}/filing/{key}/ask`; the key maps to (form_type, period) via
  `filing_reader.parse_key`. Answers cite the passages used; falls back to the whole-ticker corpus
  (flagged) when the specific filing isn't chunked. **Needs the warehouse** (like the existing Ask).

- **YoY/QoQ redline diff (2026-09-22) — the "Changed" density.** `filing_reader.diff_structured`
  aligns this filing's sections to a prior like-for-like filing (by kind + item/note number) and
  paragraph-diffs each (difflib, exact-match alignment) → added / removed / **reworded** per section.
  Reworded pairs are split **substantive vs minor** (number/date-only roll-forwards are demoted and
  hidden by default). `GET /api/companies/{t}/filing/{key}/diff?prior=`; a prior-filing picker lets
  you choose QoQ vs YoY. Frontend `DiffView` (third density, "Changed"): green added / struck removed
  / amber reworded (old text under a "was" disclosure). Shines on 10-Q QoQ (e.g. ISRG FY2026 Q2 vs Q1:
  4 added / 7 removed / 57 reworded incl. the Contingencies note). **Still deferred:** fetch the 20-F
  financials exhibit so the notes lane populates; the AI-interpret layers (hedge radar, etc.).

- **AI interpret layer (2026-09-23) — Phase 2, the "interpret on demand" marquee.** A per-section
  **✨ Interpret** button runs `chat.interpret_section` (same governed `ai_query` path as Ask) →
  JSON: plain-language **summary**, a **hedge/concealment radar** ({quote, issue ∈ vague|passive|
  buried-negative|euphemism|unquantified, note}), and **watch** questions. Route
  `POST /api/companies/{t}/filing/{key}/interpret` (loads the section text from the structured doc).
  Frontend `SectionInterpret` renders an inline panel; JSON-parse degrades to raw text. **Warehouse-
  backed** (like Ask).
- **Narrative↔numbers + whole-doc pre-read brief (2026-09-23).** `service.reading_metrics_context`
  builds a compact reported-figures block (fiscal.ai, ~3y: margins, ROIC, revenue growth, P/E) passed
  to both Interpret and Brief so the model flags where the narrative diverges from the numbers
  (`numbers: [{claim, reported, note}]`). **📋 Brief** button → `chat.interpret_brief` via
  `POST /filing/{key}/brief`: a 2-minute pre-read — diff-driven ("what changed vs the prior filing")
  when a prior exists, else synthesized from MD&A + Risk Factors — returning headline / watch /
  numbers. Frontend `BriefPanel`. **This completes the interpretive layer** (Phase 2).
- **Phase 3 tail (2026-09-23) — mostly closed.**
  - **Folder-persisted "My read"**: reviewed ticks + a per-section "My read" note now persist to
    `companies/<T>/filings/reading/<key>.json` (gitignored runtime state; the volume is the store) via
    `service.reading_state`/`save_reading_state` + `GET`/`PUT /filing/{key}/reading`. Replaces the
    per-browser localStorage; `SectionNote` component + durable reviewed.
  - **Transcript cross-read**: **🎙 vs call** compares the filing's MD&A narrative to the same-period
    earnings-call transcript (`filing_reader.transcript_for` maps a key → `q{N}-{FY}.txt`, annual→Q4;
    `chat.crossread` → divergences / call-only / filing-only / tone). `POST /filing/{key}/crossread`;
    graceful when no transcript on disk. Warehouse-backed.
  - **IFRS-note polish**: monotonic note numbering drops IFRS policy/disclosure duplicates
    (DLO 20-F: clean 1..32; ISRG 10-K: 1..14 unchanged).
  - **Deprioritized:** press-release-vs-filing gap — low marginal signal (Ask already spans the PR/8-K
    corpus and cross-read covers the call), fragile 8-K-exhibit parsing. Left as a future option.

## Phasing
- **Phase 0 — structured source (incl. notes).** The gating data-prep task. Without a clean,
  section/paragraph/notes-structured document there's nothing good to render.
- **Phase 1 — structural Reading Room.** Shell + section walk (all sections incl. notes) +
  reviewed/My-read + density toggle + YoY/QoQ redline diff + footnote elevation & cross-ref jumps.
  On-disk where possible; the "Interpret with AI" button is present but its handlers are stubbed.
- **Phase 2 — interpretive layers (warehouse).** Hedge radar, claim/novelty, narrative↔numbers,
  footnote materiality, pre-read brief.
- **Phase 3 — cross-doc + loop.** Transcript cross-read, PR-vs-filing gap, push-to-thesis.

## Open questions
1. **Canonical clean source** — HTML re-parse vs warehouse parsed docs vs raw-blob segmentation?
   (Decides Phase 0.)
2. **Diff granularity** — paragraph-level redline, or claim-level ("this assertion is new/changed")?
   Claim-level is cleaner but leans on the AI layer; paragraph redline is free and on-disk.
3. **Interpret scope** — per-section button only, or also a whole-doc "interpret everything" (cost)?
4. **Persistence** — are "My read" notes + annotations + reviewed state per-filing local JSON
   (`companies/<T>/reading/…`) or a table? (Local matches the existing reading/ concept.)
5. **How opinionated** — hedge-radar verdicts vs. just organizing? (User leaned "organize, interpret
   on demand" — so verdicts live behind the AI button, off by default.)

## Effort
**XL** — multi-phase. Phase 0 + Phase 1 are the meaningful first ship (a genuinely useful structural
reader) and are mostly on-disk once the clean source exists. Phases 2–3 layer on the AI/warehouse.