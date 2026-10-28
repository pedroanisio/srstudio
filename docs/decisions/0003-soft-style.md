# ADR 0003: The Soft style — pose-sheet blob characters on a beat

- Status: accepted and implemented, 2026-10-28 (`srstudio.blob`, `srstudio.music`, `styles.SOFT`, `canvas.WARM`,
  `graphics.captions(color=, shadow=)`, `tests/test_soft.py`, `tests/test_music.py`, episode 07 *Focus Mode*);
  revised the same day: interpolating rig with in-betweens (decisions 2–3), Google Fonts captions (decision 6),
  motion rules (decision 7), proportions (decision 8) and open-root
  front limbs (decision 9); extended for episode 08 *Camera Off* (decision 10)
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Back to the [library README](../../README.md)

## Context

The operator asked for a third look, from a reference short in which a round white character with one dark
outline sits at a desk, gives up working and dances pose-to-pose to a song, with dark lyric captions at the top of a
flat warm stage. Neither existing style draws that. Cutout characters are rigs with gradients and amplitude mouths
in fixed camera setups. Ink is square, takes are cut as a shot sequence, and poses come from mood. Neither has a
beat. The reference's character, lyrics and song belong to their author, so the style is reproduced and the content
is not.

## Decision

1. **Style `SOFT`, palette `WARM`.** Portrait 1080×1920 at 30 fps on the project clock. Input is `dialogue.json`
   with no single mixed file, because the lines, effects and music are separate pinned clips. The style uses
   Poppins Bold (decision 6) and the `SOFT_MOUTH` amplitude model. `WARM` is ink `#231E19` and white `#FFFFFF` on a
   `#F3DFCF` stage. Parts live in `srstudio.blob`.
2. **A character is one rig of fixed topology.** A `Pose` is a head and exactly five limbs (`LIMBS`: two legs,
   torso, two arms), each a tapered brush `Stroke`: a cubic centreline with a start and end width and round caps,
   outlined as a closed polygon. Because every pose has the same limbs, any two poses interpolate (`Pose.lerp`).
   Each limb is drawn twice, once as an ink outline (stroke 2 × `OUTLINE`) and once as a white fill, with all
   outlines below all fills, so head, torso and limbs merge under one outline. Arms in a pose's `front` switch, by
   opacity keys, to a pass with their own outline on top (clasped hands, arms on the desk). Adding a pose means
   adding data, not drawing code.
3. **A performance is cues, drawn as drawings.** A `Cue` holds a pose, eyes and mouth (plus offset, turn and
   mirror) until the next cue. With `ease=s`, the character leaves the previous pose `s` seconds early through
   smoothstep in-between drawings (15 a second) and lands on the cue's time. `blob.drawings` validates the cues;
   `pip` keys every limb's `path` and the head's and face's position with hold keys at each drawing time. Eyes and
   mouths are gated groups, so exactly one of each is visible at any frame; the engine test asserts this. A `sing`
   mouth follows `Episode.mouth` (`blob.mouth_track`). The first design held each pose until the next beat. That
   gave 2.8 drawing changes a second against the reference's 8.1 (frame differencing at 30 fps, character region),
   and the moves read as cuts. With in-betweens episode 07 measures 8.5.
7. **Motion rules that keep moves readable** (from a frame-by-frame review of episode 07):
   - The face changes when the pose lands, not when the move starts (`Drawing.face`).
   - An arm in front in only one of two poses travels behind the body. A test asserts that no front arm covers the
     face in any pose or in any in-between of any two poses.
   - Poses blend in pose space, and position and turn blend separately. A turn is then a rotation, and limbs keep
     their length.
   - `lift` arcs a move, and `overshoot` lands past the pose and settles one drawing later. Settling needs room
     before the next move, and a cue without it is refused.
   - `pin` keeps a planted foot fixed and solves the position from it, so a walk never slides.
   - `FLOOR` is in front of the chair, so a standing character is never drawn inside the furniture.
   - `pip(shadow=True)` keys a contact shadow under the feet.
   With these, episode 07 measures 9.5 drawing changes a second.
