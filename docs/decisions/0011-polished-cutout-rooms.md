---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0011: Two polished Cutout locations, the conference room and the reception

- Status: accepted and implemented, 2026-10-28 (`locations.conference_room`, `locations.reception`,
  `locations.CONFERENCE_SEAT`, `RECEPTION_CLERK`, `RECEPTION_VISITOR`, props `whiteboard`, `blinds-window`,
  `speakerphone`, `globe-pendant`, `slat-wall`, `reception-counter`, `tests/test_cutout_rooms.py`)
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Back to the [library README](../../README.md)

## Context

Cutout ([ADR 0002](0002-style-names.md)) had four locations: the office (wide, desk and reverse), the café and the
park. All are frontal sets of flat shapes, with a few gradients and bold ink outlines. The operator asked for two more,
more polished than those. Here, polish means four things:

- light with a source: a window, a ceiling panel, a lamp or an LED strip;
- materials that read as materials: walnut, stone, opal glass, laminate and mesh;
- shadows under objects;
- small, specific dressing that rewards a second look.

## Decision

1. **Two locations for the interview series.**
   - `conference-room`:
     - a window with venetian blinds lowered two thirds, and a city skyline behind them;
     - shafts of window light across the wall and the table;
     - a linear ceiling light;
     - a whiteboard with a marker chart (`rising=False` turns the trend down and red), sticky notes, a gloss and a
       marker tray;
     - a high-back mesh chair;
     - a walnut table with legs and a cast shadow;
     - a speakerphone with a live ring, notes and a pen, and a steaming mug.
   - `reception`:
     - a walnut slat wall washed by an LED strip, with a backlit logo;
     - two opal globe pendants with halos;
     - a plant in a ceramic planter;
     - a stone-topped, fluted counter lit along its kick, with a monitor and a vase of flowers on it;
     - a polished floor that reflects the counter and the pendants.
2. **Slots in the existing pattern, with the placements published and tested.**
   - The conference room has three slots: `behind_table` (between the chair and the table), `on_table` and
     `on_wall` (over the wall, behind the light and the chair). `rising=None` leaves the wall without its whiteboard,
     so an episode can hang its own at `CONFERENCE_BOARD` and animate it (episode 09 flips it).
   - The reception has three: `behind_desk` (between the wall and the counter), `on_desk` and `at_desk` (in front of
     the counter).
   - The constants `CONFERENCE_SEAT`, `RECEPTION_CLERK` and `RECEPTION_VISITOR` give the `x, y, scale` that
     `Episode.perform` takes.
   - Tests check that a seated office actor's whole head shows above the table or counter, and that the cut end of its
     body is hidden. They also check that a standing café actor's feet land on the reception floor inside the frame.
3. **Light is a glaze group.** Each room draws a `{id}-light` group of translucent shapes, every one at an opacity
   between 0 and 0.5, which a test asserts. The props that cast light (`globe-pendant`, `slat-wall`) take an optional
   `light=` group for their halo or wash. So the glaze stays behind the cast, and the props stay usable on their own.
4. **Ids are scoped to the location id.** Ids follow the pattern `{id}-chair`, `{id}-table`, `{id}-counter`, and so on.
   Two instances of a room can then share one document.
5. **Signed.** The cactus sits on the table and on the counter. The code is on the notes in the conference room and at
   the foot of the counter in the reception ([ADR 0001](0001-signature.md)). An unsigned canvas draws neither, and a
   test checks this.

Nothing existing changed. The new code is appended to `locations.py` and `props.py`, and the five episode scene
documents rebuild byte-identical.

## Rejected alternatives

- **An elevator.** It would suit the series, but the office actors end at the waist. A standing shot needs furniture
  in front of them, which a counter or table gives and an elevator does not.
- **Light as blend modes or radial gradients.** A glaze of flat translucent shapes keeps the Cutout look: paper
  overlays, exact under seeking, and nothing that depends on the engine's compositing.
- **New props in a module of their own.** A part's style comes from its module, and Cutout's parts are `locations` and
  `props`. Appending there registers the new parts as Cutout parts without a `style=` override.

## Consequences

- The interview series can open on a meeting or a front desk without new drawing code.
- `props.glow` and `props.GLOW` give later Cutout sets the same halo and light colour.
