---
generated-by: Claude Code (claude-opus-5-5)
---

# 0215: Release props from the frontal shoulder before a camera cut

The supported Bento candidate keeps his trunk and face as native ink. Preflight
accepts a non-spatial vector layer only when it faces the camera exactly
(`_composition_preflight._check_camera`). That is correct: the vector backend
draws a plane and does not apply a perspective transform. The trunk therefore
turns to face each new camera. At the candidate's camera cut at four seconds,
it turns from 19.09 to -19.70 degrees yaw. Relative to the solved root, the
native shoulder that carries the spatial arm moves 22.22 cm in world space.
The shared carry held the cup from 1.2 to 5 seconds, so the cup moved
(16.51, -0.11, -61.96) cm in world space during the cut.

Nothing may be attached to the frontal shoulder across a camera cut.
`drawing_body.CAMERA_CUTS` lists the camera replacements in `drawing_proof.sample`,
and a test proves they are the only view discontinuities. `check_cuts` refuses any
attachment interval that includes a cut, and `body_scene` runs it before planning.
The candidate's carry keeps the four shared grip-path keys and the pickup pose
but retimes them from (1.2, 2.4, 3.6, 5) to (1.2, 2.0, 2.8, 3.6). The cup is
set down at 3.6 seconds, in the pose it was picked up in. Its world placement
is then fixed through the cut. Peak hand speed falls from 1.75 to 1.46 arm units
per second. An empty arm may follow the turned shoulder. The shared
`carry_motion`, the legacy proof, and the shared camera are unchanged.
`hand_mesh`, `attached_mesh` and `supported_mesh` accept the motion explicitly.

Bento's feet are rigid frontal paw drawings, so a foot's toe direction is the
normal of its drawing card. Each foot layer now takes its solved sole's yaw as
well as its position, so the toes follow the body solver's forward axis in
every shot. A tilted sole has no frontal paw drawing. It raises an error
instead of being flattened.

At the default 12-fps cadence, the complete plan has 80 intervals and 196 raw
render jobs. It plans 178,661 nodes and 6,692,351,952 bytes of working storage.
The 500,000-node and 8-GiB caps are unchanged.

Rejected alternatives:

- A world-fixed, yawed trunk card keeps the shoulder still. The non-spatial
  native trunk cannot satisfy the frontal-view invariant, and relaxing that
  check would ship a projection the backend does not draw.
- Converting the native trunk and face to spatial paths would replace the
  approved native rig.
- Moving the shared camera cut to after the release would change the legacy
  proof and its evidence.
- Leaving the cup in world space while the hand jumps would break the grip.
