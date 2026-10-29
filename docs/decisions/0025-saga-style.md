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
