# Project document: valuation-basis

Source: research_val_personal/docs/valuation-basis.md
Kind: design document; may describe planned rather than shipped features.

# Valuation basis and publication safeguards

## Correctness and review bundles (2026-10-09)

Deployed and verified on FEVM app `research-cockpit`, deployment
`01f1c3ff89ca17018725660483767047` (started successfully at 2026-10-09 16:46:23 UTC).
Release checks pass: 79 Python tests, frontend build and browser interactions. Authenticated live
checks confirm the new review UI/APIs, OMAB/OWL publication blockers, and consistent portfolio/
market lookup pricing. No live assumptions or approvals were changed during verification.

The Python valuation engine computes exploratory annual FCFF. A numerical result is **not**
automatically a published valuation. Company summaries and portfolio sizing/review consume a fair
value only when its basis passes validation and the exact model/evidence has been reviewed.

Existing models without a reviewed basis now show no published FV, upside, or investment signal.
They are not grandfathered in. This intentionally includes the unresolved OMAB/OWL models.
Exploratory DCF, scenario and sensitivity workings remain accessible, with warnings in the dossier,
quick-look and deep-dive screens. No live assumptions were migrated or approved by this change.

The second bundle adds dated FX translation, frozen revisions, replay, and human-review
controls. This is still a partial V01–V05 implementation, not the offline LLM runtime or the
company-specific OMAB/OWL underwriting pilot.

## Evidence and scale

Normalization keeps its existing numerical CSVs and additionally writes complete source documents
to `normalized/<statement>-facts.json`. The loader retains original statement documents and share
snapshots; sidecars are a fallback when originals are absent. Original currency, units, metric
mapping, period and restatement/source metadata survive **when supplied by the provider**.

Numeric values are not multiplied by vendor unit labels: a cell marked `K` may already contain
an absolute amount. The model requires an explicit `numeric_value_scale: "absolute"` attestation;
Python converts those values to millions once. Missing document/page references are not invented.
This is evidence retention, not yet a full typed fact store or a per-cell provenance validator.

## Basis contract

Add a `basis` block to the full assumptions JSON after reconciling the evidence:

```json
{
  "reporting_currency": "USD",
  "trading_currency": "USD",
  "discount_currency": "USD",
  "numeric_value_scale": "absolute",
  "source": "Specific filing/share snapshot references",
  "as_of": "2026-10-09",
  "share_basis": "ordinary",
  "eligible_shares_mm": 100,
  "market_cap_mm": 1000,
  "cash_debt_reconciliation": "Document excess cash, debt perimeter and excluded investments",
  "ownership": {
    "method": "public_equity",
    "equity_fraction": 1,
    "other_claims_mm": 0,
    "source": "Specific ownership and other-claim reconciliation"
  }
}
```

`market_cap_mm` must correspond to the same price date/security/economic perimeter, not an arbitrary
provider headline. Price × model shares must reconcile within 5%; model shares must match eligible
shares within 1%. These are checks of the analyst's explicit reconciliation, not automatic validation
of every share class against legal economic rights.

For `share_basis: "ads"`, also supply `ads_ratio` (ordinary shares per ADS) and
`ordinary_shares_mm`. Eligible shares are ADS-equivalent shares; **do not convert them again**.
For `fully_exchanged`, ownership method must also be `fully_exchanged`; the denominator and all
economic claims must be sourced and reconciled, not formed by blindly summing listed share classes.

Equity bridge: `(EV - debt + excess cash) × equity_fraction - other_claims`, then divide by eligible
shares. The fraction refers to reconciled **net equity economics**, not an arbitrary revenue haircut.
When minority/noncontrolling interests are present, ownership must include a documented
`noncontrolling_interest_reconciliation`. Book-value minority interests are not automatically
subtracted as a proxy for economic value.

Reporting and nominal discount currencies must be identical. Trading currency may differ when
an explicitly sourced FX snapshot passes the checks below. The engine keeps revenue, annual
cash flows, enterprise value, debt/cash and claims in reporting currency, with nominal rates in
that currency. It translates the trading quote into reporting currency before price comparisons,
then translates per-security values and sensitivity grids back to trading currency **once**.
It does not apply USD nominal discount rates to MXN forecasts or perform live FX retrieval.

For a reporting-MXN/trading-USD model, add:

```json
{
  "reporting_currency": "MXN",
  "trading_currency": "USD",
  "discount_currency": "MXN",
  "price_as_of": "2026-10-09",
  "nominal_rates_source": "Specific dated MXN risk-free/ERP/debt-rate and weight rationale",
  "fx": {
    "from_currency": "USD",
    "to_currency": "MXN",
    "reporting_per_trading": 20,
    "as_of": "2026-10-09",
    "source": "Synthetic illustration only; replace with a real sourced snapshot"
  }
}
```

**20 is a synthetic illustration, not an observed FX rate.** The FX and price snapshot dates must
match and cannot postdate the model's evidence cutoff. Missing rate evidence, inverted direction,
nonpositive/nonfinite rates or mismatched dates block calculation/publication. This is spot
translation of a reporting-currency valuation; it is not an exchange-rate forecast or a currency
hedge model. Existing global risk-free/ERP/terminal-growth overrides remain USD-only. Investor
hurdle defaults and their provenance are frozen with the effective assumptions.

