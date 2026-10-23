# Project document: dossier-ux-backlog

Source: research_val_personal/docs/dossier-ux-backlog.md
Kind: design document; may describe planned rather than shipped features.

# Dossier UX & Analysis Backlog

Status: **DRAFT** (2026-09-15). Companion to `research-journey-design.md` and `system-reference.md`.

Origin: review of the research workflow, dossier, and deep-dives. Core complaint being solved:
*pages are information-dense and reading everything on one page makes me rush — I want room to
think and reason at each subsection, without losing any of the components.*

Guiding diagnosis: the dossier serves two jobs with one layout — **reference** (re-check a name
you know: collapsed, scannable, jump anywhere — today's design is great at this) and **reasoning**
(form a fresh judgment: one thing at a time, paced, with somewhere to write the conclusion). The
backlog keeps every existing component and adds a *reasoning* mode over the same parts. Nothing here
removes a section.

**Work order:** Epic A (A1 → A2 → A3 → A4) is the direct fix for the density complaint — do it
first. Epic B is workflow. Epic C is net-new analysis and can be picked up à la carte at any point.

Effort key: **S** ≈ half-day · **M** ≈ 1–2 days · **L** ≈ 3–5 days.

## Current implementation priority — 2026-10-09

The next implementation work is **valuation correctness → offline agentic valuation → intelligent
thesis/KPI monitoring**, before adding more valuation panels. The original A/B/C work order above
and the sequencing summary below describe the earlier UX program; they do not override this priority.

The detailed, unchecked implementation backlog is
[`agentic-valuation-monitoring-backlog.md`](agentic-valuation-monitoring-backlog.md):

- **Epic V (V01–V15):** currency/security/ownership reconciliation, canonical calculation paths,
  publication gates and regression tests; versioned artifacts and offline agent jobs; business-model
  architecture, evidence-grounded underwriting, independent review, OMAB/OWL pilots; free-form
  Valuation Studio, conversational branches, consistent publication, real comps, and calibration.
- **Epic M (M01–M08):** assumption monitoring contracts and driver dependencies; source collection,
  persistent investigations, causal/materiality assessment, proposed valuation impacts, a check-in
  briefing/review inbox, human acceptance, pilot notifications, and operational/evaluation coverage.
- **First slice:** V01–V04 containment and correctness, with failing regression fixtures before
  changing math. All new V/M items are **backlog, not implemented**.

These epics extend **B1/B2** (attention and decision→monitor→review), **C5/C6** (guidance and review
calibration), **C9/C10/C12** (sourced valuation inputs/comps), **C13** (management KPIs), and the
Valuation Deep Dive. Reuse those foundations; do not create disconnected replacement workflows.

## Progress
- ✅ **Valuation Deep Dive P4 polish + small polish (2026-09-28), verified.**
  - **Save per-method levers:** owner/EPV/SBC levers persist to `A["valuation_levers"]` (`PUT
    /api/companies/{t}/valuation-levers`, `service.save_valuation_levers`, whitelisted keys);
    `deep_dive.compute_methods` applies them on reopen + echoes `saved_levers`; deep-dive header
    gained a "Save levers" button.
  - **MC band on the football field:** the Monte Carlo P25–median–P75 becomes a football-field leg
    once MC has run (stats lifted from the `MonteCarlo` component via `onStats`, kept lazy).
  - **EPV adjusted-EBIT:** `derivations.normalized_ebit_mm` now prefers the median **adjusted-EBIT**
    margin (from `adjusted_metrics.json`, `adjusted_ebit_mm`) when ≥3 adjusted years exist, else
    falls back to reported operating margin; EPV card shows an adjusted/reported badge.
  - **Reasoning roll-up to Thesis:** a "My reads across the dossier" panel at the top of the Thesis
    section aggregates every section's "My read" note (+ reviewed tick).
  - **kpi_resolve perf cap:** `kpi_registry.resolve` now processes most-frequent names first and caps
    ai_similarity searches per run (`sim_budget=250`), deferring the long tail to the next run —
    bounds a single pipeline invocation at 1600+ obs. See [[c13v2_kpi_mining]].
  - **IFRS note detection:** `filing_reader` now catches en-dash note headings + "notes to the
    accounts"/group/combined/singular statement variants, without prose false positives.
  - **Deferred — Reading Room press-release gap:** the filings index rows for 6-K/8-K carry no
    period/title/item metadata (many have no form type at all), so press releases can't be identified
    or labelled without content-classifying each filing (a Phase-0 data task, not a reader fix).
- 🟡 **Global valuation defaults — risk-free rate + terminal growth (2026-09-20), compiles clean.**
  One setting overrides every company's `capm.risk_free` and `terminal_growth` at compute time (set
  once instead of per equity). New `shared/valuation_config.py` (JSON on DATA_ROOT, volume-synced;
  per-field range validation); applied non-destructively in `report/model_compute.compute` so it
  flows into all valuations (detail, recompute, index, snapshot); the assumptions dial shows the
  effective (global) values with `risk_free_global` / `terminal_growth_global` flags. `GET/PUT
  /api/valuation-config`; a "Valuation defaults" panel on Settings (blank field = per-equity).
- ✅ **A1 + A2 — built (2026-09-15), verified good by the user.** Dossier (`CompanyDetail`) has a
  left-rail TOC grouped by journey phase + a **Dossier / Focus** reading-mode switch. Shared
  primitives in `lib/Section.jsx` (`SectionRail`, `useActiveSection`, `useSectionRail`, and
  `useCollapse` extended with `mode`/`focusId`/`focusStep`). Focus mode: one section at a time,
  `←/→` paging, centred measure; price chart / journey rail / assumptions rail hidden in Focus.
- 🟡 **A3 — built (2026-09-16), compiles clean, pending live browser verification.** Per-section
  **"My read"** note + **Reviewed** tick on every dossier section (minus `notes`/`ask`/`files`).
  Backend: `section_state` map added to `status.json` (`shared/watchlist.set_section_state`),
  `service.get/set_section_state`, and `GET/PUT /api/companies/{t}/section-state`. Frontend:
  `api.getSectionState/saveSectionState`, a `SectionReasoning` footer in `lib/Section.jsx` (note
  autosaves debounced, reviewed writes immediately, optimistic), and reviewed ticks now light up
  in the rail TOC. Reasoning also enabled on Deep Dive.
- 🟡 **A4 — built (2026-09-16), compiles clean, pending live browser verification.**
  - **Deep Dive** fully moved onto the shared `SectionRail` + `useSectionRail` + Dossier/Focus,
    with the annual/quarterly toggle carried in the rail's `extra` slot, and per-section reasoning.
  - **Investment Case** gained a **Full / Focus** switch + `←/→` stepper in its existing `LeftNav`
    (one section at a time via a scoped `<style>` hide). Deliberately kept its own nav / Read-Work-
    Review modes / RightRail rather than rip them out — so "share one nav component" is partial by
    design; a fuller merge onto `SectionRail` is a possible follow-up if wanted.
