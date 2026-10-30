---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0045: A sloth, a goat and a hamster with drawings of their own, and a yawn, a scream and puffed cheeks for every brush character

- Status: accepted; implemented 2026-10-30 (`srstudio.toon_critters`: `Critter`, `SLOTH`/`GOAT`/`HAMSTER`,
  `pressed`, `drift`, `shade`, `shared_eye`, `shared_mouth`; `toon.EYES` gains `sleepy`, `toon.MOUTHS` gains `yawn`,
  `scream` and `puff`; `toon_cast.SLEEPY_PACE`/`SLEEPY_HOLD`, `blink_times(hold=)`; `tests/test_toon_critters.py`,
  `tests/support/toon_thumbnail.py`)
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Extends [ADR 0041](0041-toon-cast-expressions-and-wear.md); shares the `toon_cast.Drawing` hook with ADR 0044
  (the inked fox, on its own branch when this was written)
- Back to the [library README](../../README.md)

## Context

The operator picked three animals from a sheet of internet reaction memes: a sloth, a goat and a hamster. The
characters have to carry the reaction each animal is known for: a huge yawn, a scream, and cheeks puffed in delight.
They must not reproduce any of the memes. Every reel ships to YouTube, and a copyright strike can close the channel.

The operator also judged that the brush cast looks less polished than the traced cat. A `toon_cast.Look` is drawn
from its fields with one shared face. The outline is mirrored and has few points, the line weight is even, there is
no shade, and the inner marks are closed blobs. The traced cat has a dense outline, a line that swells and thins,
and open strokes.

## Decision

### Three original characters

1. **A sloth, a goat and a hamster** (`toon-sloth`, `toon-goat`, `toon-hamster`). Each is drawn from the animal's
   anatomy, not from any photograph, meme, mascot, emoji set or franchise character.
   - **Sloth:** olive and droopy. A shaggy crown with one bed-head tuft, a pale face disc, two dark stripes running
     down and out from the eyes, and a small dark nose. Long arms end in three ivory claws laid along the desk. It
     blinks slowly (`blink` 4.6 s). Its own yawn is deep and has two peg teeth.
   - **Goat:** lilac and wiry. Horns sweep up and back, ears stick out sideways, and the muzzle is long and pale with
     a chin beard. Its amber eyes have bar pupils wider than they are tall. It has thin arms and dark hooves. Its own
     scream is taller than the shared one and has shout lines at the corners.
   - **Hamster:** pink and round. A squat head sits low on the body, with round ears, pale cheek pouches, a creamy
     belly and beady glossy eyes. Its paws are tiny pale mitts with the fingers pointing up. In its own puff, the
     pouches blow up past the head.
2. **Told apart by ADR 0041's measures.**
   - Each head (all its foundation contours: head, ears, horns) reads apart at thumbnail size from every other
     character, the other two included. "Reads apart" means at or above the floor that the older cast sets, the
     closest pair among the cat, dog, frog, bear and rabbit.
   - Each coat is more than ΔE 20 in CIE Lab from every other coat.
   - The builds are tested to differ. The goat's face is the narrowest of the three and has the longest eye-to-mouth
     span. The sloth's arms are the thickest. The hamster's crown sits lowest.
3. **The whole contract.**
   - Every `EYES`, `MOUTHS` and `ARMS` kind, every `BODIES` pose, the visemes, blinks, typing frames and
     `figure_shapes`.
   - `CHARACTERS`, `LIP_SYNCED` and `DRAWERS` in `sketch`, and the registry entries.
   - `toon_wear` and the headset. Both fit the face that a `Look` carries, so they need nothing new.

### Drawn like the cat, in code

4. **A `Critter` is a `toon_cast.Drawing`.** `Look.drawing` routes the figure's foundation, eyes, lids, mouth,
   visemes and limbs to it. The hook is the same one ADR 0044 adds, line for line, so the two branches merge
   without conflict there. A critter keeps an untilted face `Look` for the shared parts and carries:
   - **a dense, asymmetric outline.** Every contour is placed by hand without mirroring, at 40 points or more against
     the fox's 14. `drift` moves it off its points by a deterministic wobble, like a hand following it.
   - **a pressed line.** `pressed` is a closed band. It is heavier where the outline faces away from the light (the
     bottom and the back) and thinner at sharp convex turns, where a brush lifts. It also has a little deterministic
     grain. Arms are inked heavier along their underside.
   - **open, tapered inner strokes** (fur on the crown and chest, the chin line, ear and paw creases, whiskers).
     They are pressed at the root and lifted at the tip, never closed blobs.
   - **one shade tone.** `shade` lays it along every run of the outline that faces away from the light, and along
     the underside of each arm from the elbow.
   - **a slight head tilt** (sloth 7°, goat −6°, hamster 5°). It turns about the neck and fades to nothing at the
     shoulders, so the arms and the desk line do not move. The shared face parts are drawn on the untilted face,
     then turned with the head.
   - **its own face drawings where the anatomy needs them**: the sloth's stripes and yawn, the goat's bar pupils and
     scream, the hamster's beady pupils and puffed pouches. Every other kind comes from the shared brush parts.
