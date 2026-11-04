---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0231: Two friends inked the News way

- Status: proposed (2026-11-04). The drawings it adds, `friends-leo` and `friends-sam`, are proposed, and the proof is
  at `generated/character-proofs/between-friends/index.html`
- Deciders: the operator; ordered by arc4d3; written by Claude Opus 5.5 in Claude Code
- Follows [ADR 0047](0047-character-versions.md), [ADR 0060](0060-news-kit.md),
  [ADR 0071](0071-news-anchor-head-rigs.md), [ADR 0142](0142-news-hands-are-a-pair.md) and
  [ADR 0230](0230-a-controller-held-in-both-paws.md)
- Back to the [library README](../../README.md)

## Context

The first Between Friends proof drew Leo and Sam as a koala and an otter in the Toon style (ADR 0230). The review of
that proof found the faces could not carry the film: Leo's range was narrow, Sam's face was the same in every frame,
the mouths were thin lines, the light was a tint over the whole frame, the couch back hid the arms, and animal heads
put a distance between the audience and the two friends. The order that followed was to draw them again as two men
of about twenty in the News inked drawing, holding generic controllers in both hands, with a generic phone in one hand
for one beat.

The story asks for faces the News anchors' vocabulary does not have: a hurt beat with the brows raised in the middle,
an embarrassed half-smile with the eyes away, a horrified gape, a dry side-eye and a deadpan. It also asks for a light
that comes from the TV onto the faces and changes with the game, while the room stays dark.

## Decision

`srstudio.inked_friends` draws `friends-leo` (a soft-edged friend in a hoodie) and `friends-sam` (the relaxed one in an
open denim shirt) with the News inked primitives (`news_inked`, `news_kit`, `news_arms`).

- A face is a typed `Look`: lid, under-lid, gaze, brow height, and the inner and outer ends of each brow, plus how
  wide the eyes open and whether the look blinks. `Look` refuses values outside the ranges a face can hold. The inner
  brow end is what tells hurt (raised in the middle) from anger (pulled down), so hurt is drawn as inner up, never
  down.
- `MOUTHS` are thirteen drawn mouths, wide enough to read at phone size: `rest`, `flat`, `set`, `sheepish`,
  `pressed`, `gape`, `smile`, `smirk` and `concern`, and the four `VISEMES` a talking track names.
- A timeline is a list of typed `Beat`s: a look, a mouth, a hold, and a head tilt, turn and lift inside fixed bounds.
  `Moves` adds nods, shrugs, swallows and a flush at given times. Each is refused when it overlaps another of its kind
  or leaves the film.
- The faces stay alive between beats: a breath, a slow head drift and blinks at a fixed rhythm run under every beat,
  and a look that should not blink (Leo's set jaw, his horror, Sam's deadpan) holds its eyes open. The rhythm is
  owned by the module, not the timeline.
- The hands are a pair. `GRIP` is one drawing for the frame's left arm, reflected for the right, so both thumbs point
  in over the controller (ADR 0142). `HOLDS` place the controller and each thumb: `pad` (sticks), `pad-press` (a
  button), `pad-pause` (the menu button), `pad-lap`, `pad-up`, and `phone`, which is Leo's alone.
- The controller and the phone are generic: rounded greys, no brand's shape, button or colour.
- `screen_light` lights only the people, through the `people` matte: a multiply layer for the game colours, a red
  wash, the cool pause and the dark room, and a screen-blend glow at the faces. The room behind them takes its own
  light, so the screen does not tint the wall.
- Both drawings are version 1, proposed, in the Toon style's parts. No reel can draw them until the operator decides.

## Alternatives rejected

- Keeping the Toon critters with new faces: the review's objection was to animal heads, not only to their range.
  `toon_gamepad` and the critters stay as a proposed Toon mechanism (ADR 0230).
- Drawing Leo and Sam through the News anchors' `perform` API with new anchors: its expression vocabulary has no
  raised inner brow, no averted gaze and no gape, and adding them there would change every approved anchor's digest.
- One tint over the whole frame from `toon_rooms.front_screen`: it colours the wall as much as the faces, which is the
  fault the review named.

## Consequences

- The proof's room and its light cues live in the proof scene, not in the library. A reel that uses these two needs
  its own set or a proposed location.
- Leo's `set` look (narrowed eyes, the jaw marked) is the closest to his neutral of all his looks. It reads on the
  contact sheet at full size; a smaller frame will lean on the held beat and the caption.
