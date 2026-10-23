# Project document: agentic-valuation-monitoring-backlog

Source: research_val_personal/docs/agentic-valuation-monitoring-backlog.md
Kind: design document; may describe planned rather than shipped features.

# Agentic Valuation & Thesis Monitoring — Implementation Backlog

## Development paused — October 13, 2026

Valuation workflow work is paused pending a rethink of the engine and research
experience. Remaining items are deferred, not currently being implemented.
See `valuation-paused-checkpoint.md` for preserved work, unresolved queued
planning, deployment state and restart guidance.

Status: **BACKLOG — NOT IMPLEMENTED** (2026-10-09).

Origin: code/features review, deployed OMAB/OWL valuation investigation, and the subsequent
discussion of offline valuation authoring and intelligent KPI/thesis monitoring.
Companion to `dossier-ux-backlog.md`, `system-reference.md`, and `valuation-deep-dive-spec.md`.

## Goal

An offline analyst agent builds an evidence-grounded, company-specific valuation. A monitoring
agent investigates whether the reasons behind that valuation remain true. The UI presents the
workings, competing interpretations, proposed revisions, and findings that need human judgment.

**Offline means background/asynchronous, not necessarily disconnected from the internet.**
Approved source retrieval and LLM calls happen in jobs, not inside page-load requests.

The LLM designs and underwrites; executable, tested calculations produce the numbers; the user
approves publication and material model changes. This is not an LLM attached to CAGR sliders.

## Locked principles

- Preserve currency, units, security identity, ownership basis, dates, definitions, and source
  provenance before doing valuation math. Vendor-normalized data is evidence, not infallible truth.
- Support company-specific drivers, forecast horizons, cash-flow definitions, and terminal
  treatments. Do not force every company into the same DCF or a fixed UI layout.
- Permit free-form narrative and models while requiring a small machine-readable artifact
  contract for facts, assumptions, calculations, outputs, validation, and versions.
- Use one accepted valuation artifact across company screens, portfolios, reports, and monitoring.
  Do not introduce another independently calculated headline fair value.
- Publish decision rationales, evidence, formulas, tests, and revisions—not raw internal model
  reasoning. Keep facts, management guidance, third-party views, and analyst judgment distinguishable.
- Missing essential evidence can result in abstention: no defensible valuation yet. Do not silently
  manufacture defaults, probabilities, or confidence scores.
- Extreme disagreement with market price triggers investigation, not an automatic fair-value cap
  or a requirement that the model converge to the market.
- Monitoring investigations and alternative model branches never silently overwrite an accepted
  model. No automated trades; user judgment owns acceptance.
- Reuse existing research, KPI, claims, monitoring, views, snapshots, and review infrastructure
  before adding parallel storage or workflows.

## Review findings to retain

Observed on **2026-10-09**; these are historical diagnostic observations, not current price targets:

| Finding | Evidence / relevant code | Implementation consequence |
|---|---|---|
| OMAB statement amounts are MXN; its trading price is USD per ADS. The model mixed these bases. | Deployed raw statement cells and listing metadata; `shared/normalize.py`, `shared/autofit_assumptions.py` | Reconcile currencies before forecasting, leverage/WACC, and per-security comparison—not just after computing fair value. |
| OMAB's deployed draft had no finite-life terminal configuration. | Deployed assumptions; `shared/report/model_compute.py` | Model concession life and investment obligations explicitly; renewal is a separate assumption/scenario. |
| OWL uses consolidated operating economics with approximately 683.9m Class A shares and no explicit Operating Group ownership bridge. | Deployed statements, share classes, assumptions, and company-detail response | Reconcile economic ownership and numerator/denominator scope; do not blindly add all share classes. |
| The headline probability-weighted fair value uses approximate exit-multiple scenarios, not the exact annual DCF. | `shared/report/model_compute.py::_annuity_px`, `compute` | Canonical scenario and headline computations must use the same executable model as the detailed workings. |
| Changing SBC and capex to 50% of revenue and setting concession life to ten years did not change the exit-scenario output. | In-memory diagnostic: OMAB base 4,933.40 unchanged; OWL base 115.06 unchanged | Add dependency/sensitivity regression tests: material assumptions cannot be displayed as levers while ignored by headline math. |
| Growth is clipped positive, margins are floored positive and mechanically improve, and peers inherit the subject's multiple. | `shared/autofit_assumptions.py` | Model decline, losses, organic/acquired growth, reinvestment, and independently calculated comparables. |
| Implausibility warnings do not prevent the summary from emitting an investment signal. | `shared/report/model_compute.py`, `app/backend/service.py::_compute_valuation_summary` | Enforce validation/publication status in every downstream consumer. |
| Investment Case's separate scenario workbench can seed revenue from the reference price. | `shared/investment_case/valuation.py::_seed_base_revenue` | Label illustrative/reverse-underwriting separately; it is not independently sourced company valuation. |

Do not publish a corrected OMAB/OWL fair value merely by adjusting the final output. Reconcile the
inputs and model structure, rerun, validate, and review.

## Delivery sequence

