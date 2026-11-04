---
updated-by: OpenAI Codex (GPT-6)
---

# Verify scenes, motion and delivery

[Library README](../README.md) · [Authoring task index](authoring-reference.md)

An agent should choose the checks required by its task before building. A successful script exit means the
script completed; it does not establish that every check ran, a video was rendered, or a drawing was approved.

## Verification

For an installed SDK, create a project and require SDK validation and usage recording:

```bash
srstudio init hello --json
srstudio build --json --require-check sdk --require-check usage hello/build.py hello
```

The explicit final `hello` is the project root. It enables usage recording and post-build frame checks.
Use the `build` argument array returned by `init --json` when paths contain spaces. Build-level options must
precede the script; options after the script/root belong to that script.

For frame checks, install the engine, set `SRSTUDIO_ENGINE` or put `scene-render` on `PATH`, and require both
rules. This repeat build deliberately replaces the starter's previous outputs:

```bash
srstudio doctor --json
srstudio build --json --require-check sdk --require-check schema --require-check anatomy --require-check text hello/build.py hello --overwrite
```

Inspect the build result's `checks` mapping. Each entry has `status: passed|failed|skipped` and per-execution
`results` with paths, reasons and findings. `skipped` is not evidence of success. Missing engines, unavailable
frame measurements, and checks never invoked by the builder remain skipped. A required check must pass for
every recorded execution. The command exits nonzero if a required check fails or is skipped.
This also applies to builders that finish with `sys.exit(0)` or `sys.exit()`.

| Check | Evidence and limits |
| --- | --- |
| `sdk` | SDK scene checks invoked through `Episode`; findings remain attached. |
| `schema` | XSD/Schematron checks, available with `srstudio[validate]`. |
| `motion-quality` | Sampled limb audits against explicitly selected `QualityProfile` limits. |
| `usage` | This build wrote the parts, figures and anatomy usage records; setup-only restoration is skipped. |
| `anatomy` | Post-build anatomy frame rules completed for the selected scenes. |
| `text` | Post-build text frame rules completed for the selected scenes. |

`artifacts` lists absolute paths published by this invocation's instrumented SDK operations. It does not scan
old files to infer outputs. Custom builders writing files or calling sr-core directly must not infer verification
from an empty artifact list or skipped SDK checks. A failure diagnostic retains available build evidence at
`context.build`. A later failure can leave published artifacts; inspect the report before retrying.

Frame checks select every scene published through `Episode.finish()` in this invocation, including custom
names and output directories, excluding `*.audio.scene.xml`. They use the supplied project root for usage
records. Old scenes in that directory are not measured on behalf of a new build. A builder that writes scene
files directly must explicitly record each completed publication with
`srstudio.build_report.artifact('scene', scene_path)` to include it in post-build frame checks. This records
an output, not SDK validation; it does not make `sdk` or `schema` pass.

### Requiring sampled motion limits

Select a `QualityProfile` in each limb track's or compiler's `BakeOptions.quality`,
then run `srstudio build --json --require-check motion-quality build.py`.
Each result's `evidence` contains the full profile (name, limits, policy and optional
calibration scope), `sampling`, and the measured `report` with structured
`quality_findings`. Compiler sampling names the track, style, fps, source duration
and placement offset. The start/end and minimum/maximum interval describe the
samples actually audited, including short final intervals; they are motion seconds.

A warn-policy breach records `failed` while permitting emission. Requiring the
check makes that build exit nonzero. Error-policy breaches record their metrics and
findings before raising; scope or geometric refusals retain a structured `error`.
No audit, no selected profile, or a profile without limits produces `skipped`.
Insufficient samples for an enabled derivative limit produce failed evidence.
Every recorded audit must pass when the check is required, including preflight.

Emission may reuse numeric preparation validated against identical inputs;
`evidence.cached=true` identifies that reuse and retains its profile and sampling
provenance, including when preparation happened before this build capture. Existing
files never satisfy the check. These are sampled limb limits: whole-body dynamics,
continuous collision safety, temporal realism and visual approval need separate
checks and rendered review.

### Reading results and retrying

These JSON excerpts show selected fields; real results include all six check entries and execution details.
On exit zero, read stdout. Here SDK validation passed but no anatomy measurement ran:

