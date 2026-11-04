---
updated-by: OpenAI Codex (GPT-6)
---

# Reusable drawings and part versions

[Library README](../README.md) · [Authoring task index](authoring-reference.md)

Use this directory of drawing families after [inspecting a contract](authoring-discovery.md). A family description does not replace its supported units, clocks and runtime bindings. Select an approved version through `srstudio.parts`; a proposed or changed drawing requires the explicit recovery described under part versions.

Run commands from the srstudio repository root.

## Rigid proxies and deterministic tone conversion

`proxy.Recipe` names each modeled part's four tones, from shade to highlight.
Use `soft_edge=0` for hard bands; equality with a threshold selects the higher
tone. Positive widths retain the smooth transition between neighboring tones.
Widths whose derived transition intervals overflow are refused before rendering;
very small representable widths saturate without overflowing the interpolation.

```python
from srstudio import proxy

recipe = proxy.Recipe(
    tones={"body": ("#102030", "#506070", "#90A0B0", "#D0E0F0")},
    soft_edge=0,
    grain_seed=7,
    oversample=2,
)
```

Keep `grain_seed` a nonnegative integer for deterministic ink. `None`, booleans,
strings and fractional seeds are refused when the recipe is constructed. A grain
grid with no variance contributes zero wander, including the smallest 2 × 2 view
at one-times sampling. Empty `quiet` families, non-`Ink` records and boolean
`oversample` values are also refused before rendering. These errors expose
`proxy.recipe.<field>` codes and `recipe.<field>` paths through `ProxyError.to_dict()`.

`proxy.layers` uses a light pass and a part-ID pass for a stationary view. A
recipe with `under` parts needs another pair of passes for those parts alone.
Use [render sessions](authoring-benchmark.md#bound-a-plate-authoring-operation)
to bound and count those attempts. The [composition guide](composition-preflight.md)
tracks the scene-plan adapters and their supported capabilities.

## The parts

Give repeated graphics distinct `id=` values. Each custom instance namespaces its text assets and layers as
`<instance id>-<text id>`; the default instance retains the original IDs. A part named with an explicit `prefix=`
or `text_id=` keeps that name on any instance, so give each such instance its own prefix.

`Canvas.gate` merges overlapping and touching visibility spans, independent of their input order; empty spans
draw nothing, and reversed, negative or nonfinite spans are refused before adding animation. Named linear and
radial gradients reuse identical declarations and raise `NativeError` for conflicting types, stops, coordinates,
units or interpolation spaces. Stick's user-space gradients use the same checks.

`srstudio catalog` lists them; `srstudio catalog --json` is machine-readable, and `--usage REPORT` adds the episodes
that use each part, from the report below.

Which episodes use a part is measured, not declared: `srstudio usage`
rebuilds every episode project on a copy and records each registered part its build calls
([ADR 0017](../docs/decisions/0017-measured-part-usage.md)). It prints the used and unused parts per kind and writes the
report that `srstudio page --usage` reads:

Registered builders, rig drawings and Canvas ID allocation emit explicit `drawing_events` notifications.
Keep the callable returned by `register`; it preserves signatures and function kind. Classes retain their
identity, with instrumentation on their own methods and preserved static/class descriptors. Shared performers
use `with drawing_events.drawing(owner):`, where `owner` is their registered callable or rig. Callable identity
prevents a retired builder from claiming the replacement registration. Explicit registered-name strings are
also accepted when attribution to that current name is intentional; unknown strings raise `UsageError`.

`usage.trace()` records parts and IDs allocated by `cv.uid()`, including custom namers. Nested scopes count
every part and assign IDs to the outermost character in that execution context. Independent coroutine tasks
keep separate figure ownership. A child task created inside a character scope inherits that ownership; await
its drawing before leaving the enclosing scope. Tracing does not make concurrent mutation of one Canvas safe.

Generators and async generators attribute each resume, including send, throw and close; yielded caller code
is outside their scope. Coroutines attribute awaited execution and cancellation cleanup. Merely creating a
deferred object is not usage. Join all drawing tasks before a trace closes: copied contexts cannot append to a
closed observer. `drawing_events.observe(callback)` receives begin/ID/end events; end events include
`successful`. Failed drawing still records attempted usage and allocated IDs, while `usage.recorded()` refuses
to publish records for a failed build. Nested traces both observe inner work. Existing profilers remain active;
there is no source, frame-local, closure or delegate inference.

```bash
srstudio usage --episodes ../generated/episodes --packages ../generated/packages --scripts episodes \
    --work _tmp/usage-work --out ../generated/catalog/usage.json
```

A project with a `voiced/` recording whose script takes `--voice` is built from it, as its delivered master was;
`--arg SLUG=OPTION` passes any other option to one episode's script. A project with no script in `--scripts` is listed
as not measured. So is an episode whose build fails: the others still run, the report is written, the failure is
printed and the exit code is 1; when every build fails nothing is written. `--skip SLUG` leaves out a project that cannot
build yet (one still in progress, with no `timeline.json`): it is reported as not measured, and a skip that names no
project is refused.

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
  walks with `walk-a`, `stride`, `walk-b`, `stand`). The expression changes when the pose lands. `blob.cue(when,
  pose, spot, scale=, ease=)` places a cue at a spot in output pixels, and `blob.settle(cues, fps)` caps each ease so
  no move starts before the previous pose has landed
  ([docs/decisions/0016-episode-helpers-in-the-library.md](../docs/decisions/0016-episode-helpers-in-the-library.md)). Limb paths are
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
  before ([ADR 0007](../docs/decisions/0007-polished-looks.md)). A seated `lounge`
  pose rests both hands on the near thigh, for the sofa.
  (`srstudio.cel`): `traced` (`cel-traced`): a traced character as a sheet of filled drawings, one held per run of
  the pose timeline; drawings and runs are data (`cel.load_drawings`, `cel.load_runs`), parsed and refused when
  malformed (`cel.CelDataError`).
