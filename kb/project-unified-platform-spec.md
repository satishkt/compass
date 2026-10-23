# Project document: unified-platform-spec

Source: research_val_personal/docs/unified-platform-spec.md
Kind: design document; may describe planned rather than shipped features.

# Unified Investment Management Platform — Technical Design

Status: **DRAFT v1** (2026-09-03). Money-layer data model resolved from PMT's `~/schema.sql`.
Deferred: risk/return metrics (out of scope for now). Phase-3 research reconciliation still to decide.

Goal: fold the PMT app's portfolio-management + risk/return metrics + look-and-feel into the
Research Cockpit, and unify research + decisioning + portfolio + watchlist + alerts into one
platform. This app is the host; PMT's money layer is rebuilt natively (not a code port) and the
existing Postgres data is migrated in later.

---

## 1. Vision & scope

One platform organized around a **position lifecycle**, with the **ticker as the atom**:

```
Idea → Screen → Research Queue (triage) → Investment Case (deep research + valuation)
     → Decision (buy/size) → Entry Plan (tranches) → Position (held)
     → Monitor (alerts / KPIs / review cadence) → Re-evaluate / Exit → Post-mortem
```

Two objects hang off each ticker:
- **Investment Case** — what I believe and why (research; already the Cockpit's strength).
- **Position** — what I own and how it's doing (money; PMT's strength, rebuilt here).

In scope: real accounts/holdings/transactions/tax-lots/cash/dividends; portfolio P&L + allocation;
risk/return metrics; watchlists + target/upside + alerts; entry-plan ladders; a candidate funnel;
markets strip / ⌘K copilot / privacy mode; and surfacing the Cockpit's document-intelligence +
valuation-engine inside the new shell.

Out of scope (for now): live order execution / broker trading, options/derivatives modeling,
multi-user tenancy (assume single user unless decided otherwise).

---

## 2. Architecture

### 2.1 Hybrid storage (decided)
- **Lakebase (Databricks-managed Postgres)** — the OLTP layer, in **one unified store with NO
  market-data/portfolio separation** (per user directive): portfolio (accounts, positions, lots,
  transactions, cash, dividends), watchlists, entry plans, alerts/notifications, sizing, AND market
  data (`eod_prices`, `fundamentals`, `earnings_events`) together. Frequent small writes; matches the
  PMT source (Postgres); migration ≈ lift-and-shift.
- **Delta / Unity Catalog** (`satish_doc_intelligence_catalog.research_cockpit`) — research +
  document analytics: the existing `investment_case_*`, filing/doc-intelligence, KPI, and valuation
  tables. Append-heavy, analytical, already built.
- **Cross-store link:** the `ticker` (and `investment_case.workspace_id`) is the join key. Databricks
  can federate queries across Lakebase + Delta when a view needs both (e.g. "held positions with
  their thesis conviction").
- Note: PMT currently splits market data into a **separate schema**; we collapse that — one Lakebase
  store holds both. The market-data schema dump is not needed yet (`eod_prices`/`fundamentals` are in
  this dump; anything missing is fetched from fiscal.ai).

### 2.2 App runtime
- FastAPI backend + React/Vite frontend, deployed as a Databricks App on the
  `fevm-satish-doc-intelligence` workspace (see `fevm_doc_intelligence_deployment.md`).
- New backend package `app/backend/portfolio/` (money-layer APIs) talking to Lakebase via a
  connection pool; existing `shared/docs`, `shared/investment_case`, `shared/valuation` unchanged.
- **No always-on background loops** (Databricks Apps forbid long-lived processes). All recurring
  work (quote refresh, metric recompute, alert evaluation, market-pulse scoring, review-due
  sweeps) runs as **scheduled Databricks Jobs**, same pattern as the research pipeline job.

### 2.3 Market data / quotes
- fiscal.ai (already used by both apps) for logos, quotes, fundamentals, ratios, peers.
- A scheduled "quote refresh" job snapshots prices into a Lakebase `price_snapshots` table and a
  `price_history` series (needed for TWR / volatility / beta / max-drawdown and benchmark vs S&P 500).
- ⏳ Open: intraday cadence + whether a second source is needed for the markets strip (SPY/QQQ/…).

---

## 3. Data model

### 3.1 Money layer (Lakebase) — RESOLVED from `~/schema.sql` (PMT public schema)
Adopt PMT's model as-is (it's clean and well-normalized: UUID PKs, `user_id` on every root table,
`created_at/updated_at`, numeric(18,8) qty / numeric(18,2) money, jsonb for flexible config). Bring
these tables 1:1:

