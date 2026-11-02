---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0202: Limbs drawn with volume, and what a video measures kept apart from what it estimates

- Status: proposed (2026-11-02)
- Back to the [library README](../../README.md)

## Context

The shared skeleton (ADR 0185) is reviewed in `tools/dance_views.py` as lines between joints. A line has no
cross-section, so a turn about its own axis does not show: a forearm twisted a quarter turn draws the same pixels as
one not twisted, and a torso turned 45° draws the same spine. Dances (ADR 0186, 0192) and the style study (ADR 0203)
both turn bones about their axes, so the review view hid part of what it was meant to show.

The study has the matching gap on the measuring side. A single camera fixes where each landmark sits in the picture.
Depth, world metres and any rotation derived from them are the estimator's inference, and a bone's twist about its own
axis is fixed only when a landmark the bone carries lies across it. The style record (ADR 0203) said none of this:
every channel's trust was stated by hand and held at its full weight.

## Decision

### A renderer-independent visual model: `srstudio.skeleton.figure`

`figure(profile, pose, view, *, unobserved=())` turns a posed skeleton and a view into typed drawing primitives:
a `Figure` of `Piece`s, each with its silhouette, end caps, centreline, stripe, lateral tick and markers, in
painter's order. It draws nothing itself; `tools/dance_views.py` draws it with Pillow.

- **Volume.** Each bone is a tapered elliptic cylinder. Limb radii are shares of the character's height (`RADII`),
  the hands, feet and toes are flat sections (`FLAT`), and the torso is four sections, hips to upper chest, whose
  widths follow the profile's hips and shoulders factors (`TORSO`). The values are mid-range adult proportions after
  ANSUR II (Gordon et al. 2014) and Drillis and Contini (1966) on a 1.70 m stature, recalled and rounded rather than
  re-measured: they are there to make a turn visible, not to fit a person. The head is a sphere.
- **Near and far.** The silhouette is the convex hull of a bone's two end rings. Each end cap is an ellipse split into
  the arc on the camera's side (solid) and the hidden arc (dashed); a cap facing the camera is all near.
- **Centreline**, drawn dash-dot.
- **Orientation markers.** A stripe along each bone's anterior reference, solid where the surface faces the camera and
  dashed where it does not; a lateral tick at mid-bone; a chest normal arrow and sternum line on the upper chest; a
  pelvis front tick; a palm normal on each hand; the head's facing tick in every view.
- **Depth order.** Pieces sort by the depth of their middle; a clavicle sorts by its outer end and before a torso
  section at the same depth.

A `View` is three orthonormal axes (`right`, `down`, `toward`); `FRONT`, `LEFT` and `TOP` are the review tool's three
planes, which are studio-mirror views (handedness flipped, as a dancer sees a mirror). `view_from_camera` takes a
limbs orthographic `Camera`. Bad profiles, poses, views and names raise `SkeletonViewError` (`skeleton.view`) or the
skeleton's own typed errors.

`tools/dance_views.py` draws this model by default in all three planes and keeps its command line and its sheet's
layout; `--look lines` draws the old lines.

### Provenance: `measured-2d`, `estimated-3d`, `unobserved`

`pose_track.frame_provenance(image, world)` states, per landmark and per bone twist in one frame, what kind of data it
is:

- a landmark's place in the picture is `measured-2d` when its visibility is at least 0.5;
- its relative depth and its world position are `estimated-3d`;
- a hidden landmark is `unobserved`.

A twist is `estimated-3d` only when all three of these hold; otherwise it is `unobserved`.

- The frame has world landmarks.
- Every landmark the bone's rule reads is visible.
- The rule's direction has a part across the bone of at least `SPAN_FACTOR × NOISE_M`, so the twist's error stays
  under 30°.

`TWIST_RULES` names the direction each bone's twist is read from:

| Bone | Twist read from | Note |
|---|---|---|
| Upper arm | the forearm | |
| Forearm and hand | the knuckles, little finger to index | |
| Thigh | the shin | |
| Foot | the heel's rise to the ankle | |
| Torso | the shoulder line | |
| Head | the ear line | |
| Shin | never | its twist and the ankle's move the foot alike |
| Neck | never | its turn and the head's turn the face alike |

With image landmarks alone, no twist is observed. `NOISE_M` is 0.035 m. On the studio reference the world landmarks'
depth jitter at the wrist, thumb, index and little finger measured 31.1 to 33.8 mm (`track_noise` gives 0.0338), and
`SPAN_FACTOR` is √2 / tan 30°, about 2.45. That makes the needed span about 8.6 cm.

On that reference, these are the shares of found frames in which each twist is `estimated-3d`:

| Twist | Share of found frames |
|---|---|
| Torso | 100% |
| Head | 98% |
| Left upper arm | 54% |
| Right upper arm | 62% |
| Left thigh | 67% |
| Right thigh | 70% |
| Forearms and hands | about 0 (the right forearm in 0.1%) |
| Feet | 0 |

The knuckle span, index to little finger in the world landmarks, is 3.7 cm on the left hand and 6.1 cm on the right
at the median of the frames where both are visible. Nine frames in ten are under 5.3 cm (left) and 7.3 cm (right), and
the right reaches the 8.6 cm needed in 0.7% of its frames, before its part along the bone is taken off. A forearm's
roll cannot be told from this footage.

### The style record: `srstudio.dance-style/1.1.0`

Each `dance_study.CHANNEL` states the `provenance` of what it reads. Each channel of a style record carries that
provenance and the `confidence` it is held at:

- the confidence is the lower of the channel's trust and `CONFIDENCE_CAP[provenance]`;
- for `measured-2d` the cap is `good`, and for `estimated-3d` it is `fair`;
- a miss weighs by the confidence, not the trust.

An `unobserved` channel is never a target. `derive` gives it no ranges and lists it under `unmeasured`.
`ChannelTarget` refuses one that holds a range or a confidence, and `parse_style` refuses a record whose provenance
or confidence disagrees with the channel. A `1.0.0` record, written before provenance, still reads: its provenance
comes from the channel table and its confidence from the cap. A `1.0.0` record that carries either field is refused
as malformed. Today every channel reads the world landmarks, so all thirteen are `estimated-3d`, and
`shoulders.tilt`, `head.bob`, `head.sway`, `arms.height` and `stance.width` drop from `good` to `fair`.

### The study overlay

`tools/dance_study.py` draws each frame's skeleton by provenance:

- bones between landmarks the estimator saw are solid lines;
- a twist held `estimated-3d` is a translucent band in the side's colour, with a stripe along the direction it was
  read from, solid when that direction points to the camera and dashed when it points away;
- an `unobserved` twist is a grey band with no stripe.

A legend in the frame says so, in Portuguese. The page's style table shows each channel's provenance and confidence.

## Rejected alternatives

- **Inferring the hidden twists from a body prior.** A learned or anatomical prior would fill every forearm roll, but
  the drawing would then show the prior as if the footage had shown it. The overlay shows what is unknown.
- **One confidence per record.** The provenance differs channel by channel and bone by bone; one number would hide
  exactly the twists that are never seen.
- **Rewriting the shipped `studio-hiphop` record to 1.1.0.** Reading 1.0.0 as legacy gives the same numbers without
  touching a record another branch is editing; a re-measure writes 1.1.0.
- **Refusing 1.0.0 records.** The provenance a 1.0.0 record lacks is fixed by the channel table, so nothing is
  guessed when it is filled in. Refusing it would break shipped data for no gain in correctness.
- **Drawing the volume in the render engine.** The review tool needs only flat primitives, and a renderer-independent
  model can be tested exactly: a stripe's offset, a silhouette's width and a cap's near arc are numbers.
- **A true (non-mirrored) front view.** The review tool's planes have always been mirror views. Their layout is kept,
  and `View.mirrored` says which is which.
