---
generated-by: Codex (codex-builder via govern) and Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# 0250 — Opt-in cactus-only signatures and credit-last captions

Date: 2026-11-06

Status: accepted

## Context

For new Okayville deliveries, arc4d3 ruled that SR-1028 reads as a render artifact:
remove it from every frame and the cover, retain the signature cactus, and put the
caption credit after the hashtags as the last block. The task records this as
Slack timestamp `1793944493.261229`, statements `videos.ruling.179` and
`videos.ruling.180`.

Already delivered reels must retain their drawings, captions and delivery
fingerprints (ADR 0037).

## Decision

`EpisodeSpec.signature_code` and `Canvas.Signature.code` accept `None` to draw
only the cactus. Code drawing returns without creating a group or consuming an
id. A performing cactus retains its animation but omits the pot code even when
`Act.code` is true. Locations share this code drawing helper, so the choice also
holds for their cover backdrop. The signature check always requires a cactus in
a signed episode and requires a code group only when the spec requests code.
The default remains `"SR-1028"`; `signature=False` still means unsigned.

`InstagramPost.credit_last=True` places a nonempty credit block after hashtags.
Absent credit or hashtags creates no extra block. The default remains false,
with title, description, credit, hashtags in the existing order. Append the field
to preserve existing positional arguments. Release loading and item construction
retain the post itself, so the option needs no duplicate release field. Delivery
fingerprints already hash `post.text()`: keep that schema and hash the actual
chosen caption, without adding an option field that would change old digests.

The separate first-delivery frame visibility gate (`frame_gates.signature_hidden`)
still measures both marks; this change does not lower that gate. A cactus-only
scene will require a separate explicit integration decision before that delivery
path can accept it.

Regression tests retain a document captured before this change and an existing
caption fingerprint, plus exercise both opt-ins and missing-mark failures.

## Rejected alternatives

Changing the project-wide default would redraw published reels and change their
caption fingerprints. Both choices must be explicit for new deliveries.

Dropping the whole signature would lose the cactus arc4d3 explicitly kept and
would weaken the signed-episode check. Keep the cactus required.

Writing an empty string or placeholder would leave an empty code group or draw
an unwanted substitute. `None` creates no code at all.