Priority key: **P0** correctness/containment; **P1** core pilot; **P2** expansion/polish.
Unchecked items below are **not fully delivered**; V01–V04 are partially implemented as recorded
below. Dependencies describe implementation order. Historical shipped UX features remain shipped.

1. **Contain and correct:** V01–V04.
2. **Shared foundation:** V05–V06, then V11's publication/consumer contract.
3. **Offline valuation pilot:** V07–V10 for OMAB and OWL.
4. **Interactive authoring:** V12–V13.
5. **Thesis surveillance pilot:** M01–M07; define monitoring contracts alongside the valuation pilot.
6. **Broaden and calibrate:** V14–V15 and M08.

**First implementation slice:** add validation status/publication gates and failing regression
fixtures for the confirmed currency, ownership, and ignored-input issues (V01–V04). Finish the
underlying reconciliations before claiming that agent-generated assumptions are trustworthy.

### First-slice implementation — 2026-10-09

- **V01 partial:** preserve provider documents/metadata alongside CSVs; explicit scale, currency,
  security, ADS and market-cap basis checks; USD-only global-rate overrides. Cross-currency models
  fail closed. Sourced FX conversion and a full typed per-cell fact store remain.
- **V02 partial:** prefer Total Debt over constituents; do not add overlapping short-term aliases;
  exclude investments from auto-draft cash. Shared equity allocation/other-claims bridge and explicit
  noncontrolling-interest reconciliation gate. Company-specific legal/economic ownership, excess
  operating cash, dilution and adjusted-metric reconciliation remain.
- **V03 partial:** Python headline scenarios/reverse/sensitivity now use the annual FCFF builder
  and equity bridge, with finite-life expiry enforced. Workbook/export, separate methods, return/IRR
  and simulation reconciliation remain; this is not a complete canonical-model migration.
- **V04 partial:** blocked/awaiting-review/approved/stale eligibility; effective-input/evidence
  digest, approval invalidation, source-aware summary cache and published-summary gates; labeled
  exploratory UI, null-safe upside and regression tests. Full review UX, lifecycle and all-consumer
  export validation remain.

See `docs/valuation-basis.md` for the schema, review procedure, limitations and migration impact.
Existing models lacking reconciled evidence and approval lose published FV/upside/signals by design;
no live assumptions have been converted or approved automatically.

### Next correctness/review bundle — 2026-10-09

- **V01:** sourced, dated reporting-per-trading FX contract; forecasts/nominal discounting remain in
  reporting currency, while prices/scenarios/sensitivity grids translate once to trading currency.
  Dates/direction/rate/source checks fail closed. Actual OMAB FX/rate evidence remains unfilled.
- **V04:** dossier review panel, explicit rationale/warning acknowledgement, optimistic revision
  checks, approval invalidation on engine/input changes, and portfolio price-currency safeguards.
  This is a personal-app review flow, not role-based identity verification or independent agent review.
- **V05 partial:** immutable input/evidence/engine/output revisions; effective globals frozen,
  tamper-checked deterministic replay, stable assumption IDs and optional supplied driver lineage.
  Full driver graphs, approved/proposed branches, and all-consumer artifact pointers remain open.
- **Validation bundle:** `python3 scripts/validate_valuation_bundle.py` runs offline synthetic
  acceptance tests, Python regressions, patch checks, frontend build and review-screen browser tests.
  No real models are approved or deployed. See `docs/valuation-basis.md`.

**Current local progress:** V06 proposal-runtime foundation, V07 structured architecture/evidence
planning and V08 bounded annual-underwriting graphs/replay/edit previews are implemented offline.
Durable remote dispatch and bounded approved-index snapshots now have local acceptance tests.
Dedicated FEVM Job `897847549464155` passed transport-only smoke run `34596542472372`
on October 10, 2026, without LLM calls. The app additions are now deployed and read-only-verified.
Live app dispatch/LLM-stage acceptance, full V08 valuation/approved branches,
V09 economic challenge and the V10 pilots remain open.
Monitoring agents and company-specific corrected valuations are not delivered by this bundle.

**Post-deployment input-size correction (deployed, read-only verified):** the Build button now
selects bounded recent history, business/security context and complete recent share-class
observations instead of sending the entire vendor archive. A partial-coverage receipt exposes
omissions; original source values/indices and publication blockers are preserved. Base inputs
target 35,000 characters, leaving room for bounded filing excerpts inside the 60,000-character
cap. The updated acceptance bundle passes 173 Python tests, frontend build and browser checks.
FEVM deployment `01f1c482af5e1af0bc9b1d4fcc0e0401` reported successful startup on
October 10, 2026 at 08:21:04 UTC. Authenticated health, tested frontend/input-selection UI,
OMAB/OWL remote-worker listings, publication blockers and app job permissions pass.
No live valuation jobs or LLM calls were started; live inference acceptance remains open.

