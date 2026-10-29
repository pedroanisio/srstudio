---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0022: Two finer Toon sets and four props that carry light and small motion

- Status: accepted and implemented, 2026-10-28 (`srstudio.toon_sets`: `toon-kitchen`, `toon-home`,
  `toon-coffee-machine`, `toon-desk-lamp`, `toon-plant`, `toon-calendar`, `cycle_keys`, `parse_pages`; the module
  added to `TOON.parts`; `tests/test_toon_sets.py`)
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Back to the [library README](../../README.md); follows [ADR 0015](0015-toon-sketches.md) and
  [ADR 0020](0020-toon-lip-synced-cast.md)

## Context

The operator asked for two more Toon locations and props, more polished than the first ones. Every Toon sketch so
far plays in the same room or in the meeting room, so a new premise has nowhere new to happen. The first sets are
flat: rectangles with an even ink line, no light, nothing moving unless a prop is asked to.

## Decision

- **A new module, `toon_sets`, in the Toon style.** It is listed in `TOON.parts`, as the other Toon modules are, so
  its parts register with the style without a per-part `style=`.
- **Ink by the brush.** Each object's outline is a `brush.rim` round its points, with the fill inside it, so lines
  swell and taper as on the characters. Architecture (cabinets, the fridge, the window) keeps straight rectangles
  with the room's ink weights, because a brushed cabinet reads as wobbly.
- **Light as layers.** A white highlight at low opacity goes on glass, steel, glaze and book spines. A soft shadow
  (`SHADOW` at 0.1 to 0.25 opacity) goes under each object. Glows are radial gradients that fade to a fully
  transparent stop (moon, bulbs, LED, lamp). Repeating details are drawn as one multi-subpath path, not hundreds of
  nodes: the tile grout and the tile glints.
- **Small motion, bounded by the caller.** Looping motion (stars, bulbs, lit windows, leaves, steam) is keyed by
  `cycle_keys` from 0 to an `end` the caller gives. With `end` at 0 there is no key at all, so a still is unchanged.
  Event motion (brewing, a lamp's light, a calendar page) takes spans or timed pages, validated like the first
  props' (`ToonDataError` on bad order, overlap, values out of range, or a page that does not read like `OCT 28`).
- **The signature stays on the desk.** `toon.desk` draws both marks (ADR 0001) because it is in front of every
  Toon shot. The new sets draw neither mark, or a shot would carry two cactuses. The lamp's and the plant's default
  places are chosen, and tested, to stand clear of the desk's cactus.
- **The sets keep the room's skeleton.** The window frame, the character corner (x 30–340, y ≥ 360), the caption
  band and the desk line are where `toon-room` has them. Any sketch built on `_toon_sketch` can swap the backdrop
  without moving its characters or captions. The home skyline sits above the laptop lid so the lid does not hide it.

## Rejected alternatives

- **Adding the sets to `toon.py` or `toon_props.py`.** Both already hold one round of parts each. A third module
  keeps each file to one round and lets this round's tests stand alone.
- **Engine effects (blur, glow filters) for the light.** `Canvas.effect` is being changed by another session, and
  gradients with alpha stops give the same soft edge with no new engine feature.
- **Signature marks in each new set.** Rejected once the marks moved to the desk, as above. A backdrop used without
  the desk is still caught by the `Episode.finish` signature gate.
- **Animating by default.** A set that always moves would change every still and every existing manifest that
  draws it. Motion is opt-in through `end`.

## Consequences

- Two backdrops and four props are registered with `episodes=()`. The catalog lists them, but no episode uses them
  yet, so they have no gallery item.
- `cycle_keys` is a public helper for any looping key in the style.