OMAB still needs actual dated FX/rate evidence, security reconciliation and a company-specific
concession forecast; OWL still needs authoritative economic ownership evidence. No values or
ownership rights for those companies are invented by this implementation.

## Review and status

The dossier's **Model evidence, revisions & human review** panel exposes the saved model's basis,
errors/warnings, currency convention, exploratory FV, revision identifier and review record.
It permits basis JSON edits, freezing, replay verification and explicit approval with reviewer
label, rationale and warning acknowledgement. Unsaved slider what-ifs or unsaved basis edits
disable approval. Approval checks the expected current revision again server-side; hard failures
cannot be acknowledged away. Saving basis/assumption edits revokes approval.

Reviewer labels are **self-declared**, not verified identities. This personal-app workflow is not
role-based separation of duties or the independent LLM accounting reviewer from V09.

`validate_basis` returns hard errors, eligibility, status and an effective-input `approval_digest`.
The digest includes statements, documents, profile, shares, effective assumptions, engine version
and hashes of the actual calculation source files. It excludes the review record itself.

- `blocked`: unresolved currency, scale, security, ownership, capital bridge or probability basis.
- `awaiting_review`: valid basis, but no matching approval (or unacknowledged plausibility warning).
- `approved`: matching reviewed inputs and no unresolved checks.
- `stale`: inputs/evidence changed since approval, with an otherwise valid basis.

Changed UI assumptions revoke approval. USD global overrides affect the effective digest, so they
also require re-review. Source-data/global-config updates invalidate the company summary cache.
Extreme valuations produce economic warnings, not clipped values or waivable accounting errors.
A reviewer must explicitly record the exact `fv_flags` list in `review.acknowledged_warnings` to
publish a warned model, as well as approve the effective-input digest.

## Model consistency and remaining scope

Headline scenarios, reverse DCF and Python sensitivity grids use annual NOPAT + D&A − capex −
working-capital investment − SBC, sharing the explicit DCF's annual cash-flow builder and equity
bridge. Finite-life forecasts stop at expiry; exit-multiple calculations cannot reintroduce a
perpetual tail. A supplied salvage value is included at expiry.

The workbook's legacy annuity formulas, separate owner-earnings/EPV/SBC methods, Monte Carlo,
return decomposition/IRR approximations and Investment Case workbench are **not fully migrated**.
Deep-dive methods remain exploratory and are not independent approved fair-value signals.
Published return decomposition/IRR diagnostics are withheld for finite-life models or models with
fractional equity allocation/other claims, since their legacy approximations do not handle those
bases. Standard-basis return diagnostics remain approximations, not annual cash-flow IRRs.
Report/export reconciliation, complete typed facts, dilution/ownership
pilots, currency-specific rate curves and all material operating-driver paths remain V01–V04 work.
Do not claim a corrected OMAB/OWL FV or complete V01–V04 delivery from these safeguards alone.

## Frozen revisions and replay

Immutable revisions live under `models/valuation_revisions/<revision-id>.json`. They contain source
documents/share snapshots, normalized financial series, effective assumptions, calculation source
files and hashes, engine/Python versions, outputs/validation, and stable assumption IDs with supplied
lineage metadata. Missing rationale/units/evidence are labeled as undocumented, not invented.
Driver metadata can be supplied in `driver_lineage` keyed by IDs such as
`operational.capex_pct_rev`. This is a minimal contract, not a full economic-driver dependency graph.

Saving the same revision is idempotent; an existing file is never overwritten. Reviews are separate
append-only decision records and the current model's review pointer. Snapshot files are written
atomically and review actions use a per-model process/thread lock with optimistic revision checks.
External gather/edit processes do not share that lock; they must finish before approving a model.
Evidence changes make current approval stale and create a new revision; older snapshots remain
available. This does not yet retain every unsnapshotted intermediate edit or establish a full
approved-artifact pointer serving every consumer (V11).

Replay uses frozen assumptions without today's global overrides or live retrieval. It checks input,
archived-code and output integrity, and requires the exact calculation engine hash. Archived code is
never executed dynamically; if the engine changed, use the original checkout/environment to replay.
Review records, timestamps and the current approval pointer are not numerical model inputs.

Legacy foreign-currency deep-dive cross-checks, Monte Carlo and industry P/E overlays are disabled
rather than allowed to mix currencies. Portfolio review/sizing requires holding-price currency to
match the approved per-security currency. Workbook/export and all-consumer migration remain open.

## Validate the bundle in one shot

Run from the repository root with Python/pytest and local frontend dependencies/Playwright Chromium:

```sh
python3 scripts/validate_valuation_bundle.py
```

The command runs valuation acceptance tests, all Python regressions, patch checks, the frontend
production build and a headless review-panel browser harness. It needs permission to bind a
temporary localhost port and launch the installed browser. It does not download data, install
packages, modify real models, approve companies or deploy. `--skip-frontend` runs Python/patch
checks only; it intentionally does not claim UI validation.

Acceptance covers synthetic currency/ADS equivalence, invalid/inverted/undated FX, nominal-rate
compatibility, expiry and cash-flow dependencies, immutable replay, tamper detection, stale edits/
restatements, hard-failure rejection, explicit warning review, summary/detail/portfolio gates, and
review-panel approve/edit/freeze/replay/blocking interactions. Browser API responses are mocked;
backend approval/replay endpoints are independently tested with temporary fixtures.