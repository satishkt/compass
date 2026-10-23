# Project document: valuation-deep-dive-spec

Source: research_val_personal/docs/valuation-deep-dive-spec.md
Kind: design document; may describe planned rather than shipped features.

# Valuation Deep Dive — Requirements & Spec

Status: **DRAFT for build sign-off** (2026-09-24). Companion to `reading-room-spec.md`,
`research-journey-design.md`, `dossier-ux-backlog.md`.

Origin: the valuation surface today is a single card on the dossier (fair value, upside, WACC,
football field, reverse-DCF one-liner). The engine underneath computes far more than the UI shows.
This feature adds a dedicated **Valuation deep dive** — one method per section, prepopulated from the
model, each with its own levers and a live recompute — mirroring how the financials **Deep Dive**
(`/c/:ticker/deep`) works for ratios.

**Core insight from the codebase audit:** most of the requested methods already have compute; they're
just not surfaced in the app. This is mostly a *surface-and-deepen* job plus **one genuinely new
engine (Monte Carlo)** and a **detailed multi-driver reverse DCF**. See §3.

---

## 1. Locked decisions (from sign-off)

1. **Placement:** a new dedicated page at **`/c/:ticker/valuation`**, a sibling nav tab to Deep Dive,
   with its own `SectionRail` + Dossier/Focus reading modes. The dossier's existing Valuation card
   stays as the *summary*; this page is the *workbench*.
2. **Interactivity:** every method **auto-populates** from the saved model **and** exposes its own
   per-method levers with a **live recompute** (like the assumptions dial, scoped per method). Edits
   are **what-if only** (session-local) unless explicitly saved back to the model.
3. **Monte Carlo inputs:** parameter spreads are **auto-seeded from each company's own history**
   (revenue-growth stdev, margin range) plus sensible bands for WACC / terminal growth / exit
   multiple, and are **user-adjustable** per driver.
4. **Monte Carlo "test":** a **price-vs-FV-distribution** read — P(undervalued), the percentile
   today's price sits at in the simulated FV distribution, and margin-of-safety at a chosen
   confidence (e.g. FV at the 25th percentile). The actionable "is it cheap once uncertainty is
   priced in?" test.

---

## 2. Sections (page outline)

