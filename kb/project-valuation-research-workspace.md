# Project document: valuation-research-workspace

Source: research_val_personal/docs/valuation-research-workspace.md
Kind: design document; may describe planned rather than shipped features.

# Supervised research workspace

The frontend now promotes supervised research out of the legacy run narrative.
FEVM deployment `01f1c669dd0510418db82a44faf33b06` succeeded on October 12, 2026
at 18:23:24 UTC. Live health, exact frontend bundle and workspace history routes
passed read-only checks. The dedicated worker remains on release `2929919c5de91101`.
Signed-in interactive acceptance remains pending.

## Layout

**Research workspace** appears directly under **Agent valuation research**.
Choose a terminal architecture run, then use the six stage buttons:

1. **Questions:** economic evidence gaps, search phrases and retrieval/planning
   controls. Existing consent and request-key recovery remain unchanged.
2. **Evidence:** choose a completed retrieval revision, inspect candidate passages
   and record exact source-cell reviews.
3. **Judgments:** choose a saved review branch and explicitly authorize a bounded
   research round. Coordinator dependency plans and researcher cards appear here.
4. **Challenges:** challenger dispositions, evidence references and objections
   are directly visible, not hidden below the old narrative.
5. **Decisions:** explicit accept/edit/reject/investigate/defer controls and saved
   decision receipts.
6. **Models:** unchanged agent-model workings and separate human decision
   branches. Model-less rounds say explicitly that no numerical valuation exists.
   Supplied external component proposals remain an optional collapsed tool.

The progress card identifies the evidence revision, known review/round counts
and the next required action. Loading and failed-read states do not count as
proof that no output exists. Navigation does not retrieve evidence, run inference,
approve assumptions or publish anything.

The older architecture, analyst and underwriting narrative remains in
**Older valuation runs and audit history — not agent-team rounds**. An older
underwriting failure does not mean a supervised research round has failed.
The initial valuation pipeline control is collapsed once a usable architecture
exists; it is explicitly separate from launching supervised team research.

## Branches and limits

Switching companies, architectures or completed evidence revisions resets the
workspace's local review/round state; proposals are not transferred across
lineages. Choosing a stage does not mark it complete. Unanswered questions,
abstention and missing models remain visible. The question dependency plan is an
ordered list with named dependencies, not a graphical DAG editor or an autonomous
agent pool.

The backend and worker contracts are unchanged. This is a presentation/navigation
change, not combined-model assembly, calibrated confidence or automatic research.
Guided source-cell capture deployed in release `01f1c66f5815113fad8043202ff5c2cb`
on October 12, 2026 at 19:02:19 UTC removes hand-written JSON from the ordinary
candidate-preparation path. The advanced JSON editor remains available.
See `valuation-guided-evidence-capture.md`.

## Verification

From `app/frontend`, `node tests/valuation-workspace.mjs` checks all six stages,
missing evidence/reviews/team output, direct coordinator and challenger visibility,
decision readiness, model absence, failed-read recovery, company/architecture/
revision isolation and untrusted-source escaping. It asserts navigation performs
no POST requests. The suite is included in the local valuation acceptance bundle.

October 12, 2026 local acceptance passed: 417 Python tests, the production
frontend build and all six browser suites. Deployment verification did not run
inference, change company data, update the worker or create a git commit.