**Worker response-completion follow-up:** the October 10, 2026 live OMAB retry
`652558977372674` failed; retained SQL output confirmed fenced JSON cut off mid-field at
the 3,000-token allowance. Worker release `1b4ab6c86754795d` raises architecture/underwriting
headroom to 8,000 tokens, requests compact complete JSON, retains output/schema/evidence
gates and prevents a failed remote attempt from consuming another call on replay without
an explicit retry. All 188 Python tests pass. The original OMAB request has four of six calls reserved and
no completed stages; no additional paid request was started. Published state remains unchanged.
Successful final-release live inference and economic acceptance are still open.
Transport-only smoke run `1016734628759542` passed with zero inference calls; authenticated
app health, tested frontend, remote-worker listings, blockers and app job permissions pass.

**Fresh OMAB live acceptance (partial):** with explicit user authorization, request
`be95fb729767c6530989e2d5ab546a4e`, run `892874394915090`, started October 10, 2026
at 09:04:58 UTC. Architecture and analyst proposals were saved; underwriting failed closed
because its horizon did not match the architect's proposed 20-year horizon. Five essential
evidence requests remain unresolved. Three calls were reserved, no repeated failed-attempt
inference consumed another reservation, and no retry was started. Revision identity,
review/approval, published revision list and publication blockers are unchanged.
Remaining work: underwriter horizon adherence and valid abstention for essential evidence gaps;
full live workflow and economic acceptance remain open. No new fair value was produced.

**Agent-runtime deployment verified:** FEVM app `research-cockpit`, deployment
`01f1c47ea01410d28f71ca88000d6de6`, started successfully on October 10, 2026 at 07:55:58 UTC.
The local acceptance bundle passes 163 Python tests, the frontend build and browser interactions.
Authenticated live checks pass for health, the tested frontend bundle, OMAB/OWL remote-worker
availability/listings, publication blockers, and app job permissions. No live research jobs or LLM
calls were started, and no assumptions or approvals were changed.

**Prior basis/pricing deployment verified:** FEVM app `research-cockpit`, deployment
`01f1c3ff89ca17018725660483767047`, started successfully on October 9, 2026 at 16:46:23 UTC.
The release acceptance command passes 79 Python tests, the frontend build and browser interactions.
Authenticated live checks pass for the review UI/APIs, OMAB/OWL FV/signal suppression and shared
portfolio/market prices. Verification did not approve or change live company models.

## Architecture pivot — research-led strategies, pilot first

The reviewed `system_architecture_engineering_specification.md` changes the execution order:
retain durable jobs, evidence snapshots, deterministic calculations and publication controls,
but replace prompt-generated annual model assembly with grounded facts, explicit normalization
and reviewed economic strategies. Do not ship the specification's hardcoded discount/multiple
defaults or its incomplete EPV examples unchanged.

- [x] **Local foundation:** strict fact/judgment/unresolved contracts and an offline finite-concession
  reference strategy with deterministic calendars, traffic/yield roll-forwards, reconciled
  zero-margin construction exclusion, explicit investment, finite rights, and security/FX bridge.
  Synthetic hand-calculation, missing evidence, contradiction, scale, expiry, replay and CLI tests
  are included in the acceptance bundle. No real OMAB valuation, API/UI integration or deployment.
- [x] **Reusable component foundation:** offline volume/yield and fee-assets mechanisms,
  independent forecast/life policies, and one shared equity/quotation/FX bridge.
  Synthetic cross-business and composition tests; no ticker-specific dispatch.
  Forecast-only PV does not masquerade as complete FV. See `docs/component-valuation-foundation.md`.
- [ ] **Next / V01–V02–V10:** hand-reviewed OMAB primary-source dossier and actual model scope;
  reconcile rights, segments, committed investment, ordinary/ADS units, economic claims and FX.
  Expand the strategy only where the actual business requires it; do not invent missing inputs.
- [ ] **V06–V07:** targeted approved retrieval, source-cell extraction, conflicts and evidence
  revisions driven by structured requests; distinguish absent disclosure from retrieval failure.
  - [x] Offline request-driven snapshot search, hashed/location-linked excerpts, architecture-gap
    adapter, exact source-cell proposals, conflict preservation, coverage/budget receipts and replay.
    See `docs/valuation-targeted-research.md`; candidates never resolve gaps or approve facts.
  - [x] Approved-index bounded targeted retrieval and durable parent-linked research revisions:
    backend submission/listing/replay, retrieval-only dedicated worker, per-query checkpoints,
    explicit retries/cancellation, frozen cutoff/provenance and preserved budgets. Local tests only.
  - [x] User-initiated agent search-phrase proposals and research-revision dossier UI:
    saved-gap validation, rationales/abstention/unaddressed requests, editable phrases,
    cost consent, scoped polling, immutable pending-submission recovery, source/coverage
    inspection, explicit retry/cancel and replay. Local tests; no deployment.
  - [x] Offline declared-human source-cell decisions and replayable evidence handoff:
    candidate/packet digests, retained source provenance, explicit interpretation/basis checks,
    conflict holds and exploratory-only eligibility. No canonical fact updates or authenticated
    approval. See `docs/valuation-evidence-review.md`.
  - [x] Persisted candidate sets and source-cell review UI/API with workspace-token identity
    verification, explicit reviewer-ID allowlist, append-only branches and same-key retry.
    Release requires user-authorization configuration and live smoke testing; no automatic
    canonical fact acceptance or publication. See `docs/valuation-evidence-review.md`.
  - [x] Exploratory component-model parameter proposal compiler, offline freeze/replay,
    persisted independent branches and dossier previews bound to one explicit evidence review.
    Exact fact/basis preservation, eligible-cell bindings, judgment/falsification receipts and
    deterministic workings; no saved-assumption or publication updates. Local tests only.
    See `docs/valuation-parameter-proposals.md`.
  - [ ] Bounded in-app agent authoring of component-model proposal branches using the new contract.
  - [ ] Autonomous iterative research orchestration, semantic/table extraction and authenticated
    review/accepted-fact handoff; then component-model parameter proposals.
