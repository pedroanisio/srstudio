---
generated-by: OpenAI Codex (GPT-6)
---

# ADR 0088: Compile acting once and place views of its performance clock

- Status: accepted (2026-11-01)
- Back to the [library README](../../README.md)

## Decision

`srstudio.acting` provides immutable score records, explicit rig emotion mappings,
strict JSON decoding, semantic compilation and random-access state. Compilation reuses
head motion, lip sync, limb motion and character clip adapters. It does not synthesize
audio, call a model or claim to infer a viewer's emotion.

Explicit tracks own whole channels. Within a beat, explicit fields take precedence over
emotion defaults; numeric targets take precedence over inferred gaze follow. A complete
HeadPlan owns gaze and head together. Limb tracks own gestures, and conflicting explicit
gestures fail. Resets cannot silently release held contacts or attached props. Invalid
input has bounded, typed diagnostics before caller scene mutation.

Discrete poses switch at transition arrival. Numeric targets ease on a bounded sample
grid. Procedural idle and speech/listening remain deterministic. A compiled plan's window
retains the complete source clock and curve context; a cut changes the camera/view, not
the character's performance. Source limb state can be sampled continuously while rendered
limb geometry retains its selected baking rate.

The initial supported families are split-head Toon (with the explicit Bento profile) and
Gloss. Capability discovery identifies their differences. Gloss does not silently emulate
unsupported directed head/gaze controls. Typed Python runtime overrides bind separately
from data-only JSON; unknown JSON fields and primitive coercions are refused.

## Verification

Tests cover deterministic state, speech and listening, precedence, contact retention,
malformed inputs, capability refusals and atomic drawing failures. Engine comparisons
check source and cut-window geometry at nonzero offsets, including actual sequence shots.
The two-family gallery builds licensed assets, an inspectable state report and a silent
scene for strict rendering. Documentation recipes execute in tests.

Rendered sequence review exposed a composition-key defect in the underlying clip adapter:
the engine moves sequence node lifetimes without moving composition key times. Adapters
now express those keys relative to each owning node's original start. Existing local and
normalized channels are preserved. Regression tests cover Actor, Toon, Gloss, plates and
native/baked limb tracks. Legacy builders outside the adapter retain their behavior.

## Alternatives and limits

Compiling independently for each shot would restart procedural phase and lose curve
context. Copying a sampled pose at a cut would preserve one frame but lose future intent.
Implicitly coercing an unsupported rig control would conceal differences from agents.
Windows of a validated source plan avoid these problems while reusing existing primitives.

Emotion mappings are authored drawing choices. This API does not add face morphing,
continuous target gaze, whole-body biomechanics or perceptual quality certification.
Numeric transition sampling does not promise continuous velocity at arbitrary new intents.
Those capabilities and calibration remain separate findings in the SDK backlog.
