# Project document: research-feature-backlog

Source: research_val_personal/docs/research-feature-backlog.md
Kind: design document; may describe planned rather than shipped features.

# Research & valuation feature backlog

Analysis features requested 2026-10-21. Items that are mainly about consuming a fiscal.ai
endpoint (incl. the equity-level total return calculator) live in
[fiscal-ai-endpoint-backlog.md](fiscal-ai-endpoint-backlog.md). "Today" notes what already
exists, so each item builds on it rather than duplicating it.

## 1. Guidance in the valuation models

Shipped 2026-10-21 together with consensus-in-valuation: `shared/valuation/anchors.py`
(`/api/companies/{t}/valuation-anchors`) feeds a *Guidance & consensus* block in the Assumptions
panel; `shared/valuation/estimate_history.py` snapshots estimates on each daily job run and the
Consensus panel shows the guidance tracking. Remaining: guidance from press releases/transcripts
for names fiscal.ai doesn't tag (e.g. ISRG has no guidance-sourced estimates), and EPS guidance
(the authored model has no EPS line).

- [x] Show management guidance next to the model's near-term assumptions (FY+1 revenue growth,
  margin, capex, share count), and add a *check* when an assumption sits outside the guided
  range.
- [x] Offer "anchor year 1 to guidance" as a one-click lever (the user accepts it; never
  silent), with the guidance cited.
- [x] Track guidance changes across quarters (raised / maintained / cut) and the company's
  record of beating or missing its own guidance. That record is evidence for how much to trust
  the next guide.

Sources: Agentic Consensus marks guidance-sourced estimates (`source: "guidance"`, with
`provenance.guidance` excerpt / filing / page and `beatAdjustment` when fiscal.ai has it);
earnings press releases and call transcripts through the document pipeline for explicit ranges.
Today: guidance only appears as a reminder in `autofit_assumptions.py` ("sanity-check … against
management guidance in the dossier") and in the new Consensus panel; no model input uses it.

## 2. Buybacks in the valuation: authorization and what's left

- [ ] Per company: the current repurchase authorization (amount, date announced, expiry if
  any), spent to date, **remaining**, and remaining as % of market cap and as years of recent
  buyback pace. Flag new or increased authorizations (8-K / earnings release) as events on the
  page and in monitoring.
- [ ] Use it in the model: the forward net-buyback rate (today seeded from the historical
  share-count change in `model_compute.py`) can be set from remaining authorization ÷ years,
  net of SBC dilution, with the source shown. Check: assumed buybacks exceed what is
  authorized plus FCF capacity.

Sources: SEC XBRL `StockRepurchaseProgramAuthorizedAmount1` /
`StockRepurchaseProgramRemainingAuthorizedRepurchaseAmount1` via companyfacts
(`shared/valuation/filing_numbers.py` already fetches it). **Coverage is patchy**: probed
2026-10-21, NFLX tags remaining authorization through 2026-06 ($27.1B), but MSFT's last tag is
2016 and ISRG's 2022. Fallback, needed for most names: extract from the "Issuer Purchases of
Equity Securities" table in every 10-Q/10-K (Part II Item 2 / Item 5), whose last column is
"approximate dollar value that may yet be purchased", via the document pipeline. New
authorizations come from 8-K text.

## 3. Management incentive KPIs in the company profile

- [ ] From the latest proxy (DEF 14A, CD&A): the metrics in the annual bonus and long-term
  (PSU) plans, weights, threshold/target/max levels, performance period, and how last year's
  payout scored. Also flag whether pay is tied to per-share/return metrics (FCF/share, ROIC,
  TSR) or to scale metrics (revenue, adjusted EBITDA, adjusted EPS).
- [ ] Show it in the profile and link each incentive metric to its series where we have it
  (e.g. a revenue-growth target next to reported growth).

Sources: fiscal.ai's filings feed has **no proxy statements** (MSFT/ISRG/ACN indexes hold only
10-K/10-Q/8-K), so DEF 14A comes from SEC EDGAR (submissions API → DEF 14A document; the app
already has `RESEARCH_SEC_USER_AGENT`), then extraction through the document pipeline. Today: the
KPIs & Segments panel shows management-*reported* KPIs mined from filings
(`service.management_kpis`), not compensation-linked ones.

## 4. Management incentives in the valuation — is it possible?

**Yes, as evidence and checks around the model, not as a direct DCF input.** Pay design doesn't
change cash flows mechanically, so putting it into the discount rate or growth would be
arbitrary. It can shape the model in four defensible ways:

- [ ] **Targets as a prior.** Multi-year PSU targets (e.g. a 3-year revenue CAGR or EPS goal)
  are management's own planning numbers. Show them next to the growth/margin path and flag
  when the model is well above what management is paid to hit (or below what it expects to
  beat).
- [ ] **Behaviour flags.** Adjusted-EPS or EPS-growth targets reward buybacks and leverage even
  when value-destroying (feeds item 5); revenue/EBITDA targets reward acquisitions and scale over
  returns; ROIC/FCF-per-share/relative TSR targets align with shareholders. Surface this as a
  scored check on the capital-allocation read, and as a reason to weight scenarios (e.g. more
  weight on the M&A-dilution case).
- [ ] **Dilution.** Equity grants and plan overhang (shares available under the equity plan,
  annual burn rate) set the gross SBC dilution the buyback assumption must offset. That is a
  real model input for the share-count path.
- [ ] **Alignment.** Insider ownership vs. salary and stock-holding requirements, used as a
  qualitative factor in the thesis/scorecard, not as a valuation adjustment.

Depends on item 3 for the data.

