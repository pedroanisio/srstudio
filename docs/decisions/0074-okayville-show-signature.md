---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0074: The Okayville show signature, and who owns the number

- Status: accepted (2026-10-31). arc4d3, by the operator's delegation of 2026-10-31, Slack 1793501087.434969 in thread
  1793465980.837619: "Show signature: approved, with one change to the mark." The change: the mark is the avatar's OK-eye.
- Deciders: arc4d3, the publishing side, for the look and the base counts; written by Claude Opus 5.5 in Claude Code
- Follows [ADR 0013](0013-designed-thumbnails-and-publish-gate.md),
  [ADR 0037](0037-the-cover-fingerprint-is-the-drawing.md),
  [ADR 0047](0047-character-versions.md) and
  [ADR 0073](0073-frame-gates-and-standing-review.md)
- Back to the [library README](../../README.md)

## Context

arc4d3 asked for three things on every new Okayville reel. One cover template whatever the art style: the same band in
the same place, the word OKAYVILLE, the episode number counted from the first reel on the account, and the premise in at
most 5 words, crop-safe for the grid and readable at thumbnail size. A small fixed corner bug from the first frame to the
end, carrying the OK-eye mark and the number, clear of Instagram's UI, of captions and of faces. And on series episodes,
their own number on the band and in the caption's first line, after the question.

The 64 reels in production stay as they are, so the new look can be measured before and after. Every published and
queued reel must rebuild byte for byte what it was.

Two facts shape the design. A number on the bug is burned into the video, so it has to exist before the final build.
And Instagram's feed is not this repository's: delivery records what was delivered, and the hourly posting job decides
what goes out and when.

## Decision

1. **The cover is a `ShowCover`, a subclass of `Thumbnail`** (`srstudio.thumbnail`). A solid band from y 1270 to the
   bottom, a yellow rule on its top, the header `OKAYVILLE #N` and the premise under it. The art above stays the reel's
   own. The band's text sits inside the 3:4 grid crop (y 240 to 1680). A subclass leaves `asdict` of every other cover
   as it was, so no existing fingerprint moves.
2. **The bug is a part, `show-bug`, drawn only by a numbered build** (`srstudio.show`). `srstudio build` reads the
   release; a release on a `ShowCover` builds inside `show.stamping(number)`, and `Episode` draws the bug as the
   composition's last child at finish, above the camera. A build with no number produces the document it always did.
   It adds no seconds and hides in the cover variant, so a release on this cover needs `cover=True`.
3. **The corner is the right gutter, x 926 to 1044, y 270 to 332.** It lies outside the safe area, so no checked text
   reaches it, and under the top 14 % of the frame, to y 270, that Meta asks to keep clear. The numbers are below.
4. **The number lives in the release and in a ledger** (`srstudio.show_numbers`). `srstudio number claim <slug>` takes
   the next number under a file lock in `generated/okayville/numbers.json` before the final build, and the release
   declares it in `ShowCover.number`. The next number is `max(base, highest claimed) + 1`. `base` is set once, from the
   publishing side's count, and claims are refused until it is. A series has its own base and count.
5. **A delivery gate refuses a reel on this cover** that is out of the look (`srstudio.show_gate`, run by `write_all`
   for first deliveries): a number missing from the ledger or different from it, a number another release holds, a
   series tag missing from the caption's first line, a bug that is missing, moves, fades, or carries another number, a
   bug over a face, a signature mark or text, a band over a face, or a video whose corner is not its scene's.
6. **The number reaches the posting job in `episode.json`,** beside `ab.json` in the outbox: exactly
   `{"number": N, "series": "saga" or "", "series_number": n}`, the typed `show_numbers.EpisodeDocument`. The series is in
   lower case. A reel in no series writes `"series": ""` and `"series_number": 0`. A reel with no number has no file, so
   the outbox of every published reel stays the same.

## The corner, measured

668 frames sampled from 15 reels across the styles, at the chip's own size, counting the frames in which the box meets
a piece of text, a signature mark, or the top 40 % of a recorded figure:

| Corner | Text | Mark | Face |
|---|---|---|---|
| Right gutter, x 926 | 0 | 4 | 10 |
| Upper left, x 80 | 63 | 0 | 39 |
| Upper right, x 802 | 38 | 0 | 16 |
| Left gutter, x 36 | 47 | 0 | 14 |

That chose the gutter, with the chip at y 232. It was drawn 66 px tall there, and that sits inside the top 14 % Meta asks
to keep clear, so it moved down. The same 668 frames through the gate's own rules, with measured text and drawn outlines:

| Chip | Text | Mark | Face |
|---|---|---|---|
| y 232 to 298 | 0 | 4 | 4 |
| y 270 to 336 | 4 | 4 | 5 |
| y 270 to 332 | 0 | 4 | 5 |

