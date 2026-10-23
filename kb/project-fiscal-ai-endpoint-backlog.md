# Project document: fiscal-ai-endpoint-backlog

Source: research_val_personal/docs/fiscal-ai-endpoint-backlog.md
Kind: design document; may describe planned rather than shipped features.

# fiscal.ai endpoints not yet surfaced — backlog

Reviewed 2026-10-21 against <https://docs.fiscal.ai/docs/api-reference>. Analysis features
(guidance, buybacks, management incentives, share-cannibal analysis) are in
[research-feature-backlog.md](research-feature-backlog.md). "Plan" is what this

## Shipped with this review

- **Agentic Consensus** — `GET /v1/company/estimates`. Company page → *Consensus estimates*:
  last-quarter surprise, next-quarter and forward-year estimates, forward P/E, estimate table
  (20 metrics, annual/quarterly, range + source + confidence), company-guidance excerpts.
  `app/backend/consensus.py`, `app/frontend/src/lib/ConsensusPanel.jsx`.
- **Street consensus** (`/v1/company/estimates/street`) and **ratings / price targets**
  (`/v1/company/estimates/street/ratings`) — wired to the documented shapes, but the plan
  returns 403 ("Wall St. analyst estimates are not included in personal API plans"). The panel
  says so and lights up if the plan changes. `/v1/company/estimates/street/consensus` is listed
  in the docs but returns 404.

## To do

Ordered by value to the research → valuation → monitoring loop.

### P1

- [x] **Consensus inside the valuation** (no new endpoint). Shipped 2026-10-21 with research
  item 1: per-year growth and margin vs. consensus in the Assumptions panel, "Use consensus",
  checks, and price-implied vs. consensus CAGR. Put Agentic Consensus next to the
  model: revenue-growth and margin paths vs. consensus, and reverse-DCF implied growth vs.
  consensus growth. A *check* when the model's FY+1 revenue or EPS is more than ~10% off consensus.
- [x] **Estimate revisions** (no new endpoint). Snapshots + 30/90-day revisions shipped
  2026-10-21; alerts on large revisions still to do. Agentic Consensus has no history parameter, so
  snapshot it daily (the financials-refresh job can do it) and show 30/90-day revisions. Raise
  an alert on large revisions for held or watchlisted names.
- [ ] **Dividends** (partly done 2026-10-21: the DDM uses its trailing declared DPS) — `GET /v1/company/dividends` · Plan: OK. DPS history, forward
  (declared) dividends, annualized DPS. Today the dividend leg of the return decomposition is
  derived from payout × earnings; use real DPS and yield, and show the dividend record on the page.
- [ ] **Total return calculator (equity level)** — uses `GET /v1/company/dividends` +
  `GET /v3/company/stock-prices` · Plan: OK. For one security from a start date (default: your
  first buy if you hold it, else a date you pick) to today: price return, dividend return and
  total return, both cumulative and annualized (CAGR), on $10,000 invested. Two dividend
  treatments: reinvested on each ex-date at that day's close (true total return), and cash
  (price return + dividends received). Uses split-adjusted prices and per-share dividends
  adjusted the same way; flags ADR / share-class conversions and dividends paid in a currency
  other than the trading one. Chart of the growth of the investment with the price-only line
  for comparison. Goes on the company page next to *Return decomposition*. That breakdown
  covers fiscal-year windows (dividend + earnings growth + buyback + re-rating); this answers
  "what has this stock actually returned since date X". Portfolio performance (`perf.py`) stays
  account-level. Depends on the Dividends item above.
- [ ] **Events calendar** — `GET /v1/events-calendar` · Plan: OK. Upcoming earnings
  dates (confirmed / estimated, session, time). An "Upcoming earnings" strip on My Research,
  Active Lists and portfolios. Also lets the financials-refresh job check a company only once its
  event shows `reported`, not twice a day across everything.
- [ ] **News summary** — `GET /v1/company/news-summary` · Plan: OK. A short markdown summary
  regenerated daily; put it at the top of the News panel.

### P2

- [ ] **Daily ratios** — `GET /v1/company/ratios/daily/{ratioId}` · Plan: OK (ids come from
  `/v1/ratios-list`; `pe_ratio` is not one). Daily P/E, EV/EBITDA, FCF yield history so
  *Valuation vs. history* bands use daily values, not period-end points.
- [ ] **Top news** — `GET /v1/top-news` · Plan: OK. A cross-company feed for Market Data and
  the home page, filtered to watchlists and holdings.
- [ ] **Institutional investors** — `GET /v1/ownership/institutional/holders` (directory,
  Plan: OK) and `GET /v1/ownership/institutional/holdings` (one investor's portfolio). Track
  chosen funds: what they hold and how it changed, linked from the ownership table.
- [ ] **Fund letters, full set** — today only `GET /v1/company/fund-letters` is used. Add
  `/v1/fund-letters` (needs `year`/`quarter`), `/v1/fund-letters/{letterId}` (full extracted
  text), `/{letterId}/pdf`, `/v1/fund-letters/investors` (Plan: OK),
  `/investors/{investorId}` and `/v1/fund-letters/companies` (Plan: OK). Full letter reader,
  investor pages, and "letters mentioning companies I follow".

### P3

- [ ] **Intraday prices** — `GET /v1/company/stock-prices/intraday` · Plan: OK. A real 1D/5D
  price chart; today the short ranges come from daily closes.
- [ ] **Ratio and metric definitions** — `GET /v1/ratios-list`, `GET /v1/standardized-metrics-list`
  (+ `/{templateType}/{statementType}`) · Plan: OK. Definitions as tooltips in Deep dive and in
  the custom-metric builder.
- [ ] **Earnings call audio** — `GET /v1/company/ir-events/audio/{eventKey}`. A player next to
  transcripts in the reading room.
- [ ] **Filing page images** — `GET /v1/filing/{filingId}/page/{pageNumber}/image`.
  Page thumbnails for cited evidence (the full PDF is already downloaded).

### Blocked on plan

- [ ] Street consensus `history=true` (5-year consensus revisions) and ratings — need the
  `analyst_estimates` feature.

## Follow-ups from 2026-10-21/22 work

- [ ] Alerts on large estimate revisions for held / watchlisted names (snapshots exist; no alert yet).
- [ ] Refresh the document index (Documents / Ask) after new filings, not just the Reading Room;
  heavier (ai_* parse + warehouse), so probably the 10-Q/10-K only.
- [ ] Section earnings releases in the Reading Room (no Item headings today: one "Cover" section).
- [ ] UI switch for `reclassify_capitalized_spend` to compare both treatments.
- [ ] Stop requesting `/v1/company/estimates/street` in valuation runs on this plan (403 shows as
  "Unavailable sources: analyst_estimates" on every run).
- [ ] Guidance for names fiscal.ai doesn't tag (e.g. ISRG): read it from releases / transcripts.

## Housekeeping

- `shared/gather.py` pulls `/v1/company/earnings-summary`, which still answers but is no longer
  in the API reference. Watch for deprecation; Agentic Consensus reported periods cover the same
  beat/miss ground.
- `FiscalAI.analyst_estimates()` (`/v1/company/estimates/street`) has no callers and 403s on
  this plan; `app/backend/consensus.py` now handles that endpoint.