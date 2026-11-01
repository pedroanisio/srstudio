---
generated-by: OpenAI Codex (GPT-6)
---

# ADR 0092: Explicit phase and channel timing for coordinated acting

- Status: accepted (2026-11-01)
- Back to the [library README](../../README.md)

## Decision

Append optional `TransitionPolicy` to `ActingBeat`, preserving positional construction
and the existing policy-free compiler output. Policies use version 1.0.0 and strict
score schema 1.1.0; score 1.0.0 rejects the new field. `ChannelTiming` assigns a delay
and optional replacement duration to a unique channel actually assigned by that beat.
Discovery reports capability-dependent channels, phase units, bounds and guarantees.

Numeric phases are anticipation before delayed launch, transition to arrival, and
settling after arrival. Anticipation and overshoot amounts are fractions of the target
delta. Curves and carried springs use the existing `head_motion.Channel` sampler;
the acting layer does not implement another easing or spring model. Policies bake
bounded linear keys, including explicit phase endpoints, at at least 240 Hz and
32 samples per spring cycle. Candidate keys are capped at 20,000 per channel before
dense interval allocation. Zero-duration numeric arrivals retain the preceding hold
until one six-decimal scene quantum before arrival.

Faces, gaze and gestures remain held states. Emotion labels follow expression arrival;
speech retains mouth ownership, and explicit full-track overrides retain precedence.
Policy excursions are validated even when an override replaces their output. Rig
envelopes constrain emitted head values; breath policies additionally stay in 0..1.
Channel reservations include anticipation and settling. Reset intervals cannot cross
active limb contacts or prop attachments, including those beginning after beat.at.

One immutable performance remains the source of every shot window. Numeric sampling
is independent of evaluation order. Renderer comparisons use exact draw/visibility
states and a 1e-9 absolute transform tolerance for floating-point time subtraction.
The contract distinguishes sampled position behavior from velocity and acceleration;
neither derivative continuity nor facial morphing is promised.

## Alternatives

- Replacing the default sine transition would change accepted scenes. Policy-free
  scores retain their existing path and a captured serialized-output fingerprint.
- Treating facial drawings as continuous values would invent missing poses. Only
  supported held drawings can be scheduled; morph support needs authored evidence.
- Unbounded spring sampling would make generated scores an uncontrolled work request.
  Frequency, duration, event counts and sample counts have deterministic limits.
- A mutable playback state would couple cuts and random-access evaluation to history.
  Persistent compiled tracks provide one source clock for all windows instead.

## Evidence

`tests/test_acting_transitions.py` exercises strict failures, legacy output parity,
independent arrivals, phase overlap, budgets, overshoot, normalized breath, explicit
ownership, contacts/attachments and engine evaluation across cuts during both phases.
`tests/test_acting_transition_example.py` executes the documentation recipe and the
three-variant study, reparses the exported scores and strictly validates its scene.
The executable study exports reproducible inputs and source hashes and supports strict
video encoding. Human ratings remain absent; numeric gates and inspected frames do
not establish a viewer preference or a general biomechanical model.
