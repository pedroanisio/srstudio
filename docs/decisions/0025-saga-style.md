---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0025: Saga, a space-opera parody style told by a deadpan field guide

- Status: accepted; library implemented, 2026-10-28 (`srstudio.saga`, `srstudio.saga_sets`, `srstudio.saga_reel`,
  the `SAGA` style and the `VOID` palette; `tests/test_saga.py`, `tests/test_saga_episodes.py`; seven episode
  scripts `episodes/saga_*_audio.py` with their builds `episodes/saga_*.py`)
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Back to the [library README](../../README.md); builds on [ADR 0019](0019-lip-sync.md) (mouths from timestamps)
  and [ADR 0021](0021-engine-native-features.md) (native captions and transitions)

## Context

The operator asked for a new style that satirises the big space-opera franchise with the humour of a dry,
absurdist galactic field guide, and for seven videos in it. Two constraints shape everything:

- **Originality.** No franchise names, logos, characters, opening crawl or theme. The parody works on the genre's
  tropes (a dark lord in a visor, armoured enforcers who never hit anything, a moon-sized station with a fatal
  flaw, a smuggler's freighter, a desert planet, a mystical energy field, a trash compactor) in our own words and
  drawings. The field-guide voice is likewise our own device, the *Handbook*, never a quotation.
- **Comedy shape.** The genre's grandeur is the setup; the turn is that the galaxy runs on the same mundane
  systems the viewer suffers at work (ticket backlogs, annual reviews, group chats, tip screens, forced updates,
  subscriptions, open-plan offices). The Handbook's footnote is the button.

## Decision

- **A style value, `SAGA`.** Portrait 1080×1920 at 24 fps, a `<sequence>` of shots each as long as its take
  (as Ink), `timeline.json` input from `srstudio.takes`, Space Grotesk 700 from Google Fonts (pinned, OFL), the
  new `VOID` palette (deep space ink, warm paper, gold shade), `lipsync.SPEECH_MOUTH`, `flat_counter("s")` ids,
  and an error-level flash check (explosions are orange fireballs with no white frame).
- **The cast, `srstudio.saga`.** Seven original characters drawn in heavy ink: Lord Gloom (visor whose red glow is
  the mouth), Enforcer Seven and Gary (helmets with a mic light; Gary is Seven with an orange stripe), Juno, Rook
  and Elder Mabel (faces with visemes and blinks; Mabel has glasses and a cane, three skin tones are named looks),
  and a bar droid whose smile bar glows. Masked characters "talk" with a light, not a mouth. Every one breathes.
- **Locations and props, `srstudio.saga_sets`.** Space, bridge, cantina (with a bar front layer and a "stare"
  event), desert at sunset, cockpit (with a console front layer and a jump event), and trash compactor (walls that
  close in by `start_px` + `travel`, capped at `WALLS_MAX`, and a back door). Props: the hologram panel `holo`
  (switching `Panel`s on the shot clock, optional face, box refused outside the vertical safe area), the cube
  battle station with its fireball, a freighter, a fighter, a pebble. Graphics: the hook badge and the Handbook
  entry card. Every location draws both signature marks.
- **Staging as data, `srstudio.saga_reel`.** An episode is a recorded take list plus one `Stage` per take (set,
  options, `Place`s, panels, props, a `Move`, blackout and shake spans, or an `Entry`). `check` refuses a staging
  that does not fit the recording before drawing: a take without a stage, an unknown part, a speaker who is not on
  screen (on a panel face counts, the narrator is exempt), a front layer that does not exist, a duplicate cast
  member, anything outside its take. `build` draws it, puts the hook over the first take, crossfades into the
  entry, adds native captions, and mixes takes, effects and the music bed with the music ducked under lines.
- **The format.** Each reel opens on the narrator's hook question, escalates in threes, holds at least 1.2 s
  before the punchline, and buttons on a typed Handbook entry. Episodes call back to each other: ticket #4471, Gary,
  the compactor. One composed music bed ("Overture, mostly") is shared by the series.
- **The look (a polish pass after the operator scored the first cut 4/10 on visuals).**
  - *Depth.* Every location draws its far plane (sky, walls, window, patrons) in its own group blurred by
    `DEPTH_BLUR`; the floor, the cast and both signature marks stay sharp, and a test refuses a mark under a blur.
  - *Light.* Light comes from the upper left. Each figure carries an inner shadow (`saga.FORM`) and a soft drop
    shadow (`saga.LIFT`), drawn shadow sides on torso, sleeve, leg and head, a gold rim on the lit edge, and a
    contact shadow that stays on the floor while the body breathes. Floors get a pool of light at the cast's feet.
  - *Finish.* Every shot is graded by `saga_sets.finish` with `GRADE`: bloom above a high threshold (so white
    armour does not glow), a vignette and fine film grain. Captions and the hook sit outside the shots, ungraded.
  - *Composition.* The cast stands at `FLOOR` (1270), just above the caption band, or at `BEHIND` behind a front
    layer, which now reaches the floor so nothing shows below it. The hologram is drawn over the camera, sized to
    its words, pops in about its own centre and ends above a standing head. The Handbook entry is sized to its
    words and centred above the caption band.
  - *Captions.* A narrated line too long for one caption is split at words into cues that fit
    (`native.cues_from_takes`).
- **Fixes found on the way.** Eyes and the fireball were anchored without `place=True` and drew at the feet and
  the frame corner; both are pinned now, with tests. `native._spans` treated a shot's `end` as absolute time; the
  engine reads a sequence child's `end` as its length (a render showed the second of two 1 s shots at 1.5 s). The
  spans now accumulate lengths, with a regression test, and the test case that encoded the old reading is
  corrected.

## Rejected alternatives

- **A coloured rim light by inner glow.** Tried in the lookbook: the glow goes all round the silhouette and reads as
  a sticker outline. The rim is drawn on the lit edge instead.

- **Reuse Ink or Toon with a space backdrop.** Ink is square and monochrome; Toon's room-and-desk staging and its
  cat are the wrong genre. A space opera needs night skies, glows and light-as-mouth helmets.
- **Draw from the franchise.** Names, silhouettes copied from it, the crawl or the theme would make the parody a
  copy and is excluded by the originality constraint; tropes are generic, specific designs are not.
- **Episode-local staging code.** Each episode drawing itself would repeat the shot loop seven times and leave no
  check between recording and drawing; the data `Stage` lets one function refuse a mis-staged take.
- **A caption-per-line overlay.** The engine's native captions (ADR 0021) already time words and stay in the safe
  area; one burned track per output.

## Consequences

- Three modules and one palette join the library; `STYLES` gains `saga`, and tests that pinned the list of styles
  now list it.
- A new episode in the style is two short files: its takes and stages, and a three-line build.
- Recording runs through `srstudio.takes` with no retries: a line the speech-to-text check mishears stops the run
  and the operator decides on the rewording.

## Amendment, 2026-10-30: a still opening and text that passes the strict encode

- Status: accepted; implemented in `srstudio.staging.freeze`, `saga_reel.Stage.still`, `saga_reel.Entry.fade`,
  `saga_sets.Panel.fade`, `saga_sets.finish(grain=, bloom=)` and `saga_sets.entry(legible=)`, with tests in
  `tests/test_staging.py`, `tests/test_saga.py` and `tests/test_saga_episodes.py`; first used by S13 *The Code* and
  S14 *Take-Home*.

**Context.** The account runs a first-second test (`Tags(test="sp-hook_motion")`). Arm `a` opens on a frame where
nothing changes for a full second; arm `b` opens on motion. A Saga shot always moves: the cast breathes and blinks,
the sets animate their lights and stars, and the grade redraws its film grain every frame. Separately, new reels
are encoded with `--strict`, which fails on any warning, and no shipped Saga reel passed it: the engine judges text
contrast at the frames where a layer is most opaque, and the hologram's squash pop, its flicker strip, the bloom
over it, the glass sheen on the Handbook entry and the crossfade into the entry each put text below the contrast
floor there.

**Decision.**

- *A still shot.* `Stage(still=True)` draws a shot and then `staging.freeze`s it: every keyed property takes its
  value at the shot's start and its keys are removed; an expression or a text animator, which cannot be held,
  raises. The grade drops film grain for it. `check` allows it only on an effect take with no move, shake,
  blackout or entry, so a line is never spoken over a frozen face. The hook card stays up, unchanged, over the
  leading still takes and pops nothing until the first spoken take, the narrator's question, which it then holds.
- *Legible text, opt-in.* `Panel(fade=True)` fades a hologram in by opacity, with no squash and no flicker over its
  words, and the shot draws such panels above the grade so bloom never washes them. `Entry(fade=True)` cuts to the
  Handbook entry and fades it up by its own opacity, graded without bloom and drawn without the glass sheen
  (`entry(legible=True)`). The episodes keep a panel up at least 0.85 s before the next replaces it, the engine's
  shortest readable text.
- *The defaults are unchanged.* Every new switch is off by default, so the frozen published reels (ADR 0040)
  rebuild to the same scene document; a fidelity rebuild of three of them was byte-identical.

**Rejected alternatives.**

- *Slow the opening with the engine's time remap.* A remapped shot still breathes and twinkles, only slower, and
  the grain keeps moving; the first second would not be still.
- *Make fade the default for every panel and entry.* It would change the drawing of published reels, which are
  frozen at an accepted drawing (ADR 0040).
- *Lower the strict findings to warnings by encoding without `--strict`.* The brief for new reels requires a clean
  strict encode, and the findings point at frames a viewer cannot read.

## Amendment, 2026-10-30: a desert that darkens under the captions

**Context.** Saga captions are white with a dark outline and sit in the band below the floor line. On the desert
the band is sunlit sand, and a strict encode of S15 *Call Juno* failed the caption contrast check (LEG-CONTRAST,
1.01:1 against the 4.5:1 floor) the moment Elder Mabel spoke at home.

**Decision.** `saga_sets.desert(..., shade=True)` lays a dusk gradient (`DESERT_SHADE`) over the dune from just
above the floor line to the frame's foot, transparent at its top edge and nearly opaque by the caption band, so the
captions read and the horizon, the hut and both signature marks stay as drawn. A stage asks for it with
`Stage("desert", {"shade": True}, ...)`. A test proves the default draws no shade and the shaded desert draws
exactly one, spanning the band below the floor line.

**Rejected alternatives.**

- *Shade the desert by default.* It changes the drawing of every published reel set on the desert (*Group Chat*,
  *Free Tier*, *Moving Day* and *On Hold*), frozen at an accepted drawing (ADR 0040); with the switch off, a
  fidelity rebuild of *Moving Day* is identical.
- *Give Saga captions a box behind them.* It changes every set and every frozen reel's caption look to fix one
  location, and a box over the floor hides the cast's feet and contact shadows.
- *Restage the desert scenes elsewhere.* The premise needs Elder Mabel at home; the location is the joke's
  setting, not a choice to make for the captions.

## Amendment, 2026-10-30: the cast stays as drawn

**Context.** Lord Gloom (black helmet, red visor, cape, lit chest panel) and the enforcers (white plate armour,
dark visor band) draw on the space-opera genre the style parodies. A redesign was built on `feat/saga-redesign`
(f151612): Gloom as a robed comptroller with a chain of office and a stepped hat, the enforcers as hard-hatted
workers in hi-vis. Every existing Saga reel rebuilt identically with the old cast pinned.

**Decision.** The operator declined the redesign. Gloom and the enforcers stay as drawn, for the reels already made
and for new ones: the operator's position is that the cast is inspired by the genre, not a copy of any design. The
redesign branch is not merged, and the operator holds this decision; only the operator reopens it.

**Rejected alternatives.**

- *Adopt the redesign as the default for new reels.* Declined by the operator after reviewing the side-by-side sheet.
- *Keep both designs selectable.* Two casts for one series splits its look between reels and keeps unused library
  code with no reel to exercise it.
