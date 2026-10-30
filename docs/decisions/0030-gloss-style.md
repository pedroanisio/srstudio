---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0030: Gloss, a trapped-in-a-cheerful-world satire hosted by a deadpan orb

- Status: accepted; library implemented, 2026-10-29 (`srstudio.gloss`, `srstudio.gloss_sets`, `srstudio.gloss_reel`,
  the `GLOSS` style and the `PLASTIC` palette; `tests/test_gloss.py`, `tests/test_gloss_episodes.py`; seven episode
  scripts `episodes/gloss_*_audio.py` recorded through `episodes/_gloss.py`, with their builds `episodes/gloss_*.py`)
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Back to the [library README](../../README.md); builds on [ADR 0019](0019-lip-sync.md) (mouths from timestamps),
  [ADR 0021](0021-engine-native-features.md) (native captions, transitions, effects) and
  [ADR 0023](0023-comic-craft-measured.md) (comic craft, measured)

## Context

The operator asked for a style that satirises the trapped-in-a-cheerful-digital-world genre, with the dark deadpan
of a calm facility AI that narrates tests and the existential absurdity of an afterlife run on a points ledger, and
for seven videos in it. Then: the first cut's visual polish scored 3.5 of 10, and it had to rise.

- **Originality.** No franchise names, designs, characters or lines. The world is the library's own: the Plaza, a
  pastel checkerboard forever-plaza with an exit door that is painted on; Sunny, a floating orb host with a screen
  face; four guests; and the Joy Points board that scores every small act.
- **Comedy shape.** The setup is relentless cheer; the turn is that the cheer is a system that cannot be left,
  only rated, scored and waited in. The joke is always the system, never a guest.

## Decision

- **A style value, `GLOSS`.** Portrait 1080×1920 at 24 fps, a `<sequence>` of shots each as long as its take,
  `timeline.json` input from `srstudio.takes`, Fredoka 600 (Google Fonts, OFL, pinned), the `PLASTIC` palette,
  `lipsync.SPEECH_MOUTH` mouths.
- **The cast, `srstudio.gloss`.** Glossy vinyl peg dolls (Nadia, Gus, Tamsin) and Sunny. Expression is data on the
  shot's clock (`face` and `pose` tracks), never a redraw. Each trait *does* something in a gag: Nadia's NEW
  sticker peels, Gus's wind-up key unwinds, Tamsin's spring base bounces, Sunny scans with a beam and wears a tie
  as the manager. Skin tones are named looks (`SKIN`). A fallen doll lifts by `LIE` so it lies on the floor rather
  than through it. Sticker lettering counter-flips with a flipped doll so it never reads backwards.
- **The material is a vinyl, built from the silhouette.** Each part is rounded by inner shadows (`FORM`, a pink
  floor bounce `RIM`); highlights and contact shadows are radial gradients (`haze`) or a few soft blurs, so the
  dolls read as toys, not flat cut-outs, and the contact shadows seat them on the set. A soft drop shadow (`LIFT`)
  is available through `finish(..., lift=True)`, but no shipped part uses it: G1–G7 carry no `gloss-lift`
  effect.
- **Sets, `srstudio.gloss_sets`.** The Plaza, the Activity Room and the Waiting Room, each with a far plane softened
  by `DEPTH_BLUR`, scenery lettering drawn in strokes and numbers as seven-segment shapes (no font, nothing a
  camera move can carry out of the safe area), and a plum caption shade from `CAPTION_SHADE` to the foot of the
  frame, so white captions read over pale tiles. Props: the Joy Points `board`, the `door`, the `ticket`; graphics:
  the `hook` card and the Plaza `notice` that buttons every reel.
- **The grade lights the world only.** `GRADE` (bloom, plum vignette, fine grain) applies to each shot's world
  group. The board, the corner Sunny badge and the notice card sit above it ungraded, so the effects never lower
  the contrast of the words.
- **The board's words are never squashed or crossfaded.** The first card pops open by `scaleY`, and its words are
  gated on only after `POP_OPEN`. A card that carries across a cut is `Card(carried=True)`: first on the board,
  from 0, and it does not pop again. A notice reached by a crossfade shows its words from `settle`, once the fade
  is over. `TONES` are at least 7:1 on the paper, because antialiasing reads about a quarter lower than the colour.
- **Staging is data, `srstudio.gloss_reel`.** A `Stage` per take (set, cast `Place`s, cards, props, one camera
  `Move`, shake, blackout, or a `Notice`) is checked against the takes before anything is drawn. The camera group
  of each shot is named `gloss-<take>-angle`, so `srstudio craft` counts its crash zooms as camera moves.
- **The beat before a punchline is quiet.** The music bed ducks `DUCK` dB under every line. It also drops a
  further `HUSH` dB through every pause that `craft.pauses` finds between spoken takes, ramping over `HUSH_RAMP`
  inside the pause. The scripted 1.2–1.4 s holds then land as near silence instead of muzak. To measure them,
  `craft.lines` now reads a takes `timeline.json` (spoken takes only), and `craft.moves` places moves inside a
  `<sequence>` on the episode's clock, as the engine does.
- **An effects budget.** Shots with 81–105 effect groups ran out of memory on the 8 GB GPU; 34 rendered. A Gloss
  frame stays near 40 effect groups: the material on the cast, the grade once per shot, and gradients in place of
  blurs wherever a soft shape will do.

## Rejected alternatives

- **Generalising `saga_reel` into one reel engine now.** It would have changed a shipped style's builds in the
  middle of another session's work. Gloss keeps its own `gloss_reel`. The shared reel engine (ADR 0031) is the
  place to merge them, proven by a byte-identical rebuild.
- **Text layers in the sets.** A crash zoom carries a text layer out of the safe area and fails the overlay check.
  Stroked lettering scales with the camera and has no safe-area constraint.
- **Blurred highlights everywhere.** Each blur is an offscreen pass and pushed frames past the GPU budget.
  Gradients give the same soft highlight at no extra pass.
- **The engine's `boxed-line` caption preset.** Black boxes over a pastel world broke the look. The caption shade
  keeps the native white-and-gold captions legible without them.
- **Grading the whole shot.** Bloom and vignette over the board lowered its text contrast below the floor.

## Consequences

- Seven Gloss reels share one cast, three sets and one board. A new reel is a script of takes plus a stage table.
- The engine's contrast check still warns on the gold active word of the native captions over pale tiles (about
  1:1 measured on changed pixels); the frames read legibly, and the warning stays visible rather than being
  silenced.
- Cards carried across shots are new layers per shot, so the engine's per-layer legibility check flags them under
  0.833 s even though they stay on screen continuously.
- New reels caption with `gloss_reel.LOOK` (`Reel(captions=...)`), the readable look Saga uses (ADR 0031): a line that
  wraps past two lines is split so no cue ends on a lone word, and every cue is held at least 0.84 s where the
  next line allows. The house default had left fragments such as "existing." on screen for 0.7 s. G7 is the first;
  the published G1–G6 keep the house look so they rebuild unchanged.
- `HUSH` and the craft fixes apply to every future Gloss reel. Other takes-based styles can adopt the hush through
  the shared reel engine.