```json
{
  "schema": "srstudio.build/1.1.0",
  "status": "ok",
  "artifacts": [{"kind": "scene", "path": "/work/hello/hello.scene.xml"}],
  "checks": {
    "sdk": {"status": "passed", "results": [{"status": "passed", "path": "/work/hello", "reason": "", "findings": []}]},
    "anatomy": {"status": "skipped", "results": [{"status": "skipped", "path": "/work/hello", "reason": "engine unavailable", "findings": []}]}
  }
}
```

On a nonzero exit, read stderr. Requiring anatomy in that situation produces a diagnostic containing the
already-published scene. `context.build.checks` has the same structure as success `checks`:

```json
{
  "schema": "srstudio.diagnostic/1.0.0",
  "code": "build.required_checks",
  "path": "require_check",
  "actual": {"anatomy": "skipped"},
  "expected": "passed",
  "context": {
    "command": "build",
    "build": {
      "artifacts": [{"kind": "scene", "path": "/work/hello/hello.scene.xml"}],
      "checks": {"anatomy": {"status": "skipped", "results": [{"status": "skipped", "reason": "engine unavailable"}]}}
    }
  }
}
```

1. Read the exit status and diagnostic before choosing a retry. Argument or lookup failures may have no
   `context.build`; do not assume artifacts were produced.
2. Repair the reported field or missing dependency. For failed frame checks, inspect each result's scene
   path and findings. Retrying identical inputs cannot fix a deterministic validation failure.
3. Inspect `context.build.artifacts` before repeating a failed build. Verification happens after publication,
   so a failure can still leave usable files. Choose a fresh output directory, or deliberately replace the
   previous outputs with the builder's overwrite option. The starter accepts `--overwrite` after its root.
4. Repeat the same required checks and evaluate the new report. An old report or scene does not satisfy them.

For the starter, after repairing an engine configuration failure:

```bash
srstudio doctor --json
srstudio build --json --require-check sdk --require-check anatomy --require-check text hello/build.py hello --overwrite
```

These checks do not encode a video or establish visual approval. Render with the separate scene-render engine;
`srstudio master` installs encoded masters write-once ([ADR 0170](decisions/0170-approved-files-are-write-once.md)).
Use [composition checks](composition-preflight.md) and [motion-quality studies](../examples/limbs_quality.py)
for their respective numeric, temporal and visual acceptance criteria.

## Tests for contributors

Run these commands from the **srstudio repository root**, after installing `.[validate,test]`.
They are repository checks, not requirements for consumers of an installed wheel.

```bash
python -m pytest -q tests/test_agent_discovery.py tests/test_agent_build_report.py tests/test_acting_document_schema.py tests/test_agent_verification_docs.py
python -m pytest -q tests/test_api_boundaries.py tests/test_timeline.py tests/test_styles.py tests/test_build.py
```

| Changed behavior | Relevant local tests |
| --- | --- |
| CLI output, project setup and diagnostics | `tests/test_cli.py`, `tests/test_onboarding_commands.py`, `tests/test_devx_review.py`, `tests/test_diagnostics.py` |
| Discovery and call contracts | `tests/test_catalog_contracts.py`, `tests/test_character_contracts.py`, `tests/test_noncharacter_contracts.py` |
| Build lifecycle and output protection | `tests/test_api_lifecycle.py`, `tests/test_finish_output_safety.py`, `tests/test_authoring_review_fixes.py` |
| Style and drawing helpers | `tests/test_ink_layout.py`, `tests/test_cel.py`, `tests/test_stick.py`, `tests/test_toon.py` |
| Soft cues, motion and locations | `tests/test_soft_cues.py`, `tests/test_blob_motion.py`, `tests/test_soft_home.py` |
| Audio, fonts and layout | `tests/test_audio.py`, `tests/test_music.py`, `tests/test_fonts.py`, `tests/test_layout.py` |
| Documentation routes and inline test references | `tests/test_authoring_navigation.py`, `tests/test_agent_verification_docs.py` |

Tests requiring the renderer or external fixtures can skip when those dependencies are unavailable: inspect
pytest's skip summary before claiming those behaviors were verified. For a bounded local check without renderer
work, use `python -m pytest -q -m 'not slow' -rs`. The full suite and coverage gate remain repository requirements.

```bash
ruff format --check src tests tools
ruff check src tests tools
mypy src
```

Episode-specific scripts and their historical verification belong to the separate
[srstudio-episodes repository](https://github.com/pedroanisio/srstudio-episodes).
This guide lists tests present in this SDK checkout; it does not assign external episode tests to local paths.
