# Project document: valuation-underwriting

Source: research_val_personal/docs/valuation-underwriting.md
Kind: design document; may describe planned rather than shipped features.

# V08 — Deterministic annual underwriting core

## Delivered locally

Workflow version 3 adds an **underwriting** checkpoint after the architect/analyst and before
the reviewer. The underwriter proposes data-only annual input paths and a typed formula graph,
or explicitly abstains with `model: null`. The worker calculates and freezes annual workings.
The reviewer receives the proposed graph and deterministic results; LLM agreement never publishes.

The UI shows annual inputs, intermediate calculations, output rows, alternative economic
scenarios, input rationale, alternatives, falsification conditions and formula lineage. A model
JSON editor previews changes against the frozen evidence and architecture **without calling an
LLM or changing saved artifacts**. Reset restores saved workings. Invalid previews leave the
displayed calculation unchanged. Preview/replay POSTs do not push the app mirror to the Volume.

## Calculation contract

`shared/valuation/underwriting.py` implements schema/engine version 1:

- A named model with a cash-flow definition, reporting currency (or unresolved), consecutive
  fiscal years matching the architect's horizon, inputs, formula nodes, outputs and scenarios.
- Each input declares its architecture driver ID or auxiliary role, annual values, fact/judgment/
  unresolved basis, source pointers, rationale, alternatives, falsification conditions and
  `user_confirmed: false`. An agent cannot declare human confirmation.
- Factual values require an exactly matching numerical source leaf for each year. Judgment paths
  remain explicit judgment; unresolved vectors remain entirely null. Unknowns propagate to
  dependent calculations instead of becoming zero or fabricated estimates.
- Every architecture driver must be represented. The graph may not silently shorten the horizon,
  reference nonexistent IDs, duplicate IDs, or contain circular dependencies.
- Allowed operations are add, subtract, multiply, divide, power, min and max on named inputs/nodes.
  No generated Python, arbitrary expressions, file/network calls, imports or dynamic execution.
- Declared dimensions must reconcile. Money means reporting-currency **millions**, counts are
  unscaled, rates are decimals, and money-per-unit means reporting-currency millions per unit,
  **not** a quoted security price. Currency declarations conflicting with the saved reporting basis
  are rejected.
- Up to three alternative scenarios override only judgment paths with an economic rationale.
  They cannot overwrite facts or fill missing evidence, and have no inferred probability weights.
- At most 30 inputs, 30 nodes, 100 years, 8 output IDs and 2,000 annual cells per scenario.
  Numbers/results are bounded by absolute value 1e15. Exponentiation is dimensionless, with
  nonnegative base and exponent magnitude at most 100. Division by zero, overflow and invalid
  domains produce visible errors/unknowns rather than infinity. Saved workings are capped at
  100,000 JSON characters.

Source pointers and equal numerical values do **not** establish currency/scale, period relevance,
perimeter, economic ownership, forecast validity or semantic source support. Copying a historical
fact into future years does not make the forecast factual. Current source-unit and economic
reconciliation limitations remain subject to V01/V02, reviewer challenge and human verification.
Scenario rationale is inspectable, not independently proven coherent merely by passing the schema.

## Frozen replay and recovery

A calculation freezes its model, evidence and architecture, an input digest, engine version/
source signature, and numerical outputs. Replay verifies the frozen inputs, requires the matching
current engine, and recomputes exact outputs without an LLM. Job-level replay also checks that the
calculation belongs to the saved evidence/architecture/underwriting checkpoints. These are integrity
checks, not authenticated digital signatures.

Interrupted jobs retain underwriter checkpoints. If the deterministic calculation is missing,
the worker reconstructs it without repeating the underwriting call. Inconsistent/tampered
checkpoints fail visibly. Version-1 and version-2 workflows keep their original stages and budgets.

## Publication boundary and remaining scope

All annual results remain exploratory. Essential architecture gaps, saved basis blockers, unknown
inputs and numerical errors are visible. `publishable` is always false and `fair_value` is null.
The engine does not automatically sum discounted cash into enterprise value, reconcile the
public-shareholder bridge, infer renewal/terminal value, convert to quoted-security fair value, or
update accounts/portfolio signals. Arbitrary output labels cannot bypass those gates.

The delivered core is not a completed OMAB/OWL valuation or a fully approved V08 model. Still open:
verified business-specific source retrieval, complete cash-flow/perimeter reconciliation,
terminal/discounting/public ownership/FX valuation contracts, immutable saved edited branches and
human approval of new-model artifacts, deeper V09 economic challenge, and V10 pilots. The dedicated
FEVM worker is provisioned and transport-smoke-tested, and app controls are deployed/read-only-verified.
Live dispatch and real LLM-stage acceptance remain pending.
Initial bounded source snapshots do not establish economic correctness.

## Acceptance

Run `python3 scripts/validate_valuation_bundle.py`. Synthetic tests cover annual fee-assets/fee-rate/
expense/tax/reinvestment calculations, economic scenario paths, unknown propagation, invalid
units/graphs, numerical errors, exact source matching, frozen replay/tampering, resume behavior,
legacy compatibility and read-only preview semantics. Browser tests cover annual rows, scenario
selection, replay, edit previews/reset and unchanged approval counts.

Tests use no live inference, approve no real models, and do not establish live model reasoning quality.