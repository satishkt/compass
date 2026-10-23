# Project document: phase1-build-plan

Source: research_val_personal/docs/phase1-build-plan.md
Kind: design document; may describe planned rather than shipped features.

# Phase 1 — Real-Money Core (build plan)

Status: **DRAFT** (2026-09-03). Companion to `unified-platform-spec.md`. Decisions baked in:
single-user (no `user_id`), Lakebase Postgres for the money layer, Cockpit Investment Case stays the
canonical research model (research reconciliation is Phase 3, not here).

## Goal / exit criteria
A logged-in user opens the Cockpit and sees a **Portfolio Overview** driven by real data migrated
from PMT: total value, unrealized/realized P&L, holdings table (per-position price/qty/value/P&L),
asset allocation, and the accounts list — plus the ability to **import holdings/transactions via
CSV**. Numbers reconcile to PMT's live Overview (≈$3.29M value, +$1.72M unrealized at review time).

Explicitly **not** in Phase 1: risk/return metrics, entry plans, alerts, watchlist funnel, research
mapping, the full PMT look-and-feel shell (that's Phase 0/2/3).

## Progress
- ✅ Step 1 — Lakebase provisioned: `projects/pmt` / production / primary (ACTIVE), db `pmt`,
  host `ep-young-pond-d80g7f6r.database.us-east-2.cloud.databricks.com`. See `lakebase_pmt_instance.md`.
- ✅ Step 2 — Phase-1 DDL applied (15 tables, user_id stripped) → `databricks/lakebase_pmt_phase1.sql`.
- ⏳ Step 6 (migration) — needs a `--data-only` export from PMT (below).
- ⏳ Step 5 (CSV import) — needs PMT's CSV format sample.
- ⏳ Steps 3/7 (backend + Overview UI) — buildable next; best after data is migrated.

## Step 1 — Provision Lakebase
- Use the `databricks-lakebase` skill to create a Lakebase (managed Postgres) instance on the
  `fevm-satish-doc-intelligence` workspace, one database (e.g. `pmt`) + one schema (e.g. `app`).
- **Billable infra — get explicit go-ahead before creating.**
- App auth to Lakebase: connect as the app's service principal (`0648ab52-…`) via OAuth token; store
- Add a connection-pool module; Databricks Apps are multi-worker, so pool per worker.

## Step 2 — Money-layer DDL (single-user)
Create from `~/schema.sql`, dropping `user_id` columns + `neon_auth.*`. Phase 1 tables:
`portfolios`, `accounts` (enum `accounttype`), `portfolio_accounts`, `positions`,
`portfolio_positions`, `portfolio_position_buckets`, `lots` (enum `lotstatus`), `transactions`
(enum `transactiontype`), `transaction_lots`, `cash_ledger_entries`, `dividend_details`,
`tags`/`holding_tags`/`position_tags`, `eod_prices`. Keep UUID PKs, numeric precision, timestamps.
(Watchlists, entry plans, alerts, sizing deferred to later phases but same store.)

## Step 3 — Backend package `app/backend/portfolio/`
- `db.py` — Lakebase connection pool (psycopg or SQLAlchemy Core).
- `models.py` / `repo.py` — typed rows + queries for the Phase-1 tables.
- `service.py` — derive holdings view: join positions + latest price → market value, unrealized P&L,
  weights; portfolio rollups (total value, realized/unrealized P&L, allocation by holding/sector).
- `api.py` — FastAPI router mounted in `app/backend/main.py`.
- Existing Delta/`shared.*` code untouched; this is additive.

## Step 4 — Pricing
- Reuse fiscal.ai (already wired) for current quotes. Phase 1: a `quote_refresh` step updates
  `positions.current_price(+_at)`; can run on-demand (Overview "Refresh") and/or as a scheduled job
  later. `eod_prices` history migrated if present, else backfilled later.
- **Dependency:** confirm the fiscal.ai quote endpoint/fields to use for live price.

## Step 5 — CSV import
- Endpoint `POST /api/import/csv` (+ account picker): parse holdings/transactions, upsert accounts,
  positions, lots, transactions; recompute cash from `cash_ledger_entries`.
- **Dependency:** PMT's CSV column format (the "Upload CSV / bulk import" it already supports) so the
  parser matches. Please share a sample CSV.

## Step 6 — Data migration (PMT → Lakebase)
1. `pg_dump --data-only --table=public.<phase1 tables>` from PMT.
2. Transform: drop `user_id` columns; keep UUIDs so FKs survive; skip `neon_auth.*`.
3. Load into Lakebase; run in FK order (portfolios → accounts → positions → lots → transactions →
   transaction_lots → cash/dividends → join tables).
4. **Validate:** total market value, unrealized + realized P&L, position count, account count vs PMT.

## Step 7 — Frontend: Portfolio Overview
- New route/page rendered in the current Cockpit shell (full PMT design shell is Phase 0, optional
  first). Reuse this app's chart lib (`app/frontend/src/lib/charts.jsx`) + `format.js`.
- Sections: total value + unrealized/realized P&L cards; holdings table (logo/ticker/price/qty/mkt
  value/P&L, fiscal.ai logos as PMT does); asset-allocation (by holding/sector); accounts list.
- API: `GET /api/portfolios`, `/api/portfolios/{id}` (rollup), `/api/portfolios/{id}/holdings`,
  `/api/accounts`.

## New API surface (Phase 1)
`GET /api/portfolios`, `GET /api/portfolios/{id}`, `GET /api/portfolios/{id}/holdings`,
`GET /api/portfolios/{id}/allocation`, `GET /api/accounts`, `GET /api/accounts/{id}/transactions`,
`POST /api/import/csv`, `POST /api/portfolios/{id}/refresh-prices`.

## Sequencing
1. Go-ahead to provision Lakebase (cost). → 2. Instance + DDL. → 3. Migration + validation (proves
   data is right before any UI). → 4. Backend package + read APIs. → 5. Overview UI. → 6. CSV import.
Migration-first means the Overview renders real numbers on day one.

## Open dependencies from you
- Go-ahead to create the (billable) Lakebase instance.
- PMT CSV import format (sample file).
- fiscal.ai quote endpoint/fields for live price.
- Confirm: do Phase 1 UI now in the current shell, or do Phase 0 (PMT shell) first?