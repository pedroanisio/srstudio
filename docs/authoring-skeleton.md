---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# One skeleton for every character

Back to the [authoring reference](authoring-reference.md).

`srstudio.skeleton` is a canonical humanoid of 55 joints and 103 named controls that any character, in any drawing
style, is posed on ([ADR 0185](decisions/0185-shared-skeleton.md)). A character states how it differs as a
`SkeletonProfile`; a pose is a root frame plus control values in radians; forward kinematics gives every joint's
frame; and bridges hand the pose to the `body` and `limbs` adapters that already draw.

<!-- skeleton-recipe:start -->
```python
from srstudio import limbs
from srstudio import skeleton as sk

toon = sk.preset("cartoon")
wave = sk.pose(toon, {"right_upper_arm.down_up": 1.2, "right_lower_arm.stretch": -1.4, "head.tilt_left_right": 0.2})
lean = sk.add(toon, wave, {"spine.left_right": 0.1})
halfway = sk.blend(toon, sk.rest_pose(toon), lean, 0.5)

joints = sk.world(toon, halfway)
drawn = sk.project(toon, halfway, limbs.Camera(origin=(540, 1500), scale=900))
body = sk.to_body_pose(toon, halfway)
arm = sk.to_arm_pose(toon, halfway, "right")
hand = sk.to_hand_pose(toon, halfway, "right")
back = sk.from_arm_pose(toon, halfway, "right", arm)
assert abs(back.value("right_lower_arm.stretch") - halfway.value("right_lower_arm.stretch")) < 1e-9
assert body.support_margin > 0 and drawn["head.tip"].xy[1] < drawn["hips"].xy[1]
```
<!-- skeleton-recipe:end -->

## Units and axes

Metres and radians; x right, y down, z forward, as `body` and `limbs`. The ground is y=0. The root is the frame of
the hips before the hips' own controls, the same frame as `body.BodyKey.root`; `profile.standing_root()` stands the
zero pose on the ground. `sk.CONTROLS` lists every `joint.dof` key in canonical order, and `sk.joint(name)` gives a
joint's parent, side, offset and controls with their limits. `sk.JOINT_TABLE.pelvis_share` and `ankle_share` are the
hips' and ankles' heights at the T-stance as shares of the reference height, and a root stands within `sk.WORKSPACE`
metres of the origin. `sk.compose`, `sk.decompose` and `sk.angle_of` turn a joint's controls into a rotation, read a
rotation back into them, and measure how far a rotation turns.

## Profiles

<!-- skeleton-profile:start -->
```python
sk.SkeletonProfile(
    "robot",
    sk.Proportions(1.4, 0.12, legs=0.8, lengths=(("forearm", 0.3),)),
    hands=("gripper", "mitten"),
    omit=("left_eye", "right_eye", "jaw"),
    limits=(("neck.turn_left_right", (-0.3, 0.3)),),
    rest=(("left_upper_arm.down_up", -1.2), ("right_upper_arm.down_up", -1.2)),
)
```
<!-- skeleton-profile:end -->

- `height_m` and `head_radius_m` are met exactly; the factors scale legs, torso, arms, shoulders and hips before that,
  and `lengths` replaces single segments in metres (`sk.SEGMENTS`).
- A hand kind is one of limbs' (`human`, `three-finger`, `mitten`, `paw`, `gripper`) or `none`;
  `sk.HAND_KINDS` shows which canonical fingers carry each digit.
- `omit` removes a joint with everything it carries. Limits can only narrow the canonical range.
- `profile.record()` is the `srstudio.skeleton/1.0.0` record; `sk.parse_profile` and `sk.read_profile` read it back
  strictly. The presets are `realistic`, `cartoon` and `stick`.

## Poses

- `sk.pose(profile, values, root=None, clamp=False)` refuses every value past its limit at once with a
  `JointLimitError` naming each control, its value and its limits; `clamp=True` clamps instead.
- `sk.rest_pose(profile)` is the character's rest; `sk.add` layers a delta; `sk.blend` slerps joint by joint.
- `sk.world`, `sk.tips` and `sk.project` give frames, bone ends and projected points.

## Bridges

| To | From | Notes |
|---|---|---|
| `to_body_pose(profile, pose, time=, planted=)` | `from_body_pose(profile, body, base=)` | `body_profile` gives body this character's legs, torso, sole and shoulder width. Needs both legs and a foot flat on y=0 (within 1e-6 m and rad). The support is body's public `support_footprint`, `support_hull` and `support_margin` over the planted soles, each set on y=0 with its yaw. Back from body, a torso turn is shared along the spine; a straight leg's knee faces across the hips. |
| `to_arm_pose(profile, pose, side)` | `from_arm_pose(profile, base, side, arm)` | limbs' wrist frame follows the forearm across the elbow's hinge; `arm_profile` gives `limbs.reach` this arm. |
| `to_hand_pose(profile, pose, side)` | `from_hand_pose(profile, base, side, hand)` | The hand's frame and every digit joint; `hand_profile` gives limbs this hand kind; `wrist_control` turns limbs' arm frame into this hand. |

A record whose geometry is not this character's is refused with `skeleton.mismatch` rather than bent to fit.

## Drawing with volume

`sk.figure(profile, pose, view)` turns a posed skeleton into drawing primitives that show a bone's turn about its own
axis, which a line between two joints cannot show ([ADR 0202](decisions/0202-limb-volume-and-provenance.md)):

- each bone's silhouette (a tapered section with radii from `sk.RADII`, `sk.FLAT` and `sk.TORSO`);
- its end caps, split into the near arc and the far arc;
- its centreline;
- a stripe on its anterior reference, solid on the near half and dashed on the far half;
- a lateral tick;
- markers for the chest normal, the pelvis front, the palms and the head's facing.

Pieces come in painter's order. A `sk.View` is three orthonormal axes. `sk.FRONT`, `sk.LEFT` and `sk.TOP` are the
review tool's mirror views, and `sk.view_from_camera` takes a limbs orthographic camera. `unobserved=` names the twists
to draw without a stripe. `tools/dance_views.py` draws this by default; `--look lines` draws the old lines.