- [ ] **V08–V09:** agent proposals compile into strategy parameters and proposed branches.
  Python owns calendars and roll-forwards. Add reverse expectations/sensitivity and economic challenge.
  - [x] Evidence-linked supplied-proposal compilation and exploratory branch previews.
  - [ ] Agent generation, independent economic review, reverse expectations and sensitivity.
- [ ] **V10:** OWL fee-paying-assets, fee economics, acquisition and public-ownership reference model;
  do not route it to a generic bank/TBV strategy.
- [ ] **V11–V13:** free-form dossier API/UI, human review and canonical accepted-artifact integration;
  then connect evidence → assumption → value → thesis monitoring from the existing monitoring epic.

See `docs/concession-strategy-pilot.md` for scope, runnable synthetic preview/replay, limitations
and the next implementation order. This foundation does not alter the deployed four-stage agent
workflow or any company model, published FV, portfolio signal or approval.

## Epic V — Evidence-Grounded Valuation Authoring

### V01 — Typed financial facts and currency/security reconciliation · P0
- [ ] Preserve source-cell currency, units/scale, fiscal period, reporting perimeter, definition,
  restatement status, document/page reference, and original vendor mapping.
- [ ] Reconcile reporting currency, trading currency, FX convention/date, ordinary shares, and
  ADS/ADR conversion; check price × eligible shares against the corresponding market-cap basis.
- [ ] Keep nominal cash flows, discount rates, terminal assumptions, debt/cash, and price comparisons
  on compatible bases. Make global defaults currency-aware rather than blindly applying them.
- **Acceptance:** OMAB fixtures detect MXN/USD mixing and repeated/missing ADS conversion;
  equivalent representations reconcile within documented tolerances; missing identity/units block
  publication rather than silently pass through.
- **Dependencies:** none.

### V02 — Ownership, normalized cash flows, and equity bridge · P0
- [ ] Reconcile consolidated economics to public-shareholder economics: noncontrolling interests,
  economic units, dilution, preferred claims, and other applicable obligations.
- [ ] Avoid adding Total Debt and its constituent debt lines twice; distinguish excess cash,
  operating cash, investments, and other assets instead of treating every investment as cash.
- [ ] Reconcile GAAP/IFRS and adjusted metrics, SBC/dilution treatment, acquisition effects,
  maintenance/growth capex, intangible/concession investment, and working capital.
- **Acceptance:** OWL fixtures demonstrate a consistent numerator/denominator ownership basis;
  omitted/double-counted claims and inconsistent adjustment bridges fail validation. No assumption
  that all share classes have identical economics.
- **Dependencies:** V01.

### V03 — One executable model for headlines, scenarios, and methods · P0
- [ ] Replace the disconnected headline annuity shortcut with evaluations of the same underlying
  annual model used by the detailed workings.
- [ ] Apply scenario-specific driver paths, reinvestment, SBC/dilution, ownership, and terminal
  treatment consistently to headline FV, sensitivities, reverse underwriting, and return outputs.
- [ ] Support finite-life businesses, including expiry during the forecast window; renewal,
  salvage, or exit value must not silently recreate an unjustified perpetuity.
- [ ] Label genuinely different methods as cross-checks, not interchangeable calculations.
- **Acceptance:** changing a material cash-flow assumption changes every dependent output;
  concession-expiry tests work in explicit forecasts and scenarios; UI, model, and report numbers
  tie. Re-run the unchanged-output diagnostic recorded above.
- **Dependencies:** V01–V02.

### V04 — Publication gates and valuation regression suite · P0
- [ ] Introduce explicit states: draft, blocked, awaiting review, approved, stale, superseded.
- [ ] Suppress authoritative FV/upside signals, sizing conclusions, and misleading portfolio
  aggregates for invalid/unapproved models; retain clearly labeled exploratory workings.
- [ ] Separate hard accounting/unit failures from economic plausibility warnings. Extreme FV,
  terminal concentration, unbracketed reverse solves, and surprising implied returns require review,
  not arbitrary output clipping.
- [ ] Test currency/scale invariance, ADS conversion, ownership allocation, debt bridges, negative
  growth/losses, reinvestment, terminal expiry, probability validity, and cross-consumer consistency.
- **Acceptance:** known-invalid OMAB/OWL fixtures cannot emit an unqualified “outperform” signal;
  reviewed extreme valuations can be retained with rationale, but hard basis failures cannot be
  waived into an approved valuation. Valuation-specific tests run with the existing test suite.
