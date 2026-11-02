---
generated-by: OpenAI Codex (GPT-6)
---

# ADR 0180: Authored facial deformation on the performance clock

- Status: accepted (2026-11-02)
- Back to the [library README](../../README.md)

Emotional transitions need authored intermediate geometry. Guessing correspondence
between arbitrary eye or mouth paths can deform teeth, pupils and ink unpredictably;
opacity crossfades produce two competing facial contours. Both were rejected.
`HeadRig.face_blender` instead declares directed `FacePose` pairs and a pure geometry
sampler. Preflight compares both endpoints with the actual bound rig's static eyes
and mouth, then validates every emitted sample before drawing or allocating IDs.

`FaceTrack` uses a bounded grid anchored at performance zero, includes off-grid
launch/arrival times and preserves samples through window cuts. Only facial layers
are repeated; the body and its head-transform chain remain shared. Sampled geometry
is held, while `PerformancePlan.sample().face_blend` describes continuous intent.
These are distinct contracts. Budgets cap frames, layers, coordinates, times and
sampling rates. Non-monotone curves are refused for this normalized deformation.

Score 1.2.0 adds the explicit `blend` boolean. Earlier schemas reject it. Existing
scores retain discrete arrival behavior. Expression overrides, speech, independent
gaze and pose replacement during a blend are refused as conflicting owners. Numeric
posture/head policy channels remain independently authored and share the clock.
Gestures remain discrete; this feature does not claim full-body emotional blending.

The first driver interpolates Bento's neutral, deadpan and concerned controls:
lids, brow position/angle/curvature, pupil clipping and a quadratic mouth curve.
It declares all six directed transitions. It does not interpolate unrelated path
arrays, marks, teeth or incompatible eye topologies. `acting.bento_blends()` returns
an opt-in candidate with version-2 paired hands and no approved part identity.
Changing the registered Bento drawings or borrowing their approval was rejected.

The [guide](../authoring-acting.md#authored-emotional-blends),
[study](../../examples/acting_blends.py), and
[contract tests](../../tests/test_face_blends.py) make the supported path explicit.