**Portfolio core**
- `portfolios` — user_id, name, description, currency, is_active, is_system, is_default,
  `target_allocation` jsonb, `benchmark_tickers` jsonb, `buckets_enabled`.
- `accounts` — portfolio_id (nullable), name, `account_type` enum, broker, account_number, currency,
  cash_balance, margin_enabled, margin_interest_rate, user_id.
- `portfolio_accounts` (M:N), `portfolio_positions` (M:N) — a position can belong to multiple
  portfolios. `portfolio_position_buckets` — per-portfolio thematic bucket_name for a position.
- `positions` — account_id, ticker, exchange, total_quantity, average_cost_basis, realized_pnl,
  current_price(+_at), is_open, sector, industry, currency, is_cash_equivalent, target_weight_pct,
  fiscal_identifier.
- `lots` — position/account/ticker, purchase_date, quantity, remaining_quantity, purchase_price,
  cost_basis_total, `status` enum (OPEN/PARTIAL/CLOSED), closed_at.
- `transactions` — account, ticker, `transaction_type` enum (BUY/SELL/DIVIDEND/DIVIDEND_REINVEST/
  SPLIT/REVERSE_SPLIT/TRANSFER_IN/TRANSFER_OUT/FEE), trade_date, settlement_date, quantity,
  price_per_unit, gross/fees/net, external_id, transfer_id, split_ratio.
- `transaction_lots` — tax-lot matching: transaction↔lot, quantity_sold, cost_basis, realized_pnl,
  `gain_type` (ST/LT), tax_rate, estimated_tax.
- `cash_ledger_entries` — account, entry_type, amount, entry_date, transaction_id, is_auto_generated.
- `dividend_details` — transaction-linked; ex/record/pay dates, gross_per_share, shares_held,
  is_qualified, is_special, source, reconciled.

**Enums:** `accounttype` {BROKERAGE, RETIREMENT, CASH, CRYPTO, RETIREMENT_401K, OTHER};
`transactiontype` (9 values above); `lotstatus` {OPEN, PARTIAL, CLOSED}.

**Watchlists / funnel**
- `watchlist_items` — user_id, ticker, company_name, thesis_id (→research), status, holding_id
  (→position), sources jsonb. `watchlist_themes` + `watchlist_item_themes` (M:N).
- `watchlist_attractiveness` — attractiveness_score, band, component_scores jsonb, quality grade,
  status_pill, ai_blurb (the "market pulse" scoring output).
- `monitor_lists` / `monitor_list_members` — the themed Active Lists.

**Entry plans (ATR ladder)**
- `entry_plans` — ticker, status, entry_price, atr_value/percent/period, volatility_class, stop config
  (enabled/multiple/price/type/trailing), full_position $/shares, bucket, risk_per_share,
  max_dollar_risk, target_price, reward_per_share, r_multiple, breakeven_win_pct, weight_at_full_pct,
  validity_days, activated/completed/expires.
- `entry_plan_steps` — tranches: step_number/type, trigger_price, trigger_atr_offset, pct_of_full,
  shares, dollar_amount, status, triggered/executed actuals.

**Alerts / notifications**
- `alert_types` — attribute, operator, threshold_value, time_window_days, is_system/is_active.
- `alert_assignments` — alert_type→scope (list|ticker) with a CHECK constraint; threshold_override.
- `alert_evaluation_states`, `notifications` (severity, deep_link, metadata jsonb, read/dismiss/snooze,
  email batching), `notification_preferences`, `notification_settings`.

**Sizing framework**
- `sizing_profiles` — weight_mos/conviction/risk, max_single_position, min_position, max_sector,
  max_correlated, cash_target, max_positions, risk caps, `mos_curve` jsonb, `conviction_config` jsonb.
