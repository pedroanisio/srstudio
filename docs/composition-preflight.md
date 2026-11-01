---
generated-by: OpenAI Codex (GPT-6)
---

# Inspect a composition manifest

[Library README](../README.md) · [Drawing architecture](../DRAWING.md)

`srstudio.composition` validates a scene manifest against host-authored asset
bindings. It resolves approved part versions, coordinates, clocks, declared
contacts, supported passes and conservative work bounds. It returns immutable
records and a reproducible digest without invoking drawing builders, reading a
render cache or creating files.

This is the manifest-validation stage of SDK-P2-07. Asset preparation, payload
verification, runtime budget enforcement and atomic scene emission remain part
of that finding. A valid manifest is not a rendered scene, approval of a new
style, or proof that a host's declared asset bounds match its prepared drawing.

## Start with a real drawing

Run the [pinned paper example](../examples/composition_preflight.py):

```sh
python examples/composition_preflight.py
```

The example prepares approved `papers` version 1 using the existing SDK, checks
its scene, counts its nodes, and supplies authored source bounds and a working
memory allowance. Its test checks the real drawing's control points and strokes
against those bounds. The drawing origin is a coordinate anchor; it does not
claim a hand grip or collision surface. One source drawing unit becomes 0.001
meters through the layer's explicit scale.

## Parse and inspect

```python
import json
from dataclasses import asdict
from srstudio.composition import parse_scene, preflight

# spec is a ScenePlan; bindings is an immutable tuple of AssetBinding records
request = parse_scene(json.dumps(asdict(spec)))
checked = preflight(request, bindings)
print(checked.digest, checked.cost.frames, checked.cost.engine_invocations)
```

Scene JSON uses schema `srstudio.scene-plan/1.0.0`. Unknown fields, duplicate JSON
keys, booleans in numeric fields, nonfinite numbers and excessive input graphs
are refused. Records are frozen, and nested collections are tuples. The JSON
boundary is limited to one MiB; direct dictionaries also have total string,
collection, nesting and graph limits.

`AssetBinding` is a host-side declaration, separate from agent scene JSON. The
host owns the facts about prepared geometry, anchors, source duration, work and
backend. Preflight checks consistency and supported capabilities; it does not
derive those facts from a part name. A binding has a numbered part version,
resolved through `parts.pin`, so a replaced or unapproved builder cannot borrow
the original approval metadata. A `StylePin` records the existing library
style's settings revision from `style_revision(name)`; it does not approve a
new style recipe.

## Coordinates and clocks

World coordinates use x right, y down and z toward the reference viewer. A
`Transform` applies uniform source-to-world scale, XYZ rotations in degrees,
then translation. Parent references compose that mapping once and must be
acyclic. A world camera owns the view and near plane. Vector source views must
remain frontal; declaring an off-axis pose cannot synthesize a new drawing.

Screen layers use drawing pixels and bypass the world camera. Information must
be screen-space vector geometry, above every picture layer, with no per-layer
finish. A parent frame must use the same coordinate space. Screen coordinates
cannot participate in world contacts.

`TemporalPolicy` maps an interval using
`source_start + (scene_time - start) * rate`. Source windows must fit the declared
source duration. A named state uses one pinned source asset. Adjacent continuous
windows must retain source time, rate and world placement; cuts are explicit.
No noise-channel or facial-transition behavior is inferred from these records.

Contacts compare authored world anchors over an explicit interval. Static
anchors and piecewise-linear source tracks are supported. The validator checks
the union of both tracks' key times and contact endpoints: between those times,
the difference is affine and its distance is bounded by the endpoints. Contact
sampling has a separate finite budget. This validates declared coordinate
agreement; it does not solve a skeleton or infer biomechanical validity.

## Costs and unsupported requests

| Estimate | Meaning |
| --- | --- |
| Frames and output pixels | Exact ceiling from decimal duration and rational fps |
| Nodes | Declared nodes per layer plus container allowance |
| Unique plates | Distinct content keys in used asset bindings, assuming a cold cache |
| Engine invocations | Sum of the distinct jobs' declared attempts |
| Samples and bounces | Pixel path samples summed across jobs; maximum bounce count |
| Memory bytes | Declared asset working storage, largest sequential job, two RGBA frame buffers and node allowance |
| Contact samples | Actual endpoint/key comparisons performed by manifest validation |

Work declarations sharing a content key must match. Input binding order does
not change the result, and unused bindings do not contribute work. Memory is a
planning allowance, not measured or enforced process RSS. Cache reuse can make
actual render work smaller; preflight does not inspect cache contents.

Cross-layer shadow receivers, split-pass intersections and per-layer finish
currently refuse with `composition.capability`. A lit scene refuses vector
picture assets without a shared-light adapter. Missing passes are never dropped.
These refusals keep unsupported emission behavior explicit while its adapters
are implemented.

Catch `CompositionError` and inspect `to_dict()` for `code`, `path`, `actual`,
`expected` and `remedy`. Version failures preserve the underlying part error as
their cause. Correct the named field before retrying; validation never mutates
the supplied manifest or binding records.