- 🟡 **"What changed" engine sharpened (2026-09-17), compiles/imports clean.** (A) read-time:
  changed claims now ranked by materiality×confidence, capped, and "new" grouped by theme; chips
  show true totals (`store._history_bundle`/`_filing_claim_meta`, `WhatChanged`/`ChangeGroups`).
  (B) fixed the comparison baseline: `insights._prior_filing` now diffs an annual against the prior
  *annual* (fiscal `_fiscal_key`), not the last interim — kills the inflated "44 new"; panel header
  uses the same fiscal prior. (C) loop tie-in: `insights._maybe_flag_review` routes to Review when
  the newest filing weakens a material claim. **A is live on deploy; B/C only take effect after the
  doc-insights/comparator stage RE-RUNS on a ticker** (e.g. re-run research/pipeline for BR).
- ✅ **Epic B (B1 + quick-pass + B2) committed + deployed (2026-09-16).** Commit `648f88e` on
  `main`; deployed to fevm. B2 is warehouse-backed — verify end-to-end live: on a name's Investment
  Case, mark an invalidation condition **triggered** (or an expected outcome **missed**), then
  confirm the name appears in the landing's "Needs attention" band as **flagged for review**.
  Also test: record a decision → a default monitor appears; quick-pass a tile → it dims + leaves
  the worklist + shows under Show → "Passed on".
- ✅ **Epic A committed + deployed (2026-09-16).** Commit `4ae8180` on `main`; deployed to fevm
  (`research-cockpit`, deployment `01f1b190789a163cb638a6b562dd48b1`) —
  https://research-cockpit-7474653807068368.aws.databricksapps.com. Recommended: smoke-test A3/A4
  on the live app (type a "My read" + tick Reviewed → reload → confirm both persist and the rail ✓
  shows; check Deep Dive rail + freq toggle and Investment Case Full/Focus).
- ⏳ **Epic B / C not started.**

---

## Epic A — Navigation & density (the core ask)

### A1 — Focus / Reasoning mode toggle on the dossier
- [x] **What:** Add a `Dossier | Focus` view toggle to `CompanyDetail`. Focus renders **one section
      at a time**, full-width and centered with generous whitespace; prev/next buttons + keyboard
      `←/→`; advance in journey order. Dossier mode is today's scroll, unchanged.
- **Why:** You literally can't see the next block, so you dwell instead of rushing. Highest
  leverage, lowest cost — reuses every component as-is.
- **Scope:** `app/frontend/src/pages/CompanyDetail.jsx`, `app/frontend/src/lib/Section.jsx`
  (add a `focus` layout wrapper around the existing `Section` children), `styles.css`. No backend.
- **Depends on:** nothing.
- **Effort:** M.
- **Acceptance:** toggle persists per session; in Focus, exactly one section shows; `←/→` and
  on-screen prev/next move through sections in the declared `sections` order; Dossier mode is
  visually identical to today.

### A2 — One shared left-rail TOC, grouped by the 9 journey phases
- [x] **What:** Replace the horizontal chip nav with a persistent **left-rail scroll-spy TOC**, and
      group the ~20 sections under the journey phases (Understand / Assess / Value / Decide /
      Monitor / Review). Adopt the pattern already in `InvestmentCase` (`LeftNav` + `useActiveSection`)
      as the single shared nav model.
- **Why:** A flat list of 20 horizontal chips is choice-overload. ~6 groups of 2–4 is scannable and
  makes "where am I on the page" == "where am I in my process."
- **Scope:** extract `InvestmentCase`'s `LeftNav` + `useActiveSection` into a shared
  `app/frontend/src/lib/SectionNav.jsx` (or fold into `Section.jsx`); wire into `CompanyDetail`;
  add a phase→sections grouping map. Show per-section state (has content / empty).
- **Depends on:** A1 (share the same section list/order).
- **Effort:** M.
- **Acceptance:** left rail highlights the active section on scroll and in Focus mode; sections
  render under phase headers; same component drives dossier + (later) deep-dive + case.

### A3 — Per-section reasoning capture ("My read") + "reviewed" tick
- [x] **What:** A collapsible **"My read"** note at the foot of each section (saved by section id),
      plus a **"reviewed"** checkbox per section, distinct from the journey stage.
- **Why:** Directly answers "room to think and reason at every subsection." Ticking considered
  judgments (not scrolling past blocks) is what actually slows the rush; the notes roll up into
  Thesis/Scorecard so deliberation compounds instead of evaporating.
- **Scope:** frontend reuse of `lib/NotesPanel.jsx` keyed by `(ticker, section_id)`; backend note
  store keyed by section (extend `journey_api.py` or notes endpoint); surface "reviewed" count in
  the left-rail TOC (A2) and optionally the journey ring.
- **Depends on:** A2 (place the tick in the rail).
- **Effort:** M.
- **Acceptance:** a note typed under a section survives reload; reviewed ticks show in the TOC;
  per-section reads are retrievable for the Thesis roll-up.

### A4 — Unify Deep Dive + Investment Case onto the shared nav model
- [x] **What:** Port A2's left-rail TOC (and A1 Focus mode where it fits) to `DeepDive` and
      `InvestmentCase`, retiring the three divergent nav paradigms (chips+collapse, chips+collapse,
      left-scroll-spy-all-open) in favor of one.
- **Why:** Consistency across surfaces; the case page currently renders every section open (its own
  density problem) — Focus/collapse fixes it too.
- **Scope:** `pages/DeepDive.jsx`, `pages/InvestmentCase.jsx`, shared nav lib from A2.
- **Depends on:** A1, A2, A3.
- **Effort:** L.
- **Acceptance:** all three surfaces share one nav component; Investment Case can be read one
  section at a time.

---

## Epic B — Workflow

### B1 — A "what needs me" worklist front door
- [x] **Built v1 (2026-09-16), compiles clean, pending live verification.** A collapsible
      **"Needs attention"** band at the top of `CompanyBrowser` (the landing "/") — no nav changes,
      respecting the locked 3-spine decisions. Ranks names by attention score from signals already
      on each index row + the journey rollup (no new backend): **price drift vs model** (|vs_model|
      ≥ 15%), **valuation gap** (upside_live ≥ +25% or ≤ −12%), **stale data** (cached price, or
      last-refresh > 30d), and **unfinished research** (journey in an early stage < 50% complete).
      Cap 12, reason chips per card, click → dossier. `WorklistBand`/`attentionFlags` in
      `pages/CompanyBrowser.jsx`. **Deferred to a v2:** open backlog questions and positions-past-
      re-review-date (both need backend aggregation over the case + Lakebase).
- [x] **Quick "pass on a name" triage (2026-09-16).** Hover-reveal `✕ Pass` on each tile + a
      Pass/Restore action in list view; optimistic, persists via the existing `passed` funnel state
      (`setStatus`). Passed tiles dim and drop out of the worklist. The **Show → "Passed on"** filter
      is the passed list; Restore un-passes. Reuses the same state as ScreenCard's "Pass on it".
- [ ] **Original spec (superset):** Add a worklist surface (new landing tab, or a band above
      `CompanyBrowser`) that ranks names by *attention needed*: price moved materially vs. model
      (drift you already compute), stale dossier, open backlog questions, positions past a re-review
      date, journey stalled at a stage.
- **Why:** `CompanyBrowser` is a great *library* but doesn't tell you *what to work on today*. This
  pulls you into paced reasoning instead of aimless browsing.
- **Scope:** backend aggregation over journey + drift + backlog + positions (`journey_api.py`,
  `portfolio_api.py`, monitoring); frontend `pages/CompanyBrowser.jsx` or a new `Worklist` page +
  route in `App.jsx`.
