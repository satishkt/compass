# Project document: concession-strategy-pilot

Source: research_val_personal/docs/concession-strategy-pilot.md
Kind: design document; may describe planned rather than shipped features.

# Research-led concession strategy — first architecture-pivot slice

This is an offline reference engine for the OMAB pilot's model family, not an OMAB valuation.
No live company inputs, saved assumptions, published revisions, agents or deployed jobs are changed.
The supplied example is explicitly synthetic. Real OMAB source grounding and model review remain open.

## Architecture decision

Keep the durable worker, frozen evidence, deterministic arithmetic and publication controls.
Stop making an LLM materialize every annual input vector and formula for the reference model.
The agent should ultimately research facts and propose economic assumptions; reviewed Python
strategies compile those assumptions into calendars, roll-forwards, cash flows and valuations.
The existing four-stage agent workflow is unchanged in this slice.

`shared/valuation/contracts.py` supplies Pydantic 2 contracts with forbidden extra fields,
strict numeric types, finite-value checks and explicit units, scale, currency, period, economic
perimeter, definition, fact/judgment/unresolved basis and evidence IDs. Judgments require rationale
and falsification conditions. No absent metric defaults to zero. Source records preserve document,
locator, excerpt, content hash and declared review state; this metadata does not prove semantic
support or authenticate reviewer identity. Agents cannot turn these artifacts into publications.

`shared/valuation/concession.py` is the first deterministic strategy. It receives an explicit
concession packet; it does not classify companies, fetch evidence or use ticker-based routing.

## Supported economic contract

- One calendar-year airport/concession perimeter, one sourced expiry date, and equal-rights ordinary
  residual equity. Valuation is at the base calendar-year end. Multi-component/SOTP modeling,
  hotel/industrial-park economics and intra-year valuation dates require later extensions.
- Reconcile reported revenue to aeronautical, non-aeronautical and construction revenue.
  Only reconciled zero-margin construction pass-through is supported. Excluding construction
  accounting does **not** exclude cash investment: all forecast investment is still charged.
- Derive base yields from operating revenue divided by disclosed annual traffic. Python compounds
  traffic and separate yields. Explicit first/steady/fade assumptions generate growth, operating
  margin, depreciation and cash-tax paths; a fade of N years reaches the steady value in year N.
  These paths are proposed judgment, not facts or calibrated probabilities.
- Python builds every calendar year through the sourced expiry. The final stub uses actual active
  days divided by days in its calendar year; full-year run-rate operations are prorated.
  Committed investment is **not** prorated: the caller supplies the actual cash amount for each active
  period, including the stub. Missing periods yield research requests rather than zero spending.
- Annual cash flow in reporting-currency millions is EBIT minus modeled cash tax, plus depreciation,
  minus explicit maintenance capex, growth capex and signed working-capital outflows. The operating
  margin already includes SBC; there is no second SBC deduction. Negative operating margins are
  supported, and loss years receive no automatic tax benefit. Tax is a declared operating-earnings
  proxy, not a full tax-accounting model.
- Require explicit signed expiry net cash: recoveries less handback/closure obligations, including
  any justified working-capital recovery. There is no automatic working-capital release, renewal,
  salvage, exit multiple or perpetuity. Conditional renewal requires a separate future strategy.
- Discount active-period-end cash flow by `(1 + rate) ** -(full_years + active_fraction)`.
  Discount rates are explicit, positive, nominal reporting-currency assumptions. Money remains
  reporting-currency millions until per-share conversion.
- Bridge enterprise value with explicit excess cash, disjoint debt and valued other economic claims.
  Use total eligible equal-rights ordinary shares, not public float. Apply ordinary-per-quoted-unit
  conversion once, then divide by reporting-currency-per-quoted-currency FX once.

This small model does not enforce airport capacity, regulated tariff caps, passenger mix,
investment-to-growth feasibility, or a full lease/ownership/tax ledger. Its schema/domain checks
are not a substitute for reviewing those economics. Different share rights or nonzero construction
margins are unsupported, not silently approximated.

## Dossier outputs and states

- `exploratory`: the supplied contract is calculable; includes normalization, annual workings,
  scenario values, equity bridge and input lineage. **Not economically approved or publishable.**
- `needs_evidence`: preserves available normalization and input lineage, lists unresolved/source-review
  gaps and targeted disclosure requests, and returns no scenario valuation. Existing known amounts
  may still appear in the partial reconciliation; the dossier is not verified.
- `invalid_model`: exposes currency, period, perimeter, reconciliation or domain contradictions and
  suppresses scenario valuation. Structurally invalid packets fail schema validation.
- Every state has `publishable:false`; no portfolio, market-price, approval or FV publication API
  is connected to the pilot. Scenario outputs are conditional estimates, not authoritative headlines.

`freeze` archives the validated input packet, output, hashes and engine signature.
`replay` recomputes it, detects modified inputs/outputs and refuses changed engine code.
Historical replay after engine changes needs the original code release; it is not silently migrated.

## Run without network or LLM usage

```sh
python3 scripts/preview_concession.py --synthetic-example --output /tmp/concession-example.json
python3 scripts/preview_concession.py --replay /tmp/concession-example.json
```

The synthetic model is a two-year concession with 120 million operating revenue, 50% EBIT margin,
20% tax, 5% revenue depreciation, 10 million maintenance investment, 5 million growth investment
and 2 million working-capital outflow each year. Annual FCFF is 37 million. At a declared 10%
discount rate, enterprise value is `37 / 1.1 + 37 / 1.1**2`; subtract the explicit net claims
and apply the synthetic share/FX contract. None of these numbers are OMAB observations.

To create a real research packet, edit the artifact's `inputs` into a separate model JSON and supply
actual reviewed evidence, explicit judgments and unresolved values. Then use:

```sh
python3 scripts/preview_concession.py --model /tmp/concession-model.json --output /tmp/concession-proposal.json
```

Output files are created exclusively; existing files are not overwritten. CLI execution is offline
and has no connection to saved company models. Real-data extraction is intentionally not implied by
being able to submit an arbitrary packet.

## Next implementation order

1. Assemble a hand-reviewed OMAB fact/normalization dossier from primary disclosures. Reconcile
   rights, segments, investment commitments, capital stock, economic claims and FX; expand the
   reference strategy where the actual economics require it. Unknowns must stay unknown.
2. Implement targeted approved-index retrieval and source-cell extraction driven by these requests,
   with conflict resolution and versioned evidence. Do not simply increase the fixed excerpt budget.
3. Let the research agent propose small parameter paths and alternative interpretations against the
   strategy contract. The engine owns dates and arithmetic; plan changes create proposed branches.
4. Add reverse expectations/sensitivities and a dossier preview API/UI. Carry explicit dates, scope,
   source sufficiency and assumptions into every displayed output.
5. Build OWL's fee-paying-assets/fee-economics/public-ownership reference strategy as a separate pilot.
6. Connect reviewer/human publication and then driver-based monitoring. Keep legacy consumers
   unchanged until canonical accepted-artifact integration is validated.

## Local acceptance — October 10, 2026

`python3 scripts/validate_valuation_bundle.py --skip-frontend` passes 194 targeted acceptance
tests and all 229 application Python tests, including 41 concession-pilot cases; whitespace
checks pass. The standalone synthetic preview and frozen-artifact replay also pass.
Frontend checks are skipped because this slice makes no frontend changes. The existing
Starlette/httpx deprecation warning remains. No live data, agent inference, approvals,
deployment or git commit is performed.