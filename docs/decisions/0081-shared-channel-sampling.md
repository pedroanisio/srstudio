---
generated-by: OpenAI Codex (GPT-6)
---

# ADR 0081: Sample the channel before quantizing the drawing

- Status: accepted (2026-11-01)
- Back to the [library README](../../README.md)

## Decision

`head_motion.Channel.sample(time)` evaluates project seconds using the key precision and default interpolation
parameters emitted to scene-render. Sampling is independent of call order. Short carried springs preserve incoming
velocity; long chains use the existing bounded bake. A bounded preparation cache avoids repeating that bake per frame.

Rafa samples the authored channel before selecting a replacement plate and holding it on twos. Quantization belongs
to the drawing; replacing every requested curve with smoothstep does not. An explicit `up` → `ahead` gaze mapping
remains for compatibility because Rafa has no upward-looking plate. Unknown gaze states are errors.

The shared scalar primitives also supply spring responses and spline coefficients to envelope analysis. TCB and
Catmull–Rom shot slices both retain neighboring keys needed for their tangents. All public head entry points validate
gaze names and finite, strictly increasing times before emitting geometry.

## Verification

Renderer integration tests compare all supported default curves, three spring damping regimes, a long carried
chain, and positions around shot boundaries. API tests verify held replacement poses and unchanged scenes after
invalid gaze input. Floating-point agreement is tested numerically; bit identity across platforms is not promised.

## Alternatives

Rejecting every non-smoothstep curve in Rafa would remove useful authored timing. Maintaining independent samplers
would allow the same plan to change meaning between drawing styles. Invoking the renderer for each sampled face
would add a process and scene serialization to a pure authoring operation.

Frozen-canvas authoring retains its explicit policy: a non-held channel crossing time zero is rejected. Sampling
the full animated channel is available separately and does not silently change that existing preview contract.