- **Dependencies:** start alongside V01; completion requires V01–V03.

### V05 — Versioned valuation artifact and driver lineage · P1
- [ ] Define a minimal artifact contract: company/security identity, as-of cutoff, facts, evidence,
  assumptions, model specification/code, scenarios, outputs, validation, review, and versions.
- [ ] Give assumptions/drivers stable IDs, units, definitions, periods, evidence links, dependency
  links, rationale, alternatives, uncertainty, and disconfirming conditions.
- [ ] Freeze input/source snapshots and retain data, model, prompt, runtime, and reviewer versions;
  preserve approved and proposed branches without overwriting history.
- **Acceptance:** replaying a frozen artifact reproduces numerical outputs; a displayed forecast
  driver can be traced to facts and judgment; restated inputs create a new version.
- **Dependencies:** V01–V04 interfaces.

### V06 — Durable offline agent runtime · P1
- **In progress — local proposal-runtime foundation delivered:** standalone durable queue,
  frozen evidence packets, analyst/reviewer checkpoints, manual retries, cooperative cancellation,
  deduplication, bounded calls/input/output/time allowances, and a blocked-model research panel.
  Saved valuations and publication gates remain untouched. See `valuation-agent-runtime.md`.
  Remote immutable submissions, idempotent Jobs dispatch, worker-owned checkpoints, three-attempt
  controls, bounded source snapshots and mirror exclusion are implemented and tested. The
  dedicated FEVM worker and app controls are deployed; live dispatch/LLM-stage acceptance remain open.
  Agent-directed retrieval, exact currency-cost accounting and isolated executable models remain open.
- [ ] Add queued, resumable jobs with explicit stages, retries, cancellation, idempotency, progress
  events, source-fetch caching, deduplication, and concurrency/cost/token/time budgets.
- [ ] Give agents approved retrieval and deterministic calculation tools; isolate generated model
- [ ] Treat source documents as evidence, not instructions. Validate generated artifacts and safe
  presentation formats before use.
- [ ] Begin with a lead analyst and an independent reviewer; retain disagreements and questions.
- **Acceptance:** page loads serve saved artifacts and never wait for an LLM; interrupted jobs
  resume without duplicate publication; failures and budget exhaustion are visible and recoverable.
- **Dependencies:** V05; reuse existing job/document infrastructure.

### V07 — Business-model architect and evidence plan · P1
- [x] Add a versioned architecture checkpoint, validated source pointers, fact/judgment/unknown
  separation, component/driver graph, forecast and accounting/bridge/terminal policies, bounded
  targeted evidence requests and UI inspection. Existing two-stage jobs remain resumable.
  See `valuation-architecture.md`; synthetic acceptance is included in the single-shot validator.
- **Acceptance boundary:** live source-grounded classification and real OMAB/OWL plans have not
  been generated or independently verified. Pointer validity is not semantic source support.
  Bounded initial approved-index retrieval is implemented; live read-only checks found partial
  OMAB/OWL coverage. Research-plan fulfillment, semantic verification and live LLM acceptance remain open.
- [ ] Classify the business using its actual economics, accounting template, segments, capital
  structure, and disclosures; select an appropriate model and cross-checks.
- [ ] Propose driver/segment structure, forecast horizon, normalization, reinvestment, discounting,
  ownership bridge, and terminal treatment with sourced rationale.
- [ ] Identify missing essential evidence and generate a bounded research plan; allow abstention.
- **Acceptance:** OMAB receives a concession architecture and OWL an asset-management architecture;
  neither is forced into a generic CAGR/margin template or the existing six-key workbench.
- **Dependencies:** V05–V06.

### V08 — Evidence-grounded underwriting and model construction · P1
- [x] Add a versioned underwriter checkpoint, bounded dimension-checked annual formula graphs,
  explicit sourced/judgment/missing inputs, scenario paths, deterministic frozen replay, annual
  workings UI and unsaved edit previews. Legacy workflows retain their stages and budgets.
  See `valuation-underwriting.md`; included in the single-shot offline acceptance bundle.
- **Scope boundary:** no automatic enterprise/public-security FV, no new-model publication or
  persisted approved edited branches, and no live source-grounded OMAB/OWL pilot. Syntactic source/
  dimension checks do not establish economics or source-unit/perimeter correctness.
- [ ] Build forecasts from operating mechanisms and driver paths; separate organic growth from
  acquisitions, mix/pricing/volume, temporary effects, and definition changes.
- [ ] Record why each assumption is reasonable, alternative interpretations, evidence limitations,
  what would falsify it, and whether it is user-confirmed.
- [ ] Produce executable models with annual workings; permit company-specific graphs, tables,
  scripts/notebooks, and narrative within the artifact/execution contract.
- [ ] Construct coherent business scenarios rather than cosmetic CAGR multipliers. Scenario
  weights, if used, are explicit judgment—not calibrated probabilities merely because an LLM
  supplied them. Monte Carlo must not launder unreliable inputs into apparent certainty.
- **Acceptance:** output can be recalculated without an LLM; missing essential inputs prevent
  publication; assumptions and calculations remain inspectable and editable.
