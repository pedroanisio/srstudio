# ADR 0039: The signature cactus may perform

- Status: accepted and implemented, 2026-10-29 (`signature.Act`, `signature.cactus(act=)`,
  `signature.home_cactus`, the `cactus=` slot of `locations.office_wide`, `office_desk`, `office_reverse`, `cafe` and
  `park`; `tests/test_signature.py`; first episode: *The Cactus*). Amends [ADR 0001](0001-signature.md).
- Deciders: the operator, by requesting The Cactus (2026-10-29); proposal by worskpace-74, approved by the
  orchestrator
- Back to the [library README](../../README.md)

## Context

ADR 0001 signs every episode with two marks drawn by the location builders, a code (`SR-1028`) and a potted cactus,
and keeps both out of the story: "they never carry a plot beat". *The Cactus* (backlog script 3) is built on the
opposite: the cast finally notices the cactus, it follows them from the office to the café to the park, ends up in
the executive chair, and the push-in on its pot reads the code as its employee number.

Two things stood in the way:

1. The cactus has no performance: one static drawing, its flower a fixed ellipse, no code on the pot.
2. Every location draws its own cactus at a fixed spot and depth. A second, performing cactus added by the episode
   would put two cacti in the café, park and executive-chair shots, and a resting one on the reverse angle would
   contradict "it follows them".

## Decision

The location's own mark becomes the performer; nothing is added beside it.

1. **`signature.Act`**, a frozen, checked value on the episode's clock: `end` (the episode's length), `turn`
   (`(seconds, degrees)` keys of the flower, times rising strictly inside `[0, end)`), `bloom` (when the bud opens
   with a pop, inside the same span, or none) and `code` (the signature code on the pot, default on). Any other
   value raises `SignatureError`.
2. **`signature.cactus(..., act=)`** draws the flower on its own pivot (`flower-of-<id>`), the bud gated until the
   bloom and five petals popping open on it, and the code on the pot with `signature.code`. The code is drawn
   inline, never as an instance, so a camera can push in on it: engines 0.8.0 and 0.9.0 soften a magnified
   instance. An acting cactus on an unsigned canvas raises: unsigned, the mark draws nothing, and the performer
   would silently leave the story.
3. **`signature.home_cactus(cv, parent, x, y, scale, slot=)`** is the location's cactus call. Without a slot it is
   `signature.cactus` at the location's spot. With one, the slot draws in its place, at the same depth, and on a
   signed canvas it must draw exactly one cactus; none or two raise `SignatureError`. Every shot still carries
   exactly one `sig-cactus`, and the build refuses anything else.
4. **`cactus=`** on `office_wide`, `office_desk`, `office_reverse`, `cafe` and `park` passes the slot through.
   The office angles refuse it with `instanced=True`: an instanced desk is one drawing shared by every angle.

The rule of ADR 0001 stays the default: a mark carries a plot beat only through `act=` or a `cactus=` slot, both
opt-in per episode. With neither, every drawing keeps its bytes: `tests/test_signature.py` pins the sha256 of each
changed location and of the cactus in two palettes as they were before this decision, and every published episode
rebuilds identically.

## Rejected alternatives

| Candidate | Why not |
|---|---|
| A separate performing-cactus prop beside the location's mark | Two cacti in a shot; the story says there is one |
| A flag that stops the next location from drawing its cactus | Hidden state between calls; a forgotten flag drops or doubles the mark with no error |
| Per-location placement presets (`"counter"`, `"bench"`, `"chair"`) | Each set would grow a menu of spots; the chair spins inside the episode's own group, which no preset can reach |
| The push-in on an instanced office | The engine samples the instance's texture and softens it when magnified |

## Consequences

- A slot may draw into any group of the location made before the cactus call (the executive chair's spinner, made
  by `office_desk`'s `behind_desk`), so the performer moves with what it sits in.
- An office shot in *The Cactus* carries two `sig-code` groups, the papers' and the pot's; ids stay unique
  (`sig-code-2`...) and `signature.missing` is unaffected.
- A new location that wants a performing cactus calls `signature.home_cactus` with a `cactus=` slot of its own
  instead of `signature.cactus`.
