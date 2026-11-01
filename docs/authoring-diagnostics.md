---
updated-by: OpenAI Codex (GPT-6)
---

# Repair failed authoring input

[Library README](../README.md) · [Authoring task index](authoring-reference.md)

Catch the documented error, inspect its typed repair fields, and validate a corrected request before retrying. The recipe below uses `HeadMotionError`; scene-construction errors may also come from `sr_core.scene.SchemaValueError`. See [extension failures](authoring-extensions.md#extending-drawing-calls) for the broader exception boundary.

Run commands from the srstudio repository root.

## Repairing authoring input

SDK failures expose `to_dict()` using `srstudio.diagnostic/1.0.0`. CLI commands with `--json` emit the same
fields on stderr and add `context.command`, including SDK failures while importing plugins. Catch the
documented exception type; use `code`, `path`, `actual`, `expected` and `remedy` to identify the repair rather
than parsing the human message. Older validation sites that have not declared these facts retain null fields.
Invalid canvas key times raise `KeyTimeError`, catchable as both `CanvasError` and the existing
`sr_core.scene.SchemaValueError`; serializing the error preserves its SDK repair fields.

Common explicit paths include `style.breath_period`, `spring.damping`, `channel.keys[1][0]`,
`speech[0].words`, `heard[0].words`, `facing[0]`, `gaze[0][1]`, `performance.mouth[0][1]`,
`blink.period`, `visibility[0]` and `keys.rotation[1][1]`. Their code families are `head.style.*`,
`head.spring.*`, `head.channel.*`, `head.speech.*`, `head.facing.*`, `gaze.*`, `rig.*` and `canvas.*`.
The path identifies the supplied input, not a general-purpose object mutation expression.

This example repairs one known invalid setting and compiles a new plan. An agent should validate its proposed
correction through the same typed constructor. Unsupported capabilities require changing the request or rig;
retrying unchanged input cannot add a capability.

<!-- diagnostic-repair:start -->
```python
from dataclasses import replace

from srstudio.acting import BENTO
from srstudio.head_motion import HeadMotionError, plan

style = BENTO.head_rig.style
try:
    replace(style, breath_period=0)
except HeadMotionError as error:
    failure = error.to_dict()
    assert failure["code"] == "head.style.range"
    assert failure["path"] == "style.breath_period"
    assert failure["expected"] and failure["remedy"]
    repaired = replace(style, breath_period=3)

motion = plan(repaired, [], 4)
motion.check_bounds(repaired)
```
<!-- diagnostic-repair:end -->

Diagnostics are bounded previews, not a lossless copy of invalid input. Each payload field has a shared
1,000-node traversal budget and 16,384-character content budget, with at most 100 items per collection,
eight nesting levels and 4,096 characters per string. Metadata strings are capped at 4,096 characters.
Markers report exhausted traversal or depth; nonfinite numbers become strings, and opaque objects become
type labels. JSON escaping and punctuation add encoded bytes beyond these content budgets.

Generated blink schedules refuse more than 10,000 blinks before drawing. Carried springs also enforce their
sampled-key budget and scene clock precision. Reduce the requested work or use a suitable local clock when
those diagnostics fire. The tested mouth, visibility and keyframe preflights leave their scene unchanged;
this is not a blanket transaction guarantee for every legacy builder.

Head planning also preflights procedural schedules: at most 10,000 estimated breathing cycles or glance
candidates, and 100,000 estimated keys per idle channel. Estimates use the shortest seeded interval and
include rounding allowance; suppressed glances still consume planning work. Intervals must preserve the
six-decimal scene clock. `head.plan.budget` and `head.plan.precision` identify the responsible style field or
duration. Increase the interval, reduce frequency, or compile a shorter source performance, then use its
windows for cuts. These limits do not establish perceptual quality or an execution-time guarantee.
