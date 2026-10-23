# Project document: valuation-parameter-proposals

Source: research_val_personal/docs/valuation-parameter-proposals.md
Kind: design document; may describe planned rather than shipped features.

# Evidence-linked component-model proposal branches

This feature is the review-to-calculation handoff. A human or external offline
agent supplies a strict component plan plus evidence-to-parameter reasoning.
The app can validate, preview and retain separate exploratory model branches.
It does **not** call an LLM, author a model automatically, repair missing inputs,
approve company facts, change saved assumptions, publish FV or select a portfolio
signal. Bounded in-app agent authoring remains the next feature.

## Authoring contract

`shared/valuation/parameter_proposals.py` defines the strict `Proposal`:

- `model`: a `ComponentPlan` using existing `volume_yield` or `fee_assets`
  mechanisms and explicit investment calendars, ownership/FX bridge and life
  policies. `sources` must be empty; compilation owns source receipts.
- `bindings`: explicit `path`, `evidence_ids` and `reasoning` for every resolved
  datum and rate path. Paths use stable component IDs, not array indexes.
- `thesis`: the model's economic interpretation.
- `challenges`: at least one explicit open economic challenge.

Print the complete machine-readable schema for offline agents:

```sh
python3 scripts/preview_parameter_proposal.py --schema
python3 scripts/preview_parameter_proposal.py --review reviewed.json --proposal proposal.json --output branch.json
python3 scripts/preview_parameter_proposal.py --replay branch.json
```

The CLI expects the **offline frozen evidence review artifact**, not the remote
authenticated envelope. Remote record exports contain this under `artifact`.
Output files use exclusive creation. CLI review identity remains declared-human.

Example binding path: `components.airports.quantity_growth`, with evidence IDs
such as `traffic_cell` and explicit reasoning for the proposed growth path.
Annual investment paths use `components.airports.investment.2026.growth_capex`.
Bridge paths use `bridge.ordinary_per_quote`.

## Compilation rules

- Select evidence from exactly one review branch. Only its exploratory-eligible
  cells are allowed; rejected, unresolved and conflict-held candidates cannot
  support model inputs.
- Reference **candidate cell IDs**, not source hit IDs. Several candidates may
  share a hit but have different numerical interpretations.
- A factual datum must match exactly one reviewed candidate's complete datum,
  including value, scale, currency, periods, perimeter, definition and rationale.
  Only `evidence` is rebound to the candidate ID. No implicit rebasing or
  transformations are labeled as new facts.
- A resolved judgment requires rationale, falsification and matching evidence
  bindings; a resolved rate path requires rationale/falsification plus a binding
  explaining the source-to-assumption reasoning. Links do not independently
  validate that reasoning.
- Unknown datums use `value: null`, `basis: "unresolved"` and empty evidence.
  Unresolved rate paths retain null endpoints with no supporting binding.
  They remain blockers, never zero or flat-growth substitutes.
- Compiler-owned sources preserve the reviewed hit's file path, raw-document
  hash, excerpt and original cell location. Full provenance remains in the
  embedded review artifact.

The shared deterministic component engine checks dimensional basis, calendars,
domains, finite rights, investment and the single equity/quotation bridge.
Its `needs_evidence` and `invalid_model` results remain inspectable blocked
branches. Exact fact mismatch, unsupported fields or unauthorized evidence
references reject the proposal rather than repairing it. Payloads are limited
to 250,000 serialized characters; remote artifacts retain the runtime's 1 MB
record cap.

The engine supports full-perimeter FCFF only. It does not establish that OMAB's
renewal/ownership economics or OWL's carry/acquisition/public-ownership structure
are complete. Forecast-only PV never receives a complete equity value. Even a
numerically complete finite-rights model remains exploratory and economically
unapproved; no upside percentage or current-price comparison is generated.

## Dossier UI and persistence

Inside **Review source-cell evidence**, expand **Exploratory component-model
proposals**. Explicitly select a saved review branch and inspect its eligible
typed inputs. Supply proposal JSON, validate and inspect the unsaved deterministic
preview, then save a separate branch. Editing the JSON or changing the review
branch invalidates the UI's previous preview.

The preview displays gaps/issues, annual roll-forwards, investment and FCFF,
component PV, any exploratory equity/quotation bridge, source-to-parameter
reasoning and open economic challenges. All source/proposal text is escaped.
Advanced JSON editing is intentional for this first handoff; richer conversational
authoring and in-app agent generation are not implemented yet.

POST preview/save use the same server-verified workspace identity and explicit
reviewer allowlist as evidence review. No user authorization or deployment
configuration is changed here. GET history retains existing app read access.

Saved records live at:

```text
valuation_runtime/<company>/<research-child>/component-proposals/<id>/record.json
```

Each record includes the exact selected review receipt/digest, immutable proposal
body, authenticated submitter envelope, deterministic frozen input/output and
engine signature. History replay validates the research-parent chain, selected
review branch, source anchoring and proposal outputs. Hashes are not signatures:
direct Volume write permissions remain part of the trust boundary.

Retained client keys recover ambiguous saves across reload using the original
body/review branch. Reusing a key with changed content or identity fails. New
keys create independent branches; none automatically supersede or accept another.
Listings fail explicitly above 100 branches instead of dropping history.

## Next boundaries

1. User-initiated bounded agent authoring against this exact contract, with
   frozen review context, explicit cost consent, abstention and checkpoint/retry
   budgets. Never fall back to generic FCF vectors or fabricated unknowns.
2. Independent economic challenge, reverse expectations and sensitivities.
3. Grounded OMAB/OWL dossiers, followed by reviewed canonical publication and
   thesis/KPI monitoring.