# Project document: component-valuation-foundation

Source: research_val_personal/docs/component-valuation-foundation.md
Kind: design document; may describe planned rather than shipped features.

# Composable offline valuation foundation

`shared/valuation/components.py` evaluates configuration, never dispatches by ticker.
Its strict `ComponentPlan` uses the existing source, datum, rate-path and investment
contracts. It supports volume × yield and fee-paying assets × fee rate. Asset flows
change the fee base, not corporate FCFF. Investment, margins, tax, depreciation and
discounting remain explicit; no growth, discount or terminal defaults are supplied.

Components have independent forecast windows. Finite-rights components require a
sourced expiry matching their last year end, explicit investment for every year,
and explicit end cash. Forecast-only components are incomplete: their operating PV
is displayed without an equity valuation. A cutoff is not evidence of liquidation.
No perpetuity, renewal, partial-year rights or inferred terminal policy is supported
in this first component slice.

Compatible full-perimeter FCFF components are summed before the shared equity bridge
in `shared/valuation/common.py` applies corporate cash, debt, other claims, ordinary
shares, quotation conversion and FX once. The concession pilot uses that same bridge.
Changing bridge code changes the concession replay signature.

Synthetic tests demonstrate both mechanisms with identical hand-calculated results,
combine separate perimeters, test fund flows, and block unsupported or unresolved
inputs. They are not OMAB or OWL estimates. Call `evaluate(plan_dict)` for an offline
proposal; the result always has `publishable: false`.

## Boundaries and next work

- Declared source review and disjoint scopes need real human verification; labels
  do not prove evidence support or prevent economically overlapping components.
- Full-perimeter equal-rights ordinary equity only. No partial ownership, carry,
  acquisitions, corporate-cost allocation or operating/financing hybrids yet.
- Fee revenue uses end-year assets, not average assets; fee flows and market returns
  must be separately reasoned assumptions. This is not a complete OWL strategy.
- Growth capex is explicit but is not yet causally linked to capacity/growth.
- Existing concession normalization and partial-year calendar remain in the
  specialized adapter; not all of that adapter has been generalized.
- Add approved targeted evidence retrieval and reconciliations next; then agent
  parameter proposals and economically justified tail policies. Require a grounded
  company dossier before judging a real-company valuation.
- Component freeze/replay, API/UI, review/publication and monitoring integration
  remain future work. No paid inference, live values or deployment changes here.

## Local validation

`python3 scripts/validate_valuation_bundle.py --skip-frontend` passes:
212 targeted acceptance tests, 247 full Python regression tests, and patch
whitespace checks. Frontend validation is skipped because this slice changes no UI.
The existing Starlette/httpx deprecation warning remains.