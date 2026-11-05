# ADR 0248: Hash-bound whole-master legacy release approval

Accepted, 2026-11-05. Owner: codex-builder.

## Decision

`master_gate.ReleaseApproval` is explicit caller-supplied evidence for a whole
legacy master already reviewed by its approver. Its required fields are
`master_sha256` (exactly 64 hexadecimal characters, compared case-insensitively),
`approver` (`arc4d3` or `Pedro`), `approval_message` (an `authority.Message` with
matching author, nonempty source reference and retained text), `scope` (only
`legacy_reviewed`), and nonempty `reason`. Construction validates these fields;
`parse` rejects missing and unknown fields, including nested message fields.
`record` returns a JSON-compatible evidence record.

`evaluate_release(master, project, release_approval=approval)` still measures the
master and returns all checks, findings, acceptance, and measurement errors
unchanged. A matching approval releases the whole master despite failed or
unmeasured checks, including a missing, errored or refused ADR 0247 final-frame
review. These legacy masters were reviewed by a person before the frame gate
existed; the whole-master approval covers that frame review too, while retaining
the current frame diagnostics. `Reading.release_approval` identifies the evidence
used and `Reading.lines()` reports RELEASED with its full evidence, alongside
every original check. Individual failed checks and `acceptance.ok` remain failed;
callers use `Reading.refused` for the overall release decision. A stale or
untyped approval refuses even an otherwise passing master, with a release
approval error in the report. The bytes are checked again after evaluation;
replacement during measurement or evaluation refuses. No approval can release
an unreadable/missing file whose hash cannot be verified.

This expresses the task's retained ruling reference, Slack 1793906449.811309:
reviewed unposted legacy masters stay ready under arc4d3's hash-bound review;
a replaced master loses the exemption. The source message and the count of
eligible masters were not independently available in this checkout. The SDK
validates evidence structure and exact byte binding, not remote identity,
message authenticity, or historical membership. Trusted callers must retain the
actual source message and supply the legacy/reviewed classification explicitly.
The SDK creates no evidence records on behalf of the approver.

There is no inferred approval or default approval: the optional argument defaults
to None. Timeline approval metadata, script waivers, historical labels, delivery
manifests and Drive presence cannot supply it. `scope` on `evaluate_release`
continues to classify per-check Dispositions; it does not infer this separate
legacy approval. This addition is limited to `evaluate_release` and the overall
`Reading.refused` decision; frame review and publication filtering stay at their
existing caller boundaries (ADRs 0246 and 0247). A frame refusal or frame error
added to a Reading remains visible in `lines()` but does not prevent release
under a valid whole-master approval for those exact bytes.

## Alternatives rejected

- Per-check Dispositions: ADR 0246 requires an exact check/line and measurable,
  eligible values. They intentionally cannot approve missing/nonfinite measures,
  missing recordings or a complete reviewed master. Fabricating one per check or
  adding a wildcard would weaken their existing contract.
- Rewriting checks to PASS/WAIVED or clearing errors: hides current measurement
  results and conflates review-based release with measured acceptance.
- Skipping measurement for approved masters: conceals failures and prevents a
  complete diagnostic report for the same bytes.
- Inferring approval from legacy status, scripts, delivery or Drive: none is an
  explicit hash-bound review, and replacement would inherit permission.
- Ignoring stale or malformed approval when measurements pass: silently drops
  invalid supplied authority instead of refusing.
- Adding publication exclusions or changing final-frame staging authority here:
  belongs to callers and exceeds this release API change.