- `sizing_results` — computed target sizes per position.

**Market data (folded into the same store)**
- `eod_prices` — ticker, exchange, date, OHLC, adjusted_close, volume (historical series to migrate if
  present, else backfill from fiscal.ai). `fundamentals`, `earnings_events` likewise.

Tags/misc: `tags`, `holding_tags`, `position_tags`, `position_reminders`, `position_downsides`.

### 3.2 Research layer (Delta) — EXISTS
`investment_case_*` (thesis, claims, evidence, assumptions, risks, valuations, scenarios, watch
items, monitoring, decisions, governance, knowledge), filing/doc-intelligence tables, KPI tables.
No change; new fields added only to fold in PMT's per-name Hub (§3.3).

### 3.3 Folding PMT's Hub into the Investment Case
Add to the case (Delta) rather than duplicating: `conviction` (x/10), `margin_of_safety`,
`fitness_score` + `fitness_bucket` (Core Compounders / Emerging / Moonshots), `quality_score`
(the 34-check framework), and an `insider_activity` view. The Cockpit already has thesis, valuation,
claims, decision journal, governance — those absorb PMT's Hub equivalents.

### 3.4 PMT also has a full research/decisioning layer — reconcile in Phase 3 (NOT Phase 1)
The dump revealed PMT is more than a PMS. Its `public` schema also holds a research/decisioning
model that overlaps the Cockpit's Investment Case, and a separate `research.*` schema mirrors the
Cockpit's document pipeline:
- Thesis/decisioning: `theses`, `thesis_versions`, `thesis_holding_links`, `thesis_attachments`,
  `journal_entries`, `fitness_evaluations(+_history)`, `quality_scores`, `quality_check_definitions`,
  `quality_check_results`, `valuation_decompositions`, `valuation_scenarios`, `position_downsides`,
  `management_assessments`, `ticker_deep_dives`, `research_reports`/`report_sections`/`annotations`,
  `research_sessions`, `research_flow_progress`, `ontologies`/`ontology_nodes`, `custom_kpis`,
  `pinned_kpis`, `metric_insights`, `industry_benchmarks`, `competitor_sets`/`competitor_entries`.
- Doc intelligence (`research.*`): `document`, `document_section`, `extraction_run`, `kpi_definition`,
  `kpi_observation`, `thesis_review`, `job_queue`, `confirm_queue`, `audit_log`, `dead_letter`.

**Decision needed (Phase 3):** treat the Cockpit's `investment_case_*` as the canonical research
model and MAP PMT's research rows into it, vs. migrate PMT's research tables alongside. Recommendation:
canonical = Cockpit Investment Case (deeper primary-source pipeline); PMT's thesis/journal/fitness/
quality/conviction become fields/rows on the case, linked to positions via `thesis_holding_links` →
`positions`. Not in Phase 1 — the near-term focus is the money layer + look/feel.

---

## 4. API surface (new, money layer)
`/api/accounts`, `/api/portfolios/*` (holdings, transactions, tax-lots, dividends, cash, allocation,
metrics, attribution), `/api/watchlists/*`, `/api/entry-plans/*`, `/api/alerts/*`, `/api/quotes/*`,
`/api/import/csv`. Existing research/doc/case/valuation APIs unchanged; a few composed read
endpoints join Lakebase + Delta (e.g. `/api/positions/{ticker}` returns holding + case summary).

---

## 5. Frontend — IA, components, look & feel
Adopt PMT's shell: uppercase top nav, markets ticker strip, radial "scanning" loader, privacy-mode
toggle, ⌘K copilot (powered by the existing chat backend), notifications, "data as of" stamp.
Design tokens: airy card layout, uppercase letter-spaced micro-labels, green/red P&L, muted slate
palette; keep self-hosted DM Sans (use it for display-number treatment rather than PMT's serif —
TBD with user).

Navigation (unified): **Overview · Portfolios · Positions/Hub · Research · Watchlists · Research
Queue · Documents · Decisions · Platform.** Per-name Hub = the Investment Case rendered in PMT's
card layout, with the Cockpit's document/valuation depth behind "Deep Dive".

