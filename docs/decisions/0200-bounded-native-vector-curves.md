---
generated-by: OpenAI Codex (GPT-6)
---

# 0200: Preserve native rig curves through bounded vector compilation

The hybrid figure emits spring and Catmull-Rom channels even when several head
channels remain still. Rejecting those curves prevented its actual authored face
geometry from entering the shared compiler. Replacing them with linear keys
would change the source's motion and continuity contract.

Vector preparation now accepts numeric spring, Catmull-Rom and default TCB
segments without rewriting the XML. This is a source-envelope extension, not
permission to omit geometric bounds or infer arbitrary deformation support.

For a spring, displacement from its target and velocity obey a nonincreasing
oscillator energy when damping is nonnegative. The bound includes the native
linear endpoint correction. A bound on the preceding segment's arrival speed
covers carried velocity. Exponential easing's endpoint snap participates in the
engine's finite-difference arrival velocity; it cannot be discarded as a small
visual error. Cubic spline segments stay inside their Bezier control hulls.
Small outward allowances cover native floating-point cancellation, including
nonzero constant carried channels. Zero-valued channels remain exactly bounded.

The worker validates finite spring parameters, numeric properties, complete
opacity envelopes and the same closed input schema used by ordinary vectors.
Only default TCB parameters are admitted. Eight consecutive carried segments are
the maximum: the native evaluator recursively evaluates the previous segment
twice, so unbounded carry chains would multiply renderer work even if the
preparation algorithm itself ran in linear time. Longer chains need explicit
bounded sampling by their author; preparation does not silently bake them.

Rejected alternatives: checking only key values misses interior excursions;
dense sampling alone cannot bound every instant; accepting every native curve
without an envelope would weaken preflight; normalizing constant channels alone
would still reject actual spring motion; changing the figure's approved drawing
or source clock would hide the integration gap.

Regression evidence includes original-versus-compiled engine transforms, the
exponential endpoint case, native constant-channel rounding and the existing
hybrid figure rendered at 1080×1920 before, at and after a compiler cut during a
face blend. Pixels match exactly at those samples. The figure remains a frontal
candidate. Complete camera/body/form/receiver integration and the full DRAWING
acceptance matrix remain separate requirements.
