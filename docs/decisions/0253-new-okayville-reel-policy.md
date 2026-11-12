---
generated-by: OpenAI Codex (codex-builder via govern)
---

# 0253 — New Okayville reel policy

Date: 2026-11-08

Status: accepted

## Context

ADR 0250 introduced cactus-only signatures and credit-last captions as opt-ins.
The corrected task and its addendum require complete disclosure, no code stamp,
a maximum runtime of 24 seconds, a frame-zero title, and no OK-eye chip for new
Okayville reels. The task cites arc4d3's 8 November ruling, Slack
`1794118363.554969`, and statements `videos.ruling.084` revision 3,
`videos.ruling.188`, `videos.ruling.189`, and
`videos.doc.authoring-delivery.011` revision 2. The latter was read from the
statement store and confirms the new signature-code default. The Slack source
was not independently read during this implementation.

## Decision

`show.NewReelPolicy` is explicit on `EpisodeSpec.new_reel_policy` for authoring
and in `show_gate.show_defects(policy={slug: policy})` for first-delivery checking.
A cover never silently enrolls a published reel in the new policy. Existing
number/ledger and cover-face checks still run. The legacy scene, frame and
rendered-corner bug checks remain on the path without a new policy. New-policy
scenes must contain no chip, including one-offs; their gate evaluates frame zero
instead of rendering a chip corner. This checks the scene document, not the
rendered video's correspondence with it; final-master review remains separate.

`social.disclosure(voices)` produces one shared line naming the synthetic voices
and containing “drawn in code”. New-policy captions must carry that complete
line in their credit block; missing or partial credit raises `DisclosureError`.
Legacy caption validation and fingerprint construction are unchanged.

New-policy documents refuse signature-code nodes and nonfinite, nonpositive or
above-24-second runtimes. `EpisodeSpec.signature_code`, `canvas.Signature.code`,
and `signature.missing` now default to `None`, superseding ADR 0250's default.
Callers preserving a code-bearing drawing explicitly pass `"SR-1028"` to both
construction and any direct requested-marks check. The cactus stays required.
No published episode source outside this SDK worktree was modified or verified.

Series are identified by `ShowCover.series`. `EpisodeSpec.situation_title` and
the policy's expected situation title must agree when drawing a series title.
One-offs use the caption's first line. After scene/camera authoring,
`Episode.title_card(post)` draws an opaque, high-contrast panel on the composition
inside the declared safe area, with a single measured line at least the existing
`minTextSize` (and at least 2% of frame height). A line that cannot fit raises
`NewReelPolicyError`, rather than wrapping or shrinking below that floor. The
panel shows for `show.TITLE_HOLD` (2.5 s) and then leaves the picture clear: it is an
opening line, not a band over the whole reel. The gate checks the evaluated
frame-zero title layer's exact text, draw flag and full opacity, so a title
asset unused or hidden at frame zero fails.

## Rejected alternatives

Applying the new gates to every ShowCover would reject published drawings.
Removing the old bug gates would lose their existing regression protection.
Making all credit mandatory in InstagramPost would change legacy caption
validation. A title stored only in metadata would not prove that frame zero
draws it. Editing published episode builders lies outside this task's worktree.

## Validation

Focused tests cover both policy branches, the 24-second boundary, disclosure
failures, code and chip refusal, exact visible frame-zero text, measured title
placement, missing series situations and explicit legacy code drawing. Legacy
signature fixtures request their original code explicitly and retain their
hash assertions. Gate integration uses evaluated-frame stand-ins; no render,
recording, publication or approval record is produced.