8. **Limbs keep their length, and the set is sized to the character.** The seated poses had arms 1.5× and legs 1.9×
   their standing length. The chair seat was too high for Pip's legs, and the keyboard was out of reach, so the poses
   stretched to touch them. The result was tube arms floating over the desk and one merged leg mass. Now every arm
   and leg stays within -20 %..+25 % of its standing length in every pose (tested). Seated arms drop to an elbow and
   reach forward, and seated legs bend at the knee. The chair seat and desk are lowered, and the laptop sits within
   reach. A test places each seated pose at `SEAT` and asserts that the hands land on `keyboard()` and the soles on
   `SEATED_FLOOR`. Legs may be in a pose's `front`: the near seated leg is outlined over the far one.
9. **Front limbs grow out of the body.** A front limb used to carry a closed outline, including a round cap at the
   shoulder in the middle of the chest, so arms looked stuck on. Now a front limb is filled, then traced only along
   its sides and tip (`Stroke.contour`, open at the root), as the reference draws them. Arms are in front whenever
   they cross the body. That covers standing, walking and clasped hands; otherwise the merged pass swallows them.
   Seated in 3/4 view, only the near arm and leg are in front, and the far arm stays behind the body.
10. **More poses, one song pipeline.** Episode 08 added `nod` (a seated pose with the head dropped and the hands
    on the keys), `cheer-a/b` (both hands raised beside the head, not in front) and `wave-a/b` (the right hand up,
    the lowered left arm in front). They are data only, held to the same limb-length, face-cover and keyboard tests.
    The sung-episode audio script moved to `episodes/_song.py`, a `Song` value with several voices by role and
    several effects, so a new song is a spec and not a copy of about 250 lines. Episode 07 is now a `Song`, and its
    `dialogue.json` is byte-identical.
4. **One tempo for poses, lines and music.** `music.Groove` maps bar and beat to seconds. Cues and lyric lines are
   placed on it, and `music.render` synthesises the groove (kick, snare, hat, bass, keys over a chord loop) from
   the same grid. The render is deterministic for a given seed and peak-levelled. A section's notes are cut where
   the section ends, so a rest is real silence.
5. **Captions** gained `color=` and `shadow=None`, giving dark text with a white outline on a light stage. The safe
   area (`VERTICAL`) keeps them inside x 80–920.
6. **Caption faces can come from Google Fonts.** `Font(google=GoogleFont(family, weight))` names the face, and
   `srstudio fonts add` / `fonts.install` fetches it. Only a single `@font-face` from `fonts.gstatic.com` is
   accepted. The file's own `name` and `OS/2` tables must match the requested family, weight and italic, the
   family's licence is stored next to it, and `fonts.lock.json` pins URL and SHA-256. Later builds verify the pin
   offline. Soft uses Poppins Bold (OFL-1.1), the rounded geometric bold of the reference captions.

## Rejected alternatives

- **Extending the Cutout rig with a blob body.** Rejected because the rig's fixed head, eye and mouth layers cannot
  produce merged limb silhouettes or full-body pose changes, and every Cutout default (gradients, bottom captions)
  would have to be undone.
- **One hand-drawn closed path per pose.** Rejected because each pose would cost a large path to draw and its
  outline would have to be redrawn by hand. Centrelines plus two passes give the same merged look from a few
  numbers.
- **Generated music** (the provider's sound-effect kind). Rejected because it is capped at 22 s, its tempo cannot be
  verified against the grid, and every change costs a request. The synthesised groove is exact, free and testable.
- **Engine path morphing between poses.** Rejected because it needs schema draft 1.8, and a continuous tween looks
  smoother than the reference, which is drawn on twos to fours. In-betweens are explicit hold-keyed drawings instead.
- **A separate group per look, gated** (the first design). Replaced because in-betweens would need one group per
  drawing. Keying paths on one rig keeps the document size proportional to drawings × limbs.
- **Copying `focus_mode_audio.py` for episode 08.** Rejected because two copies of the resolve, check, place and mix
  steps would drift apart. `_song.py` holds them once.
- **Bundling the font file or using a system font.** Rejected because a bundled file goes stale and carries no
  provenance, and system fonts differ between machines. A pinned download is reproducible and carries its licence.

## Consequences

- A new blob character is a new set of `Pose` data plus a face. The rig, cues and in-betweens are reused.
- Building a Soft episode on a new machine needs one network fetch for the font, after which builds are offline.
- The groove is deliberately simple: one chord loop and five parts. Richer music would be a new `render` option or
  a pinned audio asset, not a change to the grid.
