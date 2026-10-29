---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0040: A published video whose cover now draws differently is frozen at the drawing the operator accepted

- Status: accepted; implemented 2026-10-29 (`Release.frozen`, `social.check_delivery(frozen=)`,
  `social.publish(frozen=)`, `outbox.ready(frozen=)`, `instagram_posts.FROZEN`; `tests/test_social.py`,
  `tests/test_outbox.py`, `tests/test_releases.py`)
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Amends [ADR 0037](0037-the-cover-fingerprint-is-the-drawing.md)
- Back to the [library README](../../README.md)

## Context

After the migration of ADR 0037, `instagram_posts.py check` reported exactly five drifts:

- saga-exit-interview
- saga-expense-report
- saga-icebreaker
- saga-moving-day
- saga-on-hold

Their scenes changed after they were published, so the cover their post draws now is not the one delivered. Their
renders, `ig.txt` and `cover.jpg` are the published ones.

Published videos are frozen, so these five will not be delivered again. That left the gate red on every run, for a
known reason:

- A gate that is always red hides a new drift among the old ones.
- `publish_drive.py` held the five back from the Drive outbox.
- A full `deliver` would have redrawn their published covers.

## Decision

1. **A release can be frozen at one drawing.** `Release(frozen=<fingerprint>)` holds the `social.fingerprint` that
   its post draws now. Only the operator decides that a release is frozen. The value is 64 lowercase hex digits,
   or `ReleaseError` is raised.
2. **The gate accepts that drawing and no other.** `check_delivery(frozen=)` takes a frozen video's delivery as
   current when the fingerprint drawn now equals either the delivered one or the frozen one.
   - Every other check still applies: the render, `ig.txt`, `cover.jpg` and the manifest.
   - Any further change to the caption, thumbnail, font, scene or layout gives a third fingerprint, and the video
     drifts again.
   - `frozen` naming a video that is not published raises `DeliveryError`.
3. **A frozen video is never delivered again while it is current.** `publish` keeps the manifest entry of every
   video it does not deliver as recorded, so a full `deliver` leaves the five covers and entries as published.
4. **The exception is visible.** `check` prints the frozen videos on every run. `publish_drive.py` passes the same
   map to `outbox.ready`.

## Rejected alternatives

- **Redelivering the five.** This would replace published covers, and published content is frozen.
- **Accepting any drift for a named video.** A name-only exception would hide a later re-render, an edited file or
  a further change to the drawing. Pinning the exact fingerprint keeps every one of those visible.
- **Rewriting their manifest entries to the new fingerprint.** The manifest would then claim that the delivered
  covers were drawn from today's post, which they were not. `delivery.json` records what was delivered. The
  exception belongs in the release, next to the post it excuses.

## Consequences

- With the five pinned, `check` on the delivery as it stood on 2026-10-29 printed `84 videos, delivery current`
  and exited 0.
- On its next run, the Drive outbox stages the five again, with their published files.
- A change that alters every composed cover, such as a change to the scene SDK's bytes, makes the five drift
  together with every other video. The pins are then recomputed under the same operator decision, and the change
  is recorded here.
