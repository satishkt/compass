# Project document: valuation-evidence-review

Source: research_val_personal/docs/valuation-evidence-review.md
Kind: design document; may describe planned rather than shipped features.

# Offline source-cell review handoff

This foundation adds explicit review to exact-location source-cell proposals.
It does not run an LLM, retrieve documents, change company facts or assumptions,
close architecture gaps, publish fair value, or change portfolio signals.
The CLI remains declared-human only. A separate persisted API/UI path now
verifies a workspace user token before allowing review submissions.
Supplied component-parameter proposals now use this handoff; see
`docs/valuation-parameter-proposals.md`. In-app agent generation remains a follow-up.

## Workflow

Supply the research **output packet** (the frozen research artifact's `output`)
and an array of raw `CellProposal` objects. These can originate from local
snapshots or an index research packet; anchoring is revalidated in both cases.

```sh
python3 scripts/preview_evidence_review.py --packet packet.json --cells cells.json --output candidates.json
python3 scripts/preview_evidence_review.py --packet packet.json --cells cells.json --review decisions.json --output reviewed.json
python3 scripts/preview_evidence_review.py --replay reviewed.json
```

All outputs use exclusive creation: an existing artifact is never overwritten.
For a revision, create a new file and review the candidate digest again.
The review input has:

- `research_packet_digest`: the packet's original digest.
- `reviewer`: a local declared reviewer label, not an authenticated principal.
- `reviewed_at`: an explicit timestamp.
- `decisions`: objects with `proposal_id`, `candidate_digest`, `outcome`
  (`accept`, `reject`, `unresolved`), `rationale`, `interpretation_checked`,
  and `basis_checked`. Candidate digests come from the preparation step.

Before accepting, inspect the full excerpt and verify numerical interpretation,
units, scaling, currency, period, perimeter and definition. Exact text anchoring
alone cannot do this. Acceptance requires both check flags; flags record a
declaration, not proof of semantic correctness.

## Safeguards and boundaries

Every candidate, original hit with document hashes/location, and supplied
decision is retained. Omitted decisions stay unresolved. A conflict is held
until exactly one member is accepted and every alternative explicitly rejected;
multiple accepts cannot silently choose a winner. Basis differences remain
visible even after a declared selection.

`exploratory_evidence_ids` identifies candidates eligible for a future exploratory
parameter proposal only. It is not a canonical accepted-fact registry.
`authenticated` and `publishable` remain false and `canonical_fact_updates` is
always empty. These decisions do not alter original research packet statuses.

Frozen artifacts retain input/output digests and engine signatures. Replay
revalidates anchoring and decisions and compares recomputed outputs.
Digests detect stale inputs and accidental modifications; they are not signed
attestations and do not prevent someone rewriting an artifact and its hashes.
The CLI itself introduces no remote persistence, LLM model proposal or valuation
integration.

## Persisted dossier review

Expand **Review source-cell evidence** inside a completed targeted research
revision. The initial candidate editor accepts explicit source-cell JSON
(no automatic extraction). Save a candidate set, inspect each typed datum
beside its source excerpt, choose accept/reject/unresolved, enter rationale
and confirm interpretation/basis checks before accepting.

Candidate sets are content-addressed; review submissions use a retained
client idempotency key. Unconfirmed submissions survive reload and can retry
the exact original body. Discarding a pending draft does not remove saved
records. Every review is an independent branch; a later submission does not
automatically supersede an earlier one.

Records live beneath the original child in mirror-excluded storage:

```text
valuation_runtime/<company>/<research-child>/evidence-candidates/<digest>/record.json
valuation_runtime/<company>/<research-child>/evidence-reviews/<id>/record.json
```

Each operation replays the durable research revision and checks the frozen
parent evidence/architecture. Listing revalidates candidate anchoring, receipts,
review linkage and offline replay; stale or tampered records fail closed.
Listings currently cap at 100 records per folder and fail explicitly above
that bound rather than silently dropping history.

### Identity configuration

Configure `DATABRICKS_HOST` to the app's workspace and `EVIDENCE_REVIEWER_IDS`
to a comma-separated allowlist of workspace **user IDs**, not email labels.
workspace current-user endpoint. Confirm the required user-authorization
scopes in the deployment workspace before enabling this feature.

calls `current_user.me()` in the configured workspace. It checks the returned
active user ID against the allowlist. It never falls back to the app service
principal, a forwarded email/user header, or a client-supplied reviewer name.
Tokens are never saved in review artifacts or returned to the UI. Missing
configuration/token, verification failure or unauthorized identity disables
writes. No live user-authorization settings or allowlist were changed by
this implementation; this must be configured and smoke-tested before release.

Storage still uses the app's governed service principal, not user-scoped
file permissions. The reviewer allowlist is a personal-app authorization policy,
not company-level access control. This does not change existing app-wide read
access. Multi-user/company authorization requires a separate policy.

The persisted envelope records `authenticated: true` for the API-verified
submitter, but the embedded offline artifact deliberately remains
`local_declared_human`, `authenticated: false`, and `publishable: false`.
Identity verification proves the submitter, not factual correctness or
valuation approval. Receipts are hashes, not signatures; anyone with direct
Volume write access could rewrite both data and hashes. Treat the Volume's
write permissions as part of the trust boundary, not offline authentication.

The next handoff is implemented as validated supplied component-parameter
proposal branches referencing a specific review branch. Judgment/falsification
conditions remain explicit, without changing saved assumptions or selecting an
accepted fair value. Bounded agent generation and independent economic review
remain open.