- **Dependencies:** V03, V07.

### V09 — Independent accounting and economic challenge · P1
- [ ] Combine deterministic validation with a separate reviewer examining source support,
  accounting reconciliation, competitive constraints, growth/capital needs, and terminal economics.
- [ ] Compare with history, management guidance, suitable peers, reverse underwriting, and
  alternative model structures without forcing valuation to match the market price.
- [ ] Record objections, conflicting evidence, unresolved questions, revisions, and review outcome.
- **Acceptance:** known defective fixtures are caught for the right reasons; unsupported factual
  claims and untested model dependencies cannot pass merely on agent self-reported confidence.
- **Dependencies:** V04, V08.

### V10 — OMAB and OWL end-to-end valuation pilots · P1
- [ ] **OMAB:** passenger traffic/mix; aeronautical tariffs/yields; commercial, parking, lease/hotel
  economics; costs; construction-accounting effects; actual required/maintenance investment;
  concession life and separate renewal treatment; MXN/FX/discount-rate/ADS reconciliation.
- [ ] **OWL:** fee-paying assets by business; fundraising/deployment/realizations; fee rates; organic
  versus acquired cohorts; fee-related and performance earnings; distributable cash; financing,
  acquisition obligations, dilution, and Operating Group/public-shareholder ownership.
- [ ] Reconcile previous outputs to proposed outputs with an accounting/assumption impact
  explanation. User review is required; do not manufacture a corrected FV from a final-number patch.
- **Acceptance:** two reproducible, independently reviewed, company-specific dossiers with
  coherent scenarios and proposed monitoring contracts; no production rollout to other names yet.
- **Dependencies:** V01–V09.

### V11 — Canonical publication and consumer integration · P1
- [ ] Establish an approved-artifact pointer with explicit model date, price date, currency, security
  basis, status, source versions, and stale reasons.
- [ ] Serve accepted outputs to company/valuation pages, portfolios, reports, exports, and monitors;
  preserve legacy models during migration and clearly label illustrative/reverse-underwriting.
- [ ] Define behavior for missing, blocked, stale, and superseded artifacts, including portfolio
  coverage gaps rather than silently counting excluded values as zero.
- **Acceptance:** all consumers identify the same accepted version; changing a proposed branch
  cannot change published portfolio conclusions; cached output invalidation is version-based.
- **Dependencies:** contract starts with V05; rollout requires V04 and V10.

### V12 — Free-form Valuation Studio · P1
- [ ] Add a document/notebook-style workspace: business economics, evidence, model workings,
  scenarios, reviewer challenges, unresolved questions, and version history.
- [ ] Allow model-specific sections and forecast tables rather than requiring fixed sliders;
  use safe rendering with expandable formulas and source references.
- [ ] Display stages, tool/calculation summaries, evidence, decisions, validations, and revisions;
  distinguish facts, guidance, views, and judgment.
- **Acceptance:** both pilot models fit naturally; the user can follow a material assumption from
  disclosure to forecast to value without reading job logs or trusting an opaque narrative.
- **Dependencies:** V05–V06, V10–V11.

### V13 — Conversational revisions, branches, and review controls · P1
- [ ] Support instructions such as “separate acquisitions from organic growth,” “make concession
  renewal a separate scenario,” and “show which assumptions create the upside.”
- [ ] Create proposed branches with before/after assumptions, model-structure changes, recalculated
  values, and an impact explanation; preserve the accepted version.
- [ ] Offer accept, reject, request more evidence, edit, defer, and revert with durable reasons.
- **Acceptance:** accepted changes publish only after validation/review; attribution distinguishes
  changed facts, changed judgment, changed structure, and changed market-price assumptions.
- **Dependencies:** V09, V11–V12.

### V14 — Independent comparables and broader model families · P2
- [ ] Fetch and reconcile actual peer financials/multiples and comparable definitions; stop
  presenting copies of the subject's multiple as independent corroboration.
- [ ] Expand model families after the pilots; use appropriate cross-checks, not one mandatory
  template. Keep negative growth, losses, cyclicality, and domain-specific constraints representable.
- **Acceptance:** every comparable has its own source/as-of basis; unsupported methods are labeled
  unavailable rather than filled with generic placeholders.
- **Dependencies:** V10–V11; overlaps existing C1/C9/C10 and Valuation Deep Dive.

### V15 — Forecast-outcome tracking and calibration · P2
- [ ] Compare frozen driver forecasts with subsequent reported outcomes, including errors,
  assumption persistence, revisions, and management-guidance delivery.
- [ ] Evaluate on historical information cutoffs without look-ahead; do not optimize assumptions
  merely to fit subsequent share prices. Review numerical accuracy and evidence/reasoning quality.
- **Acceptance:** each material assumption has an outcome history; evaluation fixtures respect
  source availability dates and distinguish decision quality from market-price movement.
- **Dependencies:** V05, V10–V11; reuse snapshots and existing delivery/review features.

## Epic M — Intelligent Thesis Surveillance

### M01 — Monitoring contracts and underwriting dependency graph · P1
- [ ] Connect evidence → KPI → business mechanism → model assumption → valuation output →
  investment decision using V05's stable IDs rather than a duplicate driver registry.
