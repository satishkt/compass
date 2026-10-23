# Project document: valuation-research-rounds

Source: research_val_personal/docs/valuation-research-rounds.md
Kind: design document; may describe planned rather than shipped features.

# Supervised valuation research rounds

## Implemented local workflow

From a terminal architecture dossier, retrieve evidence and create a reviewed
source-cell branch first. Expand **Supervised research rounds and approval inbox**
under the evidence review. Select that branch, enter a question, and explicitly
authorize inference.

The dedicated offline worker runs three sequential roles:

1. Coordinator: orders investigation questions and their dependencies.
2. Researcher: proposes evidence-linked judgments, alternatives and falsification
   conditions. A component model is optional; insufficient evidence must remain
   unresolved rather than being replaced with a generic extrapolation.
3. Challenger: independently critiques every judgment, or explicitly abstains.

All roles use the same frozen reviewed evidence. The challenger sees the prior
outputs; it is a separate critique call, not an independent evidence collection.
This first slice is not a parallel agent pool.

The worker exits at `awaiting_review`; no compute remains waiting for a human.
Each round allows at most four reserved calls, 600 seconds, 8000 output tokens
per call, and no retrieval queries. Failed retries retain their budgets and saved
role outputs. Original request bodies and keys survive unconfirmed UI submissions.

## Human iteration and model branches

Each card can be accepted, edited, rejected, investigated or deferred with an
explicit rationale. Numerical edits preserve the typed parameter's dimensions
and evidence lineage. Agents cannot introduce accepted facts. Every resolved
model judgment must have its own matching card and evidence binding.

Saving decisions creates an immutable, authenticated decision branch. The
agent model remains unchanged. A separate user model retains accepted judgments,
applies explicit edits, and makes rejected, deferred, investigated or omitted
model judgments unresolved. Calculations remain deterministic and exploratory;
missing inputs block completeness.

**Prepare another round from this decision** fills a draft, retains the exact
review branch and freezes the previous decision lineage. It does not launch
inference. A new round requires new explicit consent. Investigation questions
remain `awaiting_research_permission`; evidence collection is a separate,
explicitly authorized workflow. Changed evidence requires a fresh round.

## Audit and safeguards

Requests, role outputs, final packets and decision branches are durable volume
records with content receipts. Replay revalidates reviewed cells, the original
architecture, all role contracts, role checkpoint correspondence, decisions and
deterministic calculations. Same-key retries cannot change the question,
reviewer or saved decision body.

Writes require the existing verified workspace-user allowlist. Generic job
controls cannot bypass authenticated round controls or retry consent. No round
or decision writes canonical facts, saved assumptions, approved fair values,
portfolio signals, or publication status. The UI renders evidence and rationale
as text, not HTML.

History displays the most recent 20 rounds; immutable records remain stored.
Combined model assembly, calibrated confidence intervals, autonomous retrieval,
parallel research teams and KPI-driven monitoring remain future work. This
feature was deployed to FEVM on October 12, 2026. Live health, exact frontend
and authenticated consent-rejection checks passed. A real evidence-backed
research round remains interactive acceptance testing; none was launched during
deployment.

## Local verification

`python3 -m pytest tests/test_research_rounds.py -q` covers role validation,
model branching, typed edits, identity and consent, replay tampering, cancellation,
checkpoint recovery, wire versions and retained budgets with mocked transports.

`node tests/valuation-research-rounds.mjs` from `app/frontend` covers consent,
lost-ack reload recovery, the inbox, continuation preparation, company isolation
and untrusted-source escaping using a localhost fixture, without live inference.

Both are included in `python3 scripts/validate_valuation_bundle.py`.

October 12, 2026 local acceptance passed: 23 focused round tests, 417 full
Python regression tests, the production frontend build, and all five browser
suites. Existing FastAPI/httpx deprecation and frontend chunk-size warnings
remain non-blocking. No live data, inference or deployment was used.