# Project document: valuation-guided-evidence-capture

Source: research_val_personal/docs/valuation-guided-evidence-capture.md
Kind: design document; may describe planned rather than shipped features.

# Guided source-cell capture

Deployed to FEVM on October 12, 2026 at 19:02:19 UTC:
`01f1c66f5815113fad8043202ff5c2cb`, frontend `/assets/index-xiOEi8ix.js`.
Signed-in interactive evidence capture acceptance remains pending.

The Evidence stage now offers **Guided source-cell capture** above the advanced
JSON editor. This removes hand-written JSON from the ordinary candidate-preparation
path; it is human-guided capture, not LLM extraction or semantic verification.

## Workflow

1. Choose an anchored passage from the selected completed evidence revision.
2. Copy exact quoted text into the quote field. Repeated text requires choosing
   its specific occurrence; a unique match selects its sole location.
3. Enter a stable cell ID, interpreted value, unit, scale, optional currency and
   dates, reporting perimeter, metric definition and interpretation rationale.
4. Inspect the optional exact-contract preview and add the cell to the local draft.
   Add more cells or remove draft entries without affecting saved records.
5. Explicitly **Save candidate set**, then perform the existing source-cell review.
   Acceptance still requires interpretation and basis checks plus reviewer rationale.
6. Save an evidence-review branch before authorizing supervised team research.

Rates are decimal fractions: quoted `12.5%` is explicitly entered as `0.125`.
The builder never derives that value from the quote. Disclosed `1,200 million`
is explicitly entered as `1200` with the Millions scale, not converted twice.
Unknown currency and periods remain null rather than defaulting to reporting
currency or a document year. Date values use valid ISO dates.

## Safeguards

Locations use the backend's one-based, inclusive Python-character convention,
not JavaScript UTF-16 code-unit offsets. This preserves exact source anchoring
even when supplementary Unicode characters precede a selected number.
Quote text is never normalized or trimmed.

Absent text, ambiguous occurrence selection, duplicate draft IDs, unsupported
units/scales, invalid currency/dates, empty interpretation fields and invalid or
overflow/underflow numerical values block guided additions. Drafts are bounded
to 100 cells. The source and request references come only from the chosen hit.
The advanced JSON escape hatch still goes through authoritative backend validation.

Adding/removing cells changes only the local unsaved draft. Unsaved form fields
do not survive reload. Unconfirmed candidate saves retain their original body
and are recoverable through the existing pending-submission mechanism.
Neither draft edits nor candidate saves accept facts, run inference, modify a
model, clear valuation blockers, or publish anything.

The backend checks exact anchors and immutable packets again. Anchoring proves
where text came from, not that the entered numerical interpretation is correct.
Source conflicts and dimensional/economic ambiguity still require human review.

## Verification

`tests/test_guided_evidence_capture.py` passes actual JavaScript builder output
through the Python source-cell engine, including supplementary Unicode,
repeated text, line endings and wrong-packet rejection.

`node tests/valuation-source-capture.mjs` from `app/frontend` tests typed input
boundaries, explicit numeric interpretation, repeated occurrences, draft-only
actions, malformed JSON safety, separate review, identity availability, company
isolation and recovery after an unconfirmed candidate save.

Both are included in `python3 scripts/validate_valuation_bundle.py`.
October 12, 2026 local acceptance passed: 421 Python tests, production frontend
build and all seven browser suites. Live read-only verification passed for app
health, exact frontend bytes, capture controls and workspace history routes.
The dedicated worker remains on release `2929919c5de91101`. OMAB has zero
completed evidence revisions; OWL has no terminal architecture at verification.
No live inference, company updates or git commit was performed.
Agent-assisted candidate extraction, source discovery and investigation chaining
remain next steps; this slice makes evidence preparation usable first.