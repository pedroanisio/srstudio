---
generated-by: OpenAI Codex (GPT-6)
---

# ADR 0094: Explicit drawing execution events

- Status: accepted (2026-11-01)
- Back to the [library README](../../README.md)

## Decision

Registration instruments the returned callable. Class registration preserves the
class itself and instruments its own methods, retaining static/class descriptors.
Inherited methods retain their defining class's attribution. Existing signatures,
annotations, positional/keyword default metadata, function kinds and
wrapped-function introspection remain available. Source-cost measurement unwraps
functions before resolving their global helpers, retaining transitive counts.

Shared Gloss, News, Inked News and Host performers explicitly identify their
owning registered callable. Head rigs and Canvas allocation already emit the
same event stream. Usage tracing resolves callable identity against a registry
snapshot; a retired callable cannot claim a replacement's registration. Explicit
name strings deliberately identify the current registered name and reject unknown
names. There is no profiler installation or source/frame/closure inference.

Generators emit scopes for each resume, including protocol send, throw, close and
return. Their caller's code between yields is outside the drawing. Async
generators follow the same rule; coroutine scopes cover awaited execution and
cancellation cleanup. Constructing a deferred object does not claim usage.
Catalog Entry calls also bind raw replacement functions to their current identity,
including deferred objects created before tracing begins.

Observers use context variables; each trace holds its active figure in a context
variable too. Independent tasks can interleave without combining their figures.
Nested drawings assign IDs to the outermost character, and nested traces each
receive the events. A task created inside a character scope inherits its ownership
and must finish before that scope closes. This does not authorize concurrent
mutation of one Canvas. Closing observation disables callbacks retained by copied
contexts, so callers must join their drawing tasks before leaving the trace.

Failures retain attempted usage and partial allocated IDs for diagnostics.
`recorded()` continues to refuse records for failed builds. Generator resumes can
produce separate figure records, matching the previous call/resume granularity.

## Evidence

The committed usage fixture was captured from `ea60f48d` before this migration.
It preserves used-part sets, figure IDs and exact scene XML hashes for Actor,
closure-based Collage, Gloss, both News anchors, both Inked News anchors, Host
and a Toon head rig. Tests cover active profilers, missing Python source,
replacement identity, method descriptors, nested/failing drawings, deferred
execution protocols, cancellation, interleaved tasks and closed observers.

Implementation-specific AST/frame-inference tests are replaced by tests of
explicit owner selection and actual registered calls. The unregistered-closure
test unwraps the instrumentation before copying the original closure. It still
proves that a lookalike function cannot claim a registered drawing.

## Alternatives

Keeping a profiler fallback would preserve dependence on Python source and local
names, replace other profiling tools and prevent nested trace composition.
Wrapping generators across `yield` would wrongly capture their caller's IDs.
Rejecting deferred builders would narrow accepted registration behavior. Explicit
execution scopes preserve those workflows while giving attribution one owner.
