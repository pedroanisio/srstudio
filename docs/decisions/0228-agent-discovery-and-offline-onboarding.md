---
generated-by: OpenAI Codex (GPT-6)
---

# ADR 0228: Versioned discovery and offline onboarding for agents

- Status: accepted (2026-11-04)
- Back to the [library README](../../README.md)
- Builds on [ADR 0086](0086-character-discovery-semantics.md)

## Context

Commit `74b15444` added discovery and onboarding commands without a decision record or a commit body.
This record supplies the missing rationale and describes their current contract, including the subsequent
body/keyed-motion schemas and acting-rig vocabulary. An agent needs bounded discovery, explicit input shapes
and a runnable first build without reading the entire catalog or supplying external service credentials.

## Decision

- `catalog --search`, `--summary`, `--fields`, capability filters and pagination expose compact, stable pages.
  Unknown filters and fields are repairable errors. Capabilities come from declared metadata; absent metadata
  does not imply support. The existing unpaged catalog stays available.
- `schema --json` lists document names, versions, parser/compiler entry points and guides. `schema NAME
  --version VERSION --json` returns a self-contained JSON Schema 2020-12 document. Omitted versions select
  the latest supported version; reproducible callers pin a version. Acting, body and solved limb playback
  are distinct formats. These document schemas are separate from Python callable contracts.
- Structural validation precedes runtime parsing and compilation. Geometry, timing relationships, finite
  numbers, Python integer representation, rig capabilities and cumulative budgets still need runtime checks.
  Schema metadata states those obligations. Schemas are produced from package code and work outside a checkout;
  `jsonschema` is a test dependency, not a new runtime dependency. Contributors install the `test` extra in the
  interpreter used by the gate; adding a dependency to pyproject does not update an existing shared environment.
- `ActingRig.describe()` exposes the vocabulary used by runtime validation and the selected rig's numeric
  limits, units and input paths. Unsupported controls have empty vocabularies/channels. Numeric envelopes do
  not certify emotional intent or perceptual realism.
- `init ROOT` stages a runnable Cutout starter with synthetic inputs, a build script and a bundled licensed
  DejaVu Sans Bold font. It works offline and refuses replacement unless `--overwrite` is explicit. It returns
  file names and concrete build/render commands. Creation does not render or grant drawing approval.
- `doctor` reads local prerequisite state and probes the engine's version command. It does not install packages,
  download assets or render. Build readiness, optional validation and render readiness remain distinguishable.

## Alternatives and limits

Parsing documentation prose or dumping the entire catalog wastes agent context and permits vocabulary drift.
Treating callable signatures as document schemas would accept runtime objects in data-only inputs. Treating
schema validation as semantic validation would miss support, contacts and rig-specific limits. Downloading a
font during initialization would make the first build depend on network state. These commands make inputs and
prerequisites inspectable while preserving the runtime validators and explicit output ownership.

## Verification

Discovery tests check stable pages, valid filters and compiler acceptance of advertised intent vocabulary.
Schema tests compare versioned shapes with parsers, reject malformed nested records and execute documented
round trips. Onboarding tests cover offline creation, overwrite refusal and readiness reporting. The repository
gate uses the shared environment's declared test dependencies; no temporary dependency directory substitutes
for successful collection there.
