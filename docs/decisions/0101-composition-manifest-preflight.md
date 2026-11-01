---
generated-by: OpenAI Codex (GPT-6)
---

# ADR 0101: Composition manifest preflight

- Status: accepted (2026-11-01)
- Back to the [library README](../../README.md)

## Decision

Separate strict scene requests from host-authored asset bindings. Frozen public
records describe style/part pins, source units, a camera, lights, ordered layers,
clock mappings, anchors and finite budgets. A bounded parser rejects unknown
fields and mutable or ambiguous values. Read-only preflight resolves real part
approvals, checks declared relationships and returns immutable cost evidence.

Preflight does not execute arbitrary builders to discover their behavior. The
host must supply authored bounds and capabilities for a prepared asset. Part
approval and manifest consistency are verified independently of that declaration's
geometric truth. Source preparation and bounded atomic emission must verify the
actual payload before SDK-P2-07 is complete.

World and screen spaces are distinct. Information bypasses world projection and
finishing. Parent transforms compose source scale once. Source clocks are
explicit, and continuous windows cannot silently reset them. Static and linear
anchor tracks support deterministic contact checks at all relevant boundaries;
convexity bounds each intervening linear segment. A finite contact-sampling
budget limits that validation work separately from path-tracing samples.

Cold work estimates deduplicate content-addressed plate jobs and retain their
declared sample, bounce, invocation and memory bounds. Memory estimates describe
working allowances rather than process RSS. Unsupported passes, shading,
receivers and intersections produce actionable refusals.

## Alternatives

- Calling a builder during manifest validation could render, mutate a cache or
  perform unrelated work before cross-layer failures are known.
- Inferring scale, anatomy or surface geometry from catalog names would invent
  semantics that the registered drawing does not supply.
- Accepting arbitrary JSON dictionaries as validated plans would leave unknown
  fields, shared mutable input and unbounded traversal in the repair loop.
- Sampling contacts only at interval ends would miss an interior excursion.
  Linear anchor tracks permit a complete boundary check without a dense grid.

The implementation and its current boundary are described in the
[composition guide](../composition-preflight.md). This decision implements
manifest validation and preserves the complete emission and animated-proof
requirements in [DRAWING.md](../../DRAWING.md).
