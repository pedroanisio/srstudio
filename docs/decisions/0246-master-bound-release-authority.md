# 0246: Master-bound release authority

Date: 2026-11-05

Status: accepted for the SDK gate; episodes publishing integration remains external.

## Decision

A reason is an authoring proposal, never approval. Waiver proposals retain reason,
check, optional changed bounds, and a typed Disposition with final-master SHA-256,
line identity, scope, requester and the exact retained approval message. Message
author, reference and text must be present; text must equal the retained exact
message. All proposal fields must match the disposition. Self-authored decisions,
unknown scopes, malformed bounds and stale hashes refuse.

arc4d3 may approve delegated production; Pedro may approve it and is required for
Rafa, host, new pilots, likeness, SDK main, super-tools main and auto-enhance.
The default scope is reserved, requiring Pedro. The caller supplies scope from its
trusted release classification, never from editable script waiver metadata.
These records validate evidence structure and binding, not remote account
authentication: callers must obtain the retained message from their authoritative
message store. The SDK does not request, author or persist approvals.

The actual final master is hashed before measurement and checked again afterward.
Only then can authority affect acceptance. Changed prosody bounds retain the
default limit and measured value in reports, including when the changed bound
passes. A disabled check retains its measured value, approver, exact message and
evidence reference. Missing or non-finite measurements fail closed.

master_gate.evaluate_release(master, project, scope=..., dispositions=...) returns
a typed Reading containing master_sha256 and per-check CheckVerdict records. It
uses the existing craft_bar measurement implementation for C7 on the final mix,
without changing its thresholds. Missing recordings or required measures refuse.
C7 dispositions match an exact check and master; no wildcard approval is accepted.
The sibling voice-measure lane owns expansion/correction of the C7 measures.

Missing prosody sections and pre-gate recording labels are historical metadata.
Neither those labels nor delivery/Drive presence excludes a master. The SDK gate
has no publication exemption: it evaluates every supplied master read-only. A
publishing caller may exclude a published file only after verifying platform
publication evidence itself. It must never infer publication from a delivery
manifest or Drive folder, nor re-render or mutate published reels.

master_gate.read calls the shared function. outbox.ready requires the recording
project for every candidate and evaluates the final master before constructing its
bundle. Callers can collect complete gate reports with release_reports.

## Integration limits

This checkout has no deliver CLI parser/handler and no existing calls to either
master_gate or prosody_gate from the CLI. Restoring that command is outside this
gate change. Existing outbox callers must pass projects; absence refuses safely.
The episodes publish_pilots caller is explicitly assigned to a later task and
must supply verified publication filtering and trusted release classification.


## Port onto final-master acceptance

ADR 0244's measurements and eligibility limits remain in `accept_master`.
`MasterApproval` is now an alias of `authority.Disposition`; the shared model
supersedes its ad hoc authorizer/evidence fields and owner rule. `scope` defaults
to reserved (Pedro); trusted production callers may select production (arc4d3 or
Pedro). Script waiver strings still cannot approve master exceptions. Missing
measurements cannot be approved. `evaluate_release` retains the acceptance result
and adds C7 on every supplied master; `read` uses the combined gate. Duplicate C7
views of accepted master exceptions retain the same disposition evidence.
