# Project document: on-demand-valuation

Source: research_val_personal/docs/on-demand-valuation.md
Kind: design document; may describe planned rather than shipped features.

# On-demand valuation rebuild

The company valuation page now starts a fresh-data rebuild. It does not load an
assumptions-full file, previous review approval, old currency/ownership metadata,
or a previous valuation as an input. Company identity can be reused to identify
the correct Fiscal listing; financial numbers are fetched again for every run.

## User flow

Open a company's valuation page and choose **Fetch current data and rebuild
valuation**. The page shows progress, then the financial period, market-close date,
source references, model estimates and calculation workings. Opening the page
reads the last run; it does not trigger paid-data calls. Click rebuild for a fresh
snapshot. Estimates can be changed before a run under **Valuation estimates**.

Reported facts and valuation estimates have different roles. Discount rates,
forecast growth, maintenance investment and the excess-cash allocation remain
estimates, even when historical observations inform them. Results are displayed
as estimates, without importing or manufacturing a legacy approval. There is no
probability-weighted blend of unrelated valuation methods.

## Data and extraction

Each run fetches the current Fiscal profile, annual and quarterly income/cash-flow
statements, annual and quarterly balance sheets, shares and latest prices. Calls
have provider timeouts and bounded concurrency. A failed endpoint is recorded;
its old local file is never silently substituted.

Four aligned, consecutive, discrete three-month quarters supply TTM earnings and
cash movements. Duplicate periods are deduplicated by filing/restatement date;
YTD cash-flow rows cannot be summed as quarters. If aligned TTM data is unavailable,
the most recent aligned annual period is used and labelled. A newer aligned annual
period takes precedence over older TTM data. Balance-sheet figures, shares, prices
and earnings retain their own dates. The run date is not presented as the financial
period date. Quotes more than seven calendar days old, implausibly old financials,
and stale shares produce specific input gaps.

Fiscal cell values use the provider's absolute numeric amounts. The vendor's
presentation `unit` is preserved in provenance and is not multiplied into the value
again. Every accounting input keeps its source-file key, cell pointer, period,
currency and available filing links. Derived values retain their constituent facts.

Where Fiscal inputs are incomplete and a CIK is available, a bounded SEC
company-facts request supplies a deterministic XBRL fallback. Exact supported
US-GAAP concepts and annual durations are mapped; future filings are excluded.
Existing populated Fiscal cells are not overwritten. Filing accession and the
pointer into the saved SEC response are retained. This is structured filing
extraction, not an LLM reading arbitrary filing prose. Extension concepts and
unsupported filing taxonomies remain missing inputs. SEC requires a contact in
`RESEARCH_SEC_USER_AGENT`.

Cross-currency prices use a dated ECB rate through Frankfurter. Its date and
currency direction must match the quoted price. Known minor-unit conversions
(such as GBX to GBP) are explicit. Financial cash flows and rates remain in reporting
currency; only per-security results and the reverse-DCF price boundary are translated.
Unresolved ADR/security conversion is a real missing input, not a guessed ratio.

## Accounting and model policies

- **SBC:** reported EBIT and common-shareholder net income retain the expense. No
  SBC add-back, extra subtraction or add-back-versus-dilution model is run.
- **FCFF:** EBIT × (1 − effective tax rate) + D&A − total capex − operating WC
  investment. WC investment is the negative of the sum of disclosed operating
  working-capital cash movements, excluding income-tax-payable movements. Blank
  metric definitions from other periods are omitted; a period with no disclosed
  numeric movements remains missing.
- **Buffett owner earnings:** reported common-shareholder net income + D&A −
  estimated maintenance capex − estimated required incremental WC. No unspecified
  other noncash add-back is assumed. Maintenance capex defaults to total capex;
  its fraction is an explicit estimate. Required recurring WC defaults to positive
  base-period investment, not a temporary working-capital release. The stream is
  discounted at an equity required return. Debt is not deducted again.
- **Greenwald EPV:** the median of up to five annual reported EBIT margins applied
  to current base revenue, after tax, plus D&A less maintenance capex, capitalized
  at the enterprise discount rate. Reported profit is used so management-adjusted
  SBC exclusions do not enter silently. This normalization and reinvestment
  treatment are disclosed estimates.
- **DCF:** grow base FCFF over the explicit horizon, then use Gordon terminal value.
  Enterprise value is bridged once to common equity. No terminal-growth clamping
  or arbitrary FCF conversion factor is applied.
- **Reverse DCF:** solve FCFF growth against market equity value using that same
  forward DCF and claims bridge. The solved variable is labelled. Nonpositive base
  FCFF and prices outside the bracket are unavailable, not boundary answers.
