---
generated-by: OpenAI Codex (GPT-6)
---

# ADR 0090: Describe drawing spaces, returned anchors and callback placement

- Status: accepted (2026-11-01)
- Back to the [library README](../../README.md)

## Decision

Reuse `PartContract` for verified non-character semantics. `PartContract.returns` accepts a
`ParameterContract`; optional `space` and `anchors` fields describe named 2D points in that
return value's local coordinates. Anchors require finite coordinates, a unit and a space.
These additive `x-space` and `x-anchors` annotations retain the existing part-contract
schema identifier. They do not change Python builders or provide a JSON executor.

The initial declarations cover the 52 core Cutout props, locations and graphics plus the
existing `reaching-hand` prop. Each registration explicitly selects its metadata. Locations
identify callback drawing depth and canvas-clock visibility. Graphics distinguish local
drawing dimensions from parent placement; captions identify composition-clock layer
lifetimes. Return metadata distinguishes complete groups, partial groups, no return value
and lists of layers. The cup publishes separate origin, body-center and base anchors.

Coverage is a separate SDK operation and CLI mode. It counts explicit declarations,
argument-shape completeness and the presence of units, clocks and anchors independently,
and lists undeclared entries. Ordinary catalog listing output is unchanged. Coverage is
not semantic certification; other families remain unknown until their actual contracts
are checked. The 53 declarations do not imply complete coverage of the 631 non-character
parts observed during this review.

Declarations are bound to the registered callable's identity. A direct builder replacement
cannot inherit old anchors or capabilities, even if its signature matches. Inspection marks
the stale declaration, and coverage counts the part as undeclared. Re-registration validates
the replacement's own declaration; restoring the original restores its metadata. Drawing
approval remains an independent check and cannot prove an API contract.

The held-prop recipe uses the hand's existing callback to place the cup between palm and
fingers, aligning a declared local anchor and animating their shared parent. This is a
flat authored grip. Spatial contact continues to use the separate mesh/limb compositor.
Neither an anchor nor a parameter named `grip` implies that the flat prop supports it.

## Validation boundary

Core location slots are preflighted before drawing; invalid instance/depth/cactus
combinations return explicit repair fields. The held-prop callback has the same early
presence/type check and keeps its module's error class. Callback bodies remain trusted
Python and are not executed during discovery or preflight.

Tests execute every newly described builder to compare its actual return with the
published type, exercise malformed inputs and accepted boundaries, and execute both
documentation recipes. Shared transforms keep the cup's local contact on the hand
through translation, rotation and scale. This establishes the authored 2D relationship,
not physical collision safety or a perceptually approved grip.

## Alternatives

- Inferring units, anchors or capabilities from parameter names would turn guesses into
  authoritative-looking metadata. Explicit declarations keep unknowns visible.
- A second drawing-contract framework would duplicate registry and inspection behavior.
  Extending the existing metadata supports plugins and preserves established output.
- Automatically converting every flat prop into a spatial attachment would require
  geometry, view limits and contact evidence the drawing does not supply.
- Making ordinary catalog listings contain coverage totals would break their list shape.
  A separate report lets agents request the additional information deliberately.
