# Project document: valuation-targeted-research

Source: research_val_personal/docs/valuation-targeted-research.md
Kind: design document; may describe planned rather than shipped features.

# Targeted offline valuation research

`shared/valuation/research.py` turns explicit evidence requests into bounded,
immutable research packets over local snapshots. It does not call an LLM, query
a warehouse, crawl news or mutate any model, approval or published value.

## Workflow

1. Propose a question, model targets, source description and literal search phrases.
   `requests_from_gaps(gaps, terms_by_id)` adapts existing saved architecture gaps.
   Phrases must be explicitly supplied; no hidden company-specific term defaults.
2. Export or curate complete parsed-text snapshots from the existing approved index.
   The local schema requires ticker, file path, source/URL, document class, period,
   filing and parsing times, raw-document hash, parsed-text hash and parsed text.
   The parsed-text hash is checked locally. Source provenance and raw hashes remain
   declared metadata, not authenticated approval.
3. Run `build(company, cutoff, requests, documents, max_chars=24000)` or the CLI.
   Matching is case-insensitive literal phrase search, including punctuation.
   Unlike the old fixed collector, search is not restricted to initial excerpts.
4. Inspect retained hits and coverage receipts. Optionally propose exact source
   cells with complete typed units, scale, currency, period, perimeter and definition.
   `propose_cells` checks exact text locations and own-request attribution.
5. Human review must verify meaning and normalize/reconcile numbers before they
   become model inputs. This layer never accepts facts, resolves gaps or approves FV.

The allowlist matches the existing collector: `sec`/`fiscalai`, and business,
MD&A, raw filing, transcript and investor-deck classes. A transcript hit is not
automatically a verified financial fact. Documents must belong to the company
and both filing and parsing dates must precede or equal the supplied cutoff.

## Coverage states

- `retrieved_candidates`: evidence candidates, not a resolved question.
- `no_match_in_snapshot`: phrases did not match this eligible local corpus;
  this is **not** a conclusion that the company never disclosed the information.
- `no_eligible_sources`: supplied snapshots did not provide eligible sources.
- `budget_limited`: some matching excerpts could not fit. Requests remain open.

Receipts identify excluded sources, matching/retained documents and document-limit
omissions. Every request always has `gap_resolved: false`. Contradictory proposed
values and incompatible bases are preserved as review conflicts, with no selected
winner. Text anchoring cannot detect an incorrect interpretation of a cited number.

## Offline CLI

The request file is an object containing `company`, `cutoff`, `requests`, and
optionally `max_chars`. The document file is a snapshot array.

```sh
python3 scripts/preview_valuation_research.py \
  --requests requests.json --documents snapshots.json --output research.json
python3 scripts/preview_valuation_research.py \
  --replay research.json --documents snapshots.json
```

Optional `--cells cells.json` freezes review candidates with the research artifact.
Cell locations are 1-based inclusive Unicode character offsets into original parsed
text, not byte or PDF-page offsets. `raw_text` must match that exact retained span.
Candidate `Datum.evidence` must contain exactly its hit ID. No derived arithmetic
or semantic interpretation is automatically validated by this check.

Output files are exclusively created, never overwritten. Replay checks engine,
inputs, corpus, research output and any cell proposals. Full source texts stay in
the separately retained local snapshot file, not the bounded output packet.

## Limits and integration boundary

- Twelve requests, twenty requested documents in total, three documents per
  request, three retained windows per document. Phrase occurrence scanning is
  bounded to 24 candidate windows; repeated terms can omit later relevant passages.
- Maximum 200 local documents, 2 million characters per document, 8 million in
  total. Output budget is 2,000–60,000 serialized JSON characters.
- Search terms are proposed reasoning inputs. Poor terms can miss material evidence;
  add alternate phrases and rerun as a new immutable research revision.
- The offline snapshot path has no semantic search, automatic table parsing or
  authenticity checks. Malformed/hash-mismatched snapshots fail rather than
  generate evidence.
- The remote follow-up implementation below is separate from the four-stage worker
  inference path. Original evidence and budgets are never reset to insert research.
- Next add agent parameter proposals and review/dossier UI. Live retrieval/inference
  needs separately authorized testing.

## Approved-index follow-ups and durable research revisions