Rail groups, in journey order (Value phase). Each is a `Section` with per-section reasoning ("My
read" + reviewed tick), exactly like Deep Dive.

| # | Section id | Title | New vs reuse |
|---|-----------|-------|--------------|
| S0 | `vdd-field` | **Reconciled football field** | reuse + extend (add EPV/OE/MC legs) |
| S1 | `vdd-dcf` | **Standard DCF** (Gordon + exit) | reuse (surface existing) |
| S2 | `vdd-sbc` | **DCF: SBC charged vs added back** | reuse existing dual-FCF + new dilution pairing |
| S3 | `vdd-owner` | **Owner earnings (Buffett)** | promote module → live |
| S4 | `vdd-epv` | **Earnings Power Value (Greenwald)** | promote module → live |
| S5 | `vdd-reverse` | **Detailed reverse DCF** | extend existing solver |
| S6 | `vdd-montecarlo` | **Monte Carlo + price test** | **NEW** |

S0 sits at the top as the reconciliation of everything below. Sections open by default in Dossier
mode; Focus mode pages through one at a time (`←/→`).

---

## 3. What already exists (reuse inventory)

Verified against the codebase 2026-09-24. Cite these so the build reuses, not rebuilds.

### Compute — `shared/report/model_compute.py`
- **`compute(data, A)`** is the engine. Emits (per share unless noted): `per_share` (DCF Gordon),
  `per_share_exit` (DCF exit multiple), `comps` implied px, `prob_fv` (probability-weighted
  scenarios), `bull`/`bear`/`worst`, `expected_return`, `reverse_cagr`, sensitivity grids
  (`wg_grid` WACC×g, `cm_grid` CAGR×margin, `irisk`), and `football_field`.
- **Dual FCF view already computed** (the SBC fork): `reported_style` (NOPAT + D&A − capex − NWC,
  **SBC not charged**), `owner_earnings` (NOPAT + D&A − capex − **SBC**, NWC not charged),
  `discounted` (both NWC **and** SBC charged — what the DCF actually discounts).
- **`wacc_breakdown(A)`** → auditable CAPM block (rf, β, ERP → Ke; Kd; weights; WACC) with per-input
  **source tags** (`global`/`damodaran`/`auto-draft`/`model`). Already surfaced by `WaccExplainer.jsx`.
- **`implied_growth(...)`** — reverse-DCF bisection solving the 10y revenue CAGR that justifies a
  price; `_annuity_px(...)` is the cheap closed-form px used by scenarios + grids (reuse for MC).
- Scenario weighting: `prob_fv = Σ share_px · prob` over bull/base/bear/worst.

### Standalone method modules — `shared/valuation/` (computed for the PDF, **not surfaced in the app**)
- **`epv.py::earnings_power_value(normalized_ebit, tax_rate, wacc, shares_out, excess_cash=,
  total_debt=, other_claims=, maintenance_capex_addback=)`** → `EPVResult{epv_operations,
  epv_equity, per_share}`.
- **`owner_earnings.py::owner_earnings(net_income, depreciation_amortization, maintenance_capex,
  incremental_working_capital=, other_non_cash=)`** and **`intrinsic_value(base_owner_earnings,
  discount_rate, shares_out, stage1_growth, stage1_years, terminal_growth, net_cash=, mid_year=)`**
  → `IntrinsicResult{intrinsic_equity, per_share, pv_stage1, pv_terminal}`.
- **`engine.py`** helpers: `grow`, `present_value`, `terminal_value_gordon`. Reuse for all discounting.
- `relative.py` (comps/precedent framework), `dcf.py`, `inputs.py` (normalized-data loader),
  `summary.py`.

### Recompute paths
- **Legacy / dossier what-if:** `POST /api/companies/{ticker}/recompute` (`main.py:217`) →
  `service` recomputes `compute(data, A_overridden)`; result cached on the assumptions-file mtime.
  **This page builds on this path.**
- Case-based (separate): `POST /api/investment-case/{ticker}/valuation/compute` — not used here.

### UI to reuse (`app/frontend/src/`)
- `pages/DeepDive.jsx` — the section-array + `useSectionRail()` + `useCollapse({modeKey, sectionState,
  onSaveSection, reasoningExclude})` pattern. **Copy this scaffold.**
- `lib/Section.jsx` — `Section`, `SectionRail`, reasoning primitive via `coll.props(id)`.
- `lib/AssumptionsPanel.jsx` — slider / path-editor primitives for the per-method levers.
- `lib/charts.jsx` — `FootballField` (SVG), recharts `RevenueChart`/`MarginChart`/`Sparkline`;
  hand-rolled SVG patterns in `ReturnDecomposition.jsx` (waterfall) and `CapitalAllocation.jsx`
  (bars + line) to copy for the **distribution histogram** and **variance tornado**.
- `lib/WaccExplainer.jsx`, `lib/ValuationHistory.jsx` — mount as-is where relevant.

---

## 4. Data availability & required derivations

From the normalized statements (`companies/<T>/data/normalized/*.csv`), ~20y annual history, plus
`ratios.json`, `shares_outstanding.json`, `adjusted_metrics.json`.

**Available directly:** revenue, operating profit (EBIT), net income, pre-tax income, D&A, total
capex, **SBC ($ and /rev)**, OCF, granular working-capital items, diluted-share series, total
equity/book value, cash, debt, effective tax rate, ROIC (`ratios.json`), all margins.

**Gaps → new derivations (build these once, reuse across methods):**

| Need | Gap | Derivation (default) | Where |
|------|-----|----------------------|-------|
| **Maintenance capex** | no maint/growth split | `maint = min(D&A, trailing-5y-avg capex)`; lever = "maintenance capex % of revenue" (default from that) | `shared/valuation/derivations.py` (new) |
| **Normalized EBIT** (EPV) | one-offs, cyclicality | median of (operating-margin over N yrs) × latest revenue; prefer `adjusted_metrics.json` adjusted EBIT if present | same |
| **SBC / share** | not precomputed | `sbc$ / diluted_shares`, per year | same |
| **Incremental working capital** (OE) | annual only (no qtrly BS) | Δ(AR+inv−AP) year-over-year; annual only | same |
| **WACC** | not in fiscal.ai | already computed in-app via `wacc_breakdown` — reuse, never re-derive | existing |
| **Discount rate** (OE) | n/a | = model WACC (decision §10.2; opportunity-cost hurdle deferred to C11) | existing |
| **Historical driver volatility** (MC) | n/a | stdev of YoY revenue growth; min/max operating margin; band defaults for WACC/terminal/exit | `shared/valuation/monte_carlo.py` (new) |

**Documented limitations (state in-UI, not silently):**
- Owner-earnings & EPV are **annual-only** (no quarterly balance sheet).
- Maintenance capex is an **estimate** (proxy), always labeled and overridable.
- Cost of debt is assumed (existing CAPM default), tagged in the WACC explainer.

---

## 5. Backend architecture

### 5.1 New module `shared/valuation/derivations.py`
Pure functions over the normalized `CompanyData`, each returning a per-year series + a "current"
scalar and a `source`/`method` label:
- `maintenance_capex(data, *, pct_rev=None) -> {series, current, method}`
- `normalized_ebit(data, *, years=8, use_adjusted=True) -> {value, margin, method}`
- `sbc_per_share(data) -> {series}`
- `incremental_working_capital(data) -> {series, current}`
- `net_cash(data) -> float`, `excess_cash(data) -> float`, `total_debt(data) -> float`
No API of its own; consumed by the orchestrator and MC.

### 5.2 Orchestrator `service.valuation_deepdive(folder, freq="annual", overrides=None)`
Returns a single payload the page renders. Composes existing `compute()` output with the promoted
EPV/owner-earnings and the new reverse-DCF grid. Cached on assumptions mtime like the current
valuation summary. Shape:

```jsonc
{
  "ticker": "MSFT",
  "as_of": "…",
  "shares_mm": 7430, "price": 420.1, "net_cash_mm": …, "currency": "USD",
  "wacc": { …wacc_breakdown… },
  "methods": {
    "dcf":    { "gordon_ps": …, "exit_ps": …, "assumptions": {…}, "levers": {…} },
    "sbc":    { "charged_ps": …, "addback_ps": …, "addback_diluted_ps": …,
                "sbc_cost_ps": …, "sbc_pct_rev": … },
    "owner":  { "base_oe_mm": …, "per_share": …, "pv_stage1": …, "pv_terminal": …,
                "maint_capex_mm": …, "maint_method": "min(D&A, 5y avg capex)",
                "required_return": 0.09, "levers": {…} },
    "epv":    { "normalized_ebit_mm": …, "epv_operations_mm": …, "epv_equity_mm": …,
                "per_share": …, "growth_value_ps": …/* DCF − EPV */, "levers": {…} },
    "reverse":{ "implied_cagr": …, "implied_cagr_live": …, "hist_rev_cagr": …,
                "grid": [[…]], "solve_axes": {…} }
  },
  "football_field": [ { "label": "DCF (Gordon)", "lo":…, "mid":…, "hi":… }, … ],
  "price_marker": 420.1
}
```

### 5.3 Per-method recompute
Extend the existing `POST /api/companies/{ticker}/recompute` OR add
`POST /api/companies/{ticker}/valuation-deepdive/recompute` taking `{method, levers}` and returning
just that method's recomputed block (fast; no full-model round trip where avoidable). Decision:
**add the dedicated route** so per-method levers don't churn the whole model. Levers are validated &
clamped server-side (reuse the clamp ranges in `autofit_assumptions.py`).

### 5.4 Monte Carlo `shared/valuation/monte_carlo.py`
- `default_ranges(data, A) -> {driver: {dist, p10/mode/p90 or mean/sd, source}}` for the five
  drivers: **revenue CAGR, operating margin, terminal growth, WACC, exit EV/EBITDA**.
  - revenue CAGR: mean = model near-term CAGR; sd = stdev of historical YoY growth (floored).
  - operating margin: triangular over historical [min, median/current, max].
  - terminal growth: normal, tight band around model (e.g. ±0.5pp), clamped < WACC.
  - WACC: normal around model WACC (±0.75pp), from beta/ERP uncertainty.
  - exit multiple: triangular around model exit, bounded by industry (Damodaran) range.
- `simulate(data, A, ranges, n=10000, seed=None, correlation=None) -> {samples_fv, stats}` — draws
  per trial, prices each via the **cheap `_annuity_px`** (same closed form scenarios use → 10k trials
  is <100ms), returns the FV-per-share array + summary. Default drivers **independent**; optional
  growth↔margin correlation (ρ, off by default, note the assumption).
- **The price test** (`test_vs_price(samples_fv, price, confidence=0.75)`):
  - `p_undervalued` = P(FV > price)
  - `price_percentile` = percentile of `price` within the FV distribution
  - `mos_at_conf` = (FV at the (1−confidence) percentile − price) / price  → margin of safety
  - percentiles P5/P25/P50/P75/P95, mean, sd.
- **Variance contribution** (robustness bonus, cheap): first-order sensitivity of FV variance to each
  driver (freeze others at mode, sweep one across its range) → a Monte-Carlo tornado.
- API: `POST /api/companies/{ticker}/monte-carlo` `{ranges?, n?, seed?, confidence?}` → distribution
  bins (server-binned for the histogram) + stats + tornado. `GET` variant returns `default_ranges`.
- Determinism: accept a `seed` so a shared read reproduces; default random.

---

## 6. Frontend architecture

- **Route:** add `/c/:ticker/valuation` → `pages/ValuationDeepDive.jsx` in `App.jsx`; add the
  **Valuation** tab to the company sub-nav (next to Deep dive).
- **Scaffold:** copy `DeepDive.jsx` — `sections` array (§2 ids), `useSectionRail()`, `useCollapse({
  modeKey: "valuationMode", sectionState, onSaveSection: persistSection })`, Dossier/Focus toggle.
  Frequency toggle **not** needed (valuation is annual); the rail `extra` slot instead holds a
  **"vs price" pill** (shared price marker) and a **what-if dirty/reset** control.
- **Data:** fetch `getValuationDeepdive(ticker)` on mount; Monte Carlo fetched lazily when S6 opens
  (heavier). Per-method lever changes → debounced `recomputeMethod(ticker, method, levers)` → patch
  that section's block in local state; a global **"what-if active — reset / save to model"** banner
  when any lever is dirty (mirrors the dossier dial).
- **Per-method levers:** reuse `AssumptionsPanel`'s `Slider`/`PathEditor`. Each method section renders
  a compact lever strip (collapsed by default under a "Assumptions" disclosure) + the result.
- **Charts:** reuse `FootballField` (S0); new hand-rolled SVG **histogram + CDF** and **tornado** for
  S6 (copy the `CapitalAllocation`/`ReturnDecomposition` SVG idiom + `lib/palette.js`); small
  waterfall for owner-earnings PV bridge (reuse the ReturnDecomposition waterfall).
- **Reasoning:** every section gets "My read" + reviewed via `coll.props(id)`; excluded: none.

---

## 7. Per-section requirements

Each section: **auto-populated** result up top, **levers** under a disclosure, a **chart**, an
honest **caveat line**, and reasoning footer. All levers are what-if unless saved.

### S0 — Reconciled football field
- **What:** one horizontal chart with a leg per method (DCF Gordon, DCF exit, Comps, Scenarios
  prob-wtd, Owner earnings, EPV, and MC P25–P75 band), a **price marker**, and the **prob-weighted
  FV** dot. A table below lists each method's per-share value, its Δ vs price, and a one-line "what it
  assumes."
- **Reuse:** extend `football_field` assembly in `model_compute.py` to append EPV, owner-earnings,
  and (when computed) an MC band leg. Keep the existing axis-guard so a wild leg doesn't blow the axis
  (as done for the industry-PE leg).
- **Acceptance:** legs match the individual sections exactly; price marker + prob-FV dot present;
  a method with no data drops its leg (no crash).

### S1 — Standard DCF (Gordon + exit)
- **Auto:** `gordon_ps`, `exit_ps`, the two terminal values, implied terminal multiple, PV split
  (explicit vs terminal). **Levers:** WACC inputs (rf/β/ERP via the CAPM block), terminal growth,
  exit EV/EBITDA, the 10y growth & margin paths (`PathEditor`). **Chart:** PV-by-year bars + terminal
  wedge. **Caveat:** terminal value share of PV flagged when > ~75%.
- **Acceptance:** matches the dossier's current DCF numbers at base assumptions; live recompute on
  lever change; WaccExplainer reflects edited CAPM.

### S2 — DCF: SBC charged vs added back
- **What:** two DCFs side by side — **(A) SBC charged** (treat SBC as the real cash cost it is — the
  current `discounted` path) and **(B) SBC added back** (`reported_style`), **but B must also carry
  the dilution** SBC causes (share growth), so it's apples-to-apples. Headline = **"cost of SBC per
  share" = A − B_diluted**, plus SBC/revenue and SBC/OCF context (from `earnings_quality`).
- **Why:** the naive "exclude SBC" overstates value by ignoring dilution; pairing add-back with
  dilution makes the SBC cost explicit rather than hidden.
- **Levers:** SBC % of revenue (fade), assumed dilution (default from historical net-buyback/SBC).
- **Acceptance:** A equals S1's discounted FV; B_diluted ≤ A when SBC > 0; the SBC-cost figure ties to
  A − B_diluted; both legs appear on S0.

### S3 — Owner earnings (Buffett)
- **Auto:** base owner earnings = `owner_earnings(NI, D&A, maintenance_capex, incremental_WC)`, then
  `intrinsic_value(...)` two-stage. **Discount rate = model WACC** (decision §10.2; no separate
  opportunity-cost hurdle for now). **Levers:** maintenance-capex % (default `min(D&A, 5y-avg capex)`,
  clearly labeled as an estimate), stage-1 growth & years, terminal growth. **Chart:** PV(stage-1) +
  PV(terminal) + net cash waterfall → equity → /share.
- **Caveat:** "Maintenance capex is estimated (proxy); adjust if you have disclosure." Annual-only.
- **Acceptance:** uses `shared/valuation/owner_earnings.py` unchanged; recompute on levers; net cash
  from balance sheet; per-share reconciles to the waterfall.

### S4 — Earnings Power Value (Greenwald)
- **Auto:** `normalized_ebit` (median-margin × revenue, or adjusted EBIT) → `earnings_power_value(
  normalized_ebit, tax, wacc, shares, excess_cash, total_debt, maintenance_capex_addback)`. Show
  **EPV/share vs DCF/share**, and label the gap **"value of growth"** (DCF − EPV) — the market's
  growth assumption you judge against moat durability. **Levers:** normalization window (N years),
  required return (WACC default), maintenance-capex add-back toggle.
- **Chart:** a simple bar stack — EPV (no-growth) + growth value = DCF, with the current price marker.
- **Acceptance:** uses `shared/valuation/epv.py` unchanged; growth-value = S1 Gordon − EPV; excess
  cash/debt from balance sheet; EPV independent of growth-path levers (zero-growth by construction).

### S5 — Detailed reverse DCF
- **What:** beyond the current single implied-CAGR number — a **2-D solve grid**: for a range of
  **terminal operating margins** (rows) × **exit multiples** (cols), the implied revenue CAGR that
  justifies **today's price**; the cell matching the model's assumptions is highlighted, and each cell
  is shaded vs the company's **historical achievable CAGR** (green = market implies less than history
  delivered = conservative; red = implies more = demanding). Plus the existing at-model vs at-live
  implied CAGR, and the historical revenue/FCF CAGR benchmarks.
