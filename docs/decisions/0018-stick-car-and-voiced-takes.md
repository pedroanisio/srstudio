---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0018: Stick 03 — the car, the engine's effects, word captions and voiced takes as a library pipeline

- Status: accepted and implemented, 2026-10-28 (`srstudio.takes`, `srstudio.stick_car`, `stick.words`/`word_cues`,
  `stick.rig(mouth=)`, `Canvas.effect`/`Canvas.rgrad`, `Episode.hide_on_cover`, `social.take_still`,
  `episodes/repeat_after_me*.py`, `episodes/screen_share_audio.py`, their tests)
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Back to the [library README](../../README.md); follows [ADR 0009](0009-stick-rig.md) and
  [ADR 0012](0012-stick-looks-and-call.md)

## Context

The operator asked to recreate a screen recording of an Instagram reel ("recreate Audio, and all the video") and to
grow the library with what it needed. The reel is a portrait stick-figure cartoon. A driver makes the viewer repeat
vows after him, and the joke turns on what is lying on the passenger seat. Its words come up one at a time over the
picture.

As with Stick 02 (ADR 0009), the library does not copy a third party's drawing, script or voice. Stick 03, "Repeat
After Me", is an original episode in the same format: our own script, Dev as the driver, an ElevenLabs premade voice
and a music bed composed for it.

The library had no vehicle, no word-by-word captions, and no shared code for voiced takes:
`screen_share_audio.py` held its whole recording pipeline inline. The first car the episode drew was flat. It had an
empty door, a blob dashboard, a wheel made of two ellipses, legs hanging through the door and one kind of tree. The
operator asked for "a lot" better interior and exterior animation, and pointed out that scene-render and
`sr_core.scene` offer far more than the library used. srstudio used no `<effects>`, no blend modes and no motion blur.

## Decision

1. **Voiced takes are a library pipeline, `srstudio.takes`.**
   - A `Script` holds voices, settings, `Take`s (a line or an `sfx` effect, with hold, shot, mood and speed) and an
     optional music `Bed` (a `compose.Plan`, seed, bpm, gain and fade).
   - `record` treats every provider response as untrusted:
     - speech-to-text must hear each scripted line;
     - effects are length-checked;
     - the bed must contain no words and must not be shorter than the episode;
     - the bed is conformed to the episode with a fade and its length checked again;
     - any failure raises `TakesError`.
   - `main` is the consent-gated CLI.
   - `screen_share_audio.py` now builds its `Script` with it, with byte-identical output from the cache.
