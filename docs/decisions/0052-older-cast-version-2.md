---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0052: The older brush cast drawn again, as version 2

- Status: accepted (2026-10-30). The operator approved all six from the proof clips
  (`generated/character-proofs/older-cast/index.html`): "all the old-cast approved on v2". Implemented:
  `srstudio.toon_redrawn` (`DOG`, `FROG`, `BEAR`, `RABBIT`, `RACCOON`, `HEDGEHOG`, `REDRAWN`), `Critter._lid`, the six
  `toon-*@2` records and specimens; `tests/test_toon_redrawn.py`.
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Extends [ADR 0045](0045-toon-sloth-goat-hamster.md), [ADR 0047](0047-character-versions.md) and
  [ADR 0049](0049-toon-torso-one-smooth-body.md)
- Back to the [library README](../../README.md)

## Context

The operator asked for the older brush cast to get the sloth's, goat's and hamster's smooth shoulders and polish. The
dog, the frog, the bear, the rabbit, the raccoon and the hedgehog are drawn from a `Look`'s fields, symmetric and
evenly lined, with arms that rise from the shoulders. Every published Toon reel draws them, and published reels must
stay byte-identical.

## Decision

1. **Six new drawings, one module.** `srstudio.toon_redrawn` draws each as a `toon_critters.Critter`: a hand-placed,
   unmirrored head; one `Torso` from the neck to the flank with the arms inside it; pressed ink; a shade tone; open
   inner strokes; a head tilted about the neck; and its own pupils and paws. The fox is not here: it has version 2
   ([ADR 0044](0044-inked-toon-characters.md)).
2. **Each stays itself.** Coat, dark and light colours, eye radius, mouth width, lid colour, brows and teeth are read
   from version 1, and a test holds them, with the eyes and the mouth where they were. The features each is known by
   stay: floppy ears, eyes on domes and a wide mouth, round ears, tall ears and front teeth, mask, tufts and gloves,
   spines.
3. **What each gains.** Three things are new, not only redrawn, so the operator sees them called out:
   - the dog's ears hang in front of its head, not behind it;
   - the dog and the frog blink, which they never did, and gain a highlight on the pupil;
   - the rabbit's right ear leans out, and its whiskers are tapered strokes drawn with the head.
4. **Version 2, proposed first.** Each was registered as `name@2` with a recorded digest and `status: proposed`, no
   default and no pin (ADR 0047), until the operator judged it. `toon_cast.LOOKS` keeps version 1, which published
   reels pin. A test holds the recorded digest to what the drawing draws, so a redraw cannot leave a stale one.
5. **The frog's lids follow its eyes.** Its eyes stand proud of its head, and a box of a lid sticks out over the
   domes. `Critter._lid` is the one place a lid's shape is decided: the critters keep the plain outline, and the
   frog's `_Domed` clamps the lid to the round of the eye, sleepy eyes included.

## Alternatives rejected

- **Polish fields on `Look`.** ADR 0044 rejected them for the same reason: a field can place a shared template but
  cannot redraw it.
- **Changing the six in `toon_cast`.** Every published reel draws from it.
- **Replacing the frog's eyes with a subclass of its own eye drawing.** `Critter._open_eye` already draws every kind;
  only the lid's outline differs, so only that is a hook.
- **Sharing one rig of parts across the six.** Each head, ear and belly is placed by hand. Generating them from
  version 1's symmetric outlines would keep what the operator wants gone.

## Consequences

- A drawn look costs more shapes than its version 1. In `wide`/`flat` over the seven arms the six draw 39 to 70 shapes
  a pose, where version 1 draws 23 to 45.
- Every new `EYES` or `MOUTHS` kind reaches the six through the shared drawings in `Critter`, as it reaches the
  critters.
- `Critter` has one more hook, and the three approved critters draw byte-identically (their tests hold the digests).
- The six have no `HeadRig`, so head motion (ADR 0050) stays opt-in and is refused by name for them until each gets one.
- Each is now that character's default for new reels. Published reels pin version 1 in their releases and keep it.