- **Reuse/extend:** call `implied_growth(...)` across the grid axes (cheap). **Levers:** the axis
  ranges, steady-state margin, and which price to solve to (live vs model vs a user price).
- **Acceptance:** center cell equals the current `reverse_cagr`; shading references `hist_rev_cagr`;
  "no solution" cells (price outside bracket) render as n/m, not errors.

### S6 — Monte Carlo + price test  (NEW)
- **Auto:** on open, fetch `default_ranges` and run `simulate(n=10000)`. Show the **FV-per-share
  histogram** with P5/P25/P50/P75/P95 markers and the **current price line**, plus the **test panel**:
  - **P(undervalued)** = P(FV > price), as a big stat.
  - **Price percentile** — "today's price sits at the Nth percentile of simulated fair value."
  - **Margin of safety at 75% confidence** — FV at the 25th percentile vs price.
  - A one-line verdict ("price is cheap in ~72% of simulated outcomes; MoS +14% at P25").
- **Levers:** per-driver range editors (mean/mode + spread) seeded from history, a **trials** control
  (1k–50k), a **confidence** selector, an optional **growth↔margin correlation** ρ, and a **seed**
  for reproducibility. A **variance tornado** shows which driver drives the FV spread.
- **Perf:** server-side, `_annuity_px` per trial; server bins the histogram; target < 300ms at 10k.
- **Caveat:** "Distributions are seeded from this company's own history and your ranges — not a claim
  about true probabilities." Independent-driver assumption stated unless ρ set.
