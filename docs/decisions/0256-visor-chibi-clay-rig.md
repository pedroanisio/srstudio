---
generated-by: OpenAI Codex
---

# ADR 0256: A proposed visor chibi, rigged in clay and performed on plates

- Status: proposed (2026-11-06). Look approval belongs only to arc4d3 after the animated proof, under videos.op.looks.001.
- Implementation: codex-builder, at the supplied operator request.
- Builds on [ADR 0068](0068-rafa-clay-host-on-plates.md) and [ADR 0047](0047-character-versions.md).

## Decision

Pedro asked, "consegue recriar programaticamente como um rig ?" and then ruled:
"update the rules. this is an inspired, not an copy. procced with B."
Under videos.op.inspired.001, option B means build it as drawn. This is an inspired
design, not a copy. Names, logos, catchphrases and music from external properties
are excluded. Its identity anchors are the dark visor with glowing white eyes,
white armor over a black suit, and chibi proportions. The second look pass follows the reference with a helmet
about one third of the total height. The visor is the face; there is no mouth and no modelled eyeball.

Use Rafa's units and clay mesh/material pipeline. Rigid local pieces inherit a
typed hierarchy: pelvis, chest, neck, head, paired shoulders, elbows, wrists,
hips, knees and ankles. A pose contains finite XYZ Euler rotations only; unknown
joints or states raise VisorChibiError. Children inherit translation and rotation,
so bone lengths stay fixed. The helmet and eye surfaces share the neck/head frame.

Named poses: neutral, presenting, hands_on_hips, wave, shrug, point. Expressions:
neutral, blink, suspicious, surprised, smug, happy, sad, angry. Gazes: ahead, left,
right, up, down. Eyes are emissive surfaces seated on the curved glossy visor;
a blink replaces each open shape with a thick closed stroke for a complete frame.

Path-trace each unique state once, cache it with plates.render, and composite
whole-state plates through gated layers on the host clock. Whole plates include
self-shadow changes from body poses. Quantized replacement motion reuses states;
no two-dimensional rotation pretends to turn the helmet. The proof is encoded
with --hw software as required by [ADR 0076](0076-collage-two-passes-run-in-software.md).

Register version 1 as proposed, with the proof path and drawing digest, omitting
the approval field. The parts reader accepts an absent approval as None, retaining
all Version checks: a proposed version cannot carry approval, and approved later
versions still require it. Nothing grants this part default or release-pin status.

## Rejected alternatives

- A flat portrait or articulated image: cannot demonstrate the head/visor depth.
- Separate modelled eyeballs or a mouth: lose the visor-only expression identity.
- Stretching endpoints for gestures: breaks bone lengths; use inherited rotations.
- Path-tracing every output frame: repeats identical replacement poses and faces.
- Automatic approval, or treating the inspired-design ruling as look approval:
  the ruling authorizes implementation; only arc4d3 judges the animated look.

## Evidence and limits

The proof folder is generated/character-proofs/visor-chibi, outside the source
checkout. The standalone index presents expression, gaze, pose and scale boards
and the animated proof. Tests cover state refusal, bone lengths, eye inheritance,
repeatable plate digests and proposed status. The reference image was inspected.

Renumbered from 0252 on landing: develop recorded 0252 for agent authoring and motion
evidence while this branch held the reservation, so the record takes 0256, the next
number free on develop and in the reservations.

## Second look pass

The supplied look review calls for a faceted crown and side planes, a raised ridge,
ear discs, a horizontal band visor, a broad jaw with paired cheek vents and a dark
chin notch. The body and legs are longer, with a narrower waist, sculpted limb
armor, belt pouches, black wrist cuffs and individually separated glove fingers.
The chest has a convex shield with continuous normals; point uses a straight arm
so its silhouette differs from the bent wave. Presenting adds
pelvis tilt, asymmetric leg angles and a raised open palm; hip poses keep elbows out.
The dark metallic visor suppresses the broad grey light reflection. Emissive eye
triangles retain the same vocabulary and head transform. The host adds warm optical
bloom from visible eye pixels inside their projected triangles, preserving alpha;
this excludes white armor from the bloom source. Boards use the same finish.
The earlier bubble helmet, broad full-face visor and squat body are rejected
because they miss the supplied reference. All records remain proposed.

The wave-to-hip transition raises the shoulder through an arc while the elbow
folds. A framing regression covers every unique video inbetween, because linear
joint blending briefly extended the glove outside the portrait despite both
landing poses fitting. The named pose landings and bone lengths are unchanged.
