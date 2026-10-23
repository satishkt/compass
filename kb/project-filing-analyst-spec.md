# Project document: filing-analyst-spec

Source: research_val_personal/docs/filing-analyst-spec.md
Kind: design document; may describe planned rather than shipped features.

# Filing Analyst — a structured "how an analyst reads a filing" layer for the Reading Room

**Status:** Requirements LOCKED by the user (2026-09-29). Extends the Reading Room (C14, shipped).
Build in phases; **stop for review after each phase.**

## Problem
The Reading Room renders a filing cleanly, dims boilerplate, diffs vs the prior filing, and — on
demand — interprets sections, briefs the doc, answers questions (Ask), cross-reads the call. What's
missing is **reading with intent**: an analyst opens a 10-K with a fixed checklist and reads to
answer it. The Filing Analyst encodes that checklist so a filing arrives **pre-answered, grounded,
and cited**, with drill-down to the source.

## Core design principles (non-negotiable)
1. **Everything grounded and cited.** Every claim cites a section + a **verbatim** quote. A
   post-generation **verification** step checks each quote appears in the source (normalize
   whitespace + quote glyphs); unverified claims are dropped or flagged. Never show an uncited claim.
2. **Numbers come from data, not the LLM.** Figures (revenue, margins, CFO, debt, shares) come from
   the parsed standardized statements / ratios; ratios computed in code. The LLM *explains* numbers,
   never invents/computes them. A number the LLM emits is checked against injected facts within
   tolerance; mismatches are flagged.
3. **"Not disclosed" is a valid answer** — stated explicitly, never guessed. Absence is a signal.
4. **Separate fact from interpretation** — "what the filing says" vs "analyst read", visually distinct.
5. **No investment advice** — no buy/sell/hold, no price targets.
6. **The question library is data, not code** — a versioned YAML file, editable without touching code.
7. **Cheap and cacheable** — cache by `(filing key/accession, library version, model)`; route each
   question to only the sections it needs.

## Reuse (already in the repo — do not rebuild)
| Existing | Role |
|---|---|
| `chat.retrieve(ticker, q, form_type, period)` → `{text, section, …}` | Per-question retrieval when a routed section is too large; `section` links a citation to the nav. |
| governed `ai_query` JSON pattern (`interpret_section`) via `governance.invoke` | The per-question extract + brief synth call. (No tool-use on the warehouse batch path → schema enforced by prompt + parse + **verification**.) |
| `filing_reader.load_structured` (sections w/ block `idx` anchors), `parse_key` | Routing targets + citation jump anchors. |
| `filings/reading/<key>.json` pattern (`service.reading_state`) | Cache location + volume push. |
| `chat.ask_filing` | Where Phase-2 follow-up chat lands. |
| `filing_reader.diff_structured` + "Changed" density | Phase-3 prior-filing comparison. |
| 📋 Brief (`chat.interpret_brief`) | **Subsumed** by the Analyst's executive brief. |

## Question library (v1) — `shared/docs/filing_questions.yaml`
Versioned (`version:`); each entry: `id`, `title`, `why_it_matters`, `applies_to` (10-K|10-Q|both),
`target_sections` (Item numbers / note types to route), `instructions`, `red_flags`,
`needs_financial_data` (which computed facts to inject). Seed = the 14 questions below (A–F).

- **A. Business** — 1) what it sells / how it makes money (Item 1, segment note; flags: customer >10%,
  single-source, govt exposure); 2) competitive position (Item 1/1A; specific vs generic claims).
- **B. Performance** — 3) what drove revenue & profit (Item 7 + income stmt; volume/price/mix/M&A/FX;
  flags: vague, growth from M&A, segment divergence); 4) margin trend & why (computed + explanation +
  one-offs); 5) known trends/uncertainties/outlook (Reg S-K 303; flag hedged/evasive language).
