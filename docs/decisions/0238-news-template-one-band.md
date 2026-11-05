---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0238: The News template's one band

- Status: accepted (2026-11-04). arc4d3 approved the band and the framing in Slack (thread 1793825656.258549,
  message 1793831201.407529) for Fri 6 Nov's roasts, with three fixes before the first reel ships: the phone as a
  cutaway, Gus's raised hold and a body move on every line. They are part of this decision. The craft bar (C1–C8)
  then asked for five more on 5 Nov, part of it too: the phone in inserts of at most 2 s and 15 % of the reel, the
  screen over the frame's whole height, both signature marks on the phone, a one-hand hold beside Gus's face, and the
  takes reaching the card in episodes. The proof clips are in `generated/news-template-proof/`
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
  scale 2.45 (42 % fill), Gus's 2.4 (at least 40 %), the two-shot 1.7 with the anchors at x 293 and 760 (36 %), so
  a leaning head stays inside the frame.
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
  least every 1.5 s, so no frame of it holds.
- **Gus's phone is a run of short cutaways.** `phone_insert` takes spans, one cutaway each, over an opaque backdrop,
  so nothing of the shot shows and nobody holds it, and the reel cuts back to a face between them. The chat builds
  across them: every message after the first span's start lands inside a span, each later span lands one more, each
  slides in over 0.2 s, and the last span ends on the whole chat, its last message at `CHAT_FOOT`. Each span's last
  message stays up at least `craft.MIN_DISPLAY` (0.83 s) and at most 1.5 s. `flat_inserts` refuses an insert over
  `INSERT_MOST` (2 s) or inserts that take more than `INSERT_SHARE` (15 %) of the reel; `phone_insert` runs the first
  and `band` both. `reaction(shots, end, who)` refuses an insert whose next shot is not one of `who`'s: Gus or Vera
  between two, Gus after the last.
- **The phone fills the frame.** The handset's screen runs the frame's whole height (C1: no empty dark band): a status
  bar over the safe area with the signature code as the carrier's name, the chat's head under the captions with the
  signature cactus as its picture, the chat to `CHAT_FOOT`, and the message field and a keyboard of shapes under the
  safe area, where no words go. The words are sized to fit the safe column at the push's largest scale, up to 78 px.
  `frame_gates.signature_shown` sees both marks on every frame of every insert.
- **Gus holds his phone up in one hand** in his close shot (`GRIP`, a `news_inked.Grip` with `phone_x`,
  `phone_size`, `phone_wide` and `screen`): beside his face on the frame's right, its screen turned to the camera and
  foreshortened as it turns (0.7 of its width), clear of his eyes and mouth at every turn and drop of his head and
  over the band, the fist under it on an elbow no sharper than `news_arms.ELBOW_LEAST`; the other hand rests on the
  desk. It stays inside the frame in his close shot and in the two-shot. The framing does not change; the fill stays
  at 40 %. Version 1's hold, `Grip()`, is untouched.
- **The body moves on every line.** `body` keys, from 0.2 s before each line's first word, a lean toward the other
  anchor (3.5 degrees of skew about the desk's top, so the head goes sideways and never lower), both hands up
  beside the face (`GRIPS`, a mirrored open pair above the band in every shot), and a lean away, in turn. A lean holds
  to the line's last word; the hands stay up 0.9 s. When the hands are busy with a prop, their turn leans instead.
  `obstacles` and `card_plan` take the takes, so the large card also yields to hands that come up, and a show's
  overlay gets them from `toon_sketch.Staging.overlay_said`, which hands the overlay the takes the heads read.
- **Words stay up long enough to read.** `band` refuses a lower or the story's line that an insert or another lower
  leaves up for less than `craft.MIN_DISPLAY`.

## Consequences

- A new News reel staged on version 2 meets the audit's band, fill and motion measures by construction; the tests in
  `tests/test_news_template.py` hold each rule.
- Gus's raised phone shows its screen beside his face with a glimpse of the chat; the chat itself is read in the
  cutaways. It no longer comes into the band, so the large card does not yield to it.
- A reel with a phone writes it as phone shots of at most 2 s, each ending on a face, the last on Gus's, and lands a
  message in each, its last up 0.83 to 1.5 s; the checks refuse anything else. On a 25 s reel the three inserts may
  take 3.8 s together. A lower that would show for less than 0.83 s between them must start at a cut back.
- A line's take can land across a cut: on the proof the second insert starts 0.23 s before Gus's "Obviously." ends.
- The credit leaves with the rest of the band while an insert is up, so the source is not on screen on every frame
  as version 1 keeps it: an insert's words and the captions are already the two text layers the bar allows. The large
  card opens the reel and the post's text carries the sources.
- Hands resting on the desk sit under the band in the close shots, in the area the Reels interface covers. The hands
  up and Gus's `point` are above the band.
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
- **The phone as an inset over the shot.** A handset inside the safe column left half its screen blank and sat over
  Gus's face; the cutaway gives the chat the frame's width and hands the picture back to his reaction.
- **One cutaway held over Gus's lines.** It kept the chat on screen for 5.8 s, 23 % of the reel, over the craft bar's
  2 s per flat insert and 15 % in all.
- **The phone under his chin in both fists.** At full size it read as a neck pillow, the arms a V from under the
  desk (arc4d3, 5 Nov).
- **The phone on the side of his face toward Vera.** It stays in the close shot, but in the two-shot it would cover
  Vera's face.
- **A looser close shot for the raised phone.** It would leave room for a taller phone, but the fill would drop under
  40 %, which the audit ranks first.
- **A shrug as the second body move.** In the close shots the shoulders and the hands sit under the band, so a shrug
  did not read on screen; hands up beside the face do.