- [ ] For each material assumption capture supporting evidence, leading indicators, disconfirming
  conditions, measurement definition, expected cadence, review conditions, and monitoring scope.
- [ ] Include qualitative events and confidence deterioration, not just numeric thresholds.
- **Acceptance:** OMAB/OWL each have contracts for their five most important assumptions; the user
  can inspect why an observation matters and edit the contract.
- **Dependencies:** V05 and draft V10 artifacts; existing B2/C13 are foundations, not completion.

### M02 — Source collection and investigation candidate detection · P1
- [ ] Collect quarterly filings/releases, transcripts, guidance, and a bounded set of approved news
  sources; add relevant competitor/customer/regulatory sources when specified by a contract.
- [ ] Detect new facts, model variances, guidance/definition changes, and dropped KPIs; preserve
  source timestamps, versions, comparable periods, and freshness.
- [ ] Deduplicate repeated coverage and distinguish source corrections, restatements, and new
  evidence. Detection creates a candidate, not a conclusion or automatic model revision.
- **Acceptance:** replaying or retrying ingestion cannot multiply alerts; one news story covered
  by several outlets forms one candidate/investigation.
- **Dependencies:** V06, M01; reuse document ingestion and KPI extraction.

### M03 — Persistent agentic investigations · P1
- [ ] Investigate novelty, source credibility, relevance, affected drivers, causal mechanisms,
  corroboration, contradictory evidence, and missing facts.
- [ ] Distinguish timing/noise, currency/mix, acquired growth, definition changes, and structural
  developments. Follow a bounded evidence plan rather than interpreting a headline in isolation.
- [ ] Retain hypotheses, evidence, open questions, next-review conditions, and resumable state:
  candidate, investigating, watch, confirmed impact, invalidated, resolved/no action.
- **Acceptance:** new evidence updates a durable case; the agent can conclude no action or
  insufficient evidence, and can resume without relying on conversational memory.
- **Dependencies:** V06, M01–M02.

### M04 — Materiality and proposed valuation impact · P1
- [ ] Assess measurement validity, economic significance, expected persistence, and decision
  significance; distinguish small critical-driver changes from large irrelevant movements.
- [ ] Separate changed facts from interpretation. Allow “confidence weakened; impact not yet
  quantifiable” rather than inventing a precise value or probability.
- [ ] Evaluate plausible assumption changes through the same executable model as valuation;
  produce range/sensitivity and structural alternatives when warranted.
- **Acceptance:** findings explain the mechanism and affected periods/assumptions; headline
  changes do not bypass accounting validation or automatically change an accepted artifact.
- **Dependencies:** V03–V05, V11, M03.

### M05 — Persistent check-in briefing and review inbox · P1
- [ ] Present **Needs your decision**, **Under investigation**, **Watchlist**, and **Resolved /
  no action**, including what changed since the user's last review.
- [ ] Each finding explains what changed, affected assumptions, materiality, supporting and
  contradictory evidence, uncertainty, and next action.
- [ ] Consolidate related stories into one evolving investigation; keep unresolved material issues
  visible until addressed. Rank by decision significance rather than article volume or price alone.
- **Acceptance:** a check-in briefing is available from persisted state without waiting for an LLM;
  acknowledged, deferred, reopened, and resolved items behave consistently across visits.
- **Dependencies:** M03–M04; extend B1/B2 rather than add another disconnected worklist.

### M06 — Human review and model-change proposals · P1
- [ ] Turn confirmed findings into proposed valuation branches, with changed assumptions, rationale,
  validation, and before/after impact. Never silently update accepted models.
- [ ] Offer accept, reject, request more research, keep watching, edit, and defer; record reasons.
- [ ] After acceptance, update the artifact pointer and associated monitoring contracts together;
  resolve or explicitly retain the investigation's outstanding questions.
- **Acceptance:** a monitoring finding can lead to a reviewed model revision with full lineage;
  rejection/defer leaves the accepted model untouched; no trading action is produced.
- **Dependencies:** V11, V13, M04–M05.

### M07 — OMAB/OWL surveillance pilot and alert controls · P1
- [ ] Pilot quarterly disclosures and approved news for the five contracts per company, then
  generate a consolidated check-in briefing and proposed revisions where justified.
- [ ] Exercise hypothetical OWL fundraising/deployment timing versus structural weakness and
  OMAB traffic/mix/yield versus cost/investment changes; label synthetic events as fixtures.
- [ ] Reserve immediate notifications for user-defined critical events; configure channels,
  quiet hours, severity, repeated-update suppression, pause/resume, and per-contract cadence.
- **Acceptance:** repeated headlines do not spam; weak/contradictory evidence stays visible without
  being promoted to certainty; routine findings remain in the inbox; urgent delivery is opt-in.
- **Dependencies:** M01–M06.

### M08 — Monitoring evaluation, coverage, and operational reliability · P2
- [ ] Measure false positives, missed material events, timeliness, evidence quality, reviewer
  agreement/disagreement, user decisions, and stale-source/coverage gaps.