- **Locations** (`srstudio.locations`): `office_wide(at_desk=)`, `office_reverse(in_chair=)`,
  `cafe(behind_counter=, at_counter=, on_counter=)`, `park(on_bench=, beside_bench=)`. Each takes `shots=` and gates its
  root group before drawing, so new locations should do the same (see `examples/new_episode.py`). `park(sign_lettering=False)`
  keeps the sign's board and code but drops its lettering, for a framing that crops the sign: SA01 measures text off frame too. Two polished rooms
  add window and lamp light as a `-light` glaze group: `conference_room(behind_table=, on_table=, rising=,
  speaker_talk=)` (blinds, whiteboard, speakerphone, walnut table; `speaker_talk` spans light the speakerphone's ring
  while a caller speaks, as `props.speakerphone(talk=)` does) and `reception(behind_desk=, on_desk=, at_desk=)` (lit slat wall, backlit
  logo, globe pendants, fluted counter, reflective floor); `CONFERENCE_SEAT`, `RECEPTION_CLERK` and `RECEPTION_VISITOR`
  are the tested placements ([ADR 0011](../docs/decisions/0011-polished-cutout-rooms.md)).
  (`srstudio.ink`): the shots `desk_shot`, `closeup`, `printer_shot`, `wide_shot`, `router_shot` (the router on its
  wall shelf, `close=True` fills the frame, `hand_action="reach"|"press"|"leave"` brings in the `ink-hand` prop) and
  `router_wide`, each drawn into a take's group; `router_scene(cv, g, take, **beats)` picks the shot a take names.
  (`srstudio.blob`): `office` (`soft-office`: desk, laptop and slatted chair in a 3/4 view from above, wood outlined
  in `WOOD_LINE`; drawn in output pixels for Pip at `SCALE` and sized to him: a seated pose's hands land on
  `blob.keyboard()` and its soles on `SEATED_FLOOR`, which a test asserts; `SEAT` and `FLOOR` place a sitting or
  standing pose). `home` (`soft-home`): the living room in the same 3/4 view, a fabric `sofa` (`soft-sofa`) facing
  left on a rug, a floor lamp and a side table with the cactus; the sofa shares the chair's axes and seat height, so
  a seated pose at `SOFA_SEAT` has its hip on `blob.sofa_seat()` and its soles on `SOFA_FLOOR` (tested), and
  `on_sofa=` seats a character between the seat and the near arm; `lamp_talk=` lights the floor lamp while it speaks, and
  `LAMP_SHADE` is its shade's point. `meeting_room` (`soft-meeting-room`) and
  `break_room` (`soft-break-room`) are polished rooms on a shared shell (`room_point`, walls, plank or tile floor,
  baseboards, a `-light` glaze group): a walnut table with a swivel chair (`soft-swivel-chair`), a wall screen and a
  clock; mint cabinets, a coffee machine (`soft-coffee-machine`), a fridge (`soft-fridge`), a pendant lamp and a stool
  (`soft-stool`). Both seats hold `SEAT`, and wall decor stays below `CAPTION_FLOOR` (tested;
  [ADR 0008](../docs/decisions/0008-polished-rooms.md)).
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
- **Camera** (`srstudio.camera`): `anchor`, `push_in`, `zoom_holds`, `reframe` (hard cuts by hold keys on one group),
  `crash_zoom` (a snap onto the subject within `SNAP` seconds, optional snap back; returns the cue for
  `foley.write_whoosh`, a seeded noise sweep that swells into the landing).
- **Craft report** (`srstudio.craft`, [ADR 0023](../docs/decisions/0023-comic-craft-measured.md)): `srstudio craft
  PROJECT... --renders ../generated/renders` lists each episode's punch-ins, crash zooms and pushes (camera or gag)
  and the pauses between its lines, with the rendered level inside each one (quiet or filled); `--json` for the data.
- **Mouth styles** (`srstudio.soundtrack`): `OFFICE_MOUTH`, `CAFE_MOUTH`; `dataclasses.replace(CAFE_MOUTH, idle="smile")`
  keeps a character smiling between lines.

### Toon coworkers: brush-drawn characters

