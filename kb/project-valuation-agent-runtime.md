# Project document: valuation-agent-runtime

Source: research_val_personal/docs/valuation-agent-runtime.md
Kind: design document; may describe planned rather than shipped features.

# Offline valuation research runtime — V06 foundation

## Delivered

The valuation review screen has a separate **Build agent valuation** panel. Publication blockers
do not prevent research. In local mode the action queues an immutable, content-hashed evidence
packet containing saved normalized statements, profile, shares, effective assumptions, and
validation blockers. It deliberately does not use unsaved slider changes or carry forward approval.
The app selects a bounded research packet before queueing; exceptionally large essential inputs
still fail visibly rather than silently truncating security rights or validation blockers.

## Research input selection

The Build button no longer sends the entire vendor/history archive. Both local and remote API
submissions use `shared/valuation/evidence.py` to target at most 35,000 base JSON characters,
reserving 25,000 characters inside the existing 60,000-character cap for document excerpts and
metadata. No LLM is used for selection, and saved company inputs are never modified.

- Exclude profile peer lists, secondary listings and vendor dataset catalogs. Keep business
  descriptions, identity, industry, currencies, accounting template and the primary listing.
- Keep up to eight recent fiscal-year cells per metric; reduce to six/four only if necessary.
  Fiscal-year keys and numerical values are unchanged. Different metrics can have different
  latest years; their dates must still be examined for staleness.
- Keep four recent share observations with every share class, conversion field and source link
  intact. Older array positions become null so retained JSON-pointer indices do not change.
- Preserve effective assumptions (without approval metadata) and the full validation result.
  Selection cannot waive a publication blocker.
- If still oversized, omit optional profile fields, then select whole four-year series with
  preference for financial and business-driver metrics. Never replace omitted values with zero.
  Unusually large protected business/security/assumptions data fails closed rather than dropping
  rights or fabricating facts.

The packet's `selection` receipt includes its original hash/size, policy, omitted profile fields,
retained share indices and per-statement metric/cell counts. The UI exposes this partial-coverage
receipt. Omitted or stale essential drivers require further evidence, not automatic extrapolation.

This input-selection correction is deployed to FEVM app `research-cockpit`, deployment
`01f1c482af5e1af0bc9b1d4fcc0e0401`, which reported successful startup on October 10, 2026
at 08:21:04 UTC. Authenticated read-only checks verified health, the tested frontend bundle
and input-selection UI, OMAB/OWL remote-worker availability/listings, publication blockers
and app job permissions. The acceptance bundle passes 173 Python tests, frontend build and
browser checks. No live valuation job or LLM call was started; end-to-end live inference
acceptance remains unverified.

### Worker response completion correction — October 10, 2026

Inference accepts a single complete Markdown JSON fence around an otherwise valid artifact.
Empty, non-JSON, malformed/truncated and oversized responses fail closed with stage-specific
diagnostics; schema and evidence validation still apply. Partial objects are never repaired.

Worker release `e4652d7ade7bff30` passed transport-only smoke run `685937567677807`.
One authenticated app retry of OMAB request `ca709187db20a3a01c50a681fb016c2f`
started run `652558977372674`. It failed at architecture; retained SQL results show JSON
fences with bodies cut off mid-field at the 3,000-token output allowance (11,335 and 11,175
characters). Repeated execution of this same remote attempt consumed two reserved calls.
Revision identity, review state and validation/publication blockers were unchanged.

The follow-up worker release `1b4ab6c86754795d` increases architecture/underwriting output
headroom to 8,000 requested tokens, retains 3,000 for analyst/reviewer, and asks for compact,
complete JSON under 20,000 characters. The hard 24,000-character artifact gate stays intact.
A failed remote attempt cannot reinvoke inference on replay: a new explicit retry command is
required. Interrupted attempts without a failure checkpoint remain at-least-once execution.
All 188 Python tests pass. The original failed OMAB request has four of six calls reserved and no
completed stages; its two remaining calls cannot complete all four stages. No further paid
retry or replacement request was started. Final release passed transport-only smoke run
`1016734628759542` with zero inference calls. Authenticated app health, tested frontend,
OMAB/OWL remote-worker listings, publication blockers and app job permissions pass.
The app deployment remains `01f1c482af5e1af0bc9b1d4fcc0e0401`; only the dedicated worker
was updated. Final-release live inference acceptance remains open.

### Fresh OMAB acceptance run — October 10, 2026

With explicit user authorization, one fresh request `be95fb729767c6530989e2d5ab546a4e`
was submitted through the authenticated app at 09:04:58 UTC, using worker release
`1b4ab6c86754795d`. Run `892874394915090` saved valid architecture and analyst proposal
checkpoints, then failed at underwriting with
`Model horizon must match the saved architecture; do not silently shorten it`.
The saved architecture proposes a 20-year horizon as judgment pending concession-expiry evidence.
Its planning receipt is not ready for underwriting: five essential requests remain open
(concession expiry, MDP schedule, ownership, debt currency and WACC inputs).
Neither proposal constitutes verified economics or an approved valuation.

