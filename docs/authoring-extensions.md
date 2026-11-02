---
updated-by: OpenAI Codex (GPT-6)
---

# Extend drawing APIs

[Library README](../README.md) · [Authoring task index](authoring-reference.md)

Import `register` from `srstudio` to expose a builder and `Canvas` for its drawing context. Bind an existing canvas and parent; use their declared clock rather than assuming every parent starts at project zero. [Contract examples](authoring-discovery.md#agent-contracts) include executable plugin success and failure cases. The guide below defines one-call atomicity, registry errors and ID behavior.

Run commands from the srstudio repository root.

### Extending drawing calls

`Canvas.keys()` builds and validates the complete animation before attaching it to the scene. A failed key
conversion or SDK validation leaves existing nodes and scene bytes unchanged, so a corrected call can be retried
on the same canvas. Frozen drawings also validate the supplied keys before retaining only the initial value.
This atomicity covers one `keys()` call; it does not roll back separate drawing calls made earlier.

Plugin decorators can add `slots=("at_table",)` for unannotated callback parameters and
`examples=("...Python code using ep...",)` for their own usage examples. The library's `Slot` annotations
are discovered automatically. A declared slot must name an explicit location builder parameter.

```python
from srstudio import register

@register("prop", "tip_jar", summary="A glass tip jar")
def tip_jar(cv, parent, x, y, scale=1.0):
    g = cv.group(parent, cv.uid("tip-jar"), x=x, y=y, scaleX=scale, scaleY=scale)
    cv.rect(g, -40, -90, 80, 100, radius=10, fill="#DDEAF2", stroke=cv.ink, sw=3)
    return g
```

Kinds are `character`, `location`, `prop`, `graphic`. A new location is complete only when it places both marks
of the [Signature](authoring-delivery.md#signature) convention. Registering the same kind and name twice raises `RegistryError`;
use `@register("prop", "tip_jar", replace=True)` when intentionally replacing a builder.
Parts from another package are listed with
`srstudio catalog --plugins my_package.parts`. A new episode is a script like the ones in [episodes/](../episodes):
it takes the project folder as its first argument and is run with `python3 episode.py PROJECT`,
`srstudio build episode.py PROJECT` or, once it has a release, `srstudio build <slug> PROJECT`. Its recorder
(`<script>_audio.py`, front end `srstudio.recording.main`) runs with `srstudio record <slug> PROJECT`
([ADR 0032](../docs/decisions/0032-releases-recorders-and-discovery.md)). `srstudio.sample.write_sample_project` writes a synthetic project (dialogue,
tone-burst soundtrack, font) to try a build without a TTS pass.

srstudio-defined errors derive from `srstudio.SrstudioError` and retain their built-in base (`ValueError` for bad
data, `RuntimeError` for a provider failure). The underlying SDK can also raise `sr_core.scene.SchemaValueError`
for invalid scene values, and filesystem operations can raise `OSError`. Catch those separately when needed.
A missing API key
is `MissingKeyError`, a provider HTTP failure `ProviderHTTPError`, and a builder given a flag it does not know raises
`FlagError` before building anything (`srstudio.errors.flags`;
[ADR 0034](../docs/decisions/0034-one-error-base.md)).

Built-in `shared_counter()` and `flat_counter()` ID namers rewind when a transactional authoring call fails, so a retry uses the same IDs as a fresh call. A custom `namer` owns its own state and is not automatically rewound.

Malformed timeline records and JSON raise `TimelineError` with field or file context. Catalog lookups with an
unknown kind raise `RegistryError`. The installed package includes `py.typed` so type checkers can use its
annotations.

`register` preserves decorated functions' type signatures. The core episode authoring helpers also expose
typed parameters and SDK return nodes. Office and café actors reject unknown performance extras and invalid
gesture values with `CastError` before drawing; subclasses can extend `extra_options` and override
`validate_performance` for custom behavior. `srstudio build` prints expected library errors as concise
diagnostics with a nonzero exit status.