- **Depends on:** none (independent of Epic A).
- **Effort:** M.
- **Acceptance:** worklist lists names with a reason chip each; clicking deep-links into the
  relevant section of the dossier/case.

### B2 — Close the loop: decision → monitor → review
- [x] **Built (2026-09-16), compiles + imports clean; WAREHOUSE-BACKED so verify on deploy.** Wired
      into the Unity-Catalog-backed IC layer, all side-effects guarded (best-effort; never break the
      underlying warehouse write):
  - **decision → monitor:** `decisions.create_decision` now spawns any inline `expected_outcomes` /
    `conditions` (the decision's watch items) and calls `monitoring.ensure_default_monitor` (registers
    a `sec_filings` scheduled monitor if the case has none).
  - **breach → review:** a condition set to `triggered` (`update_condition`), an expected outcome set
    to `missed` (`update_expected`), or a refresh carrying material/high-severity change
    (`run_refresh`) calls `review_routing.flag_for_review` → sets the file-based journey to the
    **Review** stage. New `shared/investment_case/review_routing.py`; `store.workspace_ticker` reverse
    lookup.
  - **visible at the front door:** the B1 worklist flags any name in the Review stage as top-priority
    ("flagged for review").
  - **Deferred:** true numeric alert *thresholds* (KPI breaks) — monitoring here is claim-change /
    refresh-severity based, not per-metric-threshold. Verify end-to-end against the live warehouse.
- **Original spec (for reference):** When a thesis/decision is recorded, auto-spawn its watch items
  + KPIs into Monitoring. When a watch item breaks its threshold, flag it and route the name back to
  the Review stage.
- **Why:** Makes the journey a *cycle*, not a one-way funnel — the thesis you wrote generates what
  you track, and a broken assumption drags you back to re-underwrite. Highest-value workflow change.
- **Scope:** `decisions_api.py`, `monitoring_api.py`, `investment_case_api.py`; journey stage
  transitions in `journey_api.py`; surfacing in `MonitoringSection` + `JourneyRail`.
- **Depends on:** none (but nicer after B1 so breaks show in the worklist).
- **Effort:** L.
- **Acceptance:** recording a decision creates monitoring rows; tripping a threshold marks the name
  for review and shows in B1's worklist.

### B3 — Stage-gated "definition of done" checklists (optional)
- [x] **Built (2026-09-24), backend smoke-tested + frontend compiles clean.** Every one of the 9
      journey stages now carries an explicit **definition-of-done checklist** (`STAGE_CRITERIA` in
      `shared/journey.py`). Each criterion is either **auto** (mirrors the stage's existing cheap
      signal — screen verdict / filings / scorecard / model — read-only, ticks itself) or **manual**
      (tickable). Auto stays auto: manual sub-items on an auto stage are tracked but never
      un-complete it. A **non-auto stage now completes when its whole manual checklist is ticked**
      (the legacy single `manual_done` flag still works as an override), so the checklist *drives*
      completion instead of one opaque "Mark done" box. `get()` returns per-stage `criteria`
      (`{key,label,auto,done}`); new `journey.set_criterion` + `criteria_auto_signals`; `PUT
      /api/companies/{t}/journey` gained `{criterion:{stage,key,done}}` (rejects unknown/auto keys);
      `api.setJourneyCriterion`. `JourneyRail.jsx` renders the checklist in the stage detail (x/y
      count, auto rows badged, manual rows are checkboxes) and the standalone "Mark done" box is
      gone. New `.jr-crit*` styles. Verified: ticking both `decide` criteria flips the stage done;
      unticking one reverts it; bad/auto criterion keys are rejected.
- **What (spec):** Each journey stage gets a small explicit checklist of what "done" means (you
      already auto-complete some). Making criteria explicit slows the rush and enforces reasoning.
- **Scope:** `journey_api.py` (stage criteria), `lib/JourneyRail.jsx` (render the checklist).
- **Depends on:** none.
- **Effort:** S.
- **Acceptance:** each stage shows its criteria; auto-checks stay auto; manual ones are tickable.

---

## Epic C — New analysis facets (pick à la carte)

Ordered by leverage-vs-effort given the fiscal.ai data you already pull.

### C1 — Valuation vs. its own history (multiple percentile bands)
- [x] **Built (2026-09-20), compiles clean.** New `lib/ValuationHistory.jsx` + a "Valuation vs.
      history" section on the Deep Dive: per multiple/yield, a percentile band (min–median–max) with
      a "now" dot and a cheap/rich chip. Direction inferred from the name (yields cheap-when-high,
      multiples cheap-when-low); currency/per-share levels excluded (only mean-reverting ratios).
      Reuses the already-loaded ratio series — no new fetch/backend. Possible follow-up: mirror a
      compact version on the dossier's Valuation section (needs a ratios fetch there).
- **Scope:** compute percentile bands from existing ratio series; chart band + current marker.
- **Effort:** S.

### C2 — Quality of earnings
- [x] **Built + DEPLOYED (2026-09-20).** On fevm `research-cockpit`, deployment
      `01f1b53ea1a616e981c5fbe9578e8bb4`; live endpoint verified for GRAB/ACN/ISRG. New
      **"Earnings quality"** section on the Deep Dive, three grouped reads from the annual
      standardized statements: **Cash backing** (OCF/NI, FCF/NI, accruals ratio (NI−OCF)/avg assets),
      **Working capital** (DSO, DIO, DPO, cash conversion cycle, receivables-vs-revenue growth), and
      **Margin & tax quality** (effective tax rate, SBC/revenue, SBC/OCF). Backend
      `service.earnings_quality` + `GET /api/companies/{t}/earnings-quality` returns each metric's
      series **with render metadata** (`dir` good-direction, `good`/`weak` thresholds, `trend_bad`);
      ratios drop out for loss/negative-denominator years rather than showing as false red flags.
      Frontend `lib/EarningsQuality.jsx` (per-metric row: latest value + verdict chip + sparkline +
      trend delta) reuses the C1 layout language, wired into `DeepDive.jsx` (rail + Focus). Annual-only
      by necessity — no quarterly balance-sheet feed. Deferred revenue isn't broken out in the
      standardized feed, so the receivables-vs-revenue divergence stands in for that red flag.
      Possible follow-up: a compact summary on the dossier's Business Quality section.
- Accruals ratio, cash conversion, deferred-revenue / DSO trends — cheap red-flag detection.
      Fits Business Quality.
- **Effort:** S–M.

### C3 — Capital-allocation track record
- [x] **Built (2026-09-21), compiles + endpoint-verified.** New **"Capital allocation"** dossier
      section (Value phase, after Return decomposition): (1) **ROIC vs. WACC over time** — fiscal.ai
      ROIC bars (matches Capital Efficiency) + a dashed WACC line, with a creates/erodes-value chip,
      current spread, and years-above-WACC count; (2) **incremental ROIC** = ΔNOPAT/ΔInvested capital
      over the full + last-5y windows, judged against WACC (NOPAT at a normalized tax rate; net-cash
      bases guard to "n/m"); (3) **buyback discipline** — gross spend, % of FCF, the net share-count
      change actually achieved, and buyback-$-weighted P/E vs. the simple average (bought below/above
      its own valuation). Backend `service.capital_allocation(folder, wacc)` reads the annual
      standardized statements + `ratios.json`; attached to `/detail` (best-effort) using the model's
      WACC from the C12 `capm` block. Frontend `lib/CapitalAllocation.jsx` (hand-rolled ROIC/WACC bar
      chart + stat tiles). Verified: ACN/MSFT compound well above WACC with disciplined buybacks; GRAB
      reads as a non-compounder (0/6y above WACC). Built its own component rather than folding into
      `ReturnDecomposition` (that one is return *attribution*; this is capital *quality*).