At 66 px the moved chip reaches the widest caption of the sample, a pill on text-me that starts at y 334 and runs under
the chip's left half, so the chip is 62 px tall and ends 2 px above it. Starting lower gives the same counts or worse, and from y 380 the
face count is 36.

The bug stays fixed: a reel that meets it is changed, never the corner. The gate refuses two of the 15 reels as they
stand, the same two at both heights and both true by the rule: take-my-phone, where the cactus's pot sits behind the chip
in 4 of 43 frames, and gloss-terms, where a robot's head touches under it in 5 of 57. They are published and will never
meet the gate; on a new reel the author moves the pose or the mark.

The chip now overlaps the top right corner of the Stick hook card, whose top edge is y 300 and right edge x 990. The
card's text ends before the chip, so the gate passes. That corner is what leaving Meta's zone costs at this x.

## The mark

The mark is the avatar's OK-eye, drawn from its vector source in the avatar's own coordinates: a tall filled yellow O, its
lower half a white eye with a black pupil and a highlight under a flat lid, then a condensed K, Anton's outline, so the
chip still needs no font. Two things differ from the source at a height of 28 px. The eye and the pupil stop at the lid
line rather than pass under a lid drawn over them, which left a white halo around the O's top. And the K stands 20 source
px further off, so the two letters stay apart.

## Numbers, and what they depend on

The number is a promise about the feed, and the only party that sees the feed is the publishing side. So the design
keeps what the code can guarantee apart from what it cannot.

**The code guarantees:** a number is unique, it rises in claim order, it is never reused, the cover, the bug and the
ledger agree, and a dropped reel leaves a gap.

**The publishing side supplies,** in Slack 1793501087.434969:

- The base. The first numbered reel is #193, from 107 posted, 21 queued and 64 in production at 23:40, so `base` is 192.
- The series. Saga's next is #19 (base 18) and Gloss's next is #10 (base 9).
- What counts. Only reels: carousels, stories and re-post variants get no number.
- The rule for reels left out. Numbers are never reused, so a pulled reel leaves a gap.
- The order. Autopost posts numbered reels lowest first, once no unnumbered reel waits, so the numbers count up on the feed.
- The reader. Autopost reads `episode.json` in the shape of decision 6. The message does not say what `series_number`
  holds outside a series; 0 is this decision's reading, and it is `Claim`'s default.

The ledger takes those counts once, when the first numbered reel needs them:

    srstudio number base 192
    srstudio number base 18 --series Saga
    srstudio number base 9 --series Gloss

## Alternatives rejected

- **Assigning the number at delivery.** It is burned in. Delivery would have to change a finished video, and the gate
  compares the video with its scene.
- **A late overlay at delivery, by ffmpeg.** The video would be a second-generation encode, its scene would no longer
  say what it shows, and the frame gates would measure something else than what goes out.
- **Computing the number from `delivery.json`.** Delivered is not posted: reels have been dropped, unpublished and held
  as holdouts, and the feed's count differs. The result would look exact and be wrong.
- **A table of numbers in a repository file.** Two sessions claiming at once would collide at merge, where a release
  file per reel exists so they do not. The ledger is locked and outside git; the release is the record in git.
- **A camera-bound bug.** It would slide and shake with the picture. A child of the composition outside the camera group
  stays pixel for pixel in place, which two moving clips confirmed.
- **The corner News uses.** It collides with burned text on Soft, Saga and Gloss, whose tops carry cards and captions.
- **A bug with a font.** Outlines read the same on every style and carry no licence or install step.
- **Keeping y 232.** It is one refused frame better on gloss-terms, a reel already refused, and it sits inside the zone
  Meta names.
- **A 66 px chip at y 270.** It runs over the top of a caption pill in 4 frames of text-me.
- **The eye on the cover band.** The request asks for the word and the number, and "OK OKAYVILLE" doubles it.

## Consequences

- `show-bug` version 1 is approved, and its approval names the drawing with the avatar's mark. A new reel pins it like any
  other part; `releases.unpinned` refuses a build that drew it without the pin.
- The look is opt-in. A new reel on a plain `Thumbnail` still ships, and the 64 in production stay as they are. Making it
  a rule for every new Okayville reel is one more gate.
- Every first delivery on this cover evaluates its frames twice more and reads one frame of the video.
- The gate reads the scene and one frame of the video, not Instagram. A face is an estimate: the top 40 % of a recorded
  figure, with outlines for the bug and the box for the band. A figure no registered character drew is unseen, and so is
  a face inside a prop. The full-size review stays.
- Instagram's UI zones are the repository's safe area, not a measurement on the app.
- The band covers the bottom of the art, and with it a signature mark set low in a frame; `Thumbnail.at` chooses that
  frame. The signature gate reads the video, where the marks are.
