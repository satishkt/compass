# Project document: valuation-cleanup

Source: research_val_personal/docs/valuation-cleanup.md
Kind: design document; may describe planned rather than shipped features.

# Valuation cleanup and model migration

This is the starting audit for simplifying the valuation code. The first cleanup
consolidates numerical plumbing while retaining existing accounting policies and
saved assumption formats. It does not establish that the current valuations are
economically correct.

## Accepted policy and accounting migration

The user confirmed Buffett's owner-earnings definition and an always-expensed SBC
policy. SBC remains in reported/normalized net income and operating profit. It is
excluded from eligible noncash add-backs, and is not deducted a second time after
starting from profit that already expenses it. Adjusted earnings that exclude SBC
must be reconciled before being accepted as these inputs.

The first accounting layer is implemented in `shared/valuation/accounting.py`:

- `buffett_owner_earnings` starts with net income attributable to the equity holders
  being valued, adds D&A and eligible other noncash charges excluding SBC, and
  deducts maintenance investment and required incremental working capital.
- `free_cash_flow_to_firm` starts with EBIT after SBC and deducts total reinvestment.
- `earnings_power_cash_flow` uses sustainable operating profit after SBC, after-tax
  operating adjustments, and D&A less maintenance capex at zero growth.

Required accounting inputs are explicit, finite amounts; missing values cannot
silently become zero. Capex is a positive outflow. Working-capital changes are
signed; a negative required working-capital change for owner earnings needs support
as an enduring release. Each call uses amounts from one period, currency and scale.
Source reconciliation and basis metadata remain the adapter's responsibility.

The standalone owner-earnings, revenue-to-FCFF and EPV helpers delegate to this layer.
Their existing public signatures remain available. The legacy EPV adapter still
takes a combined maintenance adjustment; its zero default is not evidence that D&A
and maintenance capex are equal. The new cash-earnings function requires both inputs.

The app/report annual engine, deep-dive adapters and exports have **not yet migrated**
to the accepted accounting policy. In particular, the annual engine's extra SBC
deduction, the add-back comparison UI, adjusted-EBIT source policy and misnamed
owner-earnings diagnostic remain migration work. These paths must not be described
as conforming to the confirmed policy until migrated and reconciled.

## Current calculation paths

| Path | Role | Treatment |
| --- | --- | --- |
| `shared/valuation/engine.py` | Discounting, growth, terminal math, implied-growth solver | Shared numerical foundation |
| `shared/valuation/dcf.py`, `epv.py`, `owner_earnings.py`, `relative.py` | Standalone valuation methods used by charts and notebooks | Retain public interfaces; migrate accounting inputs later |
| `shared/report/model_compute.py` | App/report annual FCFF, scenarios and sensitivities | Retain outputs, ownership bridge, currency and publication checks |
| `shared/valuation/deep_dive.py`, `monte_carlo.py` | Method comparisons, reverse grids and simulations | Use shared annual forecast pricing and implied-growth solver |
| `shared/report/excel.py` | Independently emitted workbook formulas | Requires reconciliation before replacing formulas |
| `shared/investment_case/valuation.py` | Discounted future exit equity value | A scenario workbench; does not include interim FCF |
| `shared/valuation/components.py`, `concession.py`, `underwriting.py` | Experimental component and finite-life models | Retain until callers and persisted artifacts can migrate |
| `app/backend/portfolio/valuation.py` | Position market values and P&L | Separate from intrinsic business valuation |

Research, evidence, review and worker modules support these paths; their size alone
does not make them dead code. Removing them requires a separate caller and stored-data
migration, including frontend and API contracts.

## Cleanup implemented

- DCF and owner-earnings discounting share explicit/terminal PV aggregation.
- Standalone FCFF reverse DCF, app revenue reverse DCF and deep-dive reverse grids
  share bracketed bisection. Unbracketed targets retain each adapter's existing
  `ValueError` or `None` contract. Exact endpoint roots return the endpoint;
  nonfinite values and invalid brackets raise clear errors.
