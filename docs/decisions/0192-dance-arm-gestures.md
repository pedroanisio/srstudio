---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0192: Dance arm gestures are preset moves proved on the skeleton's forward kinematics

- Status: proposed (2026-11-02)
- Back to the [library README](../../README.md)

## Context

The presets of [ADR 0186](0186-dance-moves-on-the-beat.md) bob, sway and nod, and two of them raise an arm. A song's
louder parts want the gestures people make on a dance floor: a clap, a disco point, raising the roof, a two-handed wave,
a shoulder roll, hips swaying with the hands following, and both hands held high. A gesture is a claim about where the
hands go, and ADR 0186 left that unchecked: hand positions sit at the end of a bone chain, so only the shared
skeleton's forward kinematics ([ADR 0185](0185-shared-skeleton.md)) can read them.

The skeleton's limits apply to the rest pose plus the dance's delta, and the presets rest their arms differently
(`upper_arm.down_up` -1.40 realistic, -1.20 cartoon, -1.30 stick), so a delta that fits one character can break
another's limit. The presets also differ in proportion: the cartoon's head is large and its arms short against its
shoulders.

## Decision

Seven preset moves in `assets/dance/moves.json`, on canonical controls only, in the existing schema
`srstudio.dance-moves/1.0.0` (no field was added, so no version changed):

| Move | Support | What the tests read on forward kinematics, on `realistic`, `cartoon` and `stick` |
|---|---|---|
| `clap` | either | On every beat the two hand tips (the middle of each hand's fingertips) are within 0.1 head radius on realistic, 0.3 on stick and 0.9 on cartoon, in front of the body and below the shoulders; at the far extreme between beats they are more than 2.5 head radii apart; neither hand passes the midline by more than 0.15 head radius. |
| `point-up` | either | On one the right hand tip is above the middle of the head, out past its own shoulder, while the left hand is below its shoulder; on two the reverse. On realistic and stick the pointing hand is above the crown. A `hold` waveform keeps the point after the beat. |
| `raise-the-roof` | either | Both hand tips stay above the shoulders, are highest on the beat, rise into it, and travel at least 0.3 head radius; the palms face up (the fingertips' curl direction has an upward share above 0.6). |
| `hand-wave-side` | either | Both raised hands are over 1.5 head radii further right on beat one than on beat three, above the shoulders throughout, one wave a bar. |
| `shoulder-roll` | either | Each shoulder is highest on its beat, furthest back half a beat later, lowest a beat later and furthest forward after that: a backward roll, the left a beat after the right. |
| `hip-sway` | feet | The hips are over 0.4 head radius further right on one than on two, and each hand moves the same way by more than twice the hips. |
| `hands-up` | either | A held pose that does not move: both hand tips above the middle of the head, and over 1.5 head radii above the crown on realistic and stick. |

Every gesture, and its mirror, is danced at 48 samples a beat on all three presets through `dance_pose` without
clamping, so no frame passes a limit. Arms carry lag 0, so a raised arm rides the body as the reference reel's does.
`Move.mirror` is tested against the mirror image: on the realistic skeleton, which is its own mirror at rest, every
joint of the mirrored gesture sits at the reflection of the same joint on the other side.

`Move.held()` returns a move that never moves as `Entry.hold` pairs, each target's bias, and refuses a move with a
moving pattern. `hands-up` held over `seat-groove`, `head-nod`, `shoulder-roll`, `bob` or `sway` stays within every
preset's limits and keeps both hands above the middle of the head.

Where a preset's proportions forbid the full gesture, the amplitudes fit all three and the test says what each reaches:

- The cartoon cannot reach above its crown with any arm angle its limits allow, so `point-up` and `hands-up` hold it to
  the middle of its head.
- No single set of arm angles brings all three presets' hands together. `clap` meets on realistic and stick and stops
  short on the cartoon; the cartoon claps shut at `Entry` intensity 2, which swings the arms further in and is tested.

The same test found that `bob`, `bounce` and `step-touch` swung each knee symmetrically about zero and straightened it
past `lower_leg.stretch`'s limit at the far extreme. Each knee now keeps its hit value and straightens to zero.

## Rejected alternatives

- **Hand targets solved by inverse kinematics.** A target in space would meet on every character, but the dance module
  would then depend on the skeleton, which ADR 0186 keeps apart, and a style could no longer read the gesture as
  canonical deltas.
- **Per-character amplitude tables in the moves file.** A table keyed by preset fixes the presets in the data, while any
  profile can be a character. An entry's intensity already scales a gesture for one character.
- **Finger shapes (a pointing index, a fist).** Hands differ by kind (`human`, `three-finger`, `mitten`), so a shape on
  canonical fingers reads differently on each; a style draws the hand. The gestures move arms, shoulders and wrists.
- **A held pose as its own record kind.** A move with only biases already says it, parses with the existing reader, and
  can be danced as an entry; `held()` turns it into an entry's hold.

## Consequences

- A routine has bigger moves for a song's loud parts.
- Every preset now dances on every preset character within limits without clamping, and a test holds that.
- A cartoon clap needs intensity 2 to meet. A choreographer that does not know the character leaves it at 1.
- None of the gestures has been judged on a drawn body yet; the tests prove positions, not how a style draws them.
