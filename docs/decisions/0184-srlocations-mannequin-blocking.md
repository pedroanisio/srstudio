---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0184: Block a mannequin in a 3D location and record what it meets

- Status: proposed (2026-11-02)
- Back to the [library README](../../README.md)

## Context

[ADR 0179](0179-srlocations-location-bridge.md) gives a reel a location's cameras and where each mark lands in frame.
It does not say whether a body on a mark fits there: whether a seated figure has a seat under it and a backrest
behind it, whether a hand on a desk goes into the desk, where the eyes and hands of a human-sized body are in the
frame. srstudio's own limb engine (`srstudio.limbs`) performs arms and hands in space, but it knows nothing of the
set. srlocations has a mannequin on Unity's Humanoid skeleton with clinical joint ranges, seats in its sets,
`reach_to` and `look_at`, and checks of a body against the set (`Location.faults`, `tangled`, `gap`, `footing`,
`backing`).

## Decision

The exporter poses srlocations' stock mannequin and records the result as data; srstudio never imports srlocations and
ports none of its kinematics.

### The request, schema 1.0.0

`tools/location_export.py --blocking REQUEST.json` reads a request with `location_bridge.parse_request`, the same strict
reader as a record's (`location_bridge.BlockingRequest` writes one):

| Field | Holds |
|---|---|
| `points` | named world points in metres, which looks and reaches name |
| `figures[]` | `mark`, `posture` (`stand` or `sit`), and optionally `pose` (a stock pose; the posture's own by default), `adjust` (pose controls on top), `kind`, `seed`, `height_m`, `look_at` (a point), `reach[]` (`joint`: a hand or a foot, `to` and `pole`: points) |

A figure stands or sits through `Location.stand`, which settles a sitter on the set's own seat beside the mark, as
`examples/fit_check.py` and `examples/mannequin.py` sit their figures; a sit with no seat in reach, a pose whose `sits`
is not the posture, or a reach out of range is refused. A reach is made with `reach_to` directly, not `Location.reach`,
so a limb that passes through the set is recorded, not refused, and the gate below refuses it in srstudio with the
record as evidence.

### The record, schema 1.1.0

A record may hold `blocking`; one without it is written as 1.0.0, which every 1.x reader reads, and a 1.0.0 record that
holds it is refused. `blocking` holds the `contact` numbers the checks ran with, the mannequin's `skeleton`, the set's
part paths (`set_parts`), the request's `points`, and per figure: its `request`; where it stands (`at_m`, `facing_deg`,
`off_mark_m`), `stature_m` and `arm_reach_m`; `joints_m` for `head`, `left_eye`, `right_eye`, `left_upper_arm`,
`right_upper_arm` (srlocations' `shoulders()`), `left_hand`, `right_hand`, `hips`, `left_foot`, `right_foot`;
`sight_m` (eye point and the point a metre along its sight); `seat` (the set's seat and the part under the hips, null
standing); `reached`; `clashes` (limb, set part, depth, buried); `tangled`; `support` (for each limb that should carry
it, and the back on a seat with a backrest: the gap and the part met); `carried` and `back_rests`; `at_limit`; its full
`pose` as srlocations' `Pose.spec()`; and per shot the pixels of every point, the seat's top, and pixels per metre.

The marks of 1.0.0 are recorded before any figure stands, so a record's marks are the same with or without blocking.
A record holds one moment: one pose per mark for every shot.

The reader refuses an unknown or missing field, a wrong type, a non-finite number and a list past its bound
(`RecordFormatError`), then checks (`RecordValueError`): every pixel is the shot's camera on its metres, and none in
front of the camera is missing; the right shoulder and eye are on the figure's own right for its facing, and each hand
is within an arm of its own shoulder; a sitting pose has a seat, faces the way it does and sits on the part its hips
meet, a standing one has none; every clash, support and seat names a part of the set and a limb of the skeleton; each
gap, `rests`, `carried` and `back_rests` agree; each reach missed by the distance from its limb to its point, within
srlocations' tolerance; each control at a limit is the pose's own; and the figure is on a mark of the record, as far
off it as it says.

### The gate

`LocationRecord.require_clear(*marks, carried=True)` raises `BlockingClashError` naming every limb that passes
through a part of the set or through another limb, and `BlockingSupportError` for a body nothing carries. A reel that
stands a figure in a 3D location calls it before it renders. `LocationRecord.blocking(shot, mark)` gives the body
and its pixels in one shot.

## Rejected alternatives

- **Porting srlocations' IK or collision into srstudio.** A second solver to keep in step, against a set srstudio does
  not hold; the record carries srlocations' answer and the reader checks it against the camera and itself.
- **Amending ADR 0179.** 0179 decides how a location's geometry reaches srstudio; this decides that a body is posed
  and judged by srlocations and refused by srstudio, with its own request format and gate.
- **Refusing a clash in the exporter, as `Location.reach` does.** The reel would learn only that the export failed;
  recorded, the clash names its limb and part and the gate refuses it where the reel is built.
- **Typed command-line options instead of a request file.** A figure carries a mark, posture, pose, adjustments,
  body, a look and several reaches; one file holds them, is checked by the same reader, and is kept beside the record
  so the export can be repeated.
- **Recording the figure on the marks of 1.0.0, as `framing.blocking` would once a figure stands there.** The marks
  would mean something else with and without blocking.

## Consequences

- An export with blocking runs srlocations' checks per figure, which take minutes on a large set: the park's two
  figures took a little over seven. A request holds at most 32 figures, and few is the practical number.
- Hands are recorded as wrists, and the head as its joint, not the crown.
- A swapped pair of hands is refused only when the record can tell: a reaching hand is measured against its point,
  and a free hand against an arm's length from its own shoulder. Hands that hang close to the body, each within an
  arm of either shoulder, can swap unseen, because crossed arms are a legal pose. Shoulders and eyes have no such gap.
- srlocations' mannequin is the fit test, not the character: a clear record says a human-sized body fits, and a drawn
  figure of another size or shape still has to be judged on its own frames.
- The fixture is the park, a sitter on the bench reaching into the backrest and a walker reaching up
  ([record](../../tests/data/location-bridge/park-blocking-1080x1920.json),
  [request](../../tests/data/location-bridge/park-blocking.request.json)).