2. **The car is `srstudio.stick_car`, drawn in layers.**
   - `car` is the back layer: headliner, glass and scenery, door, driver's seat and dashboard.
   - The figure is posed from `DRIVING`, with its hands on the rim (tested against the rim's ellipse).
   - `cockpit` is the front layer:
     - a knee panel the shins run under;
     - the column and the wheel over the hands;
     - a seatbelt per key, from the pillar over the shoulder to the buckle;
     - the trees' shadows sweeping across the cabin;
     - the sun through the windshield and a vignette.
   - `ride` bobs a node on the suspension: two incommensurate waves at 12 fps, phase-shiftable, deterministic.
   - `seat`, `laptop` and `phone` are props.
3. **The scenery is six parallax layers drawn far to near, and depth comes from the engine.**
   - Layers: clouds, mountains, hills, a row of farmhouses and trees, roadside trees and pines with utility poles and
     sagging wires, and a guardrail.
   - The far layers are blurred, more the farther they are, under a horizon haze.
   - The near layers carry `motionBlur="on"` at a 270° shutter, so speed reads as streaks.
   - An oncoming car (`passing=`) crosses the window motion-blurred, centred on its cue.
   - The glass glare is screen-blended.
   - Drop shadows (`car-lift`) lift the seat, dashboard, armrest, wheel and belt.
   - Inner shadows (`car-sunk`) sink the pocket, the handle recess and the speaker.
4. **`Canvas.effect(name, type, **attrs)` and `Canvas.rgrad`** define a named `<effect>` or radial gradient once
   and return its id or paint. Any part can now use the engine's effect catalogue; its INERT diagnostics report
   attributes a type does not read.
5. **Word captions are `stick.word_cues` + `stick.words`.**
   - Each spoken word runs to the next word's start. The last word lingers but never past its take.
   - Punctuation is stripped, and bare punctuation shows nothing.
   - With `min_seconds`, a word shown for less joins the next words of its take while the cue, measured with
     `fonts.text_width`, stays within `WORD_WIDTH`. R3 asks 0.3 s: words swapped six times a second cannot be read.
   - Each cue pops in on the episode clock above the shots, so a camera move never scales it.
   - Each cue is one text layer, white stroked in ink, over a feathered ink scrim (`SCRIM_PEAK` 0.75) that fades in
     and out with each run of words. The engine's contrast check judges every text layer against what is behind it.
     An ink outline layer of its own was measured as ink against the dark cabin (31 findings, down to 3.1:1). A
     single stroked layer fails over mid and light grounds. Only a controlled ground passed on dark, mid and light
     probes alike.
6. **`stick.rig(mouth=)`** takes the phoneme model and defaults to `INK_MOUTH`, which leaves existing episodes
   unchanged. R3 uses `lipsync.SPEECH_MOUTH`.
7. **A cover's backdrop is drawn from the scene, without the burned-in text.**
   - The first R3 cover was cut from an MP4 frame, so its designed headline sat on half of the hook card and a ghost
     caption. check-with-my-team's cover had the same defect.
   - `Episode.hide_on_cover(*nodes)` names the burned-in text (a hook card, the word or caption group). `finish`
     writes a `cover` variant to the scene, a `<parameters><variant>` with a `visible=false` override for each node.
   - `social.take_still` renders the thumbnail's frame with `--variant cover`. It refuses a scene with no cover
     variant, a scene drawn at another size than the video, and a blank still.
   - `instagram_posts.COVER_SCENES` maps each such episode to the scene file its video is encoded from. A delivery
     `Item` carries `(post, video, scene)`, and the delivery fingerprint covers the scene, so editing the scene is
     drift.
   - check-with-my-team adds the variant only to its voiced build. The package's silent scene stays element for
     element the shipped one (`test_fidelity`), and the voiced picture renders pixel-identical to its previous build.
8. **A zoom does not speed up the country.** A close-up or push-in scrolls the scenery at `SPEED / zoom`, so the
   trees cross the screen as fast as in the wide shot. Twice as fast, dark trees against the bright horizon failed
   the engine's flash check (6 frames over the general-flash limit). The close-up also takes `car(defocus=)`, a blur
   on everything behind the glass, so the lens focuses on the face.
9. **A rect's gradient is in the rect's own coordinates.** `stick.Gradient` says so, and a test holds every
   gradient-filled rect of the car, the seat and the words to its own box. Frame coordinates had shifted the sky, left
   the horizon haze transparent and flattened the headrest. The Stick yard's grass has the same quirk, but it is
   the shipped package's scene, so `test_fidelity` keeps it.
10. **Small screen text is held to 7:1.** The laptop's unread pill (`BADGE`) and the phone's time stamp (`STAMP`, now
   18 px bold) were measured at 3.1 to 4.5:1 once antialiased.
11. **Every Stick location signs itself.** `stick_car.car`, `stick.room` and `stick.yard` draw the cactus and the
   code (ADR 0001), so an episode no longer places them by hand.

## Rejected alternatives

- **Tracing or re-voicing the source reel.** It is a third party's work; the format is free, the drawing and the
  script are not (ADR 0009).
- **A car as a bitmap or a 3D object.** A bitmap does not scale under the close-up camera and is outside the Stick
  style's vector ink. `object3D` would bring a renderer and lighting the style has no use for.
- **Faking speed with a hand-drawn smear or a `directional-blur` effect.** Engine motion blur follows each layer's
  real velocity, so the rail streaks more than the hills without per-layer tuning.
- **A `vignette` effect.** On a group that does not cover the frame, the probe filled the uncovered area with black.
  A multiplied radial gradient gives the same darkening on any group.
- **Covering the burned-in text with the cover's gradient, or picking a frame between captions.** Both depend on
  timing and layout luck, and a word-by-word reel has no frame without text. A variant removes the text at its
  source.
- **A gentler pop-in or fewer word swaps against the flashes.** Encodes of the zoomed range without the pop-in,
  without the words and without the scrim all kept the same flashing frames. Restoring the old sky and haze
  gradients reduced them, which located the cause in the magnified scenery.
- **Keeping the take pipeline inside each episode.** It would duplicate the verification controls in every episode,
  where they would drift apart.

## Consequences

- R3 is built from library parts only: 2,317 shapes in 363 groups. Its 353 frames render at about 107 ms each on
  the workstation, motion-blur shutter sub-frames included. The encode passes the flash and contrast checks with no
  finding.
- The legibility check still reports 32 texts drawn for less than 0.833 s. 24 are word cues, which follow the
  speech by design while the SRT carries whole lines. 8 are the phone's and laptop's texts in take 06, a 0.75 s shot
  whose phone and laptop continue into the next shot as separate nodes.
- Effects are not measured by `srstudio.layout` (shadows and blurs fall outside a shape's box), as before.
- `notes.json` has the R3 episode note and gallery items for every car part, cut from the R3 render.
