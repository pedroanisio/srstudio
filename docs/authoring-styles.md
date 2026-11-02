---
updated-by: OpenAI Codex (GPT-6)
---

# Choose a style and finish a scene

[Library README](../README.md) · [Authoring task index](authoring-reference.md)

Bind an `EpisodeSpec` to a declared style before choosing its parts, timeline and caption inputs. Use the comparison below for clocks and palettes; an incompatible palette raises `StyleError`. [Timeline examples](authoring-timelines.md) and [input repair](authoring-diagnostics.md) cover validation before drawing.

Run commands from the srstudio repository root.

## Styles

A **style** is what an episode looks like before a single part is placed, and it is a value:
`srstudio.styles.Style` holds the frame and rate, the clock, the input file, the caption font, the palettes the style
is drawn in (with a mouth model per palette), the id scheme, accessibility defaults and the modules that hold its
parts. `EpisodeSpec(style=…)` resolves every field the episode does not set; an explicit field still wins; a palette
the style is not drawn in is a `StyleError`. The names and the reasoning are in
[docs/decisions/0002-style-names.md](../docs/decisions/0002-style-names.md),
[docs/decisions/0003-soft-style.md](../docs/decisions/0003-soft-style.md),
[docs/decisions/0004-cel-style.md](../docs/decisions/0004-cel-style.md),
[docs/decisions/0006-stick-style.md](../docs/decisions/0006-stick-style.md) and
[docs/decisions/0010-toon-style.md](../docs/decisions/0010-toon-style.md),
[docs/decisions/0025-saga-style.md](../docs/decisions/0025-saga-style.md),
[docs/decisions/0030-gloss-style.md](../docs/decisions/0030-gloss-style.md) and
[docs/decisions/0026-collage-style.md](../docs/decisions/0026-collage-style.md); `srstudio styles` lists
all nine. The table compares the first seven; [Collage](episode-history.md#collage-style-grown-ups-losing-to-brainrot) and
[Gloss](episode-history.md#gloss-style-a-cheerful-forever-plaza-in-nine-episodes-g1g9)
are described in the episode history.

| | **Cutout** — `CUTOUT` (default) | **Ink** — `INK` | **Soft** — `SOFT` | **Cel** — `CEL` | **Stick** — `STICK` | **Toon** — `TOON` | **Saga** — `SAGA` |
|---|---|---|---|---|---|---|---|
| Look | Flat vector shapes, soft gradients, bold outlines, like paper cut-outs | Pen stroke, one ink and one grey on white paper | Round white blob characters, one dark outline, flat warm stage, pose-to-pose | Traced, filled drawings with no outline, held per run under a measured camera push; silent | Stick figures in heavy ink traced at 12 fps, on painted, flat-shaded sets; dancers with badge heads | Flat cartoon in heavy ink on a gradient room: a cat whose expression swaps per cue and a brush-drawn, lip-synced cast, each phrase in a white pill; narrated portrait recreations and sketches | Space-opera parody in heavy ink: a lit, shaded cast on sets whose far plane is out of focus, glowing holograms sized to their words, one grade (bloom, vignette, grain) over every shot |
| Palettes | `OFFICE` (cool, stage `#D5DFDF`), `CAFE` (warm, stage `#F0DDC0`) | `MONO` (stage `#FFFFFF`) | `WARM` (stage `#F3DFCF`) | `LINEN` (stage `#c5bbb0`, shade = the lettering box teal) | `DAYLIGHT` (stage `#bda77a`, shade = the sets' brown line `#665541`) | `PEACH` (stage `#f8ead9`, shade = the cat's blue `#5bb7db`) | `VOID` (stage deep space, paper warm, shade gold) |
| Frame | 1080×1920 portrait, 30 fps | 1080×1080 square, 24 fps | 1080×1920 portrait, 30 fps | 1080×1920 portrait, 24 fps | 1080×1920 portrait, 24 fps | 1080×1920 portrait, 24 fps | 1080×1920 portrait, 24 fps |
| Clock | one composition on the project clock; camera setups gated by hold keys | a `<sequence>` of shots, each as long as its take; animations on the shot clock | one composition; each look of a character gated by hold keys on a beat grid (`music.Groove`) | one composition; the world group carries the measured camera (`cel.world`), the room its own inside it (`cel.compensate`); linear keys on the local clock, held to the end | one composition; each traced pose a group alive from its start to its end, each set a group per shot | one composition; each pose a group alive from its start to its end, the typing forearm keyed on the composition clock so it dips on the foley's keystrokes | a `<sequence>` of shots, each as long as its take; animations on the shot clock |
| Input | `dialogue.json` + one mixed `assets/dialogue.wav` | `timeline.json` with takes (words, character timestamps, one audio file per take) | `dialogue.json` with pinned generated clips + `assets/groove.wav` from `music.render` | `script.json`, a list of timed captions; the measured camera, pose runs and drawings are read from `assets/` (`cel.load_*`) | `script.json`, timed captions with a size; poses, icons, lettering and foliage are read from `assets/` (`stick.load_*`) | `script.json`, timed captions, and `assets/poses.json` (eyes, mouth, arms per run), both derived from the episode's data module (`toon.load_*`) | `timeline.json` with takes from `srstudio.takes` (words, character timestamps, one audio file per take) and the music bed |
| Mouths | five shapes from RMS amplitude windows (`OFFICE_MOUTH`, `CAFE_MOUTH`, chosen by palette) | five poses from character timestamps (`INK_MOUTH`, `phoneme_states`) | `SOFT_MOUTH` amplitude states drive the `sing` mouth of a cue | none: the style is silent and `mouth_style` resolves to `None` | none: `mouth_style` resolves to `None`; voice is narration over the captions | none: `mouth_style` resolves to `None`; the mouth is one of six drawn shapes per pose | visemes from character timestamps (`lipsync.SPEECH_MOUTH`); masked characters talk with a light |
| Captions | DejaVu Sans Bold, bottom captions with highlighted spans | Patrick Hand, top captions paged from word timings (`subtitles.chunk_words`), plus an SRT | Poppins Bold from Google Fonts (`srstudio fonts add`), dark text with a white outline at the top (`captions(color=, shadow=None)`) | traced lettering (`cel.lettering`: boxes in the shade, glyphs as white paths), no font asset, plus an SRT | Inter Bold, white with an ink outline outside, one line per cue (`stick.captions`); hook and headline are traced lettering; plus an SRT | Comic Neue Bold Italic from Google Fonts (pinned), ink text centred in a white pill whose width is measured from the font file (`fonts.text_width`), plus an SRT | Space Grotesk 700 from Google Fonts (pinned); the engine's native karaoke captions, a long line split at words (`native.cues_from_takes`) |
| Audio | `ep.audio()` (one mixed file) | `ep.audio(take=…)` (one file per take; master −14 LUFS) | `ep.audio(extra=[("groove", …, {"role": "music"})])` (pinned clips) | none (no `<assets>`, no `<audioMix>`); `ep.audio(narration=…)` for a narrated master | none in the picture; `srstudio.dub` adds a voice-over and a music bed to the built scene | none in the silent master; `ep.audio(narration=…)` plus one effects track per bed (typing, camera click) in the narrated one | `ep.audio(take=…, duck=…)`: one file per take panned by speaker, effects, the music bed ducked under lines |
| Ids | `path-0001` | `shared_counter()` → `g1, p2, e3` | `path-0001`; looks are `<character>-<pose>-<digest>` | `flat_counter("v")` → `v1, v2, v3` for every node | `flat_counter("n")` → `n1, n2, n3` for every node | `flat_counter("k")` → `k1, k2, k3` for every node | `flat_counter("s")` → `s1, s2, s3` for every node |
| Parts | `cast`, `locations`, `props`, `graphics`, `camera` | `ink`, `ink_captcha`, `ink_doorbell`, `ink_meter`, `ink_phone`, `ink_vacuum`, `subtitles` | `blob`, `soft_props`, `soft_sets` | `cel` | `stick`, `stick_airport`, `stick_car`, `stick_door`, `stick_flat`, `stick_gym`, `stick_home`, `stick_office`, `stick_school`, `stick_shop`, `stick_street`, `stick_windshield` (the reel builder is `stick_reel`) | `toon`, `toon_cast`, `toon_dinner`, `toon_everyday`, `toon_bento`, `toon_critters`, `toon_inked`, `toon_lyra`, `toon_orbit`, `toon_plate`, `toon_props`, `toon_rooms`, `toon_sets`, `toon_wear` | `saga`, `saga_sets` (the reel builder is `saga_reel`) |

The parts of one style are usable in the other (they draw with the canvas's ink, paper and shade), and the signature
marks adapt to the palette, so `srstudio catalog --style ink` lists Ink's own parts plus the shared ones.
`Timeline.load` picks the input format by content (`phrases`, `items`, or a list of captions). It raises
`TimelineError` for invalid ranges or unordered cuts. Shot-sequence takes must be contiguous from zero
(within one microsecond of recording roundoff); include pauses in a take's duration. Word and character
times must stay within their take. Frame-rounded trailing silence is allowed, and validation never retimes inputs.
A new style is a `Style` value, usually
`dataclasses.replace` of an existing one, plus a module of parts named in its `parts` (see `ink.py`: ~40 lines of
drawing conventions before the first character, or `blob.py`: a pose sheet); nothing in `Episode` is specific to a
style.

### Soft room framing and timed props

`soft_sets.Shot(time, scale, x, y)` centers the supplied room point `(x, y)`
at frame `(540, 960)`. One shot applies a static transform; multiple shots
hold each framing until the next cut. The park, bedroom, playroom and front
room apply framing to their room and cast while keeping their foreground
planter, nightstand, toy crate or shelf fixed. The default shot preserves the
original drawing.

Shot times begin at zero and increase strictly. Coordinates and positive
scales must be finite; derived transforms must remain finite, and cut times
must remain distinct after rounding to six decimal places. Invalid framing
raises `SoftSetError` before the builder changes the scene or calls a slot,
so a corrected retry can use the same canvas.

The front room's `wedged` intervals control when the sofa appears in the
hallway. Intervals are ordered and nonoverlapping, include their start and
exclude their end. These opacity gates and framing cuts follow
`Canvas.local_time`: composition time by default, sequence-shot time when
enabled. A local interval must be expressed relative to that shot's start.

<!-- soft-room-framing:start -->
```python
from sr_core.scene import Scene
from srstudio import Canvas, WARM, soft_front
from srstudio.soft_sets import Shot

scene = Scene(version='auto')
scene.add_project(width=1080, height=1920, fps='30', duration=6)
cv = Canvas(scene, WARM, font_asset=None)
soft_front.front_room(
    cv, cv.comp,
    shots=(Shot(0, 1.4, 300, 900),),
    wedged=((1, 2), (4, 5)),
    cast=lambda parent: cv.group(parent, 'cast-origin', x=300, y=900),
)
room = next(g for g in scene.iter('group') if g.id == 'soft-front-room-room')
assert (room.x, room.y, room.scaleX, room.scaleY) == (120, -300, 1.4, 1.4)
```
<!-- soft-room-framing:end -->

### Lip sync

`Performance.mouth` and `Episode.perform(mouth=...)` use `(project second, pose)` sequences. The base actor's
vocabulary is `srstudio.rig.MOUTHS`: `rest`, `round`, `open`, `small`, `smile`. In particular, use `rest`, not
the `closed` state from other styles. Actors reject unknown names, malformed pairs and nonfinite, negative or
decreasing times with `RigError` before drawing. Custom actors can extend `Actor.mouth_poses` alongside their
`draw_mouths()` implementation; retain `rest` for the default performance.

`srstudio.lipsync` turns what is said into mouth poses ([ADR 0019](../docs/decisions/0019-lip-sync.md)). The shipped
mouths stay the default, so delivered episodes rebuild unchanged. New episodes opt in:

```python
from dataclasses import replace
from srstudio import OFFICE_MOUTH, SPEECH_MOUTH, ink, sketch

ink.mouth(cv, g, take, style=SPEECH_MOUTH)                    # timestamped takes (Ink, Toon sketches)
sketch.record(sk, root, client, key=key, mouth=SPEECH_MOUTH)
ep.mouth("candidate", style=replace(OFFICE_MOUTH, letters=True))  # amplitude mouths that know the line's text
```

- `SPEECH_MOUTH` reads English spelling (*ph* is an f, the *h* of *th*/*sh*/*ch*/*wh* holds the consonant, *w* and
  *qu* round, a silent final *e* or *gh* holds the pose before it), closes the mouth on every *b*, *m* and *p* even
  when the sound falls between two samples, shows each sound 0.04 s early, and keeps the mouth open over a pause
  between words shorter than 0.12 s.
- `PhonemeStyle(first_sound=True)`, off by default, opens a take the trim cut on the sound due at its first second.
  Samples run on the clock of the file, so a trim drops the sample at its second 0 and the mouth would otherwise stay
  shut until the next one, about 0.08 s into the first sound.
- `MouthStyle(letters=True)` spreads the line's letters in order over the frames where it is voiced (a vowel weighs
  twice a consonant). The letters choose round, closed or open; the amplitude still chooses how open. Without it,
  the round mouth comes from a clock pattern, unrelated to the words.
- `srstudio lipsync TIMELINE...` scores the shipped and the speech mouth over the takes of timelines with character
  timestamps: bilabials closed, word joins snapped shut, and pose changes a second.
- `srstudio lip-proof PROJECT --master MP4 --out DIR` picks mid-word instants across a recorded reel, prints the pose
  the mouth track holds at each one, names any vowel on a shut mouth, and pulls those frames from the master to compare
  by eye.

### Engine-native captions, transitions, effects and text animators

`srstudio.native` writes the scene-render elements the library used to draw by hand
([ADR 0021](../docs/decisions/0021-engine-native-features.md); the map of adopted features is
[docs/engine-features.json](../docs/engine-features.json)). All of it is opt-in:

```python
from srstudio import native
from srstudio.native import CaptionLook

ep.native_captions()                                     # the takes' words, sung word by word, burned in
ep.native_captions(look=CaptionLook(preset="pop", upper=True, max_chars=18), mode="both")  # + a WebVTT sidecar
native.transition(shots, "shot-01", "shot-02", "whip-pan", duration=0.4)
cv.apply(layer, cv.effect("lift", "drop-shadow", offsetY=8))
cv.animate_text(layer, "pop")
```

- A caption track is centred on the safe area with its last line on the region's bottom edge. With the episode
  font, every wrapped line is measured against the safe width, so a line too wide is refused before the render.
  Capitals are wider: an uppercase look needs `max_chars` of about 18 at 53 px.
- `mode="sidecar"` or `"both"` makes `scene-render encode` write `<video stem>.<track>.<language>.vtt` beside the video.
- `CaptionLook(min_last=2, min_seconds=0.84)` makes captions readable
  ([ADR 0031](../docs/decisions/0031-shared-look-and-caption-primitives.md)). A cue whose last line would hold a lone
  word is split after a clause end, else where its halves balance. Each cue is held into the silence after it
  for `min_seconds` (the engine's minimum is 0.8333 s), and a split that would show a half more briefly is not
  made. A long take's last cue that is too small to read is re-cut with the one before it. The house look
  leaves both off, so delivered videos rebuild unchanged.
- Cues out of order or overlapping, words outside their cue, and a transition between shots that are not
  neighbours (or longer than either shot) raise `NativeError`. An unknown preset or type raises the SDK's
  `SchemaValueError`.

### Finishing a style: `srstudio.look`

A style's finish is a handful of calls with its own numbers and id prefix, never a copy of another style's helpers
([ADR 0031](../docs/decisions/0031-shared-look-and-caption-primitives.md)):

```python
from srstudio import look

lines = look.wrap(font, text, 50, 640, max_lines=3)    # measured; look.FitError when it does not fit
far = look.depth(cv, g, "mystyle-depth", 3.0)          # the far plane, out of focus
look.pool(cv, g, "mystyle-pool", "#ffc870", 40, 1160, 1000, 260, opacity=0.3)
look.fade(cv, g, "mystyle-shade", "#3a1f5cb3", 1900, 1500, width=1080)
look.grade(cv, shot, "mystyle", {"bloom": dict(threshold=0.9, radius=28, intensity=0.5)})
```

Every file hash in the library is `srstudio.digest.sha256`.

### Staging and series: `srstudio.staging`, `srstudio.series`

A sequence style stages a recorded take timeline with `staging` (the checks, the camera `rig` of a `Move` and a
shake, `blackout`, `crossfades` into a closing card, and `close` for the transitions, captions and ducked mix),
and declares its episodes once as a `series.Series` (voices, settings, music bed, font, output, reel builder,
caption look). Each episode is a `Reel` subclass's instance; `series.record` records it and `series.build`
builds it ([ADR 0031](../docs/decisions/0031-shared-look-and-caption-primitives.md)). `episodes/_saga.py` is the
worked example.

`staging.freeze(shot)` preserves the shot's starting pose and leaves the scene unchanged on failure. Properties with
additive animation retain static one-key animations so the renderer can compose them with their base values.
Timed descendants retain their opening visibility throughout the frozen shot; the shot's own schedule is
preserved. Animation sampling respects `timeBase`: composition time zero, local time minus the node's start,
or that local time divided by the node's duration for normalized keys. An omitted normalized end uses project
duration; if neither is available, freezing is refused. A curve spanning the resulting freeze point without a
key there is refused unless that segment uses hold interpolation. Provide an explicit key at that point with
the intended opening value before freezing. Expressions and text animators are also refused; these failures
leave the scene unchanged.

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

### Cast cards: `srstudio.cast_card`

`srstudio cards FOLDER` writes one 1080×1920 PNG per character in `cast_card.CAST`: the approved drawing rendered
through the engine, a name, one line and the wordmark, in Fredoka 600 and DM Sans 700. `--only rex` narrows it. A
`Card` is typed data (name, line, drawing, `Pose`, `Frame`, backdrop). Before anything is written the card is
refused if the drawing is unknown or unapproved, the line reads as engagement bait, the letters leave the story safe
zone (no text in the top 250 px or the bottom 340 px, measured from the rendered letters), the figure is too small
to read, or the panel cuts a shape down to its tip: an island of ink resting on the panel's edge and under 24 px tall.
That last refusal is fixed by moving the `Frame`, never by painting over the tip or changing the drawing. Folders are
mode 700, files mode 600.

Who gets a card: a character is cast when the same name sits on the same drawing in five or more reels, in an everyday
world. Count from the releases and `srstudio usage`. A one-reel character is not cast, and sealed worlds such as Saga
and Gloss are not everyday life. Ava is the one exception, at four reels, because the Okayville request named her.