## 5. Capital allocation: share-cannibal analysis

Today (`service.capital_allocation`): ROIC vs. WACC, incremental ROIC, buyback spend and % of
FCF, net share-count change and CAGR, and buyback timing (buyback-weighted P/E vs. the stock's
average P/E). Add:

- [ ] **Cannibal profile.** Net and **gross** share-count reduction per year (gross = buybacks
  before SBC issuance), the share of buybacks that only offset SBC, and shares outstanding vs.
  10 years ago. A clear "share cannibal" flag when net reduction is ≥ ~2–3%/yr sustained,
  FCF-funded, at reasonable valuations.
- [ ] **Where the cash went.** For each year and cumulatively: operating cash flow split into
  capex (maintenance vs. growth where D&A allows), acquisitions, buybacks, dividends, and debt
  paydown, as a stacked chart, with buybacks + dividends vs. FCF (payout > 100% = funded from
  elsewhere).
- [ ] **Is debt funding the buybacks?** Net debt issuance vs. buybacks per year, net debt / EBITDA
  trend, and a flag for years where buybacks exceeded FCF while net debt rose.
- [ ] **Are buybacks accretive?** (a) Per-share accretion: EPS and FCF/share growth vs. total
  NI/FCF growth (the gap is what the shrinking count contributed). (b) Price paid: average
  repurchase price (repurchase $ ÷ shares repurchased, from XBRL
  `TreasuryStockSharesAcquired` or the 10-Q table) vs. the model's intrinsic value then and the
  price now. (c) Return on buybacks: IRR of the repurchase cash flows valued at today's price
  (plus forgone dividends) vs. WACC. (d) Earnings-yield test: buyback is accretive when the FCF
  yield paid exceeds the after-tax cost of the cash or debt used.
- [ ] Feed the verdicts into the scorecard and into the valuation's buyback lever (item 2).

Data: standardized cash flow (repurchases, issuance, capex, acquisitions, dividends, debt
issued/repaid, SBC), shares outstanding, prices, and the XBRL/10-Q repurchase table.

## 6. Total return on my holdings, so far

For each current holding (and the book), what it has returned since I bought it, split into
where it came from. Builds on the money layer (Lakebase transactions, lots, `daily_prices`);
the stock-level "from any date" calculator in
[fiscal-ai-endpoint-backlog.md](fiscal-ai-endpoint-backlog.md) is the same math without my
trades.

- [ ] **Per holding, since the first buy** (lot-aware, so adds and trims count from their own
  dates): price change (unrealized + realized on trims), dividends actually received (the
  DIVIDEND / DIVIDEND_REINVEST transactions; reinvested shares counted once), and total. Show it
  three ways: $ gained, simple % on cost, and annualized money-weighted (XIRR over my buys,
  sells and dividends, with the current value as the final inflow, as `perf.money_weighted` does
  per account).
- [ ] **Where the price return came from:** split the price leg over *my* holding period into
  earnings growth, **buyback yield** (the company's share-count change over those dates, net of
  SBC dilution), and multiple re-rating, so the four legs plus dividends add to my total. Buybacks
  aren't cash I receive; they show up inside the price return as per-share growth, which is why
  they're a split of the price leg rather than a separate payment. Reuses the per-stock
  decomposition behind *Return decomposition* / `portfolio/decomposition.py` (today on fixed
  3/5/10y windows, not my dates).
- [ ] **Dividend check:** recorded dividends vs. what the declared DPS (fiscal.ai dividends feed)
  says I should have received for the shares I held on each ex-date, flagging missing or
  mis-recorded payments.
- [ ] **Book view:** the same columns summed across holdings (dollar-weighted), next to the
  account-level TWR / MWR the Performance tracker already shows, plus closed positions so exits
  count.
- [ ] Data notes: currency of each holding vs. the base currency (FX at each flow date, as the
  NAV does); splits via split-adjusted prices and lots.

## 7. Portfolio views by named categories (not just accounts)

Today a portfolio is an aggregation of accounts. Add user-defined **categories** (e.g. "AI
infrastructure", "Compounders", "Turnarounds", "Income") and let a stock belong to **one or
more**, then see the whole money layer through them.

- [ ] **Categories:** create / rename / colour; assign stocks (not positions, so it carries across
  accounts) from the holdings table, the company page and Active Lists. The PMT schema already has
  unused `tags` / `position_tags` / `holding_tags` and portfolio "buckets" tables; reuse or
  migrate them rather than adding a parallel set. Optional **weights** per membership (60% AI
  infra / 40% compounders) for stocks in several.
- [ ] **Category view:** value, weight, cost, and total return so far per category (item 6 rolled
  up), with the holdings in each.
- [ ] **Attribution by category:** extend `portfolio/attribution.py` (Cariño-linked daily
  contributions, today grouped by holding and sector) to group by category. Overlap needs a rule:
  with membership weights the contributions split and still reconcile to the portfolio TWR;
  without weights, each category is shown as its own lens (its contribution if counted alone),
  clearly labelled as not summing to the total.
- [ ] **Risk by category:** volatility, drawdown, beta and correlation of each category's
  sub-portfolio (from `daily_prices` / the NAV series, as `portfolio/metrics.py` does for the
  book), the category's share of total risk, and the correlation matrix between categories, so
  "diversified across themes" can be checked.
- [ ] **Category returns over time:** a chart of each category's TWR as a sleeve, and of its
  weight drift, with target weights if set.
- [ ] A portfolio can then be defined as accounts (as now) **or** as a set of categories, with the
  same Performance / Attribution / Risk pages working on either.