# ADR 0249: Outbox retains published and reviewed masters

Accepted, 2026-11-05. Owner: codex-builder.

## Context

ADR 0246 requires the caller to verify platform publication evidence before
excluding a master from release evaluation. ADR 0248 supplies a separate,
hash-bound whole-master approval for reviewed legacy masters. Previously,
`outbox.ready` evaluated every candidate without forwarding whole-master
approvals, so callers could not use either route while retaining the complete
Drive outbox. Neither delivery manifests nor Drive presence proves publication.
The external platform lists and their counts were not verified from this checkout.

## Decision

`outbox.ready` accepts optional `release_approvals`, mapping video names to typed
`master_gate.ReleaseApproval` records, and `published`, a collection of names
whose platform publication the caller has verified. Both default to empty.
Unknown names and names appearing in both arguments raise `OutboxError` before
delivery checks. Approvals are passed by name as `release_approval` to the shared
`evaluate_release`; its measurement, diagnostics and exact-hash refusal rules
remain authoritative. A changed master cannot inherit its predecessor's approval.

Published names bypass only master evaluation. Delivery drift, an untrustworthy
manifest and missing packages still hold them back. Eligible published names use
the same Bundle construction and staging as other eligible items, retaining them
in `outbox.json`. For each such name, `release_reports` receives exactly
`excluded: <name>: published on platform (caller evidence)`. The SDK does not
fetch platform evidence or infer publication from local files. The caller owns
that evidence and classification; exclusion is not a fabricated release approval.

## Alternatives rejected

- Filtering `items` in the caller drops posted reels from the staged manifest and
  shrinks Drive's `outbox.json` when staging replaces the previous outbox.
- Calling `evaluate_release` per caller duplicates Bundle building and the outbox's
  delivery/package checks.
- Treating publication as a whole-master approval conflates verified publication
  with ADR 0248 review and introduces unnecessary master reads for posted files.
- Skipping delivery or package checks for published names stages stale or
  incomplete bundles.