- **Scope:** `lib/ReturnDecomposition.jsx` + backend ratio derivation.
- **Effort:** M.

### C4 — Ownership deltas + insider transactions
- [x] **Built (2026-09-21), endpoint-verified.** Added a **direction signal** to `OwnershipPanel`
      (Stats section): (1) **net open-market insider activity, trailing 12m** — buys vs. sells by
      count/value/distinct insiders, anchored to the latest trade so a stale feed still reads; and
      (2) **institutional accumulation** — holders adding vs. trimming + net share change over the
      reported holders. Key correctness fix: classify by `transactionType`, not `acquiredDisposed` —
      most "acquired" rows are **Grant/Award** and most "disposed" are **Tax Withholding** (mechanical,
      not decisions); only Open-Market Purchase/Sale carry direction. The recent-transactions table now
      shows the real transaction label (was mislabeling grants as green "Buy") + a Value column.
      Backend `service._ownership_signal` + `_insider_kind`, surfaced in `service.ownership`.`signal`;
      frontend `lib/OwnershipPanel.jsx` signal cards + `own-signal` styles. Verified ACN (insiders net
      sellers 25:0) / MSFT (9 sales $116M vs 1 buy; institutions mixed 570:401 across 991 holders).
      **Deferred:** open-market-purchase alerting into the B1 worklist; insider-buy markers on the price chart.
- **Scope:** `lib/OwnershipPanel.jsx` + data source for insider txns.
- **Effort:** M (data-source dependent).

### C5 — Estimate revisions & guidance credibility
- [x] **C5 v1 — Delivery track record (2026-09-21), endpoint-verified.** DATA CONSTRAINT: fiscal.ai's
      `earnings-summary` feed carries **actuals only** (epsActual/revenueActual) — no consensus
      estimates and no dedicated estimates endpoint (verified live), so the classic *consensus drift*
      and *analyst beat/miss surprise* legs are NOT buildable from our data. Instead built (and
      **explicitly labeled as such** in the UI): an **execution/delivery-consistency** read from the
      reported quarterly actuals — YoY revenue/EPS growth, its steadiness (stdev → very steady/steady/
      variable/lumpy), positive-growth streak, acceleration (last-4q vs prior-4q), and how often a
      quarter beat the company's **own trailing-4q run-rate** (a proxy for "above its recent
      trajectory," NOT Street consensus). Backend `service.delivery_track_record` + `_qlabel`,
      attached to `/detail`.`delivery` (model-independent). Frontend `lib/DeliveryTrackRecord.jsx`,
      new dossier **"Delivery track record"** section (Assess phase). Verified: MSFT/ACN consistent
      compounders; TTD flagged decelerating (25%→3% YoY, beat-own 12%); GRAB variable.
- [ ] **C5b — Guidance-vs-delivered (future iteration).** The *true* guidance-credibility read: LLM
      pass over earnings-call transcripts (`companies/<T>/filings/transcripts/*.txt`) to extract
      management's forward guidance (next-Q/FY revenue / EPS / margin), then reconcile against the
      next period's actuals → a "do they hit their own guidance?" score. Bigger (L), overlaps
      **C13**'s doc-mining machinery; extraction reliability is the risk. Needs a consensus feed for
      the analyst-surprise leg (not in fiscal.ai here).
- **Effort:** M (v1 done); C5b ≈ L.

### C6 — Explicit pre-mortem tied to Review calibration
- [x] **Built + DEPLOYED (2026-09-25).** Pre-mortems are a first-class sibling of expected-outcomes/
      conditions on a decision: at decision time you capture foreseen failure modes ("if this is wrong
      in ~2 years, why?") — each with a `category` (thesis/valuation/execution/competition/financial/
      macro/governance/other) and a `likelihood` (low/med/high). At **Review** you score each:
      `materialized` (no/partial/yes) + a `was_primary_cause` toggle. A deterministic
      `premortem_calibration` (per-case + global, folded into the decision-learning summary) reports
      how many foreseen risks materialized (hit rate) and whether the loss came from a **foreseen risk
      vs a blind spot** (proxied by a loss/mixed post-mortem whose decision had pre-mortems but none
      marked primary cause). New Delta table `investment_case_premortems` (DDL in setup.sql + created
      on the warehouse); `schema.validate_premortem`; `decisions.{add,list,update}_premortem` +
      `premortem_calibration`; wired into `create_decision`/`decision_bundle`/`get_journal`/learning;
      `POST .../premortems` + `PATCH .../premortems/{id}`. Frontend: `PremortemBlock` in the Decision
      Journal (capture + review scoring), a calibration card atop the journal, and a per-card count.
- **Scope:** `investment_case_api.py` (pre-mortem field), Decision Journal + Review surfaces.
- **Effort:** M.

### C7 — Portfolio: sizing vs. edge + factor/concentration lens
- [x] **Built (2026-09-22), live-verified against Lakebase.** New portfolio **"Sizing & factors"**
      section (`/portfolios/:id/sizing`). **Sizing vs edge:** suggested weight ∝ **upside × model
      quality** (quality = ROIC vs a flat 9% hurdle + operating-margin stability → 0..1; user chose
      "upside × model quality" over an explicit conviction rating), normalized across the modeled sleeve
      to its own invested weight, read against actual weight → under/over-sized flags (Δ ≥ 1.5pp). A
      lens, not a rebalance order; unmodeled names carry factor context but no edge. **Factor +
      concentration (user chose "both"):** book-relative growth/value/quality/size z-scores, a dominant
      style label per holding rolled up by weight, sector concentration bars, and a collapsible
      per-holding z-score heatmap (teal/amber = tilt direction, not good/bad). Backend
      `portfolio/sizing.py` `compute(pid)` reuses `decomposition._equity_holdings` + `_ratios_data`
      (cached ratios: ROIC/ROE/margins/growth/FCF-yield/PE/market-cap) + `service._valuation_summary`
      for upside; `GET /api/pmt/portfolios/{pid}/sizing`. Frontend `lib/SizingFactors.jsx`. Verified on
      "Actively Managed Growth" (30 holdings, 4 modeled): DLO underweight (1.9%→11.6% sug, 123% upside ×
      0.82 q), ISRG oversized (3.9% upside left); book tilt Growth 36% / Value 29% / Quality 28%.
      **Note:** `SizingStats.jsx`/`Attribution.jsx` were NOT extended (they're realized-P&L attribution,
      a different axis); this is a forward edge×quality lens, so it got its own section. **Deferred:**
      explicit per-name conviction override; risk-budget (vol/beta) weighting.
- (Original spec below.) conviction × upside → suggested size / risk budget (you have conviction, upside, sizing
      stats); add a factor (growth/value/quality/size) + sector-concentration view on the book.