[src/srstudio/brush.py](../src/srstudio/brush.py) is a hand-inked brush for characters drawn in code: `spline`
(Catmull-Rom through the points, open or closed), `stroke` (a band whose width follows a `Pressure` profile with a
swell and a slow wobble, round caps), `outline` (a closed fill) and `rim` (the fill pushed outward by the ink
weight, whichever way the points wind), `inked` (a rim pressed by a `Hand`: heavier where the outline turns from
the light, thin at sharp tips, uneven along the way in the shape of a `Wave`, with a dry brush's fine grit when the
hand is `ragged`),
`broken` (that band in seeded pieces with tapered gaps and nicks), `wobble` (a contour's small, repeatable hand
drift, with per-sample `weights`), `facing` (a contour's samples with their outward normals), `crescent` (a shade
swelling inside an edge), `lump` (a seeded one-off blob where an ellipse would look digital), `ellipse`, and
`shift`/`rotate`/`flip`/`bounds`. Every result is a closed cubic `Shape` the Toon parts fill flat
with `toon.flat`, so a figure is a stack of filled layers (ink rim, coat, markings, limbs, face) and never a stroked
path. [src/srstudio/toon_cast.py](../src/srstudio/toon_cast.py) draws two
coworkers for the cat's desk with the cat's vocabulary and contract: `toon-dog` (orange coat, drop ears, a light
muzzle and a black nose) and `toon-frog` (green, a pale belly, three spots, eyes on the bumps of its head, a wide
mouth). A `Look` holds the coat colours, the silhouette, the eye and mouth placement and the markings;
`figure_shapes(look, eyes, mouth, arms, frame)` returns the layers for one expression (every `EYES` × `MOUTHS` ×
`ARMS` is tested to stay inside the character's corner), and `dog`/`frog` take the same poses, duration and
keystrokes as `toon.cat`, plus `enter=` for a character that comes on later. Rex (the dog) and Fern (the frog) are
the cast of the [first Toon sketches](#toon-sketches-the-report-t3-logo-bigger-t4-and-quick-question-t5).

Two more characters carry opt-in polish fields on their `Look` ([docs/decisions/0020-toon-lip-synced-cast.md](decisions/0020-toon-lip-synced-cast.md)):
`toon-bear` (brown coat, round ears lined in cream, a pale muzzle and belly) and `toon-rabbit` (pale coat, tall
ears lined in pink, front teeth and whiskers). Both have eyebrows that follow the eye kind (raised for a shock,
tilted down in a frown), a highlight on each pupil, blushing cheeks, and blinks at their own pace (`blink`
seconds, `blink_times`, a lid over each eye for `BLINK_HOLD`). The four brush-drawn characters take `mouths=`, a
viseme track of `(second, viseme)` with `VISEMES` closed, open, round and teeth. Within each pose run the mouth is
one layer per viseme heard, keyed on opacity on the composition clock (`viseme_keys`); "closed" shows the pose's
own mouth, so a character that is not speaking keeps its expression. `figure_layers` splits a figure into the
layers under the mouth, the mouth and the layers over it, so typing frames and stickers are drawn once per run.

Three more take the same contract ([docs/decisions/0041-toon-cast-expressions-and-wear.md](decisions/0041-toon-cast-expressions-and-wear.md)):
`toon-fox` (slender, tall splayed ears, white cheek tufts, dark paws), `toon-raccoon` (stout, a bandit mask,
rounded ears, cheek ruffs, dark gloves) and `toon-hedgehog` (small, a crest of spines drawn as the look's `mantle`).
The vocabulary also has eyes and mouths past the traced set: `roll`, `teary`, `wince` and `hearts` eyes, and
`grimace`, `frown`, `tongue` and `kiss` mouths. Every brush character draws them; the traced cat refuses them by
name (`toon.TRACED_EYES`, `TRACED_MOUTHS`). Any character, the cat included, can wear `toon.WEAR` per pose
(`"wear": ["glasses", "sweat", "flush"]` in a poses file, `wear=` on a sketch `Beat`), drawn by
[src/srstudio/toon_wear.py](../src/srstudio/toon_wear.py) about the character's face; on a head its drawing turns
(`toon_cast.Drawing.tilt`), the items turn with it.

Fox version 2, `toon-fox@2` ([src/srstudio/toon_inked.py](../src/srstudio/toon_inked.py),
[docs/decisions/0044-inked-toon-characters.md](decisions/0044-inked-toon-characters.md)), is the fox drawn
again the way the traced cat is drawn. Its outlines are placed by hand, unmirrored, and drift like a
hand following them (`brush.wobble`). Every ink band is pressed: heavier where the form turns from the light, thin
at the tips, with a dry brush's grit, and broken in three to five seeded places with a nick between
(`brush.broken`, a ragged `brush.Hand`). A few lumpy open strokes stay inside: the cheeks, the tail tip, a fluff in
each ear, the philtrum and the paw creases. Like the cat's, its body is one contour from the ruff into the
shoulders and flanks, and its arms leave the body inside the shoulder, slim there and widest at the forearm and
paw, inked only where they overlap the body or leave it. A darker coat tone shades the flank and the tail, and turns the head
with a crescent that starts and ends on the outline and swells into the cheek. The head tilts about the neck, the
face sits off its midline with the far eye smaller, and what it wears turns with the head. Its almond eyes with an
iris, its muzzle mouths and its visemes are drawn for its face: every `EYES` and `MOUTHS` kind is its own drawing,
and every eye a one-off of seeded lumps (`brush.lump`), never a perfect ellipse. A `Look` takes these through its `drawing` (a `toon_cast.Drawing`), so
the inked fox keeps the whole contract, and a sketch casts it as `"fox"`, at the version its release pins. Looks
without a drawing are drawn exactly as before.

### Part versions

Every registered part has numbered versions: characters, locations, props and graphics
([docs/decisions/0047-character-versions.md](decisions/0047-character-versions.md)), so a drawing can improve
without touching a published reel. `srstudio parts` lists them, a part's page in the catalog shows them, and
[src/srstudio/assets/parts.json](../src/srstudio/assets/parts.json) records each one: number, date, a note, a proof clip,
status, approval and the digest of its drawing
([src/srstudio/catalog_specimens.py](../src/srstudio/catalog_specimens.py)). A part that cannot stand alone, such as a
caption layer or a shot with a character in it, records a typed refusal instead of a digest, and
`srstudio parts --refused` lists those. A new reel gets the latest approved version, and a release pins what it draws:

```python
RELEASE = Release("a-new-reel", post, parts={"toon-fox": 2, "toon-bear": 1, "toon-desk": 1})
```

`srstudio build` leaves what it drew in the project's `parts.json`. `instagram_posts.py deliver` refuses a release with
no pins, a video with no such record and a build that drew anything its pins do not say, and `check` reports the
first and the last. A proposed version is never
the default and cannot be pinned. An approved drawing is never revised in place: a test redraws every one and fails
if its digest moves, so changing a look means adding a version. Only the operator approves a version. Only Toon's
characters read pins so far, through `toon_sketch.Staging.versions`, and the table refuses a second version of
anything else by name until its kind and style are in `parts.ROUTED`. A head rig is a second drawing, recorded on its
version with the same fields and rules, so changing an approved rig means adding a version of the character.

Version 2 of the dog, the frog, the bear, the rabbit, the raccoon and the hedgehog is the default for new reels
([docs/decisions/0052-older-cast-version-2.md](decisions/0052-older-cast-version-2.md),
[src/srstudio/toon_redrawn.py](../src/srstudio/toon_redrawn.py)): each keeps its colours and what it is known by, and
is drawn again with one smooth torso, pressed ink, a shade tone, a tilted head and its own pupils and paws. Published
reels pin version 1 and keep it.

A sloth, a goat and a hamster draw like the traced cat, in code
([docs/decisions/0045-toon-sloth-goat-hamster.md](decisions/0045-toon-sloth-goat-hamster.md),
[src/srstudio/toon_critters.py](../src/srstudio/toon_critters.py)): `toon-sloth` (olive, droopy, a pale face with dark
stripes down from the eyes, long ivory claws, a slow blink), `toon-goat` (lilac, wiry, swept horns, sideways ears, a
long muzzle and beard, bar pupils) and `toon-hamster` (pink, round, cheek pouches, a creamy belly, tiny paws held up).
Run `srstudio inspect character toon-sloth --json` (or either other name) for an executable pose recipe.
These builders accept `srstudio.toon.Pose` states using `EYES`, `MOUTHS` and `ARMS` names from that module.
The first pose starts at zero; pose starts are seconds relative to `enter`. `enter`, `duration` (the exit time),
`taps`, `mouths` and optional `LimbTrack` motion use project seconds. Builders return the pose groups.
Each is a `Critter`, a `toon_cast.Drawing` the look routes its foundation, face and limbs to: a dense hand-placed
outline with a pressed line (`pressed`, heavier at the bottom and back, thinning at sharp turns), open tapered fur
strokes, one shade tone along the edges away from the light (`shade`) and a head tilted about the neck. Each has
its own signature: the sloth's yawn, the goat's scream, the hamster's puffed pouches. Every brush character also
draws the new `sleepy` eyes (heavy lids, blinked slower: `SLEEPY_PACE`, `SLEEPY_HOLD`) and `yawn`, `scream` and
`puff` mouths (`shared_eye`, `shared_mouth`); the traced cat refuses them by name.

A critter's body and arms come from a `Torso`
([docs/decisions/0049-toon-torso-one-smooth-body.md](decisions/0049-toon-torso-one-smooth-body.md),
[src/srstudio/toon_torso.py](../src/srstudio/toon_torso.py)). `Torso(head, shoulder, slope, flank, arm)` builds one
smooth outline under a head contour: fixed-radius arcs from the neck over the shoulder and down the flank, so it
cannot make a corner. `Torso.weights` calms `brush.wobble` on that line. `Torso.limb(points, paw, coat, shade)` redraws
a pose's arm inside the body, a wedge from a thin crease at the top to full width at the forearm, its ink set low so
it reads heavier underneath, and leaves the paw to the character. `toon_torso.arm_lines` is the other way to ink an
arm, the inked fox's: only where it leaves the body or lies well over it.
Any `toon_cast.Drawing` can use it. The older brush cast still draws the shared `_limb` arms.

The sloth's, the goat's, the hamster's and the inked fox's heads can move on their own
([docs/decisions/0050-organic-head-motion.md](decisions/0050-organic-head-motion.md)). The redrawn six can too, from their
version 2 drawings ([docs/decisions/0059-older-cast-head-rigs.md](decisions/0059-older-cast-head-rigs.md)).
[src/srstudio/head_motion.py](../src/srstudio/head_motion.py) turns a `HeadStyle` and the `Speech` of a shot
(`speech_of(alignment, at, path)`) into a `HeadPlan` with `plan(style, speeches, duration)`: spring-keyed nods on the
accents of the line, a dip before a phrase, a two-octave idle, a breath tied to the pauses and glances, all
deterministic and bounded by `limit(style, name)`. Head plans keep the spring history and Catmull-Rom neighbors needed
to preserve motion across shot cuts. Long carried-spring channels are sampled into linear keys at at least 240 Hz
to preserve momentum while bounding renderer work; the sampler rejects channels exceeding its 100,000-key budget.
`limit()` describes the rig's allowed excursion, not a universal overshoot factor for every spring. `plan()`
checks every channel's response; `HeadPlan.check_bounds(style)` exposes the same check. Public Toon, Host, News,
and Rafa head entry points validate supplied plans before drawing or generating plates' face states. Gaze names
must exist in `head_motion.GAZES`, and gaze times must be finite and strictly increasing, including states outside
the current shot. Invalid gaze input raises `HeadMotionError` before scene mutation.

`channel.sample(project_second)` evaluates the emitted motion without drawing: hold, easing, spline and spring
semantics match the renderer, including emitted key precision. Empty channels sample as zero; times outside the
keys hold the nearest value. Sampling order does not matter. `channel.during(start, end)` retains the curve history
and spline neighbors needed for continuity across cuts. Rafa samples this same motion before selecting the nearest
plate and holding it on twos. Its valid `up` gaze maps explicitly to `ahead` because no upward plate exists; unknown
states are refused. See [ADR 0081](decisions/0081-shared-channel-sampling.md).
Linear, hold, and endpoint-bounded easing check their key values; Catmull-Rom, default TCB, back, and elastic
curves also check analytic extrema between keys. Unknown curve names raise `HeadMotionError`.
Short spring curves use sampled extrema plus a conservative
curvature allowance between samples; long channels use the extrema of their emitted linear keys. Validation
shares the sampler's work budget. A response outside the envelope raises `HeadMotionError` naming the channel
and bound. Reduce the excursion or adjust curve/timing; for springs, increasing damping can help. Tuning a curve
does not enlarge the approved rig. A bare `Channel(curve="spring")` uses the engine's default spring without
carried momentum; it is checked separately from explicit `Spring` channels.
For example, Goat's `Spring(2, 0.2)` settling response exceeds its face/turn envelope, while `Spring(0.8, 0.5)`
fits the same directed-turn example. `check_bounds(style, frozen=True)` checks only the initial pose emitted by
a frozen drawing, without sampling unused future spring history. Times must remain distinct on the six-decimal
scene clock. Immutable rig specimens use a separate, fixed probe generated from the rig's combined geometry
envelope; that probe folds several channels into turn/nod and is not a caller-supplied performance plan.
Generate plans with the destination rig's `style`: a plan prepared for a larger movement envelope can be
refused when applied to another character. Regenerate it with the destination style before drawing.
Explicit `facing=[(on, off, side)]` intervals take precedence over incidental glances: an idle glance is omitted
when its eye hold or head return overlaps a directed turn, including that turn's return to rest. This prevents
their head turns and face slides from adding beyond the style's intended bounds. Nonoverlapping glances retain
their original timing and seeded choices.
`toon_head.rest_springs()` is a lossy compatibility helper: it removes carried momentum and can visibly change
trajectories and velocity. New callers should use the automatic spring sampling in `toon_head.figure()` and
`Channel.during()`; preview scenes that intentionally retain spring resets.
[src/srstudio/toon_head.py](../src/srstudio/toon_head.py) draws a
`HeadRig` in nested groups with `toon_head.figure(cv, parent, rig, poses, duration, plan)`: the head turns about the
neck, and either the body's ruff or the chin hides the seam. [src/srstudio/toon_rigs.py](../src/srstudio/toon_rigs.py)
holds the rigs, and `rig_of` refuses a character with none by name. In a sketch, one line turns it on:
`Staging(..., heads=("sloth", "goat"))`. The build plans each named character from the takes in `voiced/speech.json`,
its own lines to speak and the others' to hear, and plays that plan a shot at a time. It is opt-in:
`toon_cast.figure` and the flat drawings draw as before. A `toon_torso` character gets a rig with
`toon_critters.Split` and `torso_rig`; `Split.open_chin` draws a head over the body with no line under its chin, for
a body that has no ruff or collar to hide the seam. Word stress comes from a table built by
[tools/build_stress.py](../tools/build_stress.py) from the CMU Pronouncing Dictionary
([licence](../src/srstudio/assets/stress/CMUDICT-LICENSE)).

`toon-bento` is the operator's capybara in a blazer, approved and not yet in any reel
([src/srstudio/toon_bento.py](../src/srstudio/toon_bento.py),
[docs/decisions/0062-bento.md](decisions/0062-bento.md)). He has 36 moods, 12 eye states and 9 gestures as typed data.
`toon_bento.pose_of(start, "skeptical", "folded", "left")` is one pose: a mood, with any gesture or shared arm and an eye
state over it. Pass such poses to `toon_head.figure` with `BENTO_RIG`. Each mood's tilt is held by the rig through
`HeadRig.pose_tilt`. A sketch's shared kinds draw on him as his nearest mood, and `parse_poses` admits only those. His
lip sync takes the same viseme track as the bear and the rabbit.
`srstudio inspect character toon-bento --json` includes an executable mood-change recipe and the timing
contract. Import `MOODS`, `EYE_STATES` and `GESTURES` from `srstudio.toon_bento` to discover names. The registered
builder holds mood tilts; use `toon_head.figure` for a moving head plan. Bento's named gestures supply his arms;
nonempty `limbs` replacement tracks are unsupported.

`toon-bento@2`, the version new reels draw, gives him a pair of hands
([docs/decisions/0143-bento-hands-are-a-pair.md](decisions/0143-bento-hands-are-a-pair.md)). A `Gesture` holds
`toon_bento.Paw` records, each naming its `Arm` and `Facing`; a paw on the other arm's sleeve, or two on one arm, is
refused when the gesture is built.

## Toon sketches: *The Report* (T3), *Logo Bigger* (T4) and *Quick Question* (T5)

The coworkers' episodes are short comedies written as data and cut between the two characters
([docs/decisions/0015-toon-sketches.md](../docs/decisions/0015-toon-sketches.md)).
[src/srstudio/sketch.py](../src/srstudio/sketch.py) defines a `Sketch`: its `Speaker`s (an ElevenLabs premade voice
each and the Toon character one plays, or none for a voice heard on a speaker), its `Line`s (one request each) and
its `Beat`s (every change of caption, on-screen character, expression or prop event at its scripted time, a spoken
beat naming the line and the word it starts on). `check` refuses an inconsistent sketch; `cues` (the caption script,
each cue carrying its line's speaker so `toon.captions(tints=)` colours the pill by who speaks), `appearances` (one
stretch of one character on screen, its poses counted from its entrance) and `events` (`"toast:0"`,
`"clock:09:05"`, `"logo:2.3"`, `"pop"`, `"hangup"`) are what the build draws. `record` says every line in its
speaker's voice through `srstudio.voice`, confirms each voice by name, hears each take back with speech-to-text
(the run stops on any misheard line), places the lines at the speakers' own pace and moves the beats onto the heard
words (`place`); the placed beats are written to `voiced/beats.json` and read back typed by `load_beats`. The
same run turns each take's character timestamps into its character's viseme track (`visemes`, sampled at
`VISEME_RATE` over the part of the take that was kept, joined in order by `extend_track`) and writes
`voiced/mouths.json`, read back typed by `load_mouths` (known characters, known visemes, rising seconds within the
project).

[src/srstudio/toon_props.py](../src/srstudio/toon_props.py) holds the sets and props the sketches play with, all in
the style's reference pixels: `toon-meeting` (a mint room with a whiteboard where the window was), `toon-mug`
(steam in the spans asked), `toon-clock` (hour and minute hands that jump to each `(second, "HH:MM")`),
`toon-notes` (up to four sticky notes lettered on the laptop lid), `toon-toast` (a phone notification that slides
in and shakes with the buzz; `gated=True` letters the card only once it has landed, so a camera push never leaves
its lettering wholly off frame, where the strict encode's contrast check fails it), `toon-board-text`, `toon-logo` (a sun that scales about its centre to each asked
size over 0.3 s, `scale_keys`, with a drop shadow through a span) and `toon-badge` (the call status under the
pill). `toon_cast.sticky_note` and the `stickers=` parameter of `dog`/`frog` stick a note on a character's forehead
that follows its sigh and lean. `foley.buzz` and `foley.tones` (`STING`, `CHIME`) are the phone and the sting, as
deterministic as the keyboard.

[srstudio.toon_sketch](../src/srstudio/toon_sketch.py) is the build the Toon sketches share: `build` draws one gated
group per appearance (set and props behind the character, the character on its poses, the desk, the props in
front), tints the pills, refuses a caption too wide for one pill (`fit_captions`), checks that `voiced/beats.json`
and `narration.json` agree, draws the mouths from `voiced/mouths.json` (refusing one whose end differs from the
beats'), and adds the voices and effects; `record_episode` is the ElevenLabs run plus the
keyboard between the lines, a buzz under every toast and the sting on the hangup. Each sketch is a data module
with its `SKETCH`, a `validate` for what its events ask of the props, and a `dress` for its shots:
[episodes/the_report_data.py](https://github.com/pedroanisio/srstudio-episodes/blob/develop/episodes/the_report_data.py) (Fern asks where the report is; Rex has never heard of
it; his own reminders buzz in; the notes and the one on his forehead have been there from the first frame;
"...What report?") and [episodes/logo_bigger_data.py](https://github.com/pedroanisio/srstudio-episodes/blob/develop/episodes/logo_bigger_data.py) (a client on speaker wants the
logo bigger until it is the size of the building, then popping, then smaller; the original pops; "Invoice sent.")
and [episodes/quick_question_data.py](https://github.com/pedroanisio/srstudio-episodes/blob/develop/episodes/quick_question_data.py) (T5 *Quick Question*: Pip the rabbit has a
quick question for Bruno the bear; first some context, March, then Dave; his clock jumps from 9:02 to 9:48 and his
coffee goes cold; the question is when the stand-up is, and it is on the board behind her; "Oh. Quick
follow-up."). *Quick Question* records with `record_episode(mouth=)` set to the Toon reading plus the English
spelling, closed bilabials, lead and bridged joins of `srstudio.lipsync`.

```bash
python3 episodes/the_report.py PROJECT --init                                # script.json, assets/poses.json, Comic Neue pinned
python3 episodes/the_report.py PROJECT                                       # the silent master on the scripted timing
SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/the_report_audio.py PROJECT          # the recording: audio/, voiced/, narration.json
python3 episodes/the_report.py PROJECT --voice                               # the narrated master
scene-render encode PROJECT/the-report.scene.xml -o /abs/path/the-report.mp4
```

`logo_bigger.py`, `logo_bigger_audio.py`, `quick_question.py`, `quick_question_audio.py`, `whose_milk.py`,
`whose_milk_audio.py`, `out_of_office.py`, `out_of_office_audio.py`, `date_night.py`, `date_night_audio.py`,
`in_network.py`, `in_network_audio.py`, `split_it.py` and `split_it_audio.py` take the same arguments.

*Whose Milk?* (T6, [episodes/whose_milk_data.py](https://github.com/pedroanisio/srstudio-episodes/blob/develop/episodes/whose_milk_data.py)) is the first sketch in the office
kitchen. Fern (Matilda) and Rex (Charlie) argue over the milk in the fridge, labelled Rex, 2019. The note on the
fridge escalates through `note:` events (WHOSE MILK?, IT MOVED., WHOSE YOGURT?). Each new note is cut in full frame
with `toon_sets.note_insert` for its beat, and the last one holds to the end as the button. Rex's coffee brews
behind him in every one of his shots.

*Out of Office* (T7, [episodes/out_of_office_data.py](https://github.com/pedroanisio/srstudio-episodes/blob/develop/episodes/out_of_office_data.py)) brings Pip (Alice) and Bruno
(Bill) back, and it is the first sketch in the home office at night. Bruno is on vacation, out-of-office on. He has
answered every email to say so, personally. The tear-off calendar behind him loses its pages on `page:` events, only
in his shots. His boss's reply and, as the button, his own auto-reply arrive as `toast:` events, drawn larger with
`toon_props.toasts(size=)`. The desk lamp lights his laptop, and the plant stands in front of its glow, right of his
paws.

*Date Night* (T8, [episodes/date_night_data.py](https://github.com/pedroanisio/srstudio-episodes/blob/develop/episodes/date_night_data.py)) takes the Toon home: Mae (a
rabbit, Sarah) is in the kitchen and Otto (a bear, Daniel) in the home office next door, on a video call. He has
sent her a calendar invite for dinner. Its agenda, her status as optional and, as the button, a shared spreadsheet
of apartments arrive on her phone as `toast:` events, and the fridge carries the date. The tear-off calendar
behind him jumps from OCT 29 to JUN 30 on the `page:` event of the punchline, the month their lease ends.

*In Network* (T9, [episodes/in_network_data.py](https://github.com/pedroanisio/srstudio-episodes/blob/develop/episodes/in_network_data.py)) is a phone call to an insurer. Gil (a
frog, Chris) is in the home office at night; Dana (a dog, Jessica) is in claims, in the new call-centre cubicle
(`toon_sets.call_centre`), and wears the new headset sticker (`toon_cast.headset`). Is a broken arm covered? Which
arm? They cover the right. The claims arrive on his phone as `toast:` events. Her CALLS WAITING board climbs on
`tick:` events, only in her shots, and jumps to 999 in the hold before her punchline: try again in January, fresh
deductible. After the sting, his calendar jumps to JAN 1 and the button is the callback toast, a new claim.

*Split It* (T10, [episodes/split_it_data.py](https://github.com/pedroanisio/srstudio-episodes/blob/develop/episodes/split_it_data.py)) is the end of a dinner. Brock (a bear,
Roger) wants to split the bill evenly; Mia (a rabbit, River) had a side salad and water, he had three lobsters and
the wine. It is the first sketch in the new restaurant (`toon_dinner.restaurant`), and its staging swaps the office
desk for the dinner table with the new `Staging(desk=toon_dinner.table)` option (the default stays `toon.desk`).
Each side of the table is laid with `toon_dinner.dishes`, and the card reader (`toon_dinner.card_reader`) changes
screen on `reader:` events: DECLINED for him, APPROVED for her. Her payment, his transfer of $6.50 and, as the
punchline, what it is for (half her salad) arrive on her phone as `toast:` events; the button is his last toast,
"Same place Friday?".

Two more staging options serve the opening A/B test (a still first second against a moving one). A sketch may open
on a silent, uncaptioned beat and caption its first line later: the build checks the caption script against the
sketch's first cue, not against second 0, so a still opening holds the frame unchanged until the first word. And
`Staging(camera=)` moves each shot: it is called with the dressed `Shot` (its beats are the ones drawn, scripted or
voiced) and the shot's group (set, character, desk and props; the captions stay still), and the group is named
`shot-NNN` so `srstudio craft` counts its moves as camera. Without it, shots keep their anonymous ids and every earlier sketch
rebuilds byte-identical.

## Toon dinner: the restaurant, the table, the dishes and the card reader

`srstudio.toon_dinner` draws the restaurant set in the Toon line. `restaurant(cv, parent, special=(dish, price))`
is the wall with a seascape, a lit sconce, wainscot, a leather banquette and a chalk SPECIALS board.
`table(cv, parent)` is a tablecloth that takes the desk's place in a sketch and carries the signature marks.
`dishes(cv, parent, items, id=)` lays `(kind, x[, at])` items (salad, water, lobster, shells, wine, glass, empty,
check), each appearing at `at` when given. `card_reader(cv, parent, states, at=, id=)` shows one screen per
`(start, text, tone)` state, with tones `idle`, `bad` and `good`. Bad data raises `ToonDataError`.

## Toon sets: the office kitchen and the home office at night

[src/srstudio/toon_sets.py](../src/srstudio/toon_sets.py) adds two backdrops and four props, drawn more finely than
the first sets ([ADR 0022](../docs/decisions/0022-toon-kitchen-and-home-sets.md)). Objects are inked with the brush,
so their outlines swell and taper like the characters'. Surfaces carry light: a highlight on glass, steel and
glaze, a soft shadow under each object, and glows drawn as radial gradients. Everything is placed in reference
pixels and keyed on the composition clock. Looping motion runs from 0 to `end` (`cycle_keys`) and is left out when
`end` is 0, so a still frame is the same either way.

| Part | What it is | Motion |
|---|---|---|
| `toon-kitchen` | butter wall, mint cabinets, subway tiles with a glint each, a counter at `COUNTER_Y`, a tall fridge with magnets | a `note=` (1 to `NOTE_MAX` = 14 characters) on the fridge door |
| `toon-home` | dusk-violet wall, a night window with a cratered moon, the city skyline, a gathered curtain, string lights, a bookshelf | stars twinkle, bulbs pulse, lit windows go out and come back, until `end` |
| `toon-coffee-machine` | a drip machine on the counter: carafe, coffee, steel glint | in each `brewing` span: the light blinks, drops fall, steam sways |
| `toon-desk-lamp` | an angled teal lamp at the desk's right, its head over the laptop | its cone and pool of light show in the `lit` spans (`None`: always on) |
| `toon-plant` | a terracotta pot with five glossy leaves; `at` and `scale` | the leaves sway until `end` |
| `toon-calendar` | a tear-off wall calendar in the clock's place | at each `(second, "OCT 28")` in `pages` the page above tears, tips and falls |
| `toon-note-insert` | a full-frame close-up of the fridge note, lettered at 128 px so it reads on a phone | shown from `start` to `end` under a slow push |
| `toon-call-centre` | a cubicle: a pale office wall, a flecked fabric partition, a YOUR CALL MATTERS poster, a CALLS WAITING LED board in the window's place | one count at a time from `waiting` (`(second, count)`, from 0, up to `WAITING_MAX`); the board's lamp blinks until `end`; `legible=True` letters the label lighter (`LED_LABEL`) so it passes a strict encode's contrast check |

The signature marks stay on `toon.desk`, which is in front of every Toon shot. The new sets draw neither mark, and
the defaults of the lamp and the plant stand clear of the desk's cactus. *Whose Milk?* uses the kitchen, the coffee
machine and the note insert.

`toon_cast.headset(look, mic=True)` (`toon-headset`) fits a headset to any brush-drawn look from its silhouette: a
band just over the crown, ear cups at eye height and a boom to a mic beside the mouth. It is a list of layers, like
`toon_cast.sticky_note`, passed to the figure with `stickers=` so it leans and sighs with the character.

## Toon rooms: a living room at night and a service counter, lit over time

[src/srstudio/toon_rooms.py](../src/srstudio/toon_rooms.py) adds two backdrops whose light a sketch drives
([ADR 0043](../docs/decisions/0043-lit-toon-rooms.md)). Each room has a main light and a screen. A light runs through
cues `(second, state)` from 0. The states are:

- `on` and `off`;
- `flicker`, a stutter that repeats until the next cue;
- `dim`, a fade to `DIM` over `FADE` seconds.

A screen's cue may also name a colour from `SCREEN_COLOURS` (blue, white, red, green, amber, purple). The colour holds
until a cue changes it. Cues are plain data:

```python
toon_rooms.dress(shot, "lounge", {"lamp": [[0, "on"], [4.5, "flicker"]], "tv": [[0, "on", "blue"], [3, "on", "red"]]})
```

The light shows on the sources themselves, in the set behind the character. It also reaches the character: a sketch
built with `Staging(lit=True)` gets a light layer in every shot, between the character and the desk. In that layer, a
shade multiplies the frame darker as the main light goes down, and glows add each light's colour over the
character's side of the frame. The desk, with the signature on it, is drawn after the light layer, so no light state
changes it. Tests render each state and compare the signature's pixels.

| Part | What it is | Lights and motion |
|---|---|---|
| `toon-lounge` | deep teal striped wall, a shelf above the pill with a router and the library's smart speaker (`toon-speaker` at scale 0.5), a floor lamp at the left, a wall TV over a media console, a plum sofa behind the character | `lamp` (main) and `tv` (screen, default blue); the router's lights blink until `end`; the speaker's ring follows `speaker=` (`(second, state)`, default off) |
| `toon-counter` | mint wall and wainscot, ceiling tiles with two fluorescent fixtures, a TAKE A NUMBER sign with its dispenser, a NOW SERVING board, an orange plastic chair | `tubes` (main) and `board` (screen, default red); the board shows one ticket at a time from `serving=` (`(second, "A17")`, from 0) |

`toon_rooms.ROOMS` names each room's lights, its defaults and the boxes its objects keep clear of the figure, the pill
and the desk. `toon_rooms.stage(cv, back, light, name, lights, end)` draws a room outside a sketch.

## Toon everyday props: the phone, the speaker, the receipt, the queue and the form

[src/srstudio/toon_everyday.py](../src/srstudio/toon_everyday.py) adds five props for everyday tech, money and
services, job search and dating ([ADR 0042](../docs/decisions/0042-toon-everyday-props.md)). Each stands at `at`
(reference pixels) and `scale` (0.9 to 2.0; the speaker, which carries no lettering, from 0.5), takes states keyed from 0 in rising seconds, and returns its
footprint. A footprint that leaves the frame, enters the caption band or touches `SIGNATURE_BOX`, the desk's
signature marks, raises `ToonDataError`, as does text that does not fit its box in the style's font (`measure=`,
the sketch's `Shot.measure`).

| Part | What it is | Motion |
|---|---|---|
| `toon-phone` | a phone, held (`hand=`) or set down, with typed `Screen`s: `notify`, `code`, `profile`, `declined`, `loading`, `off` | one screen at a time; a notification buzzes the phone; the loading bar fills to `fill` |
| `toon-speaker` | a smart speaker with a light ring and a halo | `off`, `listen`, `think` (a light chasing round), `speak` (pulsing), `error` (red), until `end` |
| `toon-receipt` | a receipt strip under a printer slot: a header, `(name, price)` rows, a total | unrolls from `start` at `pace` seconds a row; each row shows as the paper passes it |
| `toon-take-a-number` | a ticket dispenser on a pole under a NOW SERVING display, the customer's `ticket` in it | the display changes at each `(second, number)` |
| `toon-clipboard` | a form on a clipboard: a title and up to five `Field(label, value, at)` rows | each value is written in at its second; a `(second, text, tone)` stamp lands with a pop |

No episode draws them yet, so the catalog's notes need no gallery item for them.

## Lyra and Retro Orbit: flat print parts

[src/srstudio/toon_plate.py](../src/srstudio/toon_plate.py) draws a mid-century poster as brush shapes: `shape` turns an
absolute path into a closed `Shape`, `Frame` places a plate inside a part, and `clip` and `inside` stand in for a clip
path. A plate keeps its literal colours on any canvas palette.

[src/srstudio/toon_orbit.py](../src/srstudio/toon_orbit.py) adds two 9:16 locations, `planetarium_salon` and
`starlight_terrace`, and five props: `telescope`, `moon_globe`, `saturn_model`, `field_notebook`, `signal_clicker`.
Signs are live text in the two fonts of `Lettering`, Bebas Neue and DM Sans, installed with `fonts.install`; with no
`Lettering` they stand blank. `print_finish` is the one grain, and it fits `Staging.finish`. Neither set signs a shot,
so a reel there gives its shots a `Staging.desk` that does.

[src/srstudio/toon_lyra.py](../src/srstudio/toon_lyra.py) is `lyra`, an owl who presents astronomy. `MOODS` and
`EYE_POSES` are typed data; `pose(start, name)` writes a pose in either, and `mood()` and `eye_pose()` refuse an unknown
name. She is lip synced through her beak, and `LYRA_RIG` is her head rig, with `mood_plan` turning her head from mood
to mood. Her moods go through the rig, not through `toon_cast.figure`, which holds to the shared names.

Lyra and her rig are approved. The two locations and five props are proposed, so a reel cannot use them until they are
decided. The reasons and where the port differs from the pack are in [docs/decisions/0063-lyra-retro-orbit.md](decisions/0063-lyra-retro-orbit.md).

## Leo and Sam: two friends holding controllers, proposed

[src/srstudio/toon_gamepad.py](../src/srstudio/toon_gamepad.py) adds a generic game controller held in both paws.
`Player` is a critter in a top whose own arm kinds are the four `GRIPS`: `pad` (both thumbs on the sticks),
`pad-press` (the right thumb on a button), `pad-lap` (lowered, thumbs off) and `pad-up` (lifted). Each is a typed
`Hold`. The paws are a pair: `GRIP` is drawn for the frame's left arm and reflected for the right, so both thumbs point
in over the top edge.

[src/srstudio/toon_friends.py](../src/srstudio/toon_friends.py) is `toon-leo`, a koala in a mustard hoodie, and
`toon-sam`, a sea otter in a teal tee, with `LEO_RIG` and `SAM_RIG`. Their builders draw through the rig held still,
so a pose names a grip wherever it names an arm:

```python
from srstudio import toon_friends, toon_head
from srstudio.head_motion import HeadPlan
from srstudio.toon import Pose

poses = [Pose(0.0, "half", "flat", "pad"), Pose(2.0, "down", "flat", "pad-lap")]
toon_head.figure(cv, parent, toon_friends.LEO_RIG, poses, 4.0, HeadPlan.still())
```

Both characters and both rigs are proposed, so `toon_rigs.rig_of` refuses them and no reel can use them until the
operator decides. `toon.parse_poses` still holds to the shared arm kinds, so a sketch cannot name a grip yet. The
reasons are in [docs/decisions/0228-a-controller-held-in-both-paws.md](decisions/0228-a-controller-held-in-both-paws.md).