- Annual forecast pricing has a descriptive public name, `annual_forecast_price`.
  `_annuity_px` remains a compatibility alias for older callers and notebooks.
  Scenario, sensitivity, reverse-grid and simulation callers use the new name.
- Removed the unused `CONV = 0.92` approximation constant from the Python engine;
  corrected comments that described annual calculations as an annuity closed form.
- Approval snapshots include the shared math source now used by the app solver.
  Engine edits invalidate existing review digests and prevent replay with a different
  engine, as required by the current artifact contract. Archived inputs are retained.
- Numerical tests cover explicit and terminal PV, equity bridges, existing mid-year
  timing, forward/reverse round trips, bounds, and invalid solver values.

## Accounting issues to resolve in the model redesign

1. **Two different owner-earnings definitions.** The standalone function starts
   with net income and deducts maintenance investment and incremental working
   capital. The report's `fcf_views.owner_earnings` starts with NOPAT, deducts total
   capex and SBC, and omits working capital. These should not share a model label.
2. **Equity versus enterprise claims.** Deep-dive owner earnings starts with net
   income, discounts at WACC and adds cash minus debt. Define an equity cash stream
   discounted at cost of equity, with explicit nonoperating adjustments; avoid
   deducting debt twice from a stream already reflecting financing obligations.
3. **Maintenance capex and missing data.** Deep-dive maintenance capex is a proxy;
   missing incremental working capital can become zero. Require explicit sourced
   amounts or disclosed estimates, and distinguish unknowns from actual zeroes.
4. **EPV normalization.** Current EPV capitalizes normalized EBIT after tax plus an
   optional adjustment. Standardize sustainable after-tax operating earnings,
   D&A minus maintenance capex, normalization years and excess-cash claims. A zero
   adjustment should be an explicit assumption rather than proof of equivalence.
5. **SBC policy.** Annual FCFF subtracts SBC after NOPAT; verify whether operating
   profit already expenses SBC. Choose expense retention or add-back plus dilution
   consistently so the economic cost appears once.
6. **Working-capital units.** Standalone DCF takes annual change as a fraction of
   revenue; app forecasts use incremental revenue times a working-capital ratio.
   Normalize to an explicit currency amount for annual change before valuation.
7. **Terminal policy.** App Gordon growth silently caps growth at WACC minus two
   points, while standalone Gordon rejects growth at or above the discount rate.
   Standalone mid-year terminal discounting also uses year N minus one-half.
   Make effective growth and timing explicit. Preserve finite-life expiry handling.
8. **Reverse-DCF question.** Standalone reverse DCF solves FCFF growth; app reverse
   DCF solves revenue growth at assumed margins and reinvestment. Label the solved
   variable and hold all other assumptions fixed. The notebook generator currently
   passes first projected FCFF as the reverse model's base, requiring period review.
9. **Exports and scenarios.** Workbook approximations and investment-case terminal
   scenarios are not equivalent to a full annual DCF. Reconcile or label them
   before presenting them as comparable valuation outputs.

## Intended simplified foundation

Use explicit currency, period, amount scale and security basis for all inputs.
Rates are decimals. Accounting preparation should produce named annual amounts:

- FCFF = EBIT × (1 − cash tax rate) + D&A − total capex − change in operating NWC.
- Owner earnings = normalized net income + eligible noncash charges − maintenance
  capex − required incremental operating working capital, with explicit SBC policy.
- EPV cash earnings = normalized after-tax operating profit + D&A − maintenance
  capex, including explicit sustainable operating adjustments at zero growth.

Models then consume these prepared cash flows rather than infer accounting
definitions from revenue percentages. Enterprise streams use an enterprise discount
rate and one claims bridge; equity streams use an equity required return. Reverse
DCF should call the same forward model with one declared unknown. Relative models
must distinguish enterprise multiples from equity multiples. Growth, reinvestment
and terminal assumptions remain estimates with visible sources and judgments.

Migration order: standardized accounting inputs, pure forward models, reverse solver
adapters, app payloads, then workbook/notebook exports. Remove superseded code only
after caller migration and numerical reconciliation. The cleanup above intentionally
does not change these economic policies before that reconciliation.