- **Scope:** `lib/SizingStats.jsx`, `lib/Attribution.jsx`, portfolio metrics pipeline.
- **Effort:** M–L.

### C8 — Behavior-through-drawdowns map (portfolio-wide)
- [x] **Built (2026-09-21), live-verified against Lakebase.** New portfolio **"Behavior"** section
      (`/portfolios/:id/behavior`). Every BUY/SELL is placed by the security's **trailing-1-year
      (≈52-week) drawdown at the trade date** — the common axis that lines names up despite different
      calendars. Two views: (1) **diverging buy/sell bars per drawdown bucket** (bars = trade count,
      currency-neutral; notional in the tooltip), and (2) a **per-holding scatter** — max drawdown
      while held (x, deeper left) vs. net trades in drawdowns (y): added ▲ / sold ▼, dot-colored by
      class. Plus a one-line **verdict** from behavior in deep (≤−20%) drawdowns. Backend
      `portfolio/behavior.py` `compute(pid)` (live) joins `transactions` to stored `daily_prices` via
      `prices_store.series_many`; `GET /api/pmt/portfolios/{pid}/behavior-drawdowns`. Frontend
      `lib/DrawdownBehavior.jsx`. Verified on "All Accounts" (1342 txns, 981 priced, 2.5s): net buyer
      into weakness — 426 buys vs 116 sells at 20%+ drawdowns. v1 chose count-driven bars + rolling-1y
      reference + bars & scatter (user). **Deferred:** notional FX conversion; rebased-overlay view.
- (Original spec below.) **What:** Generalize the single-security buy/sell markers (green/red triangles on the price
      chart) into a **portfolio-wide** view of behavior during drawdowns: across all names, which /
      how many did I *buy into* a drawdown (conviction, doubling down) vs. *sell into* one (fear,
      capitulation) — and did I hold through it.
- **Why:** The single-name markers already reveal thesis-conviction vs. fear on one security; rolled
  up across the book this becomes a genuine **behavioral-edge mirror** — am I systematically adding
  at lows or capitulating at lows?
