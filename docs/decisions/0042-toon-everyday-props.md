# ADR 0042: Toon everyday props

- Status: accepted and implemented, 2026-10-30 (`srstudio.toon_everyday`: `phone`, `speaker`, `receipt`,
  `take_a_number`, `clipboard`; `tests/test_toon_everyday.py`, `tests/support/toon_bounds.py`)
- Deciders: the operator, through the orchestrator worskpace-e5 (the batch's premises and the starting set);
  implementation drafted by Claude Opus 5.5 in Claude Code
- Back to the [library README](../../README.md)

## Context

The next reel batch leans on Toon, the style of two of the five best-performing reels (*Logo Bigger*, *Split It*).
Its premises are broad adult situations, weighted as follows:

| Premise | Reels |
|---|---|
| Everyday tech | 10 |
| Money and services | 4 |
| Job search | 4 |
| Dating | 2 |

The style's props cover the office and the dinner. There is the mug, the clock, the sticky notes, the whiteboard, the
logo, the call badge and the toasts in `toon_props`, the kitchen and home props in `toon_sets`, and the dishes and
the card reader in `toon_dinner`. Nothing in the style is a screen the audience reads, a device that answers back, a
bill that keeps growing, a queue or a form.

Two rules already bind every prop, and nothing enforced them for Toon. Props stay clear of the signature marks (the
skill asks each style for a test like Collage's `signature_box`). Lettering must read on a phone and never be cut
by the frame. The existing Toon props bound their text by character counts (`card_reader`'s `SCREEN_MAX`,
`toasts`' 24 characters), which says nothing about how wide the text is in the style's font.

## Decision

A new module, `srstudio.toon_everyday`, holds five props chosen for the weighting:

| Prop | Premises | What changes on cue |
|---|---|---|
| `phone` | tech, money, dating | typed `Screen`s: `notify` (buzzes the phone), `code` (2FA or password prompt), `profile` (a dating card with pass and like), `declined` (the customer's side of a refused payment), `loading` (a bar that fills to `fill`, stuck at 99% if asked), `off` |
| `speaker` | tech | a light ring and halo: `off`, `listen`, `think` (one light chasing round), `speak` (pulsing), `error` (red) |
| `receipt` | money, services | the strip unrolls from a printer slot at a pace per row; each row shows as the paper passes it |
| `take_a_number` | services | the NOW SERVING number; the ticket in the dispenser is the customer's |
| `clipboard` | job search, services | a form's values are written in at their seconds; a REJECTED or HIRED stamp lands with a pop |

Every one of them keeps the same rules, enforced when it is drawn, not only in tests:

1. **Placed by data.** A prop stands at a reference point `at` (the style's screen pixels), is drawn `scale` times
   about it, and takes plain values (tuples, or the frozen `Screen` and `Field` dataclasses) that an episode's
   `*_data.py` can hold, as `split_it_data.py` holds the card reader's screens. Each returns its footprint, the
   reference box it may draw in over its whole life, including the phone's buzz and the stamp's pop.
2. **Refused where it does not belong.** A footprint that leaves the frame, enters the caption band, or touches
   `SIGNATURE_BOX` raises `ToonDataError`. `SIGNATURE_BOX` is the reference box around the cactus and the code
   that `toon.desk` and `toon_dinner.table` draw. A test measures both marks on both fronts against it, so a moved
   mark fails the build instead of letting a prop cover it.
3. **Text measured.** Every text is fitted to its box with the sketch's `measure` (`Shot.measure`, the advance
   widths of the style's font): one line or as many as the box holds, each line no wider than the box. A receipt
   row fits its name and price side by side. A form's value fits the room its measured label leaves. Sizes are 24 px
   or more, and `scale` is at least 0.9, so the smallest lettering stays at or over the engine's legibility floor
   (`ink_meter.LEGIBLE_PX`, 21.6 px). The speaker carries no lettering, so its floor is 0.5 (`SPEAKER_SCALES`), small
   enough to stand on a shelf.
4. **States from 0, rising.** States are `(second, …)` from 0 in strictly rising seconds, on the composition
   clock, one shown at a time. Looping motion (the speaker's chase and pulse) is keyed step by step up to the
   shot's end, which is bounded (`MAX_END`), so the number of keys is bounded too.

`tests/support/toon_bounds.drawn` reads a drawn group back from the scene document through its transforms, and can
set an animated value first, such as the stamp at the height of its pop. The tests use it to prove that each
footprint holds everything its prop draws.

## Rejected alternatives

| Candidate | Why not |
|---|---|
| Add the five to `toon_props` | That module is the office set. Five props with their own data types would double it, and the batch's other workers are editing the neighbouring Toon modules. |
| Bound text by character count, as `card_reader` does | Character counts let wide text through and refuse narrow text; the font's widths are what the frame shows. |
| Keep props clear of the marks with a test only, as Collage does | A test covers the placements the tests make; refusing at placement covers every sketch's own data. |
| Let a long receipt run off the bottom of the frame | Lettering cut by the frame reads as a rendering slip (the skill's rule); the footprint refuses it instead. |
| A separate dating-app card prop | The dating card is a phone screen. A second device would duplicate the phone's placement and buzz. |
| A laptop screen facing the camera | The Toon desk shows the laptop from behind; the phone carries the screens instead. |
| A second card reader for the payment gag | `toon_dinner.card_reader` is the merchant's side. The phone's `declined` screen is the customer's, and it does not duplicate the reader. |
| A free-form screen (any text in any box) | It could not be measured or tested per layout. Typed kinds with named fields refuse a field a kind does not draw. |
| A NOW SERVING display separate from the dispenser | One unit is the familiar deli fixture, and one footprint keeps the pair together on screen. |

## Consequences

- No episode uses the props yet, so the catalog's coverage check, which asks for parts that rendered episodes use,
  needs no gallery item for them. The first episode that draws one adds its notes entry.
- The module draws nothing in any existing episode: every published episode rebuilds byte-identical.
- The marks' box is pinned by measurement: moving the cactus or the code on the desk or the table fails
  `test_the_signature_box_holds_both_marks_on_the_desk_and_on_the_table` until `SIGNATURE_BOX` follows.
- The lit rooms of ADR 0043 (`toon_rooms`, built alongside on `feat/toon-rooms`) draw their own smart speaker on
  the lounge shelf and a TAKE A NUMBER sign and NOW SERVING board on the service counter, fixed in the set. The
  placeable speaker is `speaker`, so the rooms call it once both are merged rather than draw a second
  version of the speaker. At 0.5 this speaker is as wide as the shelf's (34 px), and the lounge gets its states. The
  counter's wall board stays part of that set: the room's light cues colour it, and a wall board is a different object
  from the portable dispenser on a pole.
- A sketch maps its own events to states (`reader:` events become card-reader screens in *Split It*). The props
  take plain states and know nothing of a sketch's beats.
