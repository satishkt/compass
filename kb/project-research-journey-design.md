# Project document: research-journey-design

Source: research_val_personal/docs/research-journey-design.md
Kind: design document; may describe planned rather than shipped features.

# Research Journey — design

A **governed, personalized research workflow** that turns the app's standalone tools
(screen, doc extraction, thesis/claims/evidence, valuation, decision journal, monitoring)
into ordered **stages of deepening analysis**. Inspired by the "TDI Terminal" reference:
a per-company staged deep-dive plus a personal "My Journey" hub.

Design decisions (owner, 2026-09-04):
- **Soft gates** — the journey guides and warns; it never blocks navigation.
- **Overlay first** — keep today's company page; add a journey rail + progress. A full
  staged-tab rebuild of the company page is Phase 2.
- **Configurable scorecard** — TDI's 7 categories are the default, but categories and
  weights are user-editable under *Style*.
- **Progress now, governance next** — ship the spine + progress + soft gates first;
  per-stage required-artifact rules, sign-off/review states, and a transition audit trail
  come in Phase 2 (they map onto the existing `governance_api`).

## The spine — 9 stages

A ticker moves through these. Each stage *is* a bundle of existing tools surfaced as
"the step to do now," with a cheap completeness signal.

| # | Stage | Existing tools = the step | Auto-complete signal (Phase 1) |
|---|-------|---------------------------|--------------------------------|
| 1 | **Idea** | add to watchlist, capture source/reason | company folder exists |
| 2 | **Screen** | 10-Q pre-screen + fundamentals rubric | `status.json` has a `screen_verdict` |
| 3 | **Understand** | Overview · KPIs & Segments · Financials · Documents + Ask + extract | filings or a research dossier on disk |
| 4 | **Assess** | Scorecard (configurable, 1–5) + Written Analysis (thesis/claims/evidence/risks) | `scorecard.json` ≥ half categories rated |
| 5 | **Value** | Valuation workbench (DCF/SOTP/scenario/reverse-DCF) | `models/<T>-assumptions-full.json` exists |
| 6 | **Decide** | Decision journal: conviction, expected outcome, conditions | manual check-off (Phase 2: decision row) |
| 7 | **Position** | entry plan → position in an account | manual check-off (Phase 2: Lakebase position) |
| 8 | **Monitor** | KPIs / alerts / refresh, re-evaluate triggers | manual check-off (Phase 2: monitor row) |
| 9 | **Review** | post-mortem: outcome vs. expectation | manual check-off (Phase 2: post-mortem row) |

**Completeness ring (0–100)** = weighted blend of completed stages (equal weights by
default; overridable in Style). A stage counts as complete when its auto-signal is true
*or* the user checks it off. Soft gates mean the ring/rail only *warn* about missing steps.

## Storage — JSON on the volume (no new Delta tables in Phase 1)

Mirrors `shared/watchlist.py` (`companies/<T>/status.json`): instant reads, no warehouse
round-trip on page load, synced to the UC volume by the app's write-through middleware.

- `companies/<T>/journey.json` — `{stage, manual_done:{stage:bool}, history:[…], updated}`.
- `companies/<T>/scorecard.json` — `{ratings:{category_key:1..5}, notes:{…}, updated}`.
- `<DATA_ROOT>/journey_style.json` — global config: `scorecard_categories:[{key,label,weight}]`,
  `gate_mode` (default `soft`), optional `stage_weights`, `screen_pass_threshold`.

Phase 2 can promote these to Delta if cross-company analytics need SQL; the module boundary
(`shared/journey.py`) keeps that swap local.

Default scorecard categories (TDI): Moat, Industry, Management, Skin in game, Incentives,
Financials, Balance sheet — each rated 1–5, equal weight.

## Backend

`shared/journey.py`
- `STAGES` — ordered stage definitions (key, label, blurb).
- `style()` / `save_style(patch)` — global config with defaults merged.
- `scorecard(ticker)` / `save_scorecard(ticker, ratings, notes)`.
- `auto_signals(ticker)` — cheap filesystem/`watchlist` checks per stage.
- `get(ticker)` — `{stage, stages:[{key,label,done,auto,manual}], completeness, scorecard_score}`.
- `set_stage(ticker, stage)` / `mark(ticker, stage, done)`.
- `pipeline()` — cross-company rollup for the hub (funnel counts, per-name stage + ring).

`app/backend/journey_api.py` (router, mounted in `main.py`)
- `GET  /api/journey` → `pipeline()`
- `GET  /api/journey/style` · `PUT /api/journey/style`
- `GET  /api/companies/{t}/journey` · `PUT /api/companies/{t}/journey` (`{stage}` or `{mark:{stage,done}}`)
- `GET  /api/companies/{t}/scorecard` · `PUT /api/companies/{t}/scorecard`

## Frontend

- `lib/JourneyRail.jsx` — overlay at the top of `CompanyDetail`: the 9 stages as a stepper,
  completeness ring, per-stage status (auto ✓ / checked / to-do), CTA deep-links into the
  existing sections/pages, soft "still missing…" hints, manual check-off + set-current-stage.
- `lib/ScorecardPanel.jsx` — the configurable 1–5 scorecard; a new `scorecard` section in
  `CompanyDetail` and reachable from the rail's Assess step.
- `pages/MyJourney.jsx` (`/journey`) — hub: **Stats** (funnel by stage, avg completeness),
  **My Research** (all names by stage + ring), **Journal** (reuses decisions), **Valuations**,
  **Style** (edit categories/weights, gate mode). Favorites/Annotations/Profile are Phase 2.
- Nav: a **My Journey** entry (Stats · My Research · Journal · Style · Valuations), matching TDI.

## Phase 2 (fast follow)
- Rebuild `CompanyDetail` into TDI-style ordered **stage tabs** with Prev/Next + the ring.
- **Governance**: per-stage required-artifact *rules*, review/sign-off states, and a
  transition **audit trail** via `governance_api`.
- Auto-signals for Decide/Position/Monitor/Review wired to decisions/positions/monitors.
- **Annotations** highlight layer; PDF-of-journey export; Favorites.