- **Cash and claims:** no cash is assumed excess by default. Borrowings use a
  disclosed total or nonoverlapping current/noncurrent debt components. Reported
  total equity minus common equity can establish an aggregate book proxy for
  outside equity claims; those claims are not also added individually. Without
  that reconciliation, missing preferred/minority claims prevent an equity DCF or
  EPV, while an otherwise complete owner-earnings calculation remains available.
- **Growth:** the default forecast estimate is annual historical revenue CAGR
  bounded to −20% to +20%, clearly labelled as an estimate of future cash-flow
  growth. A user can supply expected growth directly. It is not a reported fact.

The simple enterprise models are intended for standard operating companies.
Bank/insurance reporting templates need specialized models. ADR rights,
finite-life rights, complex ownership, tax-loss regimes, ambiguous debt scopes and
unmapped filing concepts may need additional interpretation. Missing information
is not cured by assigning a source label or treating absence as a reported zero.
The process does not claim that automated data retrieval completes underwriting.

## Persistence and historical models

Runs live under `companies/<ticker>/models/current_valuation/runs/<run-id>/`:

- `run.json`: lifecycle, policy, source errors and timestamps.
- `sources.json`: frozen responses used by the calculation.
- `engine.json`: the shared calculation source at that run.
- `result.json`: sourced inputs, estimates, workings and model results.

`latest.json` identifies the active run. The latest fresh run supersedes the legacy
summary and detail calculation, including when fetching fails. Historical research,
old assumptions, reports and reviewed revisions are retained as historical files;
they are not erased or relabelled current. Existing workbook/report generators
have not been rewritten to emit this new process and their old exports must not
be presented as its output.

Only two rebuild workers run concurrently, and a per-company process lock prevents
duplicate concurrent work. Background completion explicitly syncs its files and
active pointer to the Databricks volume, since request middleware has already
returned. Incomplete sync is reported. Lock files are not mirrored. An app restart
makes unfinished runs visibly interrupted; a rebuild fetches from scratch.

API routes:

- `GET /api/companies/{ticker}/current-valuation`: latest run, no new retrieval.
- `POST /api/companies/{ticker}/current-valuation`: typed policy body (or `{}`),
  returns HTTP 202 and a run identifier.
- `GET /api/companies/{ticker}/current-valuation/{run_id}`: poll a specific run.

Lifecycle: queued → fetching → calculating → completed, failed or interrupted.
A completed run may have estimated, partial or needs-inputs results. A fetch
failure is distinct from a model lacking a required fact.

## Validation

The Python regression suite passes 489 tests, including accounting, currency,
period alignment, source failure, SEC fallback, ordinary-share and equity-claims
reconciliation, interrupted work, and separation from legacy metadata. Production
frontend build passes. Chrome validation exercised an actual fresh ACN rebuild,
rendered all four model outputs and reported no browser console errors. ACN's live
pilot used TTM through August 31, 2026 and the October 16 close; it did not inherit
the older saved model's period or approval metadata.

## Startup mirror recovery

Startup downloads replace files atomically and preserve files modified after
sync began. Cleanup uses the same cutoff, so a long-running initial sync cannot
delete newer valuation runs. Temporary write files are excluded from mirroring.
Missing local run records/results are restored directly from the volume on read.
If recovery fails, the valuation is marked unavailable and the company list stays
usable, without reverting to legacy assumptions. Active valuation records and
company profiles are prioritized during startup download.

## Visual explanations

The valuation panel includes a market-price comparison, an accounting waterfall,
a fair-value waterfall, historical and reverse-DCF growth comparisons, cash-flow
projection paths and an editable EPS/P/E scenario. Each chart includes numerical
values. Chart data comes from the exact saved source snapshot; older runs can be
explained without fetching new fundamentals.

The intrinsic-value bridge starts with base cash earnings capitalized with zero
growth. It adds explicit-horizon growth with a zero-growth terminal assumption,
then the incremental effect of terminal growth, and finally the cash/claims
bridge for enterprise models. The signed contributions reconcile to saved fair
value; allocation is sequential and interaction effects depend on that order.
The terminal-value timing share is a different view of the same cash flows.

The EPS/P/E chart is a separate undiscounted future-price scenario, with constant
shares and no dividends. It applies EPS growth first, then the exit P/E, explicitly
assigning the interaction to re-rating. The DCF itself uses a Gordon terminal
value and does not model a separate multiple re-rating.

New rebuilds request Fiscal /v1/company/estimates/street (Zacks analyst consensus),
subject to subscription/coverage. Fiscal agentic estimates are not substituted.
Analyst rates compare the first two future annual forecasts and retain metric,
basis, dates and inputs. Adjusted EPS is labelled and is never fed into the
SBC-expensed valuation. Historical revenue, net-income and FCFF CAGRs are shown
uncapped over their own dated periods; nonpositive endpoints have no CAGR.

GET /api/companies/{ticker}/current-valuation/{run_id}/explanation supplies the
chart data. New runs persist explanation.json with sources and results.