The request ended with three of six calls reserved, no underwriting/calculation artifact and
no reviewer stage. Failed-attempt replay did not consume another reserved call. No retry or
additional request was started. Authenticated before/after checks verified unchanged revision
identity, saved review/approval, published revision list and validation/publication blockers.
The earlier response-completion failure did not recur in architecture; full live workflow and
economic acceptance remain open. Next investigate the underwriter's horizon contract and
valid abstention on unresolved essential evidence, without weakening the horizon validator.

## Research workflow

Targeted follow-ups now have a separate retrieval-only child-request path linked to a
terminal parent's saved architecture. They do not resume inference, reset budgets or
replace the parent's evidence. They use the same dedicated job and mirror-excluded
namespace, with immutable per-query checkpoints and research revisions. See
`valuation-targeted-research.md` for the API, explicit retry/replay controls and limits.
Separate user-initiated search-planning children now propose phrases before reviewed
retrieval, and the dossier UI exposes planning, draft searches, coverage and source
receipts. Follow-up wire protocol version 4 prevents older full-valuation workers
from interpreting these requests as ordinary version-3 valuation runs.
See `valuation-search-dossier.md`. This is locally tested only, not deployed.

New jobs run a business-model architect, lead analyst, annual-model underwriter, then a separately
prompted skeptical reviewer, using the existing governed SQL `ai_query` transport. The architect produces a validated
declarative plan with source pointers, drivers, policies and bounded evidence requests. The analyst
and underwriter receive the saved plan. The underwriter supplies a bounded declarative formula
graph or abstains; the worker computes and freezes annual workings without an LLM. The reviewer
receives both the proposed graph and computed workings and retains objections and questions.
Disagreements remain in separate saved artifacts. These are not new fair values, independently
verified facts, human approvals, or replacements for a reviewed published valuation.

Workflow version 2 introduces the architecture checkpoint. Original version-1 jobs (including
records without a version field) retain their two-stage analyst/reviewer workflow. Version-2 jobs
retain their three-stage architecture workflow. Version 3 adds annual underwriting and deterministic
calculation artifacts. New requests do not reuse an older completed workflow as a newer one.
An active older job must finish or be
cancelled before queuing a new job for that company. See `valuation-architecture.md` for the
planning contract and its limitations; see `valuation-underwriting.md` for calculations and previews.

The local queue is stored under `jobs/valuation_agent` in `RESEARCH_DATA_ROOT`. Atomic checkpoint writes,
file locks, progress events, cancellation, explicit retries, and input deduplication survive app
request completion and process restarts on the same persistent filesystem. One worker at a time
and one active job per company are allowed. A repeated request with the same evidence returns the
existing active/completed job. Failed retries retain completed stages.

## Run locally

1. Start the app with the usual local data root and without `RESEARCH_VOLUME`.
2. Open the company valuation review and select **Build agent valuation**.
3. In a separate terminal with the **same** `RESEARCH_DATA_ROOT`, authenticated Databricks SDK
   access, SQL warehouse access, and `RESEARCH_CHAT_MODEL` configured, run:

   ```sh
   python3 -m shared.valuation.agent_jobs <job-id>
   ```

4. Keep the panel open or revisit it to read saved progress and proposals. Page requests never
   invoke the LLM. Cancel/retry controls operate on the durable job record.

Re-run that worker command after an interruption. An interrupted call can be repeated because
no response checkpoint exists; its reserved call/time allowance is not refunded. This permits
at-least-once inference, not exactly-once inference or billing.

## Guardrails and limits

- Six reserved calls per version-3 job (four for older jobs), 8,000 requested output tokens for
  architecture/underwriting and 3,000 for analyst/reviewer, 60,000 input JSON
  characters, and 24,000 output JSON characters. Input character limits are not exact token counts.
- A 900-second cumulative inference/calculation allowance for version 3 (600 seconds for older
  jobs), with at most 180 seconds reserved per call.
  SQL cancellation is best-effort; this is not a hard OS/process/network wall-clock sandbox.
  Model routing and governance logging can add time outside inference.
- Cancellation is cooperative: an active inference may finish and incur cost before its result
  is discarded. Budget exhaustion cannot be bypassed by retrying the same job.
- Sources and prior proposals are explicitly untrusted evidence. The agent has
  no generated-code execution tool, arbitrary retrieval tool, or publication tool. Declarative
  arithmetic is interpreted by the bounded deterministic engine, never `eval`. Returned JSON
  is shape/size-validated and rendered as escaped text, never HTML.
- Only the worker transport uses ambient Databricks credentials. No generated code is executed.
  No claim of isolated generated-model execution is made.
- The worker never writes saved assumptions, review decisions, portfolio valuations, or frozen
  published revisions. Existing deterministic calculation and human publication gates remain intact.

## Remote execution

