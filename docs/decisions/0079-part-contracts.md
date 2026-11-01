---
generated-by: OpenAI Codex (GPT-6)
---

# ADR 0079: Describe part shapes and semantics without drawing

- Status: accepted (2026-11-01)
- Back to the [library README](../../README.md)

## Decision

Part inspection exposes `srstudio.part-contract/1.0.0` alongside its existing Python signature and examples.
Argument and return representations use JSON Schema 2020-12. Resolvable annotations describe primitives,
literals, nullable values, sequences, tuples, mappings, typed dictionaries, and dataclasses. Unresolved and
recursive types remain explicitly unknown. Runtime objects remain runtime bindings. Expansion stops at eight
type levels or 2000 shape visits per callable; helper operations have a four-level nesting limit.

Frozen metadata supplies units, clocks, bounds, capabilities, vocabularies, and helper operations. Metadata is
checked before replacing a registry entry and restored with the original builder. Default values do not supply
missing annotations. Registration does not change drawing or introduce validation that an existing builder did
not have. Shape completeness is separate from semantic validity; every contract requires runtime validation.

Actor inspection separates construction from building and publishes the capabilities and names exposed by the
base rig. Overridden build methods keep their own signatures without inheriting unverified placement semantics.
Bento explicitly declares held head motion and no limb-track replacement, the project exit meaning of duration,
relative pose clocks, and the names its pose factory accepts.

## Verification

Tests inspect every registered entry without drawing, exercise nested and unresolved types, verify CLI JSON,
check malformed metadata and replacement restoration, and execute the documented plugin's valid and failing
paths. Existing catalog templates and examples keep their original behavior.

## Alternatives

Parsing prose or inferring capabilities from argument names would silently turn incomplete information into
false guarantees. A second registry of hand-written signatures would drift from the callable. A universal JSON
executor would need additional typed decoders and runtime binding rules; this discovery contract does not claim
to supply either. Builders and their typed constructors retain semantic validation.
