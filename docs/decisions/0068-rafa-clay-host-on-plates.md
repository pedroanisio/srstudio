---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0068: Rafa, a clay host shot as replacement plates

- Status: accepted (2026-10-31). The operator approved his look as drawn at the proof: "Rafa is approved". The operator
  chose his voice the same day: "will is the voice".
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Builds on [ADR 0066](0066-talking-head-host-kit.md) (the host kit), [ADR 0020](0020-toon-lip-synced-cast.md) (lip sync)
  and [ADR 0050](0050-organic-head-motion.md) (head motion)
- Back to the [library README](../../README.md)

## Context

The operator's decision: "Rafa will replace Lint on the talking head pilot". The show stays The Unwritten Rules and keeps
the host kit, so the host becomes a parameter of the kit. Lint keeps his part, `proposed`, and his delivered reel,
unpublished, and takes no new work.

Rafa comes from a concept study: a clay man modelled in 3D and path-traced. The kit draws in 2D. A talking head holds the
frame for 20 to 30 seconds at 30 fps, so 900 frames of one character, and his face has to blink, glance, nod and speak.
The picture is judged at full size, so the clay has to survive being the largest thing on a phone.

The engine path-traces on this machine. On the RTX 3050 here a 1080 by 1920 frame at 48 samples and 4 bounces took 2.74 s
and 634 MB of memory, and a rerender was identical to the byte.

## Decision

**Replacement animation with plates.** He is shot the way a stop-motion puppet is. `srstudio.rafa` holds him, his rooms
and his props as code, `srstudio.clay` bakes them to meshes, and `srstudio.plates` renders a plate once, cached under
`generated/` and named by the digest of what went in. A reel is a list of typed faces, one a frame
(`rafa_host.faces`), and `rafa_host.perform` lays out the whole man at his pose with an eye-and-brow patch and a mouth
patch gated over it. His head moves on twos and on plate steps, so a turn is a real turn and the nose crosses the face.

**His head is one skin.** `srstudio.rafa_skin` blends the study's balls into one field and takes its outer surface, so a
cheek or a chin cannot read as a stuck-on piece. Colour is painted on that surface, and pressed marks are displacements
of it. A mouth presses its own skull: the corners sink, a fold runs to the nose, and an open mouth is a real hollow with
teeth in it. So a mouth plate carries its own skin, and the patch cut from it carries the difference.

**Moods are typed.** The study's three expressions are `Mood` records: public smile, social battery at 1%, internal
meltdown. Tired is his resting state, set by the lids, and only a meltdown opens his eyes. His left brow stays flat and
his right stays arched in every mood. An unknown mood, gaze, lid, mouth or pose is refused.

**Depth by plates.** The room is a far plate, blurred. He is a plate on clear. The worktop, the prop, his forearm and hand
and the near edge of the room are one foreground plate, in front of him, so the prop and hand have real contact shadows.
That plate gets a lens falloff (`plates.soften`): sharp to the back of the worktop, soft towards the camera. A hand can
reach the prop because the forearm lives in the foreground plate and the join is under the sleeve.

**The clay finish is geometry and normal maps.** The engine documents that its `unevenness` is not applied by the path
tracer. So the skin carries thumb and tool marks as a deterministic displacement, and everything else carries a normal
map made in code: knit on wool, thumb marks on clay. A soft sheen is a material setting.

**The picture recomposes the study's board.** The worktop is deep enough to run out of the frame, so no empty front face
is shown, and the caption sits on it. The kitchen's back wall goes from terracotta to a cooler dark sage, within the
study's palette, so his skin stands off it, and a rim light from the key's side is on his plates and not the room's.
One key direction lights every plate, and `host_kit.finish` is the one grade.

**The library holds no pack.** Geometry and materials are code in their own modules. Nothing in `src/`, the tests or the
docs reads the concept pack, and no OBJ, scene or script of it is vendored. Lettering is typed data in Fredoka, from
Google Fonts.

## Measurements

Each line is one face, a composite of base plate, eye patch and mouth patch against a direct render of the whole face, in
8-bit levels:

```
public-smile open 0.0 0.0 mean 0.066 p99.9 5.0 max 8.0 n>16 0 n>32 0
social-battery wide 4.0 3.0 mean 0.067 p99.9 4.0 max 7.0 n>16 0 n>32 0
internal-meltdown round -6.0 6.0 mean 0.055 p99.9 4.0 max 7.0 n>16 0 n>32 0
public-smile teeth 8.0 -3.0 mean 0.057 p99.9 4.4 max 7.0 n>16 0 n>32 0
```

The 12.3 s stand-in talking clip took 73 new plates, 4 poses, 20 eyes and 51 mouths, in 777 s with other jobs sharing the
GPU, and a rebuild that reused them took under 130 s, a change of one prop included. Encoding 369 frames took 14 s.

## Consequences

- `rafa` and his seven parts are approved as drawn. Changing the look now means adding a version. His voice is
  ElevenLabs premade Will, `eleven_multilingual_v2`, seed 52026, stability 0.42, similarity 0.75, style 0.35.
- `rafa_reel` stages a sketch of his as one long appearance: each beat's `Act` names a framing, a prop and a mood, and they
  change on one frame ahead of the word. It has no part record, because it draws no new thing but him and the seven
  parts. Its tote insert is a new plate of the approved prop, whose drawing does not change.
- The family cap in `tests/test_specimens.py` rises by one.
- `host_kit.spoken` and `host_kit.head_plan` take the cast. Lint's cast and framings are untouched, and published reels
  stay byte-identical: no drawing they use changed.
- A reel costs plates once: each new pose, eye and mouth is a render, and a rebuild costs nothing. The catalog specimen of
  a part is a document that names plates by digest, so a fingerprint needs no render.
- Plates are 1080 wide, so a punch-in upscales them. The kit's `close` and `tight` framings will soften him a little.
- The man is not in the foreground plate, so he casts no shadow on the worktop. The key is in front of him, so his shadow
  falls behind him and this is the correct picture.
- Only frame-right reaches: a gesture off the worktop would need new plates per gesture.

## Rejected alternatives

- **Raster 3D.** Real-time shading loses the soft contact shadows and bounce that make him read as clay, which is the
  look he was chosen for.
- **A drawn 2D port.** It keeps the show's rig pattern and costs no render, but it is another drawn character. The brief
  is the 3D pack, and the depth and parallax of a turn would have to be faked.
- **A measured direct path trace of every frame.** At 2.74 s a frame the 900 frames of a 30 s reel cost 2,466 s of GPU for
  each build, repeated for any change of take, and the polished scene costs more a frame. Plates repeat poses, so the same
  reel costs far fewer renders, and a change of take reuses the mouths it has. Composited plates matched direct renders of
  the same faces, so a direct render buys no visible picture.

## Superseding note on Lint

Lint stays in the repository and on Drive, unpublished. `host-lint` stays `proposed` and is not used for new work.