The app's `/tmp` mirror is not a shared durable queue. With `RESEARCH_VOLUME` and
`VALUATION_JOB_ID` configured, routes use `RemoteRuntime` directly through the Files API.
If the dedicated job ID is absent, queue/control mutations fail closed. The existing
research pipeline is untouched.

Remote records live under `<volume>/valuation_runtime/<company>/<request-id>/`, excluded
from app mirror pull, push and pruning:

- Immutable `request.json` freezes the original packet, workflow version and submission cutoff.
- Immutable `attempt-0.json` through `attempt-2.json` authorize bounded execution attempts.
- `dispatch-N.json` saves the Jobs run ID; dispatch tokens are stable across ambiguous failures.
- Immutable `cancel.json` is a persistent cooperative cancellation command.
- Only the worker writes mutable `checkpoint.json`; the app reads it without resynchronizing it.

The browser retains a client request key across ambiguous submission failures and reloads.
The same key reuses the original request even if app inputs change. A deliberate new research
pass uses a new key. Requests and attempt commands are persisted before dispatch; call/time
reservations and checkpoints are persisted before inference. A failed checkpoint upload stops
execution rather than invoking an unaccounted call.

The dedicated serverless Job has concurrency one, queueing enabled, no schedule, no automatic
task retries and a 1,800-second task timeout. Different deliberate requests can queue for the same
company; this is not distributed per-company transactional deduplication. Retries retain completed
stages and call/time charges, with at most three remote attempts. GETs never dispatch or infer.
Listing inspects at most 20 recent directory entries by modification time; it is not a complete
historical audit. Cancellation also requests Jobs cancellation; already-running inference can
still incur cost. The worker uses temporary local locks, not Volume FUSE locking or atomic rename.

## Source snapshots

Before the first architecture call, the remote worker reserves a 60-second retrieval allowance
within its cumulative budget. It selects approved `sec`/`fiscalai` document-index records whose
filing and parsing dates are no later than submission. It never downloads full parsed filings.
At most four records and 18,000 excerpt characters fit inside the existing 60,000-character
packet limit. Opening excerpts and bounded keyword windows include concession, fee-paying,
noncontrolling and capital-expenditure context.

Snapshots retain file/source metadata, raw and parsed SHA-256 hashes, excerpt hashes and
character locators. Distinct sections of the same raw filing remain eligible; repeated parsed
content is deduplicated. Retries reuse the saved snapshot without refetching. Coverage is
`partial` or `no_approved_evidence`, never comprehensive. The UI shows escaped source text.
Qualitative architecture facts may cite these excerpts; annual numerical facts still require
matching profile/statement/shares numerical leaves.

This is initial bounded retrieval, not agent-directed research-plan fulfillment, news ingestion,
source-cell numeric extraction, or semantic evidence verification.

## Provisioning and activation

`databricks/job_valuation.json` defines the dedicated job. `scripts/provision_valuation_worker.py`
prints a preview unless `--apply` is supplied. It uploads a content-addressed workspace release,
creates only the dedicated job, and grants the specified app principal `CAN_MANAGE_RUN`.
It never redeploys the app. `--smoke` tests immutable request transport and remote code startup
without source retrieval or LLM calls. Required options are profile, workspace-root, volume,
catalog, schema, warehouse, model, owner and app-principal.

For subsequent releases, explicitly pass `--existing-job`; the script refuses an unrelated job
or any active/queued runs. Suspend submissions before updating and drain the queue. No existing
code release is overwritten. The app principal needs its existing Volume read/write permissions;
the worker run-as identity needs document-index, warehouse and model access.

**Verified FEVM worker:** Job `897847549464155`, code release `bc59f43f0bb71c7d`.
Transport-only run `34596542472372` succeeded on October 10, 2026, with zero LLM calls.
Live bounded read-only queries on that date found three eligible OMAB records and four OWL records;
this establishes partial index coverage, not independently verified company facts or valuations.
`scripts/check_valuation_sources.py` can repeat this read-only check.

`app.yaml` points to the dedicated job. FEVM app deployment
`01f1c47ea01410d28f71ca88000d6de6` started successfully on October 10, 2026 at 07:55:58 UTC.
Authenticated read-only checks passed for health, the tested frontend bundle, remote-worker
availability and authoritative listings for OMAB/OWL, and the app principal's `CAN_MANAGE_RUN`
job permission. Both companies remain publication-blocked. No research jobs, LLM calls, approvals
or assumptions were changed by these checks. Actual app-principal dispatch and real LLM-stage
acceptance remain unverified.

Still open: agent-directed follow-up retrieval/news ingestion, exact token/currency-cost accounting,
automatic retry scheduling, live source-grounded V07 acceptance, full V08
ownership/FX/terminal valuation integration and approved artifact branches, V09 deeper economic
challenge, and V10 OMAB/OWL pilots.
The architect, analyst, underwriter and reviewer use the same configured model in separate calls; they are
not distinct models/providers.

## Single-shot acceptance

```sh
python3 scripts/validate_valuation_bundle.py
```

Tests use synthetic evidence and stub inference; they do not contact live models, change live
approvals, deploy, or incur inference costs.