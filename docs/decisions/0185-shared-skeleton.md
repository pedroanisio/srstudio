---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0185: One customisable skeleton for every character and style

- Status: proposed (2026-11-02)
- Back to the [library README](../../README.md)

## Context

The dance SDK has to make any character dance or move, in any drawing style. Today each style answers "where is the
elbow" in its own way: `srstudio.body` solves a pelvis, torso and two legs; `srstudio.limbs` solves one arm and hand;
the rigs of each style hold their own joints in screen pixels. A move written for one has to be rewritten for the
next, and nothing says whether a pose is possible for a body at all.

srlocations already carries a humanoid mannequin with 55 joints and 103 named controls, each with limits, built from
reference photographs. Its moves and blocking are written against those names. srstudio cannot import srlocations
(the two pin different sr-core versions, see [ADR 0179](0179-srlocations-location-bridge.md)).

## Decision

`srstudio.skeleton` holds one canonical joint table, a per-character profile that resizes and trims it, a pose of
rotations on it with forward kinematics, and bridges to the records `body` and `limbs` adapters already draw.

### The joint table, schema `srstudio.skeleton-joints/1.1.0`

`src/srstudio/assets/skeleton/humanoid.json` is srlocations' mannequin, read once at srlocations commit
`4ae2278214de6e704d8dcbab8f293b6a47438483` and converted to srstudio's axes. Its `srlocations_commit` follows
`location_bridge.SRLOCATIONS_COMMIT` when a pin move leaves srlocations' joint table unchanged: every joint's name,
parent, offset, rest, solid and controls with their limits and signs, and the forward kinematics that place them.
`be0aabc` left srlocations' mannequin and `interchange` untouched. `9db12ca` changed both (balance, walk paths, Mixamo
names, `JOINTS_VERSION` 1.0.0, a corrected hands-on-hips pose) but not the table, whose digest srlocations' own test
holds at `88629dcb422eb384`:

| Field | Holds |
|---|---|
| `schema` | `srstudio.skeleton-joints/1.1.0`; a reader refuses another major |
| `srlocations_commit` | the commit the table was read at |
| `srlocations_joints_digest` | SHA-256 of `json.dumps([[joint, [control, ...]], ...])` over the joints in order, with `json.dumps`' default separators; srlocations computes the same digest (`88629dcb422eb384...`) |
| `reference_height_m`, `head_radius` | the mannequin's height (1.75 m) and head radius, as a share of that height |
| `sole` | `width` and `heel` (1.1.0): the foot's sole across and how far it reaches behind the ankle, as shares of the height, from the foot solid srlocations draws (`Bulk` radii 0.034 across, 0.074 along, centred 0.03 ahead of the ankle); `body_profile` scales them with the foot instead of guessing them from the hips |
| `joints[]` | `name`, `parent` (the first joint, `hips`, has none), `side` (-1 left, 0 middle, 1 right), `region` (torso, head, arm, leg), `offset` (where it sits on its parent at rest, as a share of the height), `rest` (a unit quaternion `[w, x, y, z]`, which only the thumbs use), `dofs[]`, and `tip` where a bone ends with no child |
| `dofs[]` | `name`, `kind` (`rotate`, or `translate` on the root only), `axis` (one of +/-x, +/-y, +/-z, on that joint's own side), `low`, `high` (radians, or metres for a translation) |

The conversion: srlocations' axes are x right, y up, z forward in degrees; ours are x right, y down, z forward in
radians, so every offset has its y negated. A yaw turns about +y, a pitch about +x and a roll about -z, each times
its stored sign, and a left joint's yaw and roll are negated. A joint's local turn is its rest and then its controls
in order, the first outermost; the hips' translations apply in the root frame before its turns. Forward kinematics
on this table matches srlocations' own to 1e-9 m on every joint for random poses.

The reader refuses a repeated key, NaN or Infinity, more than 1,000,000 bytes, an unknown or missing field, a wrong
type, a value out of its bound, a parent not listed earlier, a second root, an axis off the coordinate axes, two
controls about one axis on a joint, a rest that is not a unit quaternion, and a digest the names disagree with.
Moving the srlocations pin starts by comparing digests.

### The profile, schema `srstudio.skeleton/1.0.0`

A `SkeletonProfile` says how one character differs from the canon, as data:

| Field | Holds |
|---|---|
| `schema`, `name` | the schema and the character's name |
| `proportions` | `height_m` and `head_radius_m`, both met exactly; optional `factors` on `legs`, `torso`, `arms`, `shoulders`, `hips`; optional `lengths_m` replacing single segments (ankle, hip, thigh, shin, foot, torso, neck, clavicle, upper_arm, forearm, hand) |
| `hands` | the kind of each hand, from limbs' kinds (`human`, `three-finger`, `mitten`, `paw`, `gripper`) or `none`, each mapped to canonical fingers and a bone count |
| `omit` | joints the character does not have, with all they carry: legs, toes, eyes, a whole arm |
| `limits` | narrower limits for named controls; a profile can only narrow the canonical range |
| `rest` | the character's rest pose, as control values |

The derivation keeps the mannequin's shares: one scale fits the stated height once the factors and the head are
applied, so the crown lands exactly at `height_m`; `lengths_m` then replaces single segments. Three presets ship:
`realistic` (1.75 m, human hands, arms at the sides), `cartoon` (1.0 m, head about a third of the height, short legs,
three-finger hands) and `stick` (1.6 m, mitten hands, no eyes, jaw or toes).

### The pose

A `SkeletonPose` is a root frame (the hips before their own controls, as `body.BodyKey.root`) and control values by
`joint.dof`. A value past its limit is refused, with every such control listed with its value and limits;
clamping is opt-in. `world` gives a frame per joint the character has, `tips` gives the crown, toes and fingertips,
and `project` draws through `limbs.projection.Camera`. `blend` slerps each joint and reads the turn back into that
joint's own controls on the branch nearest a straight mix; `add` layers a delta.

### How the skeleton composes body and limbs

The skeleton does not replace `body` or `limbs`; it feeds them. `to_body_pose` gives a `body.BodyPose`: the root at
hip-joint height between the hips, the torso as the upper chest's turn there, both legs, and the support polygon and
margin from body's own mass proxy over the feet flat on y=0, through body's public support geometry
(`support_footprint`, `support_hull`, `support_margin`). A sole counts as flat within the bridge's 1e-6 tolerance;
body's support takes only exact ground soles, so each planted sole is set on y=0 with its yaw for the footprint while
its leg is reported where it is. With no foot down there is no `BodyPose`. `to_arm_pose`
and `to_hand_pose` give `limbs.ArmPose` and `limbs.HandPose` for one side, in limbs' own frame conventions, and
`arm_profile`, `hand_profile` and `body_profile` give each module the anatomy of this character; `body_profile`
sets body's `shoulder_width` to the distance between the upper arms' joints, so a body plan places the shoulders where
the skeleton does rather than at body's default of 1.5 hip widths. `wrist_control`
gives the limbs `HandControl` that turns limbs' arm frame into this hand's frame: at zero forearm twist limbs' palm
faces where the skeleton's palm does not, so limbs' forearm twist carries half a turn. `arm_profile`'s twist range
therefore straddles pi; limbs' orientation-constrained solve keeps a wrist's winding inside it, so a `limbs.Motion`
holding this hand's frame reads the same forearm twist as `wrist_control`.

Each `from_*` reads a record back into controls, keeping everything else from a base pose, so a pose solved by
`limbs.reach` or sampled from a `body` plan lands on the skeleton. A record whose geometry is not this character's is
refused as a mismatch rather than bent to fit. Where the record cannot say what the skeleton needs, the conversion
states its choice: a body torso turn is shared along spine, chest and upper chest by their canonical ranges; the knee
keeps no twist of its own; a straight leg's hinge is taken across the hips, and one lying along that line is refused
as ill-posed.

### Errors

Every failure is a `SkeletonError` (an `SrstudioError`) with a stable code, the path that failed, what was found and
what was expected: `skeleton.schema`, `skeleton.unknown`, `skeleton.absent`, `skeleton.limit` (as `JointLimitError`,
listing each violation), `skeleton.mismatch`, `skeleton.support` and `skeleton.ill-posed`.

## Rejected alternatives

- **One skeleton per style.** Every style would need its own moves, limits and solvers, and a dance written for Toon
  would not run on Stick. Styles differ in proportions and in which parts they draw, which a profile states as data.
- **Importing srlocations.** The two pin different sr-core versions, so one interpreter cannot hold both, and every
  srstudio test would need srlocations installed. The table is data with its source commit and digest instead.
- **Positions instead of rotations.** A pose of joint positions cannot hold a limit, a twist or a hand's turn, lets
  bones stretch, and has no blend that keeps bone lengths. Rotations on a fixed tree keep every bone its length, and
  positions follow from forward kinematics.

## Consequences

- Moves are written once against canonical control names and run on any profile that has those joints; a move that
  names a control the character omits is refused by name.
- Adapters that draw from `body` or `limbs` records can be fed from a skeleton pose without change.
- limbs' `HUMAN` thumb has three segments, as the skeleton's has ([limbs catalog](../catalog/limbs.md)), so a
  human hand from `hand_profile` has limbs' human topology. limbs' simplified three-finger hand keeps a two-segment
  thumb; `hand_profile` gives it the skeleton's three, which limbs takes as the profile's own anatomy.
- Moving the srlocations pin re-reads the table and compares digests before anything else.
