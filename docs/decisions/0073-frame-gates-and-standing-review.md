---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0073: Frame gates and a standing full-size review

- Status: proposed (2026-10-31), on arc4d3's messages of that day: "Make the full-size frame review a standing gate for
  every Okayville batch from now on", "Add the defect classes you found (floating figures, missing limbs, a detached
  head, run-together captions) to your checks, so the next batch catches them automatically", and "Full-size frame
  review on each reel's first render, not after the batch. Look at a few full-size frames per reel as soon as it first
  renders: captions, faces, marks inside heads, props. A defect then costs one re-render instead of holding a whole
  batch."
- Deciders: arc4d3, the publishing side, for the standing gate; written by Claude Opus 5.5 in Claude Code
- Follows [ADR 0037](0037-the-cover-fingerprint-is-the-drawing.md),
  [ADR 0040](0040-frozen-releases-at-an-accepted-drawing.md) and
  [ADR 0048](0048-caption-looks-are-approved-and-measured.md)
- Back to the [library README](../../README.md)

## Context

A review of the Okayville batches of 31 October looked at frames of each reel at full size, one image at a time. It
found what the authors' reduced-size passes had missed: figures that stop in a straight cut above the counter, a
waitress and a kid with no legs, a head 130 px off its neck, a set that ends above the bottom of the frame, captions
that run two sentences together, and reels that never show a signature mark though their parts list draws it.

Those passes used contact sheets, which show that a shot exists and not that a body ends. The review itself views four
frames per reel, which is a sample. Neither can be the only control.

Published content is frozen, so nothing here may ask a delivered reel to change.

## Decision

1. **Five classes are refused at first delivery.** `write_all` in `episodes/instagram_posts.py` runs them on `first`,
   the videos delivering and not in the manifest, by the test ADR 0056, 0064 and 0065 use. The refusal is a typed
   `FrameGateError` naming the reel and the measure, before anything is written. `check` does not run them: it runs no
   engine, and a delivered reel owes nothing.
2. **A build records which nodes are a character.** A scene's nodes are anonymous, so `usage.trace` keeps the ids each
   character call drew in `figures.json` beside `parts.json`. The scene stays byte for byte what it was. A new reel
   with no record is refused until it is built by `srstudio build`.
3. **The measures read the engine's frames.** `scene-render eval` gives each live node's world matrix and opacity, and
   the scene gives its outline, so a gate samples a frame every 0.5 s and the last one without rendering a pixel, and
   the placing is the engine's own (`srstudio.framegraph`).
4. **The review stays, in two steps, in the funny-reels skill.** The building agent views a few full-size frames of
   each reel at first render, before going on to the next reel. Someone who is not the author then views the finished
   batch at 1080x1920, one image at a time: the first frame, 2 s, 75 % and the last frame. The orchestrator checks each
   blocker before acting on it, and a blocker holds its reel. Batches deliver independently: "deliver batch by batch, a
   batch never waits for another".

## The gates and their numbers

Every number below was measured on the reels' scenes as they were when the review saw them, rebuilt byte-identical, and
on the 64 reels of the three batches after their fixes.

**Run-together captions** (`frame_gates.captions_run_together`). A burned window is compared with the reel's sentences,
from its transcript or its subtitles. A pair of words that ends one sentence and starts the next, and that is not also
said inside a sentence, may not sit in one window unmarked. A marked window (`Take it. Whatever`) passes. Over the built
reels it finds nine, all real on reading: `Take it Whatever`, `home He wears a tie`, `Hey Over here`, `Step one Two` and
the rest. Silent reels have nothing to compare.

**Signature marks** (`frame_gates.signature_hidden`). Both marks must be seen in `MIN_SHOWN` = 0.5 of the sampled
frames, "most" in its literal sense. A mark is seen when 75 % of its box is on the frame and clear of solid shapes in
front. Reels the review named as missing marks measure 0.0 (third-snore, more-tired, good-you), and clean ones 0.79 to
1.0. Over 170 built reels the median is 0.86 and the first quartile 0.45. 42 of the 125 delivered reels in that survey
are under the line, which is why the gate cannot apply to them.

