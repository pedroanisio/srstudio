---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0238: The News template's one band

- Status: proposed (2026-11-04). The frame, the framings and the head motion are a proposal: the proof clip is at
  `generated/news-template-proof/`, and no reel may stage on `srstudio.news_template` until arc4d3 approves it
- Deciders: arc4d3; ordered after the 4 Nov News craft audit; written by Claude Opus 5.5 in Claude Code
- Follows [ADR 0060](0060-news-kit.md), [ADR 0071](0071-news-anchor-head-rigs.md) and
  [ADR 0142](0142-news-hands-are-a-pair.md)
- Back to the [library README](../../README.md)

## Context

The 4 Nov audit of the News reels found the frame failing the craft bar in four ways:

- BREAKING, the lower-third, the ticker and the desk's chevron bar stacked into a strip of graphics about two fifths
  of the frame tall, and the PARODY tag stood on stories that are real.
- The anchors filled about 30 % of the frame's height and about 10 % of its area, so a talking face was small.
- A three-second line could pass with the head still: the nods of rig v3 (ADR 0071) were sized for that small face,
  and the head only turned when the other anchor spoke.
- The large source card sat at a fixed height over the desk, where Vera's hands and the papers are from the first
  frame. A builder's measurement also found a full-frame insert frozen for 2.2 s.

The audit's fixes were: one band of at most a fifth of the frame for the label, the lower-third and the ticker; medium
close-ups that fill at least two fifths of the frame; nods and turns driven by the speech; the source card off the
hands and props; and no PARODY tag on a real story.

## Decision

`srstudio.news_template` is version 2 of the News frame (`TEMPLATE = 2`). Version 1 stays as it is, so every reel
delivered on it renders the same; a new reel opts in by staging with `news_template.stage`, lettering with
`news_template.captions` and drawing its words with `news_template.band`.

- **One band** from `BAND_TOP` (y 1240) to `BAND_FOOT` (y 1420, the safe area's foot): 180 px, 9.4 % of the frame.
  The label row carries the credit chip on a real story, or BREAKING (and PARODY when asked) on fiction, beside the
  current kicker; under it the story's one line (the lower's, or with `line=` the story's own while no lower is up,
  so the row is never empty); under that the ticker, whose tab is sized to the show's name it carries. The bug,
  the chevron bar and the second label row are gone, so the band and the captions are the only two text layers. The
  band stands down while an insert is up. `band` refuses PARODY on a story that has a source.
- **Medium close-ups.** A shot is a camera on the version-1 set (`Framing`): the desk's middle placed at
  `(540, desk_y)` and the set scaled about it, the room behind at 55 % of that magnification. Vera's close shot is
  scale 2.45 (42 % fill), Gus's 2.4 (at least 40 %), the two-shot 1.75 with the anchors at x 300 and 780 (38 %).
  `desk_y` is chosen so the lowest a face reaches, at the most its head turns, rolls, nods and tilts, stays 6 px above
  the band; `face_reach` checks that the hair stays under a two-line caption and the skin inside the frame. `fill`
  measures the silhouettes (jacket, neck, skin, hair) above the desk, not their boxes. A pose tilted past 6 degrees is
  refused, since its chin would reach the band. The captions move up to y 226, where the bug's row was.
- **Heads keyed from the speech.** `STYLES` resize the rig-v3 nods for the closer face (Vera 9 px with a 2 degree
  roll, Gus 12 px with 3), and `onsets` adds a turn on each line's onset: toward the other anchor on a reply, away on a
  line that follows the anchor's own, back to camera 0.9 s after the first word. The reel's first line is said to
  the camera. The turns never overlap the ones
  `news_head.facing` makes or a hold. Everything is computed from the takes, so the same takes give the same plan.
  `crown_travel` measures how far the top of the hair moves over a span; a three-second talking hold must move it at
  least 15 px in the frame.
- **The source card is the band.** The large card fills the band with the outlet, the date and the headline, so it
  covers nothing above y 1240. `card_plan` ends it `EASE` before the first hand or prop of the shots (`obstacles`:
  hands, Gus's phone held and down, Vera's papers, the mug and the notepad, each in frame pixels over the time it is
  there) comes into the band, or at the moment the story goes small. If that leaves under 2 s, only the credit shows,
  from the first frame.
- **Inserts keep moving.** `insert` pushes a full-frame insert in from 1.16 to 1.2 times the handset's size, keyed at
  least every 1.5 s, so no frame of it holds; `phone_insert` draws Gus's phone inside it, the handset's screen inside
  the safe column and under two lines of caption.

## Consequences

- A new News reel staged on version 2 meets the audit's band, fill and motion measures by construction; the tests in
  `tests/test_news_template.py` hold each rule.
- In Gus's close shot his held phone is drawn at chest height, behind the band. The card yields to it, but the band
  does not. Clearing it needs either a higher phone hold (an acting change for arc4d3) or a looser framing that misses
  the 40 % fill.
- The credit leaves with the rest of the band while an insert is up, so the source is not on screen on every frame
  as version 1 keeps it: an insert's words and the captions are already the two text layers the bar allows. The large
  card opens the reel and the post's text carries the sources.
- Hands resting on the desk sit under the band in the close shots, in the area the Reels interface covers. The acting
  hands of Gus (`up`, `point`) are above the band.
- The episodes repository needs its srstudio pin moved to a commit with this module before a reel can opt in.

## Rejected alternatives

- **The band at the top of the frame.** It would sit over the hair of a medium close-up and under the captions, two
  text layers pressed together, and the Reels interface's top is lighter than its foot, so the strip would waste the
  better area.
- **The captions inside the band.** It would put three text rows in one strip and change the captions' line on every
  cut between a lower-third and none; the captions stay over the heads, the second and last text layer.
- **A smaller framing with the version-1 graphics.** A close shot at scale 1.22 fills 10 % of the frame and cannot
  reach two fifths without the graphics' 40 % strip coming out.
- **Measuring fill by the anchor's height share.** The audit's "about 30 %" matches the height share of the version-1
  close shot (31 %), but height ignores how wide a body is: a thin figure at full height would pass. The silhouette's
  area is the measure.
- **Moving Gus's phone hold higher.** It would clear the band, but it is an acting change to an approved rig, and it
  needs arc4d3's word first.