- **The hard part (user's open question):** securities' price action happens at different calendar
  snapshots, so a shared calendar x-axis doesn't line them up. **Proposed fix — don't use calendar
  time; use each security's *drawdown state* as the common axis.** For every transaction, compute the
  name's drawdown from its trailing peak (or distance from 52w high) *at that transaction's date*,
  then position the transaction by that drawdown depth, not its date. Options to iterate on:
  - **Drawdown-bucket bars:** buckets (0…−10%, −10…−20%, −20…−30%, deeper); per bucket, count/notional
    of buys (green) vs sells (red). Answers "in drawdowns past −20%, I bought X names, sold Y."
  - **Behavior scatter (one dot per holding):** x = max drawdown experienced while held, y = net
    action during that drawdown (added / trimmed / exited). Quadrants = "held & added" (conviction)
    vs "sold into the drawdown" (capitulation).
  - **Rebased overlay:** rebase each holding's price to its entry (t=0) and overlay, with markers —
    simplest but mixes different market regimes, so less clean than the drawdown-state axis.
- **Scope:** transactions + lots (Lakebase) joined to `eod_prices` / daily price history to derive a
  trailing-peak / drawdown series per name; portfolio-metrics pipeline for the rollup; a new chart in
  the portfolio Performance/Attribution area (`lib/Performance.jsx` / `lib/Attribution.jsx` /
  `lib/charts.jsx`). Reuse the existing single-security marker logic as the per-name primitive.
- **Effort:** L. Iterate — start with the drawdown-bucket bars (simplest, answers the core question).

### C9 — Damodaran datasets → valuation inputs (ERP by country/industry, industry multiples)
- [x] **C9 Phase 1 — ERP by country (2026-09-21), endpoint-verified.** The "quick win": ingested
      Damodaran's country equity-risk-premium table (NYU Stern, **as of 2026-01-05**, 178 countries)
      into a curated snapshot `shared/reference/damodaran_erp.json` (source URL + as-of embedded;
      refresh annually). `shared/damodaran.py` maps a company → country via `profile`
      (headquarters → legal domicile → mature-market fallback) and returns the ERP + a source label.
      Wired into `autofit_assumptions` (CAPM `equity_risk_premium` = country ERP instead of the flat
      0.055; stamps `capm.erp_source="damodaran:<country>"`); added a global **`erp`** knob to
      `valuation_config` (+ `_apply_global_overrides`) and the Settings "Valuation defaults" panel;
      `wacc_breakdown` now tags the ERP source `damodaran`/`global`, so the **C12 WACC explainer shows
      a "Damodaran" chip**. Verified: ACN→Ireland 5.01%, MSFT→US 4.46%, GRAB→Singapore 4.23%,
      unknown→mature 4.23%. Shifts draft/quicklook FVs + newly-researched models to country ERP;
      saved models keep their stored value until recomputed.
- [x] **C9 self-service refresh + viz (2026-09-21), live-verified.** `damodaran.refresh()` re-fetches
      + parses the NYU country table (header-anchored on the "Country" cell so a title row can't be
      mistaken for the header) and writes a writable snapshot to `<DATA_ROOT>/reference/` (takes
      precedence over the bundled default; volume-synced like `valuation_config`). `GET /api/damodaran`,
      `POST /api/damodaran/refresh`, `PUT /api/damodaran/auto-refresh`; lazy annual auto-refresh
      (`maybe_auto_refresh` on GET when >1yr stale, once/process) + `run_damodaran_refresh.py` job
      entrypoint for a real yearly cron. Settings "Damodaran country data" card (as-of/count/mature/
      stale + Refresh-now + annual toggle) and a **`/damodaran` viz screen** (summary tiles, risk-band
      distribution, searchable/sortable country table). Live refresh on the deployed app returned ok
      (egress to NYU works).
- [x] **C9b — industry multiples / PE / PEG / growth (2026-09-21), endpoint-verified.** Ingested
      Damodaran's `vebitda` (EV/EBITDA, EV/EBIT) + `pedata` (current/forward PE, PEG, expected 5y
      growth) US industry tables (94 industries, Jan 2026) → `shared/reference/damodaran_industry.json`.
      **GICS→Damodaran-industry mapping** (`damodaran.industry_for_profile`): curated overrides
      (~65 GICS names) + a fuzzy token match on subIndustry/industry/industryGroup (sector EXCLUDED —
      too coarse, false-matched); the matched industry + match type are surfaced (transparent, since
      the map is heuristic); a bad match degrades to no-match (→ safe self-multiple fallback).
      **Wired into models:** `autofit_assumptions` anchors the **exit EV/EBITDA to the industry median**
      (×0.85 fade) instead of the subject's own, stamping `exit_ev_ebitda_source`. `service.industry_
      benchmarks` attaches to `/detail`; dossier **Industry-benchmark panel** (Valuation section) shows
      the medians + matched industry. `damodaran.refresh_industry()` folded into the combined refresh;
      **`/damodaran` viz gained an "Industry multiples" tab**. Verified: MSFT→Software (exit 20.8×),
      ACN→Computer Services (12.0×), GRAB→Transportation (10.7×). **Deferred:** industry betas
      (unlevered→relevered), operating benchmarks (margins/ROIC/reinvestment), regional (non-US) sets.
- [x] **C9b-2 — industry betas (2026-09-21), live-verified.** Ingested Damodaran's `Betas.html`
      (unlevered β corrected for cash, levered β, D/E) into the industry snapshot. **Replaces the flat
      β=1.1 CAPM default:** autofit relevers the industry unlevered β to the company's own leverage
      (β_L = β_U·(1+(1−tax)·D/E), clamped [0.5,2.2]) and stamps `capm.beta_source`; the "Refresh
      reference inputs" button also relevers β for saved models; `wacc_breakdown` tags β `damodaran`
      → C12 WACC-explainer chip; Industry-benchmark panel shows unlevered/levered β. Verified live:
      ACN β→0.99 (Computer Services), MSFT 1.26 (Software), GRAB 0.78 (Transportation). Uses the same
      GICS→industry mapping + per-company override, so a corrected mapping fixes β too.
- [~] **C9b-3 — IN PROGRESS (paused 2026-09-21).** Three parts:
    - [x] **Part 1 — operating benchmarks (margins + ROE)** shipped (commit f8d8ff7, deployed): margin.html
      (gross/net/pre-tax operating margin) + roe.html ingested into the industry snapshot and shown in the
      Industry-benchmark panel (context, not model inputs). ROIC skipped (no HTML dataset; C3 covers it).
    - [ ] **Part 2 — regional (non-US) sets** (M–L, NOT STARTED): fetch/parse the Europe/Japan/Emerging/
      Global variants of vebitda/pedata/Betas/margin/roe and route by the company's country/region
      (profile `headquartersRegion`). Long — do fresh. `refresh_industry`/`_IND_URLS` is where it plugs in.
    - [x] **Part 3 — wire PE/PEG/growth as model sanity bounds. ALL THREE DONE (3a/3b/3c) + DEPLOYED.**
      All of 3a + 3b + subject-metrics + 3c live on fevm `research-cockpit` (deployment
      01f1b5db2f531672afe98dec0a03087b, 2026-09-21 16:49 UTC).
      - [x] **3a — soft growth flag (2026-09-21), no FV change.** `service._growth_sanity_flag` compares the
        model's near-term (≤5y) revenue-growth CAGR from `dcf_growth_path` against the industry's expected
        5y growth (Damodaran `pedata`); attached to `industry_benchmark.growth_check` in `company_detail`
        after compute. Fires only on a *material* over-assumption (ratio ≥ 1.5× **and** gap ≥ 3pp — the pp
        floor stops "2× but only +2.7pp" cases like TTD). Surfaced as an amber chip in `IndustryBenchmark.jsx`,
        honestly labelled as a directional check (our rev CAGR vs an EPS-growth benchmark), not a model input.
        Verified across the 9 modeled names — none currently trip it (models are conservatively fitted).
      - [x] **3b — industry-PE × EPS leg on the football field (2026-09-21), no FV change.**
        `service._industry_pe_leg` = industry median **forward** P/E × a forward EPS proxy (year-1 modelled
        revenue at the latest reported net margin, per share). Trailing/current-P/E medians are NOT used —
        Damodaran's are inflated by near-zero-earnings peers (MSFT's industry current P/E ≈ 122×). Added to
        `R["football_field"]` (both `company_detail` and `recompute`, so it survives live what-if) as a
        `low/mid/high` bar. Loss-makers → no leg (CRCL). An **axis guard** (`_PE_LEG_AXIS_*` = [0.4×,2.5×] of
        price) keeps a pathologically divergent value (ACN 4.9×, TTD 4.1×, GRAB 0.31×) off the shared chart
        axis; it's still surfaced as text in the benchmark panel (`ib.pe_leg`, `on_field`). Verified across the
        9 modeled names: MSFT/DLO/ISRG/BMI/RMD charted, ACN/TTD/GRAB text-only, CRCL none.
      - [x] **3c — anchor fitted growth toward industry expected growth (2026-09-21), CHANGES FV.** Opt-in,
        saving button (like "Refresh reference inputs"), NOT automatic — model changes stay deliberate.
        `service.anchor_growth_to_industry` → `_fade_growth_to_industry`: keeps the first `_GROWTH_ANCHOR_KEEP`
        (=2) years as fitted (near-term is company-specific/knowable), then ramps a 0→1 weight over the later
        years to blend each toward the industry expected growth (Damodaran `pedata`), **down-only** (never
        raises a conservative model). Touches ONLY `dcf_growth_path` (stamps `growth_anchor_source`); scenarios
        + every other assumption untouched, so it moves the DCF (Gordon/exit) legs, not the prob-weighted FV.
        Route `POST /api/companies/{t}/anchor-growth`; button shows only when the fitted 5y CAGR > industry
        (else nothing to pull), reports before→after CAGR + DCF Gordon/exit, reversible via the sliders/reset.
        Same cross-type caveat as 3a/3b (our revenue CAGR vs an EPS-growth benchmark). Verified: ISRG
        13%→11.1%-anchored, DCF exit 392.3→390.8; CRCL/MSFT untouched (fitted already ≤ industry).
    - **Part 3 COMPLETE (3a display flag + 3b football-field leg + 3c growth anchor).**
- [ ] **(original spec):** **What:** Ingest Aswath Damodaran's published datasets (NYU Stern) and wire them into the
      valuation model as credible, country/industry-specific inputs and benchmarks:
      **equity risk premium by country**, **industry betas / unlevered betas**, **industry valuation
      multiples** (EV/EBITDA, EV/EBIT, P/E, EV/Sales…), and industry operating benchmarks (margins,
      ROIC, reinvestment, cost of capital).
- **Why:** today CAPM uses a single repo-default ERP (0.055) and autofit comps default to the
  subject's *own* current multiple — both weak. Damodaran's data gives a defensible ERP per the
  company's country and industry-median multiples/margins as comps + sanity bounds — a much better
  draft FV and a benchmark for the researched model.
- **Scope:** (a) acquire + parse his datasets (he publishes Excel/CSV: `ctryprem`, ERP history,
  `vebitda`/`pedata`/`psdata`, `margin`, `roic`, `betas` — quirky formats, updated ~annually in Jan);
  store on the data root / a small table; (b) map to our companies via `profile` (country +
  sector/industry → his industry taxonomy — the fuzzy part); (c) wire into `autofit_assumptions`
  (ERP by country in CAPM; industry exit-multiple + comps instead of self-multiple) and surface as
  benchmarks; optionally auto-set the global ERP via the `valuation_config` knob we built.
- **Effort:** L. The industry-taxonomy mapping is the hard part; ERP-by-country is the quick win.

### C10 — Comps over time (peer trends, not a snapshot)
- [x] **Built (2026-09-22), data-verified.** A new **"Trends"** view on the Competitors section
      (`PeerCompare.jsx`, alongside Table/Scatter): a small-multiples grid of peer-overlay line panels,
      one per metric, over the windowed periods (last 10 annual / 16 quarterly), subject drawn bold in
      Lava, colours matching the peer chips (a stable `colorByKey` off the full column order — fixes the
      chip-vs-chart drift when an unavailable peer shifts indices). Defaults to a **key-trend set**
      (`KEY_TREND_IDS` — ROIC, ROE, operating & FCF margin, asset turnover, revenue growth, EV/EBITDA,
      P/E: the four themes the spec names); an **"All metrics"** toggle expands to the full grouped set,
      and **"Clip outliers"** (shared Tukey-fence `clipDomain`) is available per the drill-down's rule.
      **No backend change** — reuses `compare()`'s existing `values[peer][metric][period]` (already
      cached per-peer, 7-day TTL), so no new fiscal.ai fan-out. `MetricChart` was NOT reused (it overlays
      one company's many metrics; this needs many companies on one metric) — added a compact `MiniTrend`
      instead. Verified: MSFT + 8 peers × 22 periods, all key metrics fully populated.
- [ ] **(original spec):** **What:** On the Competitors/comps view, compare peers **over time** across capital efficiency
      (ROIC / ROE / incremental ROIC), operational efficiency (margins, asset turns, cash conversion),
      valuation multiples, and growth — as multi-year time series, not just today's point-in-time.
- **Why:** the current `PeerCompare` is a snapshot; the signal is in the *trend* — who is compounding
  ROIC / expanding margins, whose multiple has re-rated. That's what separates the quality names.
- **Scope:** fetch each peer's historical ratios/fundamentals from fiscal.ai (same ratios feed the
  Deep Dive already uses, per peer) and render peer-overlaid time series per metric (reuse
  `MetricChart`); lives on the Deep Dive Competitors section or a dedicated comps-over-time view.
  Watch cost: N peers × M metrics × T periods = a fiscal.ai fan-out (cache per peer).
- **Effort:** M–L.

### C11 — IRR / hurdle-rate lens on every investment
- [x] **Built (2026-09-28), compiles + endpoint-verified.** Design decided with the user:
      **(b) probability-weighted scenario IRRs** — each scenario's IRR is the same Grinold–Kroner
      total return used elsewhere (income yield + earnings growth + multiple re-rating), anchored to
      base-year NOPAT (so the current earnings multiple = price / current NOPAT/share) grown to the
      scenario's year-10 revenue × terminal margin, then prob-weighted. This gives the right baseline
      (a fairly-priced name earns ~its discount rate, not ~0% as a naive convergence-to-FV gap would)
      and a realistic spread. **Hurdle = global fixed % + per-name override** (precedence:
      assumptions `hurdle` > `valuation_config.hurdle` > repo default 12%), mirroring the
      rf/erp/terminal_growth global-config pattern. Backend: `model_compute.{_resolve_hurdle,_irr_block,
      irr_at}` + `DEFAULT_HURDLE`/`IRR_HORIZON`; `compute()` emits an `irr` block (expected_irr,
      cushion_pp, clears, prob_clears, per-scenario irr/upside, hurdle+source, horizon_years);
      `service._vd` surfaces `irr` (model price) + `irr_live` (re-anchored via `irr_at`, falls as
      price rises); `_compute_valuation_summary` + `quicklook.draft_valuation` also carry `irr`;
      `valuation_config` gained the `hurdle` field + `hurdle_override()`. Frontend: `lib/IrrHurdle.jsx`
      (headline "Expected IRR X% vs hurdle Y% → ±Z pp", diverging per-scenario bars with a hurdle
      gridline, prob-clears line) mounted in the dossier Valuation section + the quick-look draft;
      Valuation section peek shows "IRR X% vs Y%"; Settings → Valuation defaults gained a
      "Required return (hurdle)" knob. Verified across 9 modeled names: ACN +15.2%/DLO +14.1%/TTD
      +19.1% clear the 12% bar; MSFT +8.5%/ISRG +8.2%/RMD +9.1%/GRAB +5.0%/BMI +6.4% fall short;
      CRCL (loss-maker) → no meaningful IRR (card hidden). **Deferred (as scoped):** portfolio-wide
      IRR ranking + a B1 worklist "below hurdle" signal (user picked the dossier surface only);
      money-weighted IRR reconcile for held positions (option c).
- **(original spec below.)** **What:** Frame every name by **expected IRR vs a hurdle rate** ("does this clear my bar?")
      instead of only upside-to-FV — so names compare on a time-and-opportunity-cost basis, against a
      threshold, and against each other.
- **Why:** upside % ignores the horizon and the opportunity cost of capital; IRR-vs-hurdle is how you
  actually rank ideas and decide whether a given return is worth the risk.
- **Status:** under-specified — flesh out together. Open design questions:
  - **IRR of what?** (a) *Expected IRR from the valuation* — annualized return to reach FV over a
    horizon + dividends (we already compute `expected_return` / the return decomposition); (b)
    *probability-weighted IRR* across the bull/base/bear/worst scenarios (each has prob + implied px
    + a 10y horizon — a natural fit); (c) for *held* positions, reconcile with the money-weighted
    IRR the portfolio tracker already computes.
  - **Hurdle source:** a global config (reuse the `valuation_config` pattern) — fixed required
    return (e.g. 12–15%), or WACC, or rf + a required equity premium; global with a per-name override.
  - **Where it shows:** per-name (dossier + the quick-look draft), and portfolio-wide — rank
    holdings/candidates by IRR vs hurdle, a "clears hurdle" chip, and feed it into the B1 worklist.
  - **Read:** "expected IRR X% vs hurdle Y% → +Z pp cushion" (or a shortfall that argues against it).
- **Effort:** M once the IRR definition + hurdle source are pinned (leverages the existing scenarios /
  `expected_return` + the config pattern). **First step: decide (a)/(b)/(c) and the hurdle source.**

### C12 — WACC explainer with sourced inputs (pairs with C9)
- [x] **Built (2026-09-20), compiles + endpoint-verified.** `compute()` now emits an auditable
      `capm` block (`shared/report/model_compute.wacc_breakdown`): rf, β, ERP → Ke; cost_debt_pretax
      × (1−tax) → after-tax Kd; equity/debt weights; WACC = wE·Ke + wD·Kd — recomputed to equal
      `_wacc` exactly. Each input carries a **source tag** (`global` config override / `auto-draft`
      default / `model` = the company's own; a `damodaran` tag is reserved for C9). Passed through
      `service._vd` (dossier) and the quicklook `derivation` (draft). Shared `lib/WaccExplainer.jsx`
      renders the waterfall + an equity/debt weight bar + chips on any non-`model` input; mounted as
      an expandable "Cost of capital — how WACC is built" under the dossier Valuation cards, and
      inline in the quicklook "How this fair value was reached". Verified live-shape: ACN all-`model`,
      GRAB all-`auto-draft`. **Sourced rf/ERP/β still depend on C9** (Damodaran) — until then inputs
      are the repo/auto defaults or the model's own.
- **Original spec:** Make WACC transparent instead of a bare "12.0%". Show the full derivation with each
      input and its source: **Ke = rf + β·ERP** (CAPM), **Kd = cost_of_debt_pretax × (1 − tax)**,
      capital weights E/(E+D) and D/(E+D), → **WACC = wE·Ke + wD·Kd**. Tag where each input came from
      (repo default / **Damodaran** country-ERP + industry (unlevered→relevered) beta / fitted / user
      override).
- **Why:** today the number just appears; an auditable breakdown builds trust and shows *which*
  assumption is driving it. Damodaran (C9) supplies credible, sourced rf/ERP/beta so the defaults
  aren't hand-waved.
- **Scope:** a WACC breakdown component (extend the draft's "How this fair value was reached"
  derivation into a full CAPM/WACC waterfall with per-input source chips); `compute` already exposes
  `ke`/`wacc`/the `capm` block — add the source tags; beta/ERP sourcing depends on **C9**. Lives on
  the dossier Valuation section + the quick-look draft.
- **Effort:** S–M (explainer); the sourced inputs depend on C9.

### C13 — Management KPI evolution & discovery from filings
- [~] **v1 BUILT (2026-09-22), data-verified. Hybrid chosen: ship data-driven now, layer LLM later.**
      Derives management KPI evolution from the disclosed segment/KPI set (fiscal.ai `segments_and_kpis`,
      already on disk — no LLM/warehouse run). `service.kpi_evolution(folder, freq)` classifies each
      reported metric over its history as **ADDED** (introduced mid-history, still active), **DROPPED**
      (reported ≥2 periods then stopped, or fiscal.ai-discontinued — the quiet-drop red flag),
      **REDEFINED** (≥2 variants sharing a base name after stripping `(Pre/Post-FYxx)`/`(GAAP)`/… — a
      rename/realignment; netted out of add/drop so a segment realignment isn't a wave of fake drops),
      or continuing. `GET /api/companies/{t}/kpi-evolution?freq=`. Frontend `lib/KpiEvolution.jsx`
      mounted atop the **KPIs & Segments** panel (`SegmentsPanel.jsx`): dropped (red) / redefined
      (amber) / added (info) chip groups + click-any-KPI-to-chart via `MetricChart`. Verified: MSFT
      dropped Windows/Office/Devices Revenue (FY2024) + 18 redefined (FY2024 segment realignment); ISRG
      0 dropped (a quality tell) + Ion/da Vinci placements added; ACN North America→Americas shows as a
      drop+add at FY2024 (a rename with a wholly different name isn't caught as "redefined" — known v1
      limit).
- [x] **v2 BUILT + PILOTED (2026-09-23).** LLM-mined KPIs from the filings, reconciled vs fiscal.ai.
      Ran the discovery pipeline on ISRG (warehouse): `kpi_discover` (ai_extract over structured docs) →
      1612 observations → `kpi_registry.resolve` (ai_similarity) → ~106 canonical KPIs → `promote` →
      facts. `service.management_kpis` pulls registry+facts and reconciles against fiscal.ai's FULL
      metric vocabulary (segments/KPIs + standardized statements + ratios), so standard financials count
      as "in fiscal" and `beyond_fiscal` = genuinely-novel operating metrics; drops generic/statement
      lines + de-dupes. `GET /api/companies/{t}/management-kpis` (lazy, warehouse). Frontend: a "✨ Load
      KPIs mined from the filings" section in the KPI panel (beyond-fiscal group + collapsible
      also-covered). Pipeline stages `kpi_discover`/`kpi_resolve`/`kpi_promote` added to
      `run_stage.py`+`pipeline.py` so future research populates it. ISRG beyond-fiscal surfaced ASP,
      da Vinci placements by region, Ion biopsy procedures / installed base / procedure volume+growth.
      **Caveats:** ai_extract is noisy (some OCI/amortization lines leak through the filter); series
      populate as `promote` finishes (read live). Discovery is slow (~an ai_extract per candidate page).
- [ ] **(original spec):** **What:** Go beyond standard financials by mining the documents:
  - **(a) Extract management's guided/favorite KPIs** from the current *and historical* 10-Ks / MD&A
    (the operating metrics they choose to highlight — NRR, units, ARPU, take rate, backlog, bookings…).
  - **(b) KPI diff over time** — what was **added**, **dropped**, or **redefined** across filing years.
    A quietly-dropped KPI is often the one going the wrong way — a red flag worth surfacing.
  - **(c) Reconcile** management-reported KPIs vs what fiscal.ai actually provides (coverage gaps),
    and track the management ones over time (reuse `MetricChart`).
  - **(d) Discover other trackable KPIs** from MD&A + analyst docs + fund reports — metrics worth
    tracking that aren't in the standard financial feed.
- **Why:** the KPIs management spotlights (and stops reporting) are a strong, thesis-relevant signal
  the standard financials miss.
- **Scope:** extends the existing doc-mining pipeline (`shared/docs/insights.py` claims,
  `kpi_discover.py`, `kpi_registry.py` — check overlap first); an LLM pass over current+historical
  filings to pull guided KPIs + values/periods; a period-over-period KPI diff (added/dropped/redefined);
  reconcile against `segments_and_kpis`; a "Management KPIs" panel on the dossier tracking them over
  time with drop/add flags; extend to analyst/fund docs.
- **Effort:** L.

### C14 — Reading Room: guided active-reading aid for 10-K / 10-Q  ✅ BUILT
- [x] **Built + DEPLOYED (2026-09-23), all phases.** `/read/:ticker[/:key]`, `shared/docs/filing_reader.py`
      (HTML→structured incl. 20-F/IFRS notes), signal spotlight + Light/Med/Strong strength, **Changed**
      YoY/QoQ redline diff, **Ask** (RAG), **✨ Interpret** (explain + hedge radar + narrative↔numbers),
      **📋 Brief**, **🎙 vs call** transcript cross-read, and durable folder-backed reviewed + "My read"
      notes. Spec: `docs/reading-room-spec.md`. **Deferred polish:** press-release-vs-filing gap; tighter
      IFRS note detection.
- [ ] **What (spec):** A dedicated full-screen workspace (`/read/:ticker/:filing`, separate from the dossier)
      to actively read a whole filing — organized so signal stands out, with a YoY/QoQ redline diff,
      first-class **footnote / notes** surfacing, and an **"Interpret with AI"** button (organize by
      default, interpret on demand). Unit = one filing; all sections incl. notes.
- **Why:** filings bore/conceal; the real disclosures hide in the notes. An active-reading aid turns a
  passive slog into a deliberate walk and puts *what changed* + *what's buried* front and center.
- **Full spec:** [`docs/reading-room-spec.md`](reading-room-spec.md) — locked decisions, feature
  layers (structural vs AI-on-demand), footnote lane, data-availability findings (raw is a flattened
  blob; notes not extracted; needs a clean structured source = Phase 0), reuse map, phasing, open Qs.
- **Effort:** **XL**, multi-phase. Phase 0 (clean structured source incl. notes) + Phase 1 (structural
  reader: section walk, diff, footnote elevation, reviewed/My-read) are the first meaningful ship;
  Phase 2 (hedge radar, claim/novelty, narrative↔numbers, materiality) needs the warehouse; Phase 3
  (transcript cross-read, push-to-thesis).

---

## Sequencing summary
**Next implementation priority:** follow V01–V04 and the V/M delivery sequence in
[`agentic-valuation-monitoring-backlog.md`](agentic-valuation-monitoring-backlog.md).
The numbered list below is the historical UX sequencing.

1. **A1** (Focus mode) — smallest change that fixes the complaint; ship and live with it.
2. **A2 → A3** — left-rail TOC grouped by journey + per-section reasoning capture.
3. **A4** — unify Deep Dive + Investment Case onto the shared model.
4. **B1 → B2** — worklist front door, then close the decision→monitor→review loop.
5. **C1, C2 …** — layer in analysis facets whenever, starting with the cheap high-context ones.