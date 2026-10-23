# Project document: valuation-search-dossier

Source: research_val_personal/docs/valuation-search-dossier.md
Kind: design document; may describe planned rather than shipped features.

# Agent search plans and follow-up research dossier

This is a human-controlled research loop, not a new published valuation:

1. Open a terminal valuation job with a saved architecture, then **Follow-up research dossier**.
2. Explicitly allow an agent planning call and select **Propose search plan (LLM)**.
   The page queues work; it does not invoke the model synchronously.
3. Inspect the proposed phrases, rationales, questions and unaddressed gap IDs.
   Select **Use proposed search plan** to copy phrases into an editable draft.
4. Select the gaps and revise literal phrases. Nothing is retrieved automatically.
5. Select **Launch reviewed searches**. The retrieval-only child preserves the parent
   evidence, cutoff and approvals.
6. Inspect coverage, open questions, source passages, exact character locations,
   hashes, worker steps and replay results. These are unreviewed candidates, not
   accepted facts or permission to publish a fair value.

## Search-planning contract

`shared/valuation/search_planning.py` validates a separate proposal with exactly
`status`, `analysis`, `questions`, and `searches`. Each search has a saved `gap_id`,
1–8 literal `terms`, and a `rationale`. Unknown/duplicate IDs, unsupported fields,
invalid terms and inconsistent abstentions are rejected.

Saved model targets, source allowlists, document limits, cutoff, questions and
assumptions cannot be changed by the planner. Partial proposals preserve an explicit
unaddressed-gap receipt. Typed validation does not prove that a phrase or rationale
is economically sensible; human review remains necessary.

The separate child request freezes the parent architecture and evidence. Its worker
uses the existing governed `ai_query` transport with the new `search_plan` prompt
family, reserves allowance before inference, and freezes `search-plan.json` before
completing its checkpoint. No retrieval or model calculation runs in this stage.

Limits: two total reserved LLM calls, 180 cumulative seconds, up to 90 seconds per
call, 3,000 requested output tokens per call, and the existing three-attempt ceiling.
A normal successful request uses one call. A failed call retains its reserved
allowance and needs explicit retry. A saved proposal is reused after a lost checkpoint
acknowledgement. A new request key is a new user-authorized job, not a budget reset.

Search proposals can abstain. Fenced/truncated/non-JSON or invalid responses still
fail closed through the existing response parser; no numerical facts are inferred
from the planner's output. Replay is an integrity check, not evidence acceptance.

## API and worker compatibility

`POST /api/companies/{ticker}/valuation-agent-jobs/{parent-id}/search-plans`
accepts exactly `{"request_key": "<32 lowercase hex characters>"}`.
`GET` at that path lists recent planning children. Existing child-job controls
support `retry`, `cancel`, and `replay-search-plan`.

Planning and retrieval children use follow-up wire protocol version **4**; the
existing full valuation workflow remains version **3**. An older version-3 worker
rejects version-4 requests before inference rather than mistaking a follow-up for a
full valuation. The new worker rejects unknown kinds and protocol mismatches.
Release the app and dedicated worker together before using these features.

## Dossier behavior

`app/frontend/src/lib/ValuationResearch.jsx` is scoped by ticker and parent job ID.
It polls only while the dossier is expanded and requires the remote runtime.
Planning needs an explicit cost-consent checkbox. Retrieval drafts start with empty
phrases; there are no hidden ticker-specific search defaults.

Unconfirmed submissions persist their original body and idempotency key in local
storage. Reloading offers an explicit retry of that frozen submission, not a new
request with edited phrases. Confirmed submissions clear the pending key. Ordinary
valuation listings exclude both types of follow-up child.

Source text, planner text and URLs are rendered as escaped text, never injected HTML
or executable links. Missing matches are labeled as limited index coverage, not proof
of absent disclosure. Budget and document-limit omissions remain visible. Replay
does not close evidence gaps. UI retry labels disclose possible additional planning
call costs.

## Still open

- Accepted-source-cell annotation/review and authenticated fact handoff.
- Evidence-supported component-model parameter proposals and updated dossiers.
- Automated iterative research orchestration with explicit stopping conditions.
- Live FEVM deployment and authorized smoke/economic acceptance tests.

No deployment, live inference, portfolio signal change, accepted fact or published
valuation is part of this implementation.

## Local validation

`python3 scripts/validate_valuation_bundle.py` passes 289 targeted acceptance tests,
324 full Python tests, the production frontend build, whitespace checks and both
Playwright suites. The new planner has 20 Python tests; the dossier suite verifies
cost consent, manual phrase review, no automatic retrieval, malformed phrase blocking,
pending submission recovery after reload, source escaping, replay and ticker isolation.
Polling discards responses predating a submission/control action.

Existing Starlette/httpx deprecation and frontend chunk-size warnings remain.
All Databricks/LLM transports in acceptance tests are mocked; this is not live
economic or deployment acceptance.