- **C. Quality of earnings** — 6) do earnings become cash (CFO/NI, FCF, WC swings, SBC%, capitalized
  costs; flags: receivables>revenue growth, inventory build, CFO<NI, factoring); 7) accounting
  judgments & changes (critical estimates, policies, rev-rec; flags: policy/estimate changes, useful-
  life changes, reserve releases, GAAP vs non-GAAP gap); **7b) non-GAAP / adjusted-metric
  reconciliation (added v2)** — find the GAAP→non-GAAP reconciliation (MD&A or a footnote/appendix),
  itemize each adjustment (SBC, intangible amortization, restructuring, impairments, legal), quantify
  it, and explain/verify the bridge; flags: recurring costs added back as "one-time", a widening
  GAAP-vs-adjusted gap, adjustments with no itemized reconciliation. The parsed adjusted figures
  (adjusted EBIT/EBITDA/net income/EPS from `adjusted_metrics.json`) and the **implied size of the
  add-backs** (adjusted − reported) are injected as ground truth; routing matches reconciliation
  blocks by title even when they are not a numbered Note. 8) what the auditor says (Item 8/9A: CAMs,
  material weakness, going concern, auditor change, restatement — **any hit tops the brief**).
- **D. Balance sheet & capital** — 9) balance-sheet & liquidity strength (debt ladder, variable-rate,
  covenants/headroom, off-B/S, pension; flags: near-term maturities w/o refi plan, tight covenants,
  going concern); 10) capital allocation (capex vs D&A, buybacks/dividends/M&A/paydown, share-count
  trend, buybacks just offsetting SBC).
- **E. Risks & governance** — 11) company-specific & new risks (Item 1A; skip boilerplate; rank; mark
  new/reworded — Phase 3); 12) legal/regulatory/contingent liabilities (Item 3 + contingencies note;
  probability language, accrued vs disclosed); 13) insider/governance oddities (related-party, comp
  structure — note Part III incorporated-by-reference to proxy, dual-class, turnover).
- **F. 10-Q-specific** — 14) what changed since the last 10-K (Part II 1A updates, new MD&A, subsequent
  events, guidance changes, Q vs YTD vs PY; account for seasonality). *(Phase 2.)*

## Per-question output schema
```json
{ "question_id": "cash_conversion",
  "short_answer": "1-2 sentences, plain English",
  "detailed_answer": "markdown, a few paragraphs max",
  "facts": [{"claim": "...", "citations": [{"section_id": "...", "quote": "verbatim text"}]}],
  "analyst_read": "interpretation, clearly labeled",
  "signal": "positive | neutral | watch | concern",
  "signal_reason": "one line",
  "red_flags": [{"flag": "...", "severity": "low|medium|high", "citations": [...]}],
  "not_disclosed": ["items the question expects that the filing doesn't cover"],
  "confidence": "high | medium | low",
  "follow_up_questions": ["...", "..."] }
```
Plus engine-added: `verification: {quotes_checked, quotes_verified, numbers_checked, numbers_ok,
score}` and per-citation `verified: bool`. Unverified quotes are dropped (Phase 1) or flagged.

## Pipeline (`shared/docs/filing_analyst.py`)
1. **Route** — pick sections via `target_sections` + signal filter from the structured doc; if a
   routed section is too large, `retrieve` the most relevant chunks instead of truncating. Sections
   are tagged with `section_id` so citations resolve to nav anchors.
2. **Extract** (per question) — governed `ai_query` returns strict JSON (schema above). System prompt:
   a skeptical sell-side analyst who explains plainly, obeys grounding / no-advice / "not disclosed"
   rules. Context: company, form, period, routed sections (tagged `section_id`), injected financial
   facts table.
3. **Verify** — every quote must appear verbatim in its cited section (whitespace/quote-normalized);
   every number the LLM states must match injected facts within tolerance. Drop/flag failures; record
   a verification score.
4. **Synthesize** — one call over verified answers → executive brief: 3-sentence business summary, top
   5 takeaways, top red flags ranked by severity (each linked to its question). Auditor/going-concern
   hits float to the top.
5. **Persist & serve** — cache to `filings/reading/<key>-analyst.json` keyed by (key, lib version,
   model); write **incrementally** so the UI can poll and show questions as they finish.

## Financial facts (`financial_facts(folder)`)
Compact computed block from `*_standardized.json` + `ratios.json` (+ `adjusted_metrics.json`):
revenue & growth, gross/op/net margin (trend), CFO, NI, CFO/NI, FCF, SBC & SBC/rev, total debt, cash,
net debt, interest, share count trend, key ratios. Rendered as a small labelled table injected per
`needs_financial_data`. This is the ground truth the LLM's numbers are checked against.

