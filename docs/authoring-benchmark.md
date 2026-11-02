---
generated-by: OpenAI Codex (GPT-6)
---

# Measure the authoring loop

[Library README](../README.md) · [Authoring reference](authoring-reference.md)

Run the pinned, font-free fixtures with the renderer you use for production:

```sh
python -m srstudio.benchmark \
  --engine /absolute/path/to/scene-render \
  --output generated/authoring-benchmark/report.json \
  --repeats 3
```

Each repeat starts a fresh Python process and an empty plate cache. The report
separates package import, complete catalog discovery, performance planning,
scene compilation, rendering, cache reuse and fresh-render verification. Fixtures
cover coordinated vector acting, a moving limb contact and two lit 3D plates.
The drawing fixtures contain eight frames at 360 × 640 and eight frames per
second. The plates are 64 × 64. No fonts or network downloads are needed.

| Measurement | Meaning |
| --- | --- |
| `entries` | Described registry entries, including their public contracts |
| `state_samples` | Explicit plan samples on the nine-point fixture grid |
| `audited_motion_samples` | Samples reported by the limb compiler's audit |
| `frames` | Frames compiled or rendered in that phase |
| `plates` | Requested plate definitions; verification renders each again |
| `engine_invocations` | Renderer launch attempts; warm plate hits must use zero |
| `observations_seconds` | Wall time for each repeat, including result hashing |
| `peak_worker_rss_bytes` | Worker process lifetime peak memory, excluding renderer and GPU memory |

Counts are per phase and per repeat. The sample counts do not include every
internal sampler call. Adding compilation and recompilation counts would count
the same intended frames twice.

Cold means a fresh application process/cache. OS filesystem and GPU caches are
not flushed. Warm discovery and warm plate reuse happen in the same process;
plate reuse includes renderer identity hashing. Recompilation measures another
build with the same plan; it does not claim that compilation is cached.

The report records fixture parameters, package versions, Python source hashes,
renderer bytes, platform and configured renderer selectors. Pin GPU hardware,
drivers, dependencies and host load separately when comparing timings. Use the
recorded phase output hashes to check equivalence when evaluating an optimization.
Different renderers may legitimately produce different pixels; compare within
one pinned toolchain before making a performance claim.

Repeats are limited to 1–7. `--worker-timeout` defaults to 300 seconds and
`--engine-timeout` to 60; both must be positive, at most 600 seconds, and the
engine limit cannot exceed the worker limit. These limits stop runaway work;
they are not performance targets. The benchmark requires POSIX process groups
so a timed-out worker and its renderer descendants can be stopped together.

Unknown worker fields, incomplete measurements, output differences, renderer
failures and toolchain changes refuse publication. A previous report survives
failure. Successful reports are atomically replaced with mode `600`, and private
working directories are removed. CLI failures emit a structured diagnostic to
stderr and return status 2. Ordinary correctness tests assert output and work
counts, without timing thresholds.

## Bound a plate authoring operation

```python
from srstudio import plates

with plates.render_session(max_invocations=2, timeout=30, max_memory_bytes=8 * 1024**3) as work:
    image = plates.render(plate, engine=engine, cache=cache, fonts=fonts)

print(work.invocations, work.completed, work.failed, work.engine_seconds)
```

The scope covers plate and printed-texture renderer launches, including nested
calls. Every enclosing scope spends a launch attempt, and the shortest active
timeout and smallest memory allowance apply. Cached images spend no attempts. Use `max_invocations=0` to
require cache reuse. Changing the returned stats does not restore the budget.
After scope exit, the previous limits are restored.

The default memory allowance is 8 GiB. `max_memory_bytes` accepts an integer from
1 byte through 1 TiB and caps each renderer process's virtual address space using
POSIX `RLIMIT_AS`, including runtime library mappings. It does not cap aggregate
RSS or GPU memory. Each captured output stream is limited to 64 KiB. Timeouts and
other failures terminate the owned process group, including descendants retaining
output pipes after their leader exits. Failed renders cannot publish partial
cached images. Launch failures and explicit retries consume attempts; the SDK
does not retry automatically.

`PlateError.to_dict()` reports `plate.render.budget`, `plate.render.timeout`,
`plate.render.output` or `plate.render.engine` with repair information. Process
failures retain the typed cause and a bounded stderr excerpt. A memory-limited
native exit is reported as an engine failure; its exit code alone cannot prove
memory exhaustion.

The scope limits synchronous renderer work in its context. Mesh preparation,
image decoding and unrelated renderer APIs remain outside these limits. Calls
without a session retain their existing execution behavior. This is resource
control for trusted renderer programs, not a security sandbox.
