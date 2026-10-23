# Project document: valuation-architecture

Source: research_val_personal/docs/valuation-architecture.md
Kind: design document; may describe planned rather than shipped features.

# V07 — Business-model architecture and evidence planning

## What happens before underwriting

New valuation research jobs have four checkpoints:

1. **Architect:** identify the disclosed economics and propose a company-specific model plan.
2. **Analyst:** reason from that saved plan, retaining essential gaps and alternative interpretations.
3. **Underwriter:** turn supported inputs and judgment paths into bounded annual formula graphs,
   or retain unknowns/abstain rather than invent estimates.
4. **Reviewer:** challenge the architecture, analyst and annual workings separately, including whether cited source
   leaves actually support the claims.

The architecture is not executable code or a fair-value calculation. Its schema lives in
`shared/valuation/architecture.py`. The review UI displays the saved plan, economic components,
driver dependencies, forecast mechanics, falsification tests, source excerpts and research requests.
Neither a finished job nor a plan-ready label approves or changes a saved valuation.

## Contract

An architecture artifact contains the usual `status`, `analysis`, and `questions`, plus `plan`:

- Business classification, economics and reporting template.
- Proposed method, forecast horizon and rationale.
- Economic components linked to stable driver IDs.
- Drivers with definitions, units, mechanisms, forecast/fade treatment, dependency IDs and
  falsification conditions.
- Policies covering accounting normalization, reinvestment, nominal discounting, public ownership
  and cash/debt claims, reporting/trading currency and terminal/finite-life economics.
- Alternative cross-checks and a bounded evidence plan.

Every substantive claim separates `fact`, `judgment` and `unresolved` and carries a list of
absolute JSON pointers into the frozen evidence packet. References must resolve to nonempty scalar
leaves. Fact claims require profile, normalized statement, shares or snapshotted document sources, not existing valuation
assumptions. Fiscal years are part of statement pointers; slash/tilde-containing keys use JSON
pointer escaping. Array indices support vendor share records.

A resolving pointer only proves that a source exists in the packet. It **does not prove semantic
support, source accuracy, recency, or independence**. Vendor profile text is not equivalent to a
primary filing. Reviewer challenge and eventual human source review remain necessary. Self-labeling
a claim as a fact does not establish its truth.

Unresolved claims need essential evidence requests targeting their exact architecture paths.
Unsupported classification requires abstention; an abstaining artifact must identify essential
missing evidence. Unknown driver IDs, dependency cycles, extra fields (including execution code),
and unsupported schema versions are rejected before the analyst can continue.

## Bounded research and initial source snapshots

The schema permits up to 8 components, 12 drivers, 6 cross-checks and 12 research requests.
Each request specifies the missing question, economic consequence, affected architecture paths,
essential/optional status, disclosure to find and a 1–3 document allowance. Total requested
documents cannot exceed 20. A proposed horizon is 1–100 years; abstention may leave it unresolved.
Existing runtime input/output/call/time limits still apply.

These are retrieval **requests**, not claims that the research plan was fulfilled. Local jobs
use normalized statements, profile, shares and assumptions. Remote jobs also snapshot bounded,
dated excerpts from approved-index filings before the first architecture call. Claims may cite
`/documents/0/excerpts/0/text`; qualitative text is not a typed numerical input. Snapshots carry
hashes and locators, but coverage remains partial. Agent-directed follow-up retrieval, news
ingestion and source-cell numerical extraction remain open; see `valuation-agent-runtime.md`.

The worker derives `planning.ready_for_underwriting` from a proposal with no essential gaps,
and saves the outstanding essential gap IDs and document allowance. This is architecture-stage
readiness for further review—not proof of input sufficiency, agreement from the reviewer, approval
of numeric assumptions, or publication readiness. `publishable` remains false.

## Business-specific behavior and acceptance boundary

There is no ticker-to-template switch. Architect instructions ask for finite rights, passenger
traffic/mix/yields, construction accounting and required investment **when the supplied economics
support a concession model**. They ask for fee-paying assets, fee rates, organic/acquired cohorts,
fundraising/deployment, fee/performance earnings and economic-unit reconciliation **when supplied
economics support an asset-manager model**. Other companies need their own architecture.

Offline synthetic fixtures cover these distinctions, missing concession life, public ownership
gaps, missing/circular dependencies, bad citations, legacy workflow compatibility and UI rendering.
The fixtures do not establish real OMAB/OWL facts or demonstrate a live model's reasoning quality.
Live source-grounded acceptance and the V10 pilots remain pending.

V08's local annual graph engine now supplies deterministic, recalculable workings and unsaved edit
previews; see `valuation-underwriting.md`. Source-grounded public ownership/FX/terminal valuation,
approved artifact branches and pilots remain open. It must not merely translate this plan into a
new FCF CAGR. The FEVM worker is provisioned and transport-smoke-tested, and app controls are
deployed/read-only-verified. Live dispatch and LLM-stage acceptance remain pending;
see `valuation-agent-runtime.md`.

Run the single-shot offline checks with `python3 scripts/validate_valuation_bundle.py`.