- **Acceptance:** median FV ≈ the deterministic base FV when ranges are tight; P(undervalued) moves
  correctly as price/ranges change; reproducible with a fixed seed; tornado ranks drivers by variance
  contribution.

---

## 8. Cross-cutting requirements
- **WACC / required-return provenance:** every method shows which discount rate it used and its source
  chips (reuse `WaccExplainer`); owner-earnings may use a required return ≠ WACC and must say so.
- **Per-share bridge & units:** one shared enterprise→equity→per-share bridge (net cash, shares from
  the model), consistent across methods; `units_note` from the assumptions file respected; non-USD
  reporting currencies handled as the model already does.
- **What-if isolation:** per-method levers never mutate the saved model; a global dirty banner offers
  **Reset** and **Save to model** (the latter writes the assumptions file via the existing save path
  and triggers the volume push).
- **Caching:** base payload cached on assumptions-file mtime (reuse `_compute_valuation_summary`
  pattern); MC never cached (seed-dependent) but cheap.
- **Empty/again states:** a name with `has_model=false` shows a "no model yet — run research or draft
  a quicklook" panel, not a broken page (mirror the dossier).
- **Reasoning roll-up:** per-section "My read" persists via the existing `section-state` store and
  should be retrievable for the Thesis/Scorecard roll-up (same as dossier sections).