**A figure's cut** (`figure_gates.cut_of`). The longest level run of a figure's bottom edge, within 6 px, is a cut when
it reaches `MIN_CUT` = 90 px, a quarter of the figure's height, and sags under 3 px. A cut passes at the frame's lower
edge, behind a cover that hides `COVERED` = 80 % of it and goes on `COVER_DEPTH` = 40 px, or held by something behind
it: a ledge at its row, or legs tucked under a hem, which is what the fix to book-a-table drew.

| Measure | Passes | Refused |
|---|---|---|
| Width | a small round chin, 66 px | the shortest real hem, 99 px |
| Share of height | a shoe's sole, 0.19 at most | a real hem, 0.28 at least |
| Sag | a brushed cut, 2.3 px at most | a round head, 3.8 px at least |
| Hidden | a counter hiding most of a dog, 0.82 | the car hiding part of the fox, 0.74 |
| Cover depth | the shallowest real ledge, 51 px | Priya's stool seat, 24 px at most |

It refuses one-more-taste's four figures (cuts 279 to 549 px at y 1405 to 1411), the cat of call-your-mother (723 px,
25 px over the table), the fox of the-noise, Deb and Priya of book-a-table and the barista of how-is-everything and
headphones.
Of the 64 fixed reels it refuses one, ill-get-this, whose two men stop in straight cuts on the face of the counter: a
real defect the review did not reach. The reels those fixes changed pass: one-more-taste, the-noise, call-your-mother,
book-a-table. So do the five clean reels held out for proof: its-soaking, free-shipping, your-lasagna, one-more-page,
loaded-right. Stick figures are strokes and have no fill to end, so the measure skips them.

**A detached head** (`figure_gates.head_offset`). The Stick rig keys its head apart from its body, so a pose can leave
them apart. The offset is the head's distance from the line of the torso in head radii, and `HEAD_OFFSET` = 0.75 is the
limit. seat-belt-sign measures 0.89. Everything else measured stays at or under 0.58, the tired slump of more-tired, and
the fix to seat-belt-sign brings it to 0.49.

**A set that runs out** (`figure_gates.run_out`). A 48 px band along each edge shows the project background through no
solid shape. It is a defect when one edge shows it on 90 % and the other three on at most a quarter: a frame with no
set, like free-shipping's flat colour, shows it on every edge. the-tongs is caught from 18.5 s to its end, and none of
the 64 fixed reels are.

## Consequences

- Reels undelivered at this writing that the gates refuse until fixed: ill-get-this (cut figures), and on the signature
  did-you-pack 0.20, headphones 0.33, how-is-everything 0.0, some-assembly 0.47, four-coats 0.26, scan-the-code 0.0.
  Viewed at full size, the marks of four-coats and scan-the-code sit behind a suitcase and a head.
- Every first delivery evaluates its frames twice, once per frame gate, which adds to `deliver` per new reel.
- The gates do not see: an arm with no hand and a hand with no arm (baby-monitor's mitts, text-me's third arm), legs
  absent from a figure the frame crops anyway, scenery hanging in mid-wall (wave-back's rack), a caption over a face, a
  mark that is on the frame but too faint to read, or anything an effect draws, since `framegraph` reads outlines. Cuts
  under 90 px on small figures and a run-out under 48 px also pass. These stay with the review, and a clean gate proves
  none of them.
- The cover and support numbers rest on a thin margin in places (0.74 against 0.82). A new style with a soft-bottomed
  costume or a tall thin cover will test them. Change one only on rendered proof, never to quiet a reel.

## Rejected

- **Only per-reel tests**, as the fixes of the batches added. Each holds one reel it already knows about, and the next
  reel's defect is a new one.
- **A raise in the Stick rig for the head.** A build-time refusal would stop delivered reels from rebuilding, which
  `srstudio usage` does for every episode.
- **A part's contract that it has legs or is declared cropped.** A contract states intent, and third-snore shows what
  that is worth: its parts list drew both marks. The Cutout barista declares no legs by design, and a reel can hide
  that legitimately. Only the frame says whether it did.
- **Comparing rendered pixels.** Rendering a whole reel per gate costs more than evaluating it, and a pixel does not say
  which figure it belongs to. The review already looks at pixels, with eyes.
- **A vision model as a gate.** Its output would be one more unverified report, and ADR 0015 already refused a model as
  a judge of what ships. The review stays with reviewers, checked by the orchestrator.
- **Dropping the review once the gates exist.** The gates cover what could be measured, and the classes above could not.
