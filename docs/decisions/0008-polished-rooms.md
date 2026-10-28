---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0008: A shared room shell, and two polished Soft locations

- Status: accepted and implemented, 2026-10-28 (`blob.meeting_room`, `blob.break_room`, `blob.room_point`,
  `blob.WALL_DECOR`, `blob.FRIDGE_BOX`, props `soft-swivel-chair`, `soft-stool`, `soft-coffee-machine`, `soft-fridge`,
  `tests/test_soft.py`)
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Back to the [library README](../../README.md)

## Context

The Soft style had two locations, `soft-office` and `soft-home` ([ADR 0003](0003-soft-style.md),
[ADR 0005](0005-audio-call-and-looks.md)). Both are drawn in the 3/4 view from above, with flat fills. The operator
asked for two more, more polished than the first two. Here polish means three things: walls and a floor with depth,
light that falls on things, and props with sheen and a shadow under them. The new characters Juno and Remy
([ADR 0007](0007-polished-looks.md)) need a place to be.

## Decision

1. **One room shell shared by both rooms.**
   - `room_point(a, c, up)` maps room coordinates to pixels in the rig's 3/4 axes. `a` runs along the back wall,
     `c` comes out from it and `up` rises.
   - `wall_quad`, `floor_quad` and `_block` (a box with a top face, a near face and an end face) build everything else.
   - `_shell` draws the back and side walls, a plank or tiled floor, an ambient-occlusion band where floor meets wall,
     and the baseboards.
   - Each room has its own `RoomPalette`.
2. **Light is a glaze group.** Each room draws a `{id}-light` group after its floor. It holds translucent patches
   where a window's light lands, with opacity between 0 and 0.5, and a test asserts that range. In the break room,
   the pendant lamp's cone is a gradient that fades toward the floor, and it is drawn over the counter it lights.
3. **`soft-meeting-room`.**
   - A walnut table at desk height (`TABLE_TOP`). The laptop's keyboard lies on it.
   - A swivel office chair (`soft-swivel-chair`) whose seat holds the rig's `SEAT`. So every seated pose works there
     unchanged, and both facts are tested.
   - A wall screen showing a gradient slide with bars and page dots, a gloss and a webcam.
   - A wall clock, and a side window whose light falls on the floor.
   - A notepad, a water glass and the signature cactus on the table.
4. **`soft-break-room`.**
   - Mint wall cabinets over a stone counter with a tiled backsplash.
   - A window with a herb pot and the signature cactus on its sill.
   - A coffee machine (`soft-coffee-machine`) with a carafe and a steaming mug.
   - A pastel fridge (`soft-fridge`) with magnets and a sticky note.
   - A pendant lamp.
   - A stool (`soft-stool`) whose seat holds `SEAT` and whose base meets `SEATED_FLOOR`. A seated pose therefore works
     on it too.
   - `BREAK_STAND` places a standing character.
5. **The captions own the top of the frame.** Soft captions sit in y 250–430.
   - Tests require that every piece of wall decor (`WALL_DECOR`) and the fridge's top (`FRIDGE_BOX`) lie at or below
     `CAPTION_FLOOR`, inside the frame, and, for the decor, on its own wall.
   - The pendant's cord is the one thing that crosses the caption band, because it hangs from above the frame.
6. **Signed.** Each room carries `sig-cactus` and `sig-code`, as [ADR 0001](0001-signature.md) requires, and is gated
   by `shots=`.

Nothing existing changed. The five episode scene documents were rebuilt and are byte-identical to the build from
before ADR 0007.

## Rejected alternatives

- **Draw each room freehand in pixels, like `soft-office`.** Two rooms full of furniture would repeat the projection
  arithmetic in every prop. A single `room_point` keeps every face on the same axes, and lets the tests reason in room
  coordinates.
- **Light with blend modes.** A multiply or screen layer would depend on engine compositing for a flat style. A glaze
  at low opacity gives the same read and stays exact under seeking.
- **A tall fridge reaching the ceiling.** Its top would sit in the caption band. It is 620 units tall instead, which
  the test pins.

## Consequences

- A new Soft room is a palette, a `_shell` call and props built from `_block`, all on axes the rig already sits on.
- Seated poses work on the office chair, the sofa, the swivel chair and the stool alike, because each seat is built
  around `SEAT`.