---

## 6. Background jobs (scheduled, not in-app)
- `quote_refresh` — pull fiscal.ai quotes → `positions.current_price` + `eod_prices` (for current
  valuation; history also backfills here).
- `alert_eval` — evaluate `alert_types`/`alert_assignments` → `alert_evaluation_states` →
  `notifications`.
- `market_pulse` — candidate scoring → `watchlist_attractiveness`.
- `review_sweep` — flag positions overdue for re-evaluation (`position_reminders`).
- ~~`metrics_recompute` (Sharpe/Sortino/TWR/vol/beta/max-DD)~~ — **OUT OF SCOPE for now** per user;
  revisit once `eod_prices` history + a benchmark series are in place.
Wire like the existing pipeline job (job JSON in `databricks/`, params, serverless env threaded via
`--catalog/--schema/--warehouse` pattern already established).

---

## 7. Migration plan (PMT Postgres → Lakebase)
1. Stand up a Lakebase instance + one unified schema on the fevm workspace; create the money-layer
   tables + enums from §3.1 (DDL adapted from `~/schema.sql`; drop `neon_auth.*`).
2. **Phase 1 tables to migrate first:** portfolios, accounts, portfolio_accounts, positions,
   portfolio_positions, portfolio_position_buckets, lots, transactions, transaction_lots,
   cash_ledger_entries, dividend_details, tags/holding_tags/position_tags, eod_prices (if present).
3. One-time load: `pg_dump --data-only` from PMT → load into Lakebase (both Postgres → minimal
   transform; keep UUIDs so FKs survive). Validate row counts + total market value / realized +
   unrealized P&L against the live PMT Overview ($3.29M value, +$1.72M unrealized at review time).
4. Phase 3: migrate/ map the research/decisioning tables (§3.4) into the Cockpit's Investment Case;
   link `thesis_holding_links` → positions; reconcile tickers to existing case workspaces by symbol.
5. Market-data history: migrate `eod_prices` if populated; otherwise backfill from fiscal.ai.
   (Metrics that consume it are out of scope for now.)
6. Decide cutover vs dual-run; if dual-run, logical replication or periodic re-sync until PMT retires.

---

## 8. Phased roadmap
- **Phase 0 — Shell/design system:** PMT nav IA, markets strip, loader, privacy mode, ⌘K. No new data.
- **Phase 1 — Real-money core:** Lakebase tables + accounts/holdings/transactions + CSV import +
  portfolio Overview (value, P&L, allocation, accounts, holdings table).
- **Phase 2 — Analytics:** tax lots (ST/LT + est. tax), dividends, cash, allocation views, sizing
  framework. (Risk & Return metrics — Sharpe/TWR/beta/etc. — deferred, out of scope for now.)
- **Phase 3 — Unify research:** reconcile PMT's research/decisioning layer (§3.4) into the Cockpit's
  Investment Case (conviction/MoS/fitness/quality/insider); merge Active Lists + Research Queue +
  Review Queue into one Watchlist → Queue → Position funnel.
- **Phase 4 — Close the loop:** entry-plan ladders wired to decisions; alerts + market-pulse;
  review-due → notifications; ⌘K copilot across portfolio + research.

---

## 9. Open questions
- **Multi-user vs single-user.** PMT's schema has `user_id` on every root table (multi-tenant). Keep
  it (future-proof, migrate as-is) or collapse to single-user? Recommendation: keep the column,
  default to one user — zero cost now, no rework later.
- **Research reconciliation (Phase 3):** canonical = Cockpit Investment Case with PMT research mapped
  in (recommended), vs. migrate PMT's research tables wholesale. See §3.4.
- Intraday price cadence + markets-strip source (fiscal.ai vs other).
- Alert delivery channel — in-app notifications only, or also email (schema has email batching)/Slack?
- DM Sans display treatment vs importing PMT's serif for display numerals.
- Lakebase instance sizing; whether to mirror a few money tables into Delta for cross-analytics.
- Risk/return metrics deferred — confirm when to bring back (needs `eod_prices` history + benchmark).