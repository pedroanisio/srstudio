---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0041: Three more Toon characters, expressions past the traced set, and things any character wears

- Status: accepted; implemented 2026-10-30 (`toon_cast.FOX`/`RACCOON`/`HEDGEHOG`, `Look.mantle`/`Look.paw`,
  `toon.TRACED_EYES`/`TRACED_MOUTHS`, `toon.WEAR`, `Pose.wear`, `srstudio.toon_wear`, `Beat.wear`, `Cast.wear`;
  `tests/test_toon_cast_more.py`, `tests/test_toon_expressions.py`, `tests/test_toon_wear.py`)
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Extends [ADR 0014](0014-toon-brush-characters.md) and [ADR 0020](0020-toon-lip-synced-cast.md)
- Back to the [library README](../../README.md)

## Context

The next Toon reel batch covers everyday tech, money and services, job search and dating. A three-person scene
with the current cast had to reuse coats and head shapes that read alike at phone size. The faces also had no way
to show an eye roll, tears, a wince, being smitten, clenched teeth, a frown, a tongue out or a kiss.

The traced cat constrains every change to the vocabulary. `parse_art` checks cat.json's eye and mouth tables
against `toon.EYES` and `toon.MOUTHS` exactly, and nothing in the art can draw a kind it was not traced with.

## Decision

### Three characters

1. **A fox, a raccoon and a hedgehog**, each a `toon_cast.Look`.
   - **Fox:** slender. Tall ears splayed outward, white cheek tufts, dark paws.
   - **Raccoon:** stout. A bandit mask, rounded ears set in on a narrow crown, cheek ruffs, dark gloves.
   - **Hedgehog:** small, with a low head. A crest of spines that is longest over the crown, and beady eyes.
2. **Each one is told apart by its head at thumbnail size, as measured.** The test samples each head and its ears
   (down to the shoulders every body shares) on a 12 px grid. Every new head must differ from every other
   character's at least as much as the closest pair of the older cast (the cat and the frog) differ from each
   other. The floor is computed from the older cast, not chosen. The coats are more than ΔE 20 apart in CIE Lab
   from every other coat. The raccoon's torso is at least 30 px wider than the others'. The hedgehog's head is at
   least 50 px narrower.
3. **`Look` gains two optional fields:** `mantle`, an outline drawn in the dark coat behind the ears and the body
   (the spines), and `paw`, a paw colour other than the coat. Both default to empty, so the older cast draws as
   before.
4. **The three take the whole contract.**
   - Every ARMS and BODIES pose, the four visemes, blinks, and `figure_shapes` as data.
   - `CHARACTERS`, `LIP_SYNCED` and `DRAWERS` in `sketch`, so a sketch plays them by name.
   - The `toon-fox`, `toon-raccoon` and `toon-hedgehog` registry entries.

### Expressions

5. **Four eyes and four mouths join the vocabulary.**
   - **Eyes:** `roll` (pupils up and aside over a risen lower lid), `teary` (big glossy pupils and a tear at the
     outer corner), `wince` (a chevron squeezed toward the nose) and `hearts`.
   - **Mouths:** `grimace` (clenched teeth wider than the mouth), `frown`, `tongue` (a smile with the tongue out)
     and `kiss` (a pucker).
   - Brows lift at the inner end for teary and wince, and arch for hearts.
   - Wince and hearts eyes do not blink.
   - The rabbit's front teeth stay off a grimace and a kiss.
   - Every existing kind's branch is unchanged.
6. **The traced set is frozen and named.** `toon.TRACED_EYES` and `TRACED_MOUTHS` are what cat.json holds, and
   `parse_art` checks against them. `EYES` and `MOUTHS` are the traced kinds plus the new ones.
