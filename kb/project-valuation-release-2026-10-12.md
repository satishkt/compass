# Project document: valuation-release-2026-10-12

Source: research_val_personal/docs/valuation-release-2026-10-12.md
Kind: design document; may describe planned rather than shipped features.

# FEVM test release — October 12, 2026

## Latest release: guided evidence capture

App deployment `01f1c66f5815113fad8043202ff5c2cb` succeeded at
19:02:19 UTC (15:02:19 America/New_York).
Source: `/Workspace/Users/satish.terala@databricks.com/research_cockpit_releases/20261012-guided-capture`.
Frontend `/assets/index-xiOEi8ix.js` matches the tested local build exactly.

The Evidence stage now offers guided exact-quote source-cell capture and explicit
numeric/dimensional interpretation. The advanced JSON editor remains available;
candidate saving and separate authenticated review gates remain unchanged.

Backend, shared code, dependencies and app configuration match the preceding
release. Worker `897847549464155` remains on release `2929919c5de91101`;
research pipeline `557334341404887` was not modified.

Pre-deployment acceptance passed: 421 Python tests, production build and all seven
browser suites. Live read-only checks passed for health, exact frontend bytes,
capture controls, workspace history routes and unchanged worker release.
OMAB still has zero completed evidence revisions; OWL has no terminal architecture.
Signed-in interactive capture acceptance remains pending.

Hard-refresh and open **Research workspace → Evidence → Guided source-cell capture**
after completing retrieval. No inference, decisions, saved models or company data
were changed by deployment verification. No git commit or push was performed.

## Previous release: research workspace navigation

App deployment `01f1c669dd0510418db82a44faf33b06` succeeded at
18:23:24 UTC (14:23:24 America/New_York).
Source: `/Workspace/Users/satish.terala@databricks.com/research_cockpit_releases/20261012-research-workspace`.
Frontend `/assets/index-vwPg1WW2.js` matches the tested local build exactly.

This release promotes Questions → Evidence → Judgments → Challenges →
Decisions → Models to the top-level Research workspace. The older run narrative
and initial valuation-pipeline controls are separated from supervised team rounds.
Progress and explicit missing-output/failed-read messages guide the next action.

The backend, shared valuation code and app configuration are byte-identical to
the preceding app release. Dedicated worker `897847549464155` remains on release
`2929919c5de91101`; neither it nor research pipeline `557334341404887` was updated.

Pre-deployment acceptance passed: 417 Python tests, production build and all six
browser suites. Live read-only verification passed for health, the exact frontend,
workspace history routes and the unchanged worker release. No inference, retrieval,
decisions, assumptions, model updates or publication were initiated.

At verification, OMAB still had no completed evidence revision and OWL had no
terminal architecture. The separate Chrome test profile required login; signed-in
interactive usability remains user acceptance.

Hard-refresh **Agent valuation research** and look for **Research workspace**.
Choose the architecture run. For OMAB, start with **Questions** to collect evidence;
then follow the next-action card to **Evidence** and **Judgments**. **Challenges**,
**Decisions** and **Models** display team output once a consented round completes.
The old October 10 narrative is now under the collapsed audit-history section.
No git commit or push was performed.

## Previous release: supervised research rounds

App deployment `01f1c6478cf91e17aa960a11e46b4af2` succeeded at
14:17:52 UTC (10:17:52 America/New_York).
Source: `/Workspace/Users/satish.terala@databricks.com/research_cockpit_releases/20261012-research-rounds`.
Frontend `/assets/index-Ep9UIPZK.js` matches the local production build exactly.

Dedicated valuation job `897847549464155` now uses immutable release
`2929919c5de91101`. Zero-inference transport smoke run `498913113820638`
succeeded. Only the dedicated worker was updated; research pipeline
`557334341404887` was not modified.

