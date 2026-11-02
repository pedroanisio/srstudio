---
generated-by: OpenAI Codex (GPT-6)
---

# 0197: Solved limb playback has an explicit clock and anatomy

External rigs already solve world-space arms and hands. Requiring a private `Motion` subclass forces callers to
own duration inference, frame-boundary semantics and serialization. Re-solving that geometry through procedural
gesture controls changes the source performance.

`Motion.keyed(samples, fps)` is an instance factory retaining the source anatomy and replacing procedural drivers.
The returned `Motion` holds samples at their exact `i / fps` timestamps. Its duration includes the last frame's
interval. It checks bounded immutable record graphs, bone lengths, wrist frames, normals, digit topology and
control limits before publication. Random-access sampling performs no IK and never applies a second root transform.

Playback has a distinct closed `srstudio.limbs-keyed/1.0.0` schema. Procedural schemas retain their existing shape.
The decoder preserves already-unit quaternions instead of repeatedly renormalizing solved geometry. The existing
5 MiB persistence bound remains independent of the in-memory sample and graph bounds.

Different-anatomy retargeting and action chaining are refused because fixed world poses do not encode how to
solve those operations. Callers must author new samples. Holding frames is explicit and carries no general
position or derivative continuity guarantee at frame boundaries.

Rejected alternatives: nearest-sample rounding changes poses half a frame early; linear interpolation can alter
bone lengths and contacts; pretending duration is a root animation adds a transform unrelated to the solved rig;
adding samples to the procedural schema makes old readers ambiguously accept a new execution model.