5. **Each critter's signature expression is its own drawing.** A test asserts that the drawing differs from the shared
   one.

### New kinds for every brush character

6. **`sleepy` eyes** are very heavy lids over low pupils, with a lid line and a bag line. `figure` blinks them at
   `SLEEPY_PACE` (1.8) times the look's blink period and holds each blink for `SLEEPY_HOLD` (0.34 s), against
   `BLINK_HOLD`. `blink_times` takes the hold and refuses one that is not positive.
7. **`yawn`, `scream` and `puff` mouths.**
   - **yawn:** a tall oval showing the throat and the tongue.
   - **scream:** wider than a shock, with a row of teeth, the tongue and the throat.
   - **puff:** a closed smile between two cheeks puffed outward.
   - `shared_eye` and `shared_mouth` draw these for every brush look. The rabbit's front teeth stay off a scream,
     which bares its own row.
8. **The traced cat refuses all four by name** (`ToonDataError`, "the traced cat has no 'yawn' mouth"). It has no
   fallback, as in ADR 0041, because cat.json was not traced with them.
9. **Every existing kind on every existing character draws byte-identically.** A test pins digests of the older
   looks' full expression sweep, and the rebuild proof checks the published episodes.

## Why these three

They cover three reactions the cast could not show: exhaustion, loud outrage and small delight. Each one comes from
the animal's anatomy (a sloth's yawn, a goat's bleat, a hamster's pouches), not from a particular picture. The three
builds are droopy and heavy, wiry and long, and small and round. These sit apart from the existing cast and from each
other, as measured.

## Alternatives rejected

- **Likenesses of the meme animals.** This covers the photographed sloth, screaming goat or hamster, and any famous
  cat or dog. A recognisable copy of a viral photo or a named pet invites a copyright or likeness claim, and a strike
  can close the channel. The characters take the reaction, not the picture.
- **Real people from the sheet.** Their likeness is not ours to use, in a caricature or anywhere else.
- **Emoji-style faces** (a yellow disc, the platform set's eyes and mouths). An emoji set's look belongs to its
  vendor, and the cast would read as stickers rather than characters.
- **Drawing the three as plain `Look`s.** They would keep the even line and the mirrored outline that the operator
  judged unpolished. The `Drawing` hook lets them draw like the cat without changing how the older cast draws.
- **Basing on ADR 0044's branch, or growing `brush.py`.** That branch was not merged. Waiting on it, or editing the
  shared brush, would couple two parallel changes. `pressed` and `drift` live in `toon_critters` and overlap
  `brush.inked` and `brush.wobble` from that branch. Merging the two is a follow-up for whoever merges both.
- **Falling back to a traced kind on the cat** (shock for scream, half for sleepy). This silently draws something
  other than what the script asked for.
- **A goat with a horizontal-slit pupil drawn literally.** At reel size it read as a dash and made the goat look
  blind. A short, thick bar over an amber iris reads as a goat's eye.
- **The first, wider sloth and taller hamster heads.** They scored 0.19–0.21 against the cat, the frog and the
  hedgehog at thumbnail size, under the 0.22 floor. The sloth's head was narrowed above the shoulders and given a
  tuft. The hamster's head was lowered and squatted. Both now clear the floor.

## Consequences

- A sketch can cast the sloth, the goat and the hamster by name. Every brush character can yawn, scream, puff its
  cheeks and look sleepy.
- A critter draws 63 to 66 shapes in a pose (up to 79 with its own signature mouth). The fox draws 35 and the traced
  cat 26 to 29. The scene files and the draw time grow in proportion. They are still well inside what a reel
  renders.
- A script that gives the cat a new expression fails at the draw, naming it.
- When ADR 0044's inked fox merges, it routes eyes and mouths through its own `Drawing`. It then has to draw
  `sleepy`, `yawn`, `scream` and `puff` itself, or delegate them to `shared_eye` and `shared_mouth`, as a critter
  does for the kinds it does not draw.
- Published episodes are unchanged. Rebuilt from their published projects, their scene files match the baseline
  byte for byte: 76 identical, with `the-router` differing as it did before this change.
