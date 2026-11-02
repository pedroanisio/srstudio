---
updated-by: OpenAI Codex (GPT-6)
---

# Reusable drawings and part versions

[Library README](../README.md) · [Authoring task index](authoring-reference.md)

Use this directory of drawing families after [inspecting a contract](authoring-discovery.md). A family description does not replace its supported units, clocks and runtime bindings. Select an approved version through `srstudio.parts`; a proposed or changed drawing requires the explicit recovery described under part versions.

Run commands from the srstudio repository root.

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
the cast of the [first Toon sketches](episode-history.md#toon-sketches-the-report-t3-logo-bigger-t4-and-quick-question-t5).

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