The backend now supports follow-ups attached to terminal valuation requests that
have a saved architecture. `RemoteRuntime.submit_research` validates selected saved
gap IDs, freezes the architecture/evidence digests and cutoff, and submits a separate
retrieval-only child request to the dedicated valuation job. It does not retry or
modify its parent. Original company identity is preserved while the document ticker
comes from the frozen primary-listing profile (falling back to company identity).

Search phrases are explicit proposals supplied by the caller or the separate,
user-initiated search-planning agent. The architecture stage itself is unchanged.
Completed research does **not** automatically launch another valuation or resolve
the architect's gaps. See `valuation-search-dossier.md` for planning and UI controls.

`shared/valuation/index_research.py` binds company, cutoff, literal search patterns
and document limits as SQL parameters. It searches full parsed text server-side,
returns only bounded excerpts, and reports eligible/matching document counts.
It retains the first occurrence per phrase and at most three windows per document.
Regex metacharacters in phrases are escaped; no arbitrary caller SQL is executed.
Unlike local full snapshots, full parsed text is not downloaded or independently
rehashed: raw/parsed hashes are index metadata, while excerpt hashes are computed
locally. Source/ticker, cutoff, hashes, positions and count consistency are checked
before candidate evidence is retained.

Durable records remain in the mirror-excluded `valuation_runtime` namespace:

- `request.json`: immutable child plan and frozen parent provenance.
- `attempt-N.json` / `dispatch-N.json`: existing explicit retry/idempotent dispatch.
- `queries/<gap-id>.json`: immutable normalized response and integrity digest.
- `research-revision.json`: immutable bounded evidence revision linked to its parent.
- `checkpoint.json`: worker-owned reservations, per-query progress, errors and final
  research packet; no new architecture, accepted fact or publication artifact.

The worker reserves query/time allowance **before** retrieval and persists each query
response before advancing. Retries reuse completed responses, including responses
saved before a checkpoint acknowledgement was lost. Failed attempts require explicit
retry; repeated delivery of that failed attempt cannot automatically issue another
query. Budgets are 24 total reserved queries, 300 cumulative seconds, at most 60
reserved seconds per query, and the existing three-attempt ceiling. No LLM calls are
reserved or issued. Failed calls retain their allowance; observed overruns are charged.
SQL/network cancellation remains cooperative, not a hard wall-clock sandbox.

Read-only replay verifies the frozen specification, original engine release, every
query response and the final research revision. Engine changes require the original
release for replay/resume; this is an integrity guard, not authenticated review.

### API (available after deployment)

`POST /api/companies/{ticker}/valuation-agent-jobs/{parent-id}/research-revisions`
accepts the following shape; gap IDs must actually exist in that parent's saved plan:

```json
{
  "request_key": "0123456789abcdef0123456789abcdef",
  "terms_by_id": {
    "gap_concession_expiry": ["concession expires", "expiration date", "concession term"]
  },
  "max_chars": 24000
}
```

These phrases illustrate proposed retrieval, not verified expiry assumptions. Reusing
the same key/plan returns the same child; changing that plan under the key is rejected.
Queueing retrieval can incur warehouse/job compute costs, but invokes no LLM.

`GET` at the same path lists that parent's recent research revisions. Ordinary
valuation listings exclude retrieval-only children. Use existing child-job control
routes with `retry`, `cancel`, or `replay-research`. Local standalone mode returns a
clear remote-runtime requirement for submission; the offline CLI remains available.

The follow-up dossier now supports user-initiated agent plans, editable phrases,
retrieval submission, source inspection, explicit retry/cancel and replay. Accepted-fact
handoff, autonomous research loops and model re-authoring remain open. The app and
worker must be released together before use. This has not been deployed or live-tested.

The index/worker integration adds 23 local tests, including mocked SQL/Volume/Jobs
transport and actual API route dispatch. The full acceptance bundle now passes
269 targeted tests and 304 full Python tests, plus whitespace checks. These tests
do not establish live Databricks SQL execution or remote deployment success.

## Validation

`python3 scripts/validate_valuation_bundle.py --skip-frontend` passes 246 targeted
acceptance tests, 281 full Python tests and patch whitespace checks. The 34 new
research tests cover targeted search, provenance/cutoffs, hashes, literal/Unicode
locations, coverage budgets, conflicts, replay/tampering and CLI no-overwrite.
No frontend code changes; frontend checks are skipped. The existing Starlette/httpx
deprecation warning remains.