7. **The cat refuses what it was not traced with.** `toon.cat` validates every pose before it draws anything. An
   eye or mouth outside the traced set raises a `ToonDataError` that names it ("the traced cat has no 'hearts'
   eyes"). There is no fallback to a nearby traced kind.

### Wear

8. **`toon.WEAR` is glasses, a sweat drop and a flush, toggled per pose.**
   - `Pose.wear` is an optional `"wear"` list in a poses file. `parse_poses` refuses an unknown item, one listed
     twice, or a value that is not a list.
   - A sketch's `Beat.wear` is checked against `Cast.wear`. The Toon cast offers `toon.WEAR`; other casts offer
     none.
   - The scripting helpers take `wear=`.
   - Nothing worn writes nothing. A pose dict and a `beats.json` beat carry `wear` only when something is worn, so
     the files of every earlier sketch are unchanged.
   - `appearances` compares whole poses, so taking the glasses off starts a new pose.
9. **The items are drawn about a face, not a look** (`srstudio.toon_wear`).
   - A `Face` is the two eye centres, the eye radius, and the mouth's centre and width.
   - `face_of(look)` gives a brush character's face.
   - `CAT_FACE` is measured from cat.json: the centres of the "wide" eye whites and of the "flat" mouth. A test
     re-measures it from the art.
   - The cat's eyes are one drawing for every body, so its face is fixed across the poses.
   - Unlike a new expression, the items are overlays that need nothing traced, so the cat wears them honestly.
10. **Each item has its layer.**
    - The flush goes on the cheeks under the nose, whiskers and mouth. It sits low enough that a blink's lids leave
      it showing.
    - The glasses and the sweat drop go over the face: after the blink lids, so the glasses stay on through a
      blink, and before any paws raised to the face, so a paw covers them.
    - The lenses fit the normal eye ring with 18 % of an eye radius of air. A shocked eye bulges past its frame
      rather than every pair of lenses growing until the dog's touch.
    - The items always draw in `WEAR` order, whatever order a pose lists them in.

## Alternatives rejected

- **An owl.** A beak cannot take the lip visemes or the mouth vocabulary honestly. Every mouth would need a
  beak-specific drawing.
- **A raccoon tail and raccoon brows.** The tail is clutter and is hidden by the desk in most shots. Brows are
  invisible on the mask.
- **A hand-picked distinctness threshold over the whole figure.** The shared torso dilutes the difference
  between heads, and a picked number says nothing about the older cast. The head-region metric with a floor
  computed from the older cast does both.
- **Letting the cat fall back to the nearest traced kind** (wide for hearts, flat for frown). This silently draws
  something other than the script asked for, which the brief and the verification rules forbid.
- **Tracing the new kinds onto the cat.** The traced art comes from a reference reel, and a new drawing in its place
  would not be traced.
- **Wear as `Look` fields** (like `teeth`). These would be per character, not per pose, and a sketch toggles them
  per line.
- **Wear as `stickers=`.** Stickers are drawn last, over any paws raised to the face, can't put a flush under
  the nose, and the cat takes none.
- **Wear registered as standalone props.** A prop is placed in a scene. Wear moves with the pose (sigh, lean) and
  layers between face parts, like the eyes and mouths, which are not registered either.
- **More items (a hat, a tie, a phone).** A hat fights the ears and the headset. A held phone needs the arms. The
  brief asked for two or three that a sketch can toggle per line.

## Consequences

- A sketch can cast the fox, the raccoon and the hedgehog by name, use the new expressions on every brush
  character, and dress anyone per beat.
- A script that gives the cat a new expression fails at the draw, naming the expression. `sketch.check` stays
  cast-generic and does not know the cat is traced.
- `tests/test_toon_cast.py` draws every `EYES` × `MOUTHS` × `ARMS` on all seven brush looks (8,281 cases). It is
  the slowest Toon test file.
- Published episodes are unchanged: their poses carry no wear and use only the traced kinds, and every existing
  drawing branch is untouched. Rebuilt from their published projects, their scene files match the baseline byte
  for byte: 76 identical, `the-router` differing as it did before this change.