Local acceptance: 417 Python tests, production build and five browser suites
passed. Live health, exact frontend, remote-worker listings, OMAB dossier routes
and authenticated rejection of round requests without inference consent passed.
OMAB and OWL remain publication-blocked. No company retrieval, inference,
review/model decisions, saved assumptions or approvals were created or changed.
Only isolated transport-smoke records were written.

At verification, OMAB had a terminal architecture but no completed evidence
revision; OWL still had no terminal architecture. An actual evidence-backed
research round and interactive inbox remain user acceptance, not a claimed
live end-to-end test.

Hard-refresh the app. For OMAB, open **Agent valuation research**, its terminal
architecture run, and **Follow-up research dossier**. Launch reviewed searches
and wait for retrieval to finish, then prepare and review exact source cells.
Under **Review source-cell evidence**, expand **Supervised research rounds and
approval inbox**, select a saved review branch, enter a question and explicitly
authorize the bounded round. The worker should stop at `awaiting_review`.
Record card decisions to create a separate user-model branch; continuation
preparation alone does not launch another round.

See `valuation-research-rounds.md` for limits. Roles are sequential; autonomous
retrieval, parallel teams, combined models and calibrated confidence intervals
are not part of this release. No git commit or push was performed.

## Previous release: supplied reviewed models

App `research-cockpit` deployment `01f1c6306cc911a0ac909df96e444667`
started successfully at 11:32:15 UTC (07:32:15 America/New_York).
Source: `/Workspace/Users/satish.terala@databricks.com/research_cockpit_releases/20261012-reviewed-models`.
Verified frontend: `/assets/index-CLoxgtHb.js`, byte-identical to the local build.

Dedicated valuation job `897847549464155` uses release `bc510ff34a95152a`.
Transport smoke run `818937427037070` succeeded with zero inference calls.
Research pipeline job `557334341404887` was not modified.

`EVIDENCE_REVIEWER_IDS` permits only verified workspace user `8083820129023134`.
The app already exposes `iam.current-user:read` in its effective user scopes.
Authenticated malformed-payload probes reached validation in evidence preparation,
component preview and component save routes, confirming reviewer verification.
These probes rejected before persistence; no company review/model branches were created.

## Validation

- 394 application Python tests and all four local browser suites passed.
- Production frontend build and patch whitespace checks passed.
- Live health, exact frontend bundle, remote-worker listings, OMAB research/plan
  history endpoints and reviewer authentication passed.
- OMAB and OWL remain publication-blocked.
- Chrome's separate test-browser profile reached the workspace login page; actual
  logged-in browser interaction remains user acceptance testing.
- No company retrieval queries, LLM calls, accepted facts, saved assumptions or
  approvals changed. The isolated transport smoke wrote only smoke-runtime records.

## Start testing

1. Open the FEVM app and hard-refresh. Sign in with the allowed account; complete
   any authorization consent presented by the platform.
2. Open OMAB's valuation review and **Agent valuation research**. Expand its saved
   terminal run, then **Follow-up research dossier**. An underwriting error in the
   existing run does not prevent follow-up research from its saved architecture.
3. Select evidence gaps, enter literal search phrases and use **Launch reviewed
   searches**. This retrieves evidence without an LLM planning call. The optional
   **Propose search plan (LLM)** control requires explicit consent and incurs inference.
4. When retrieval finishes, expand **Review source-cell evidence**. Prepare exact
   source-cell JSON, inspect sources/basis and explicitly record decisions.
5. Expand **Exploratory component-model proposals**. Select the saved review branch,
   supply a model proposal, inspect its deterministic preview and save a separate
   exploratory branch. Unknowns and incompatible basis must remain blockers.

OWL did not have a terminal saved architecture in the live listing at verification.
Its follow-up dossier requires first creating a parent architecture; **Build agent
valuation** runs the existing paid valuation pipeline, not the new component author.

Source-cell interpretation and component-model JSON are currently supplied by a
human or external offline agent. In-app model authoring is not implemented. Nothing
in this release automatically replaces a saved valuation or clears publication gates.
See `valuation-evidence-review.md` and `valuation-parameter-proposals.md` for contracts.