## 9. Phasing
- **P1 — Surface the existing engine (no new math):** route + page scaffold, S0 field, S1 DCF, S5
  reverse-DCF *number* (not yet the grid), reasoning. Ship value fast.
- **P2 — Promote the modules:** S2 SBC pairing, S3 owner earnings, S4 EPV; the new
  `derivations.py`; per-method recompute route.
- **P3 — New engines:** S5 detailed grid, **S6 Monte Carlo + price test** + tornado.
- **P4 — Polish:** save-to-model, football-field MC band leg, roll-up into Thesis, opportunity-cost
  required-return config.

## 10. Resolved decisions (signed off 2026-09-24)
1. **Maintenance-capex default = `min(D&A, trailing-5y avg capex)`**, overridable per-method, always
   labeled as an estimate. ✅
2. **Owner-earnings discount rate = WACC** (no separate opportunity-cost hurdle for now; the
   opportunity-cost/hurdle idea stays with the deferred **C11 IRR/hurdle** item and may share config
   later). ✅ — S3 lever set drops the required-return override; it uses the model WACC.
3. **Monte Carlo drivers independent by default, with an optional growth↔margin correlation ρ** the
   user can turn on. Independent understates joint tail risk — stated in-UI. ✅
4. **EPV normalization window = 8 years**, preferring `adjusted_metrics.json` adjusted EBIT when
   present, else median operating margin × latest revenue. ✅
5. **Phasing P1 → P2 → P3 → P4 as in §9.** ✅

### Remaining implementation note (not a blocker)
- **Recompute perf:** S1's growth/margin path edits need the full DCF → keep S1 on the full
  `POST /recompute` path; every other method's levers use the light per-method route (§5.3).

## 11. Reuse map (don't rebuild)
`model_compute.compute` / `wacc_breakdown` / `implied_growth` / `_annuity_px` · `shared/valuation/{
epv,owner_earnings,engine,inputs,relative}.py` · `POST /recompute` + mtime cache · `DeepDive.jsx`
scaffold · `Section.jsx` reasoning · `AssumptionsPanel.jsx` levers · `charts.jsx` FootballField +
recharts · `WaccExplainer.jsx` · `ReturnDecomposition`/`CapitalAllocation` SVG idioms · `palette.js`.

**New code:** `shared/valuation/derivations.py`, `shared/valuation/monte_carlo.py`,
`pages/ValuationDeepDive.jsx`, per-method lever components, histogram/CDF + tornado charts,
`/valuation-deepdive`, `/valuation-deepdive/recompute`, `/monte-carlo` routes.