## Drill-down UX (`ReadingRoom.jsx`)
- **Brief view (landing):** executive brief on top; then question cards — title, `why_it_matters`,
  short answer, **signal badge** (positive/neutral/watch/concern), red-flag count.
- **Question detail:** detailed answer; a **facts list** where each citation is clickable → jumps to
  the passage in the **existing section navigator** with the quote highlighted; **analyst read** as a
  separate labelled block; red flags (by severity); **not-disclosed** items; follow-up chips.
- **Auto-run + progress:** on open, GET cached; if absent, POST to run and **poll** — cards appear as
  they finish ("Analyzing… 6/13"). **Re-analyze** per filing + **regenerate** per question. Dev mode
  shows tokens/cost + logs prompt/response.
- Subsumes the 📋 Brief button.

## Phases (stop for review after each)
1. **Phase 1 (this ship) — 10-K only.** Library YAML + pipeline (route → extract → verify →
   synthesize) + financial-facts injection + caching + incremental persist/poll + Brief view +
   question detail with **working citations** (jump + highlight). Unit tests for routing / quote
   verification / number checks; eval scaffold.
2. **Phase 2** — scoped per-question drill-down chat, follow-up chips, "explain this" plain-English
   toggle, and **10-Q support** (Q14 + 10-Q section mapping).
3. **Phase 3** — prior-filing comparison (detect prior 10-K/10-Q same CIK; **semantic** risk-factor
   diff; MD&A & policy diff) → "what changed" brief section + badges on affected questions. Reuses
   `filing_reader.diff_structured`.
4. **Phase 4** — industry question packs by SIC/tag (banks: NIM/uninsured deposits/ACL/CRE/AOCI;
   SaaS: RPO/NRR/deferred rev/SBC; REITs: FFO/AFFO/occupancy; insurers: combined ratio/reserves;
   energy: reserves/hedging). Library supports optional packs selected by SIC.

## Quality & evaluation
- **Golden set** of 4-6 real filings across industries (mega-cap tech, a bank, a retailer, a small-cap
  with a known material weakness / going-concern).
- **Eval script** (`scripts/eval_filing_analyst.py`): runs the pipeline on the golden set, reports
  citation-verification rate, schema validity, "not disclosed" rate, latency, cost/filing; plus
  hand-written assertions (e.g. "bank X brief mentions CRE exposure"; "company Y auditor question
  flags the material weakness").
- **Unit tests** (local, no warehouse): routing, quote verification (whitespace/quote normalization,
  near-misses), number checks, library load/validation, financial-facts derivation.
- **Dev logging** of prompts/responses per question for tuning.

## Implementation constraints (this repo)
- Warehouse `ai_query` batch path has **no tool-use/structured-output** → schema enforced by strict
  prompt + robust JSON parse + the verification step (the real guardrail).
- Numbers are injected from the **standardized statements** (the repo's parsed financials); we do not
  parse raw XBRL facts separately.
- Progressive UI via **incremental cache writes + client poll** (no SSE): POST starts the run in a
  background thread that writes each finished question to the cache; GET returns partial + `status`.
- Extract `max_tokens` = 4000 (the rich JSON + verbatim quotes truncates below that → parse failure →
  a blank card). `_parse_json` tolerates ```json fences, trailing prose, and brace-balances from the
  first `{`; a genuine parse miss surfaces the raw model text (tagged, counted as a soft error) rather
  than showing an empty answer.

## Pipeline integration
`shared/docs/filing_analyst.analyze_recent(ticker)` pre-runs the analysis for the most-recent annual +
interim structured filings; it's a first-class stage `filing_analyst` (`run_stage.py`, `pipeline.py`,
`jobs.py` label map) and a **task in the Databricks research job** (`databricks/job_pipeline.json`,
depends on `download_filings` + `chunk_index`). This pre-warms the cache so the app serves instantly.
NOTE: adding it also restored `download_filings` to the job graph (it was in `pipeline.py` but missing
from the job — pre-existing drift; `kpi_*` are still absent). **The job JSON must be re-applied to the
live job** (`databricks jobs reset --job-id <RESEARCH_JOB_ID> --json @databricks/job_pipeline.json`)
for the new tasks to run; the app deploy alone does not update the job. The on-open auto-run+cache
path works regardless, so the pipeline pre-run is an optimization, not a dependency.