---
generated-by: OpenAI Codex (GPT-6)
---

# ADR 0086: Declare character semantics at registration

- Status: accepted (2026-11-01)
- Back to the [library README](../../README.md)

## Decision

Every built-in registered character carries explicit core capabilities and family-specific units, clocks,
vocabularies and helper metadata. Repeated semantics are assembled by internal factories that receive explicit
arguments at registration. The factories never infer behavior from a name or invoke a builder. The registered
callable and its actual typed records remain authoritative; drawing, timing and defaults are unchanged.

Capabilities describe the selected callable: typed limb replacement, authored HeadPlan input, and named facial
controls are distinct. A held tilt, idle movement or external performance adapter does not grant a capability to
a wrapper that cannot accept it. Rafa's static body builder therefore has false facial capabilities; its separate
face constructor is a discoverable operation. Soft's existing pose interpolation and foot pinning are explicit
additional capabilities. Custom Stick pose names remain open references into the supplied mapping.

Metadata distinguishes project, canvas, entry-relative and take-relative clocks. Exit times and interval lengths
carry separate roles. Nested metadata can decorate nullable sequences/tuples and common fields in record unions;
every non-null branch must support the requested structure. Incompatible alternatives fail metadata validation
instead of being silently omitted.

## Verification

Tests inspect all registered characters without drawing, execute representative family builders from declared
vocabularies, exercise invalid inputs and constructor bounds, and check nonzero entrance timing. Existing family
tests retain drawing behavior. The authoring reference includes an executable discovery-to-drawing recipe.

## Alternatives and limits

A second runtime registry of inferred metadata would drift from registration and could survive a replaced
builder. Deducing clocks from names would confuse duration lengths with project exit times. Treating every rig
as an Actor would misrepresent model builders and held-drawing APIs. Explicit family declarations avoid those
assumptions while retaining the existing plugin contract and replacement/restore behavior.

Discovery does not decode generated JSON, replace runtime semantic validation, or promise physical/perceptual
quality. Runtime objects, legacy extras and unresolved plugin annotations remain explicitly incomplete. New
actor adapters and acting composition build on these declarations rather than changing their meaning.
