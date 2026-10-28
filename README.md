# srstudio

Reusable cast, locations, props, graphics and an episode builder for [scene-render](https://github.com/pedroanisio/scene-render),
written on the [sr-core](https://github.com/pedroanisio/sr-core) Python scene SDK (`sr_core.scene`). Back to the
[workspace README](../README.md).

The seven shipped episodes (*The honesty interview*, *Pressure*, *Fast at Math*, *Multitasking*, *The Wi-Fi Password*,
*The Printer* and *Work Training Be Like*) are rebuilt from this library in [episodes/](episodes/) and reproduce their packaged `.scene.xml`
element for element (`tests/test_fidelity.py`). Everything they use is a registered, parameterised part you can reuse
in a new episode, and every new part you register shows up in `srstudio catalog`.

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[validate,test]"      # sr-core (the SDK), lxml for XSD + Schematron checks, pytest
srstudio catalog                       # 11 characters, 14 locations, 30 props, 13 graphics; --style cutout|ink|soft|cel
srstudio styles                        # Cutout 1080×1920 @ 30 fps clock · Ink 1080×1080 @ 24 fps sequence · Soft 1080×1920 @ 30 fps clock · Cel 1080×1920 @ 24 fps clock
python3 examples/new_episode.py        # writes examples/out/coffee-review/coffee-review.scene.xml
python3 -m pytest tests                # unit/integration tests; fidelity with SRSTUDIO_PACKAGES, engine tests with SRSTUDIO_ENGINE
```

## How an episode is built

```python
from srstudio import Episode, EpisodeSpec, camera, cast, graphics, locations

ep = Episode(EpisodeSpec(slug="fast-at-math", number="03", title="Fast at Math — The Interview 03",
                         description="...", root=PROJECT, seed=52023, background="#D5DFDF"))
t, P = ep.t, ep.P                                   # the timeline from dialogue.json; P(i) is phrase i

wide = ep.setup(locations.office_wide, t.shots({"wide", "manager-reaction"}),
                at_desk=lambda g: ep.perform(cast.Manager(ep.cv), g, 560, 724, 1.45,
                                             blinks=[(P(2).start - .27, P(2).start - .12)],
                                             arms="articulated", facepalm=(t.reaction + .06, t.ending)))
camera.anchor(wide, 560, 724)
camera.push_in(ep.cv, wide, scale=[(0, 1), (t.reaction, 1.62)])

close = ep.setup(locations.office_reverse, t.shots(lambda a: a not in {"wide", "manager-reaction"}),
                 in_chair=lambda g: ep.perform(cast.Candidate(ep.cv), g, 540, 737, 2.07,
                                               smile=[(P(1).end + .03, t.cuts[2].time)]))

graphics.quiz_card(ep.cv, ep.comp, "QUICK MATH", "17 × 19 = ?", show=(P(2).start - .08, P(4).end + .12),
                   verdict="NOPE.", verdict_span=(P(4).start - .21, P(4).end + .12))
ep.captions(highlights={"dialogue-6": [("But it was ", False), ("fast.", True)]})
ep.audio()
ep.markers()
ep.finish()                                         # check (SDK + XSD + Schematron) → <slug>.scene.xml
```

A project folder holds `dialogue.json` (phrases with measured `start`/`end`, `camera_cuts`, `reaction_start`,
`end_card_start`, optional `park_start`, optional ElevenLabs `timing_file`s), `assets/dialogue.wav` and the caption
font. `Episode` reads both and gives you:

| Member | What |
|---|---|
| `ep.t` | `Timeline`: `phrases`, `cuts`, `reaction`, `ending`, any `*_start`/`*_end` beat, `spans(role)`, `shots(angles)`, `word_time(phrase, "several")` |
| `ep.track` | `Soundtrack`: RMS amplitude windows that drive the five mouth shapes |
| `ep.cv` | `Canvas`: typed drawing helpers on the SDK (`path`, `rect`, `ellipse`, `line`, `group`, `text`, `grad`, `keys`, `gate`, `pop_in`, `expression`) with the episode's palette |
| `ep.setup(builder, shots, **slots)` | A location gated to its shots; slots are callbacks that place things at the right depth |
| `ep.perform(actor, parent, x, y, scale, ...)` | An actor with mouth sync, `smile`, `blinks`, `nods` and actor-specific extras |
| `ep.mouth(role, smile, style, speaking)` | Per-frame mouth states, reusable across two instances of one character |
| `ep.captions(specs, **style)` | Caption text assets and layers; `highlights` colour a span of a caption |
| `ep.audio(...)`, `ep.markers()`, `ep.finish()` | Mix, section markers, check and write |

`finish()` refuses to write a document with findings (`strict=True`) and always writes `sdk-validation.json`.

`ep.audio()` plays whatever the project brings (`ep.audio_source`): pinned generated clips (`extra=` adds the
groove), one audio file per take (`take=` maps a take to its track options), one mixed `assets/dialogue.wav`
(`track_id=`), a verified `narration.json` (`narration=`, through `srstudio.narration.narration_cues`), or nothing
for a silent style. The master comes from the style's `Mix` (`Style.mix`: −16 LUFS, −1.5 dBTP, 24-bit; Ink −14 LUFS
without a bit depth); `loudness=` and `true_peak=` override it, and an option the source cannot take is a
`TypeError`. The explicit `audio_mix`, `mix` + `take_audio`, `generated_audio` and `add_track` stay for mixes the
one call does not cover.

## Styles

A **style** is what an episode looks like before a single part is placed, and it is a value:
`srstudio.styles.Style` holds the frame and rate, the clock, the input file, the caption font, the palettes the style
is drawn in (with a mouth model per palette), the id scheme, accessibility defaults and the modules that hold its
parts. `EpisodeSpec(style=…)` resolves every field the episode does not set; an explicit field still wins; a palette
the style is not drawn in is a `StyleError`. The names and the reasoning are in
[docs/decisions/0002-style-names.md](docs/decisions/0002-style-names.md),
[docs/decisions/0003-soft-style.md](docs/decisions/0003-soft-style.md) and
[docs/decisions/0004-cel-style.md](docs/decisions/0004-cel-style.md); `srstudio styles` lists them.

| | **Cutout** — `CUTOUT` (default) | **Ink** — `INK` | **Soft** — `SOFT` | **Cel** — `CEL` |
|---|---|---|---|---|
| Look | Flat vector shapes, soft gradients, bold outlines, like paper cut-outs | Pen stroke, one ink and one grey on white paper | Round white blob characters, one dark outline, flat warm stage, pose-to-pose | Traced, filled drawings with no outline, held per run under a measured camera push; silent |
| Palettes | `OFFICE` (cool, stage `#D5DFDF`), `CAFE` (warm, stage `#F0DDC0`) | `MONO` (stage `#FFFFFF`) | `WARM` (stage `#F3DFCF`) | `LINEN` (stage `#c5bbb0`, shade = the lettering box teal) |
| Frame | 1080×1920 portrait, 30 fps | 1080×1080 square, 24 fps | 1080×1920 portrait, 30 fps | 1080×1920 portrait, 24 fps |
| Clock | one composition on the project clock; camera setups gated by hold keys | a `<sequence>` of shots, each as long as its take; animations on the shot clock | one composition; each look of a character gated by hold keys on a beat grid (`music.Groove`) | one composition; the world group carries the measured camera (`cel.world`), the room its own inside it (`cel.compensate`); linear keys on the local clock, held to the end |
| Input | `dialogue.json` + one mixed `assets/dialogue.wav` | `timeline.json` with takes (words, character timestamps, one audio file per take) | `dialogue.json` with pinned generated clips + `assets/groove.wav` from `music.render` | `script.json`, a list of timed captions; the measured camera, pose runs and drawings are read from `assets/` (`cel.load_*`) |
| Mouths | five shapes from RMS amplitude windows (`OFFICE_MOUTH`, `CAFE_MOUTH`, chosen by palette) | five poses from character timestamps (`INK_MOUTH`, `phoneme_states`) | `SOFT_MOUTH` amplitude states drive the `sing` mouth of a cue | none: the style is silent and `mouth_style` resolves to `None` |
| Captions | DejaVu Sans Bold, bottom captions with highlighted spans | Patrick Hand, top captions paged from word timings (`subtitles.chunk_words`), plus an SRT | Poppins Bold from Google Fonts (`srstudio fonts add`), dark text with a white outline at the top (`captions(color=, shadow=None)`) | traced lettering (`cel.lettering`: boxes in the shade, glyphs as white paths), no font asset, plus an SRT |
| Audio | `ep.audio()` (one mixed file) | `ep.audio(take=…)` (one file per take; master −14 LUFS) | `ep.audio(extra=[("groove", …, {"role": "music"})])` (pinned clips) | none (no `<assets>`, no `<audioMix>`); `ep.audio(narration=…)` for a narrated master |
| Ids | `path-0001` | `shared_counter()` → `g1, p2, e3` | `path-0001`; looks are `<character>-<pose>-<digest>` | `flat_counter("v")` → `v1, v2, v3` for every node |
| Parts | `cast`, `locations`, `props`, `graphics`, `camera` | `ink`, `subtitles` | `blob` | `cel` |

The parts of one style are usable in the other (they draw with the canvas's ink, paper and shade), and the signature
marks adapt to the palette, so `srstudio catalog --style ink` lists Ink's own parts plus the shared ones.
`Timeline.load` picks the input format by content (`phrases`, `items`, or a list of captions). A new style is a `Style` value, usually
`dataclasses.replace` of an existing one, plus a module of parts named in its `parts` (see `ink.py`: ~40 lines of
drawing conventions before the first character, or `blob.py`: a pose sheet); nothing in `Episode` is specific to a
style.

## The parts

`srstudio catalog` lists them; `srstudio catalog --json` is machine-readable.

- **Characters** (`srstudio.cast`): `Manager`, `Candidate` (office rig: five mouth shapes, blink overlay, head nods,
  static or articulated arms, raised brows, pupils, facepalm, pointing forearm), `Barista`, `Customer` (café rig;
  standing or `seated=True`, phone, held cup) and `pigeon`. Subclass `Actor` (or `OfficeActor`/`CafeActor`) and override
  `draw_body`, `draw_head`, `draw_eyes`, `draw_face_front`, `draw_blink`, `after_head` to add one.
  (`srstudio.ink`): `human` (the round-headed doodle, drawn per take with its mood: waiting, pointing, screaming),
  `printer` (a talking prop: LED and voice marks when it speaks, shaking shell and bobbing paper when it whirrs) and
  `router` (`talking-router`: four LEDs chase and the antennas bob when it speaks; `power="down"`/`"up"` steps the
  LEDs off or sweeps them on for a reboot, `drop_at=` blacks them out mid-take; the model plate carries the signature).
  (`srstudio.blob`): `pip`, the sprout-headed blob of the Soft style, one rig of five tapered brush `Stroke`s
  (legs, torso, arms) and a head. Every pose in `POSES` (stand, step, walk-a/b, stride, sit, type-a/b, nod, clasp, lean,
  groove-a/b/c, cheer-a/b, wave-a/b) has the same limbs, so any two interpolate: a `Cue(ease=)` arrives through smoothstep in-between
  drawings (`blob.drawings`, 15 a second) and lands on its beat. Poses blend in pose space while position and turn blend
  apart, so a turn rotates instead of shrinking limbs; `lift=` arcs a move, `overshoot=` lands past the pose and
  settles a drawing later, and `pin="leg_l"` keeps that foot planted and solves the position from it (a side-step
  walks with `walk-a`, `stride`, `walk-b`, `stand`). The expression changes when the pose lands. Limb paths are
  hold-keyed per drawing in two passes (outline, then fill) so the body merges under one outline; arms switch to a
  front pass whenever they cross the body (standing, walking, clasped hands; seated, only the near arm and leg, the
  far arm stays behind in 3/4 view). A front limb is filled, then traced along its sides and tip only
  (`Stroke.contour`), so it grows out of the body instead of sitting on it; a limb moving to or from the front
  travels behind the body. Every arm and leg keeps its length in every pose (tested
  within -20 %..+25 %), so limbs bend at elbows and knees instead of stretching.
  `shadow=True` keys a contact shadow under the feet. Eyes `EYES` (ring eyes with pupils, look, wide, happy, squint, closed) and mouths `MOUTHS` follow the head;
  `sing` follows the soundtrack (`blob.mouth_track`). The rig is `blob.blob(..., look=)`: a `Look` names the body
  fill, blush, topper, hair and features, so `pip` is the rig in `PIP` (white, blush, sprout) and `bo`, the boss,
  the same rig and pose sheet in `BO` (pale blue, side-parted hair, square glasses, no blush). Two more looks
  are polished: `juno` in `JUNO` (apricot, auburn bun and scrunchie, scalloped bangs, freckles, lashes) and `remy`
  in `REMY` (lavender, curling tuft, headset with mic boom, gloss). A look may turn on `shade` (a crescent away
  from an upper-left light), `gloss`, `catchlights` and `lashes`; all are off by default, so Pip and Bo draw as
  before ([ADR 0007](docs/decisions/0007-polished-looks.md)). A seated `lounge`
  pose rests both hands on the near thigh, for the sofa.
  (`srstudio.cel`): `traced` (`cel-traced`): a traced character as a sheet of filled drawings, one held per run of
  the pose timeline; drawings and runs are data (`cel.load_drawings`, `cel.load_runs`), parsed and refused when
  malformed (`cel.CelDataError`).
- **Locations** (`srstudio.locations`): `office_wide(at_desk=)`, `office_reverse(in_chair=)`,
  `cafe(behind_counter=, at_counter=, on_counter=)`, `park(on_bench=, beside_bench=)`. Each takes `shots=` and gates its
  root group before drawing, so new locations should do the same (see `examples/new_episode.py`).
  (`srstudio.ink`): the shots `desk_shot`, `closeup`, `printer_shot`, `wide_shot`, `router_shot` (the router on its
  wall shelf, `close=True` fills the frame, `hand_action="reach"|"press"|"leave"` brings in the `ink-hand` prop) and
  `router_wide`, each drawn into a take's group; `router_scene(cv, g, take, **beats)` picks the shot a take names.
  (`srstudio.blob`): `office` (`soft-office`: desk, laptop and slatted chair in a 3/4 view from above, wood outlined
  in `WOOD_LINE`; drawn in output pixels for Pip at `SCALE` and sized to him: a seated pose's hands land on
  `blob.keyboard()` and its soles on `SEATED_FLOOR`, which a test asserts; `SEAT` and `FLOOR` place a sitting or
  standing pose). `home` (`soft-home`): the living room in the same 3/4 view, a fabric `sofa` (`soft-sofa`) facing
  left on a rug, a floor lamp and a side table with the cactus; the sofa shares the chair's axes and seat height, so
  a seated pose at `SOFA_SEAT` has its hip on `blob.sofa_seat()` and its soles on `SOFA_FLOOR` (tested), and
  `on_sofa=` seats a character between the seat and the near arm.
  (`srstudio.cel`): `room` (`cel-room`: wall, plank floor fanning from a vanishing point and a wooden desk under the
  room's own measured camera re-expressed inside the world's, `cel.compensate`); `cel.world` places the measured
  camera on the group everything else is drawn in.
- **Props** (`srstudio.props`): desk papers, plant, chairs, laptop, water glass, silent phone, coffee cup, menu board,
  café window, pendant lights, espresso machine with steam expressions, pastry stand, buildings, tree, shrubs, park sign,
  bench, and the gradient sets `office_paints`/`cafe_paints`.
- **Graphics** (`srstudio.graphics`): `episode_slate`, `quiz_card`, `answer_bubble`, `scorecard`, `dashboard`,
  `notification`, `password_card`, `location_slate`, `connected_card`, `captions`; `ink.caption` for the top captions
  and `subtitles.write_srt` for the external file; `cel.lettering` (`cel-lettering`) for a caption traced as boxes and
  glyph paths.
- **Music** (`srstudio.music`): `Groove(bpm)` turns bars and beats into seconds; `render(groove, sections)`
  synthesises a deterministic groove on that grid (rests are cut, not faded), `write_wav` stores it.
- **Camera** (`srstudio.camera`): `anchor`, `push_in`, `zoom_holds`, `reframe` (hard cuts by hold keys on one group).
- **Mouth styles** (`srstudio.soundtrack`): `OFFICE_MOUTH`, `CAFE_MOUTH`; `dataclasses.replace(CAFE_MOUTH, idle="smile")`
  keeps a character smiling between lines.

## Extending

Register a part so the catalog and other episodes find it:

```python
from srstudio import register

@register("prop", "tip_jar", summary="A glass tip jar", episodes=("06",))
def tip_jar(cv, parent, x, y, scale=1.0):
    g = cv.group(parent, cv.uid("tip-jar"), x=x, y=y, scaleX=scale, scaleY=scale)
    cv.rect(g, -40, -90, 80, 100, radius=10, fill="#DDEAF2", stroke=cv.ink, sw=3)
    return g
```

Kinds are `character`, `location`, `prop`, `graphic`. A new location is complete only when it places both marks
of the [Signature](#signature) convention. Parts from another package are listed with
`srstudio catalog --plugins my_package.parts`. A new episode is a script like the ones in [episodes/](episodes/):
it takes the project folder as its first argument and is run with `python3 episode.py PROJECT` or
`srstudio build episode.py PROJECT`. `srstudio.sample.write_sample_project` writes a synthetic project (dialogue,
tone-burst soundtrack, font) to try a build without a TTS pass.

### Google Fonts

A style's caption face can name a Google Font (`Font(google=GoogleFont("Poppins", 700))`). Fetch and pin it once:

```bash
srstudio fonts add Poppins --weight 700 --into PROJECT/assets/fonts
```

`srstudio.fonts.install` asks the Google Fonts CSS API for the TrueType file, accepts only a single `@font-face`
served from `fonts.gstatic.com`, reads the file's own `name` and `OS/2` tables to check that family, weight and
italic match the request, and fetches the family's licence (OFL, Apache or UFL) from the google/fonts repository.
Only then does it write `<family>-<weight>.ttf`, the licence and `fonts.lock.json` (URL, SHA-256, licence). Later
runs verify the pinned SHA-256 and do not touch the network; a file that changed is refused. An episode whose
style font is missing stops with the `srstudio fonts add` command that fetches it.

## New episodes with generated audio: *Five Years* (06)

[episodes/five_years.py](episodes/five_years.py) is the first episode made on the library rather than ported to it.

```bash
python3 episodes/five_years_audio.py PROJECT --key-stdin < key   # resolve, speech check, trims, dialogue.json
SRSTUDIO_ENGINE=scene-render srstudio build episodes/five_years.py PROJECT   # scene + overlay check
scene-render encode PROJECT/five-years.scene.xml --strict         # renders/five-years.mp4
```

**Generated audio, resolved by the engine.** Every line and effect is a `<generated>` asset
(`srstudio.generated.Generated`) for the `srstudio-elevenlabs` provider ([src/srstudio/provider.py](src/srstudio/provider.py),
console script `scene-render-provider-srstudio-elevenlabs`, or `SR_PROVIDER_SRSTUDIO_ELEVENLABS="python -m srstudio.provider"`).
`scene-render resolve` runs the provider for each stale item and pins the file's SHA-256 in the document; the
episode plays each pinned clip on its own `<audioTrack>` (`Episode.generated_audio()`, placements from the
`clips` of `dialogue.json`) and refuses a clip whose file no longer matches its pin. The provider parses the
resolve request strictly, needs `SRSTUDIO_ALLOW_CLOUD=1`, and writes nothing until ElevenLabs speech-to-text hears
the scripted line; a mismatch fails the item and asks for another `@seed`.

`srstudio.voice` treats the provider's output as untrusted. It parses dialogue, sound effects and speech-to-text
into typed values that reject unknown fields. It checks that the aligned characters spell the requested line,
that timings are finite and ordered, and that each clip is audible and as long as its alignment or its requested
length. Any violation raises `VoiceOutputError` and nothing is cached. Every uncached call is one request, never
retried; cached clips and transcripts are re-verified when read. `tests/test_voice.py`, `tests/test_provider.py`
and `tests/test_generated.py` feed malformed, truncated and adversarial responses and requests through each path.

**Safe area.** `EpisodeSpec(safe_area=srstudio.VERTICAL)` declares a `<safeArea>` with `enforce="error"` and makes it
the project's: the engine then fails validation and rendering when text or a caption leaves x 80–920, y 220–1420
(the engine's documented production box for 1080 × 1920; its platform presets are approximations). The engine does
not measure vector graphics, so `srstudio.layout.check_overlays(scene, ["squeak-loud", ...], engine=...)`
evaluates every frame, maps each drawn shape under the named groups through its world transform (exact bounds for
lines, quadratic and cubic curves and arcs, plus the stroke's reach) and reports every crossing; episode 06 runs it
with `strict=True` after `finish()`. Episodes 01–05 declare no safe area and are unchanged.

**Symbols.** `Canvas.symbol(id, draw)` defines a symbol once and `Canvas.instance(parent, id, symbol)` places it
(ids inside are scoped `instance/inner`); `office_wide`/`office_desk(instanced=True)` share the room and the desk
that way. The engine draws an instance into an offscreen at its frame size and scales that texture, so an instance
under a camera push-in renders soft; episode 06 pushes in on its wide angle and therefore keeps the inline drawing.

Parts added for it: the `office-desk` location (the wide office without the foreground candidate; `chair=False`
leaves the chair to the slot), the `chair-back` prop, the `squeak-mark` graphic, and `camera.spin` with
`camera.show_facing` (a turn about the vertical axis, one `|cos|` key per frame, the far side swapped in at each
edge-on moment).

## Ink episode: *The Router* (Ink 02)

[episodes/the_router.py](episodes/the_router.py) is the first original Ink episode: the internet is down and the router
would rather be rebooted by hand. Twenty takes as a shot sequence (desk, human close, router on its shelf, wide).

```bash
SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/the_router_audio.py PROJECT --font DIR   # voices, effects, timeline.json
python3 episodes/the_router.py PROJECT                                            # scene, SRT, ig.txt
scene-render encode PROJECT/the-router.scene.xml --out-dir OUT                    # OUT/renders/the-router.mp4
```

[episodes/the_router_audio.py](episodes/the_router_audio.py) makes one request per take through `srstudio.voice`
(typed parse, alignment spells the line, audible, right length), confirms each voice id is the premade voice it names,
and requires ElevenLabs speech-to-text to hear every line as scripted; three interjections were respelled until it did.
Each verified clip is trimmed, levelled and conformed to one 48 kHz mono WAV per take under `audio/`, checked to the
sample, and `timeline.json` lists the takes with words and character timings relative to the take. The key is read
from `ELEVENLABS_API_KEY` and never written. Parts added: `talking-router`, `ink-hand`, `ink-router-shot`,
`ink-router-wide`.

## Soft style episode: *Focus Mode* (07)

[episodes/focus_mode_audio.py](episodes/focus_mode_audio.py) declares seven sung lines and a record scratch as
`<generated>` ElevenLabs items. The engine resolves and pins them, speech-to-text must hear each line as written,
and each line is placed on its beat of `Groove(bpm=120)`. A line that would run into the next stops the build. The
script then synthesises the groove on the same grid: bars 0–5 play, bars 6–7 rest for the deadline, and the groove
creeps back in bars 8–9. [episodes/focus_mode.py](episodes/focus_mode.py) places Pip's cues on that grid (typing on
eighths, sway, wiggle, hands-behind-head groove, freeze, a planted-foot side-step out of frame) with eased
in-betweens (four drawings before a beat, two before an eighth; the scratch cuts without any), arcs on sitting and
standing, overshoot on dance landings and a contact shadow, and burns the lyrics at the top in Poppins inside
the `VERTICAL` safe area. The audio script also pins the caption face with `fonts.install`.

```bash
grep '^ELEVENLABS_API_KEY=' .env | cut -d= -f2- | SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/focus_mode_audio.py PROJECT --key-stdin
python3 episodes/focus_mode.py PROJECT && scene-render encode PROJECT/focus-mode.scene.xml --output main -o "$PWD/focus-mode.mp4"
```

## Soft style episode: *Camera Off* (08)

Both sung Soft episodes share one audio pipeline, `srstudio.song` ([src/srstudio/song.py](src/srstudio/song.py)). A `Song` lists its voices
by role, its `Line`s on (bar, beat), its `Effect`s, the groove `Section`s and where the last line must end. `main`
resolves and pins the items, checks each line with speech-to-text, places the lines and effects on the grid, renders
the groove, pins the caption font and writes `dialogue.json`. The refactor leaves episode 07's `dialogue.json`
byte-identical.

[episodes/camera_off_audio.py](episodes/camera_off_audio.py) is the second song. It has ten lines in two voices:
Pip (Will) sings, and the boss (Eric) talks from the call. It also has a mouse click, a call chime and a groove. Polite
hat and keys play in bars 0–2, the whole groove in bars 4–7, and the meeting music returns in bars 10–11. The music
rests while the camera goes off and while the boss asks.

In [episodes/camera_off.py](episodes/camera_off.py), Pip nods along on the beat (`nod`), clicks the camera off,
grooves, cheers (`cheer-a/b`) and waves at nobody (`wave-a/b`). He freezes on the chime, then scrambles back to type
on the eighths. A call badge over the laptop shows what the meeting sees: CAM ON, CAM OFF, SHARE?, SHARING. Boss lines
are captioned in blue. The video is 24.4 s.

```bash
grep '^ELEVENLABS_API_KEY=' .env | cut -d= -f2- | SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/camera_off_audio.py PROJECT --key-stdin
python3 episodes/camera_off.py PROJECT && scene-render encode PROJECT/camera-off.scene.xml --output main -o "$PWD/camera-off.mp4"
```

## Cel style package: *Work Training Be Like*

The fourth style comes from the silent package `mushroom-training-2.0.0` (a recreation of an Under Studio
workplace-training cartoon: a mushroom at a desk, teal caption boxes with hand lettering, a slow camera push).
[episodes/mushroom_training.py](episodes/mushroom_training.py) rebuilds its `scene.xml` element for element and its
SRT byte for byte from the package's own data: `script.json` (timed captions with their lettering boxes and glyph
paths), `assets/camera.json` and `assets/room-camera.json` (measured camera samples every 0.25 s), `assets/poses.json`
(which drawing is held when) and `assets/pose-NN.json` (the traced contours of each drawing). Nothing in the library
is specific to the mushroom: `cel.traced` holds any sheet of drawings, `cel.room` draws the set in any palette, and
`cel.lettering` draws any boxed glyph paths. The package's character art, dialogue and lettering are adapted from the
reference and remain their author's; the style, the loaders and the conventions are what the library keeps.

```bash
python3 episodes/mushroom_training.py /path/to/mushroom-training-2.0.0/project   # scene.xml, SRT, ig.txt, qa/
scene-render encode scene.xml -o /abs/path/mushroom-training.mp4                 # 1053 frames, 43.875 s, silent
```

### Narrated master

The silent build is the fidelity reference; a narrated master is the same scene with an ElevenLabs voice-over
(premade voice *Alice*) and keyboard foley on the mix. [episodes/mushroom_training_audio.py](episodes/mushroom_training_audio.py)
reads the caption script and speaks each caption through `srstudio.voice` (typed parse, alignment check,
speech-to-text that must hear the scripted words, voice id confirmed by name) at the narrator's own pace: nothing
is asked again faster and nothing is time-stretched. `srstudio.narration.plan_relaxed` places the clips: a line
that outlasts its caption spills into the next, which waits for it (a 40 ms guard, at most 0.9 s after its own
caption, then the spilling line is cut instead); a montage fragment ("He...", "Lunch...") starts on its caption
and is cut where the caption ends, which is the joke; and the project is extended past the last caption so the
last line is heard whole. Three one-word fragments and the spelt-out score are spoken in a form the recogniser
can confirm (`SPOKEN`). Under the voice, `srstudio.foley` synthesises two to four keystrokes wherever the
package's tracked hand (`assets/poses.json`, sampled every 0.25 s) moves more than 8 px while on the keyboard
(poses flagged `raised` are skipped), seeded so the bed is reproducible; the keystroke onsets are written to the
manifest (`effects[].taps`) and the drawn keyboard sinks 4 px on the same beats.
The clips are conformed to 48 kHz mono under `audio/` and listed in `narration.json` with their placement, the
typing bed (`effects`), the extended `duration` and SHA-256s; `mushroom_training.py --voice` checks the manifest
and the hashes, holds the last drawing and caption to the extended end, and presses the keyboard: a traced
drawing's ink is one compound path whose holes are the coloured areas, so no limb can move on its own, but
`cel.Pressed` splits every fill's subpaths inside the keyboard box into what sinks (filled regions with the
holes they carry) and what stays (the ink frame), so the keyboard face and its key rows dip inside the frame on
each keystroke. It adds one dialogue track per clip and one effects track at −8 dB, and encodes with AAC
mastered by the Cel style's mix. The cloud step needs `SRSTUDIO_ALLOW_CLOUD=1` and `ELEVENLABS_API_KEY`; cached takes cost nothing.

```bash
SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/mushroom_training_audio.py PROJECT   # audio/vo-NN.wav, narration.json
python3 episodes/mushroom_training.py PROJECT --voice                       # scene.xml with the 41 tracks
scene-render encode PROJECT/scene.xml -o /abs/path/mushroom-training.mp4    # h264 + aac, 43.875 s
```

## Signature

Every episode built with this library carries two recurring marks that sign the work. They are a convention
decided on 2026-10-28 ([docs/decisions/0001-signature.md](docs/decisions/0001-signature.md)) and implemented in
[src/srstudio/signature.py](src/srstudio/signature.py). Episode 06 (`five-years`) is the first signed episode; the
seven shipped packages predate the convention and build with `signature=False`.

| Mark | What it is | Where it appears |
|---|---|---|
| **Code** `SR-1028` | A short diegetic code, in the style of Pixar's A113, drawn as stroked glyph paths (no font asset, so it never trips the legibility check) in the location's own colour | Office: on the top sheet of the desk papers. Café: the last line of the menu board. Park: the corner of the park sign. Doodle: the model plate under the printer's output tray |
| **Prop** `signature-cactus` | A small potted cactus, redrawn in the language of each palette (gradients in `OFFICE`/`CAFE`, pen stroke in `MONO`), about 6 % of the frame height | Office: the far corner of the desk. Café: the shelf. Park: beside the bench. Doodle: on the desk, between the laptop and the edge of the frame |

Rules:

- Both marks are drawn by the location builders through `srstudio.signature.code(cv, parent, x, y, height, color=…)`
  and `srstudio.signature.cactus(cv, parent, x, y, scale)`, never by episode scripts, so a new location adds one call
  per mark and an episode cannot forget them. Both return `None` and draw nothing on an unsigned canvas.
- `EpisodeSpec.signature` controls both and defaults to `True`. The seven shipped episode scripts pass
  `signature=False`, because their packages predate the convention and the fidelity tests reproduce them element for
  element; re-signing them is a new package version, not a rebuild.
- The code is `EpisodeSpec.signature_code` (default `SR-1028`); changing it is a project-wide decision, not a
  per-episode one. A character without a glyph (`A–Z`, `0–9`, `-`, `.`, space) raises `ValueError` at build time.
  The groups are ided `sig-code`, `sig-cactus` (then `-2`, `-3`… per location) so `tests/test_signature.py` asserts
  both are present in every location of a signed scene, absent when `signature=False`, and that the `MONO` variant
  adds no gradient paints.
- The marks never carry story information, never sit inside a caption's box or on a face, and stay inside the
  engine's safe area. They must not trigger the legibility check: the code is at least the `minTextSize` of the
  episode's `<accessibility>` or is drawn as paths.

## Instagram captions

Every episode ships with an `ig.txt`: title, description, credit and hashtags, in that order, separated by blank
lines. The caption is data before it is text: `srstudio.social.InstagramPost` holds the four parts and refuses to
write when a limit is broken (title longer than the 125 characters the feed shows before folding, more than 30
hashtags, a malformed or duplicate hashtag, a caption over 2200 characters, an empty title or description). The
error is `InstagramPostError`, with every problem listed.

- The captions of the shipped episodes live in [episodes/instagram_posts.py](episodes/instagram_posts.py) as a
  `POSTS` map keyed by project slug; each episode script calls `ep.instagram(POSTS[slug])` before `ep.finish()`, so a
  build leaves `ig.txt` next to the scene. Recreations credit the original author in the caption itself.
- `python3 episodes/instagram_posts.py <folder>` writes one `<folder>/<video name>/ig.txt` per rendered video, for the
  videos that were encoded before the step existed.
- `tests/test_social.py` covers the layout, each limit's failure path, the episode hook and every shipped post.

## Verification

- `tests/test_build.py` builds an office and a café episode from a synthetic project and asserts the SDK, the XSD and
  the Schematron report nothing; it also asserts `finish()` refuses a document with findings.
- `tests/test_ink_layout.py` does the same for the square Ink style from a synthetic `timeline.json`, and for *The
  Router*: the LED chase and voice marks, the power states, the blackout, the hand's three actions, the shelf shots
  with their signature marks, and a ten-take build through `router_scene`; `tests/test_the_router.py` covers the
  audio step's checks (script shape, word and phone timings against the trim, the schedule, the conform to the
  sample, the voice-name check) with mismatched, cut and malformed inputs.
- `tests/test_styles.py` asserts what each style decides, that an explicit field wins, that a foreign palette is
  refused, that a silent style needs no mouth model, and that the registry and the CLI know the style of every part.
- `tests/test_cel.py` covers the Cel style (silent, font-less, one id counter), the caption-script timeline, every
  loader with malformed camera, run, drawing and caption files, the room camera compensation, the drawing
  conventions (even-odd paths, radius-less rects, five-decimal keys held to the end) and a silent build with no
  `<assets>` that the SDK and the engine validate, the tracked-point loader with bad samples and the pressed
  keyboard (subpath split by nesting depth so holes travel with their shape, press keys on the composition clock, a
  plain drawing when nothing is struck, errors for relative paths, bad boxes and an empty box).
  `tests/test_narration.py` covers the narration step's slots, bounded speed-up, placement rules (lead, tempo,
  cut), look-ahead plan, the relaxed plan (natural pace, spill, bounded lag, montage cut, extended duration),
  tempo conform and the manifest check (items, optional `lag`, `effects`, `duration`) with malformed, tampered
  and missing inputs; `tests/test_mushroom_training_audio.py` pins the script to the library steps, the natural
  speed and the respellings; `tests/test_foley.py` covers the keystroke bed (bursts from motion, determinism,
  peak, bounds, the written file).
- `tests/test_signature.py` asserts the two [Signature](#signature) marks are in every location of a signed office
  episode, absent from an unsigned one, typed on a code without glyphs, and gradient-free in the `MONO` palette.
- `tests/test_layout.py` covers safe-area validation, exact path bounds for every SVG command, the overlay check
  against the engine (inside, crossing, hidden, rotated, instanced) and every malformed-input path; `tests/test_symbols.py`
  asserts instanced office angles draw each shape with the same world transform as the inline drawing.
- `tests/test_soft.py` covers the Soft style and palette, top captions, stroke outlines, interpolation and placement,
  the pose sheet, the two-pass silhouette, in-between drawings, rotation-preserving turns, arcs, planted feet,
  overshoot and settle, the cheer, wave and seated-nod poses, that no front arm covers the face in any pose or in-between, every refused cue, the sung
  mouth track, the keyed rig and contact shadow and, on the engine, that exactly one eyes and one mouth of Pip are
  visible at each frame, the seated legs reading as two, the looks (Bo's ids, fills and hairline, Juno's and
  Remy's shade, the shade crescent's geometry, lashes on every eye and catch-lights only on pupils, Pip and Bo
  drawing no polish, the whole cast in one scene without an id clash) and the soft home (the hip on the cushion, the soles and the sofa's front on one floor,
  the lounging hands on the lap, a seated character between the seat and the near arm);
  `tests/test_audio.py` asserts `ep.audio()` builds each source's mix exactly as the explicit calls do, the style's
  master levels, verified narration cues (a tampered clip is refused) and the refused options;
  `tests/test_music.py` covers the beat grid, deterministic and peak-levelled rendering, silent rests, beat-exact
  kicks and every refused setting; `tests/test_fonts.py` covers the request, every refused stylesheet, the font-file
  reader on damaged files, install with offline reuse, a tampered pin, wrong family or weight (nothing written),
  licence fallback, the size limit and the CLI, against a fake fetcher with a real TrueType file.
- Quality gates (`pyproject.toml`): `ruff format --check`, `ruff check`, `mypy src`, and branch coverage of at least 80 %.
- `tests/test_fidelity.py` rebuilds the seven shipped episodes from their extracted packages
  (`SRSTUDIO_PACKAGES=/path/to/extracted` with `<name>-<version>/project` inside) and compares them with the shipped
  `.scene.xml` using [tools/compare_scene.py](tools/compare_scene.py): every element, attribute and text in document
  order, numbers rounded to five decimals, `metadata` ignored, `animate`/`expression` children compared after their
  sibling shapes (the engine evaluates them by property, so their position among shapes does not change the picture).

Rendering needs the scene-render engine (`scene-render encode <slug>.scene.xml`); it is not part of this package.

## Layout

```
src/srstudio/   canvas, styles, timeline, soundtrack, rig, cast, props, locations, graphics, camera, ink, subtitles,
                blob, music, fonts, episode, registry, sample, voice, provider, generated, layout, cli
episodes/       the seven shipped episodes on the library, episodes 06 and 07 with their audio scripts (+ _common.py)
examples/       new_episode.py — new prop + new location + new episode in 90 lines
tests/          unit, integration and fidelity tests
tools/          compare_scene.py
```

MIT, like sr-core.
