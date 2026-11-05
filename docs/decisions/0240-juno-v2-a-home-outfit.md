---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0240: Juno version 2 wears a home outfit, drawn by the rig as part of her look

- Status: proposed (2026-11-05). `juno@2` is recorded `proposed` with no approval. arc4d3 approves it, or not, from
  one full-size still of her standing and one seated (`generated/okayville/jp-review/juno-v2/`). Until then
  `parts.get("juno").latest()` stays version 1.
- Deciders: arc4d3 (ruling L27, Slack 1793854854.581609); drafted by Claude Opus 5.5 in Claude Code
- Extends [ADR 0007](0007-polished-looks.md) (a `Look` makes the rig a character) and
  [ADR 0047](0047-character-versions.md) (versions, pins, digests)
- Back to the [library README](../../README.md)

## Context

arc4d3 held the release of Juno & Pip episodes 1–3 with L27 (Slack 1793854854.581609): *"Juno reads as naked."*
`blob.JUNO` paints her body and head in one fill (`JUNO_FILL`, `#FAD5BE`), so in every kitchen shot her body is the
same peach as her face, with no clothing line. Seated (ep1, "Bit less salt.") she reads unclothed. Only ep2's coat and
scarf dress her, and that coat is drawn by ep2 alone (`_jp_ready_in_five.coat`). arc4d3 asked for a top and trousers in
a palette colour clearly apart from her skin, with a collar and cuff line, the head, hair and face exactly as they
are, on every shot of ep1–12.

Published reels draw Juno version 1 and are frozen (ADR 0047), so the fix is a new version, not an edit.

## Decision

1. **The outfit is part of the look.** `blob.Outfit(top, trousers, trim, hand, foot, cuff)` is a new optional
   `Look.outfit`. `blob.blob()` draws it in the same pass as the body, from the same strokes, so it follows every pose
   and in-between with no work in an episode:
   - the torso in `top`; each arm sleeved in `top` and each leg in `trousers`, cut square where the cloth stops
     (`blob.cut`), so a sleeve never laps over the hand;
   - a sleeve stops `hand` (26) pose units short of the arm's tip, measured along the arm, and a trouser leg `foot`
     (22) short of the leg's; every hand and foot is the same size in every pose. An in-between that folds a limb
     shorter than two of those keeps half of it clothed;
   - a `cuff` (12 units) band in `trim` at each wrist and ankle, with an ink line where it meets the skin and a finer
     seam on the cloth's side;
   - a `trim` collar under the chin (`blob.collar`): a band 14 units round the head's rim, centred on the line to the
     body and kept 6 units inside the torso, so the silhouette never changes and a coat drawn over the body covers it;
   - limbs in front dress in the front pass too, under their own ink trace;
   - dressed, the arms are drawn first in the merged fill and the torso over them, so an arm held behind the body
     stays behind the top. With one fill nobody could see the difference; with a top, a hand would float on it.
2. **Her home outfit is a teal top and mustard trousers with a cream collar and cuffs** (`JUNO_HOME`: `#3F8F8A`,
   `#D29B2A`, `#F6EAD3`). The kitchen already uses both accents, and the brief offered them. Teal is the
   complement of her coral scrunchie and stands clear of the pale green kitchen wall. Mustard is warm against the cool
   top, so the two read as two garments, and dark enough to hold against the pale floor. Cream makes the collar
   the clearest line on her.
3. **Cloth cannot read as skin.** `Look` refuses an outfit whose top or trousers come within `MIN_CLOTH_DISTANCE`
   of its fill. The limit is 40, measured as CIE76 ΔE\*ab (the straight distance in CIE L\*a\*b\*, sRGB D65;
   `blob.delta_e`). A just-noticeable difference is about 2.3. Measured: the top is 52.6 from the fill and 54.8
   from the head's shade; the trousers 50.6 and 42.5; top to trousers 77.5. The trim is 11.2 from the fill. It is a
   collar and cuffs and is never a garment, so it carries no limit, and the ink line separates it from the skin.
4. **Juno version 2 is version 1 in that outfit.** `JUNO_V2 = replace(JUNO, outfit=JUNO_HOME)`: every other field is
   version 1's, which a test holds. `blob.juno_v2` is registered as `juno@2` with a `_blob` specimen and a recorded
   digest, `status: proposed`. `blob.juno` and `JUNO` are untouched. Version 1, Pip, Bo and Remy draw byte-for-byte
   as they did on develop a455e253, and a test holds the scene sha256 of each over every pose.
5. **A reel calls version 2 by name.** Soft builds read no pin (`parts.ROUTED` is Toon's characters only), so
   `parts.CALLED_VERSIONS = ("juno",)` lets `juno` take a second version. A new reel calls `blob.juno_v2`, and the
   build's record says `juno: 2` through the registered name. The rule matches `KIT_VERSIONS` for the news kit.
   Other Soft characters are still refused a second version by name.

## Alternatives rejected

- **Another body fill (`fill` = a top colour).** It gives no clothing line, no collar and no cuffs, and it colours the
  hands and feet, so she would read as a teal person.
- **A second fill for the body, apart from the head.** It has the same problems: hands and feet take the cloth's
  colour, and there is no collar or cuff.
- **Clothes worn per episode, as ep2's `coat()` is drawn.** Every episode would have to remember them, twelve times
  over, with front and back passes rebuilt outside the rig. arc4d3 asked for her on every shot of ep1–12, and only
  the look holds that.
- **Editing `JUNO` in place.** Published reels draw version 1 and are frozen (ADR 0047), and the digest test refuses
  it on purpose.
- **Routing every Soft character through pins (`ROUTED`).** Soft builds do not read a pin. Routing them would let a
  second version of Pip draw for every published reel.
- **Sleeves and trousers to a fixed fraction of the limb** (ep2's coat uses 0.78). Measured on the pose sheet, the
  hooked arms (`hug`, `clasp`, `lean`) bunch their length near the hand. At 0.78, the `hug` arm kept 5.7 units of
  arm past the sleeve, a nub where a hand should be. Arc length keeps every hand the same.
- **The collar as part of the silhouette** (a crescent drawn in the outline pass). It changes her outline at the
  shoulders and shows from under ep2's coat.
- **Round-capped garment ends** (`Stroke.outline`). Drawn first, they bulged a cream disc over every hand and foot.

## Consequences

- A look without an outfit draws exactly as before. A look with one costs more shapes a drawing: five cloth paths,
  four cuffs with two lines each, and the collar's band and line, all hold-keyed on every drawing.
- Dressed, a back arm crossing the body is hidden behind the top. Seated `lounge` shows one hand on the thigh, where
  version 1 showed one hand and a second, invisible on the same peach.
- ep2's coat (`_jp_ready_in_five.coat`) covers the top, collar and sleeves. Measured on rendered frames, standing and
  on the sofa, 0 px of the top's colour show. Below the coat's hem the trousers show, as trousers under a coat do:
  standing, the ankle cuffs (756 px of trim) and two wedges of trouser 5 px tall (30 px). Seated, the coat does not
  cover the legs, and the trousers show.
- Episodes move to version 2 when arc4d3 approves it: each calls `blob.juno_v2` where it called `blob.juno`, passes
  `look=blob.JUNO_V2` where it passed `blob.JUNO`, and pins `juno: 2`.