- [ ] Add replay fixtures for duplicate news, KPI redefinition, restatements, temporary misses,
  conflicting guidance, structural breaks, unavailable sources, and job interruptions.
- [ ] Track collection freshness, job health, costs, latency, and unresolved investigations;
  stale/missing source coverage must not be presented as a healthy thesis.
- **Acceptance:** investigations can be audited and replayed at an information cutoff; evaluation
  includes no-action outcomes, not just alert volume or agent-reported confidence.
- **Dependencies:** V06, V15, M07.

## Reuse and integration map

| Existing capability | Starting point | Backlog linkage |
|---|---|---|
| Draft assumptions and valuation math | `shared/autofit_assumptions.py`, `shared/report/model_compute.py`, `shared/valuation/` | V01–V04, V07–V10 |
| Normalized statements and raw source cells | `shared/normalize.py`, `shared/valuation/inputs.py`, gathered statement JSON | V01–V02, V05 |
| Filing analysis and evidence verification | `shared/docs/filing_analyst.py`, document store/reading room | V07–V09, M02–M03 |
| KPI discovery, definitions, and model-driver flags | `shared/docs/kpi_discover.py`, `shared/docs/kpi_registry.py` | V05, M01–M02; C13 |
| Claims and claim-to-assumption links | `shared/investment_case/valuation.py`, investment-case store | V05, V11, M01; distinguish illustrative models |
| Proposed/accepted views and model history | `shared/views.py`, `shared/snapshot.py` | V05, V13, V15, M06; expand to structural/terminal changes |
| Background research jobs | `app/backend/jobs.py`, `app/backend/pipeline.py`, `run_stage.py` | V06; do not run agents in read endpoints |
| Decision → monitor → review | `shared/investment_case/monitoring.py`, decisions/review APIs | M01–M08; B2 |
| Attention worklist and guidance delivery | Existing B1, C5, C6, review/calibration features | M05, V15, M08 |
| Valuation presentation and published summaries | `app/backend/service.py`, valuation pages/reports, portfolio consumers | V04, V11–V13 |

## Decisions before implementation

- [ ] Choose artifact/investigation persistence and concurrency strategy after reviewing existing
  schemas. Immutable artifacts may live on the volume; pointers, states, and review actions need
  durable, concurrency-safe updates. Do not assume the current single-replica file mirror scales.
- [ ] Select the LLM/runtime and approved source access, execution boundary, budget, retention,
  and notification channel. Existing platform capabilities should be preferred where sufficient.
- [ ] Decide how to migrate legacy drafts without presenting them as approved agent-authored models.
- [ ] Agree acceptance tolerances and reviewer/publication policy for the OMAB/OWL pilots.

## Pilot exit checklist

### Supervised research-round slice (FEVM deployed October 12, 2026)

- [x] Frozen-evidence coordinator → researcher → challenger role calls; ordered
  question dependencies, explicit abstention and evidence-linked judgment cards.
- [x] Offline worker exits at human review; bounded calls/time, checkpointed retries.
- [x] Authenticated accept/edit/reject/investigate/defer decision branches;
  separate deterministic agent/user models and immutable audit/replay receipts.
- [x] Explicitly authorized continuation from a saved decision; no automatic
  retrieval, inference, canonical updates or publication when saving decisions.
- [x] Deploy this slice; verify live health, matching frontend and consent rejection.
- [ ] Perform interactive OMAB/OWL evidence-backed research-round acceptance.
- [x] Add a local top-level six-stage research workspace, explicit next actions,
  direct team output and separate collapsed legacy audit history.
- [x] Deploy the workspace navigation and verify the exact frontend and read routes.
- [ ] Perform signed-in interactive workspace usability acceptance.
- [x] Add local guided source-cell capture with exact quote/occurrence anchors,
  explicit dimensional interpretation and unchanged candidate-review gates.
- [x] Deploy guided capture; verify live health, exact frontend and unchanged worker.
- [ ] Validate guided capture interactively on completed OMAB evidence.
- [ ] Add separately consented agent-assisted source-cell extraction; do not
  present anchored proposals as semantically verified or automatically accepted.
- [ ] Add separately authorized evidence investigations, parallel research teams,
  explicit combined-model assembly and calibrated uncertainty evaluation.
- Details and current limits: `docs/valuation-research-rounds.md`.

- [ ] OMAB/OWL facts, currencies, ownership, cash-flow definitions, and terminal treatments reconcile.
- [ ] Detailed workings, scenarios, headlines, portfolio summaries, and reports use consistent models.
- [ ] Both companies have reproducible artifacts, reviewer findings, and explicit approval status.
- [ ] Valuation Studio supports evidence inspection, model-specific workings, and proposed branches.
- [ ] Five underwriting monitoring contracts per company are connected to the accepted artifacts.
- [ ] Quarterly/news fixtures produce investigated findings, a check-in briefing, and reviewed
  proposals without automatic publication or alert spam.
- [ ] Accounting, valuation, agent, monitoring, and publication regression/replay checks pass.
- [ ] Source freshness, unresolved evidence, job failures, and budget limitations are visible.

No feature in this backlog is marked delivered merely because a legacy screen or monitor exists.