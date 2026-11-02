---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0171: One GPU job at a time

- Status: proposed (2026-11-01), on the operator's approval to port four ideas from pnkit; written by Claude Opus 5.5
  in Claude Code
- Source of the idea: pnkit, the operator's other kit: `~/heavy.lock` taken around every heavy render, and
  `tools/vm_preflight.py`, which names the lock's holders from `/proc/locks` and `ps`; rewritten here in srstudio's
  style rather than copied
- Back to the [library README](../../README.md)

## Context

The machine has one GPU (an RTX 3050), and the test gate, plate path-tracing, proxy rebuilds, the clay and paintover
studies and every encode share it. The gate's `test_proxy` warm rebuild failed with the engine's "Not enough memory
left" while another render held the card, and passed alone. Nothing in srstudio knew another job was on the GPU.

Which engine calls use the GPU was measured, not assumed: each verb ran under `strace -f -e trace=openat` on a copy of
a built reel, counting opens of `/dev/nvidia*` and `/dev/dri/*`.

| Verb | Device opens |
|---|---|
| `render` (one frame) | 114 |
| `encode --hw software` | 117 |
| `encode` (hardware encoder) | 393 |
| `gpus` | 104 |
| `validate`, `eval`, `resolve`, `captions`, `inspect`, `scopes`, `--version` | 0 |

`--hw software` changes the encoder, not the renderer: its log says "rendering on NVIDIA GeForce RTX 3050 (Vulkan,
DiscreteGpu)", its video carries libx264's SEI, and `nvidia-smi` sampled the process on the card during a 4 s encode
(peak 424 MiB). `scopes` loads the Vulkan library but opens no device.

## Decision

1. **`srstudio.gpu.held()`** is a context manager that takes an exclusive `flock(2)` on one file and gives it back
   when the block ends, on success or error. The kernel drops the lock with the process, so a crash never leaves the
   GPU taken.
2. **The file is `/run/lock/srstudio-gpu.lock`**, or `$SRSTUDIO_GPU_LOCK`. `/run/lock` is where the file-system
   hierarchy puts locks for devices that many programs share. It is writable by every user (mode 1777), on a tmpfs
   that a reboot clears, and it is one path for the whole machine: every worktree, venv, session and agent meets the
   same file. The file is opened with `O_NOFOLLOW`, so a symbolic link planted at that path is refused.
3. **The wait is bounded by ordinary code.** `held` polls with `LOCK_NB` every 0.25 s until `$SRSTUDIO_GPU_WAIT`
   seconds pass (900 by default, pnkit's bound). Then it raises `GpuBusyError`, which is both an `SrstudioError` and a
   `TimeoutError` with code `gpu.busy`. The error names each holder and each waiter by pid and command line, read from
   `/proc/locks` by the file's device and inode. A wait that is not a finite number of seconds, at least 0, is a
   `GpuLockError`.
4. **It is re-entrant within a process and taken at the leaf.** The lock wraps each engine call alone, never a wait on
   a worker, so a parent never holds the GPU while its child waits for it. A forked child does not inherit the
   parent's hold.
5. **The call paths that take it** are every `render` and `encode` the library, the pilots and the tools start:
   - `plates._engine_render`, which covers plate path-tracing, `proxy` pictures, printed materials and composition
     bundles. The wait happens before the render budget is spent and outside the engine-seconds count.
   - `master.encode`, which covers `srstudio master`.
   - `frames.at_size` (`srstudio frames`), `social.take_still` (the cover still), `thumbnail.render`,
     `cast_card._draw`, `bible_diagram.render`, `show_gate._render_corner`, `catalog_page`'s pose sheet,
     `catalog_specimens._render` and the poster render, and `benchmark._render_frames` (in its worker process).
   - `episodes/pilots/pedro_drive.encode`, the stills in `pedro_drive_3d.main`, `pedro_drive_toon_gates.render`, and
     `tools/creationbot_avatar.main`.

   `validate`, `eval` (layout and framegraph), `resolve` (generated audio), `captions` and `scopes` do not take it.
6. **A test that can fail holds the rule in place.** `tests/test_gpu.py` reads every module in `src/srstudio`,
   `episodes` and `tools`, finds each command literal `[engine, "render" | "encode", ...]`, and fails when no
   `with gpu.held()` covers it.
7. **Hand-run renders can join the lock.** util-linux `flock(1)` takes the same lock: run
   `flock -w 900 /run/lock/srstudio-gpu.lock scene-render render ...`. This was checked both ways against `held`.

## Consequences

- The gate's proxy tests now wait for another GPU job instead of running beside it out of memory. If the other job
  holds the GPU past the wait, they fail with `GpuBusyError` naming that job, not with the engine's memory error.
  Render tests in a parallel run take turns on the GPU, so a gate that runs them in parallel spends that time waiting.
- A render started outside srstudio (a bare `scene-render` in a shell, or another kit) does not see the lock unless it
  goes through `flock(1)`. The lock is advisory, and the GPU itself does not enforce it.
- A wait counts against no plate render budget and no process timeout, because both start after the lock is taken.

## Alternatives rejected

- **`~/heavy.lock`, pnkit's place.** Each user's home is its own, so a second user or a service account would not
  see it. A home directory also survives reboots, while a lock file belongs with the machine's runtime state.
- **`/tmp`.** It is a tmpfs here too, but anyone can replace or delete a file in `/tmp`, and pytest's folders under it
  are pruned. `/run/lock` is the place the hierarchy names for this purpose.
- **`$XDG_RUNTIME_DIR`.** It is per user and per login session, and a systemd unit may have none.
- **A file in the repository or under `generated/`.** Each worktree has its own, so two worktrees would render at
  once. That is the case the lock exists to stop.
- **A blocking `flock` with `alarm` for the timeout.** Signals do not mix with threads or with library code. Polling
  with `LOCK_NB` keeps the bound in plain code, and a test can drive it with an injected clock.
- **Checking free memory with `nvidia-smi` before a render.** Two jobs can both see enough memory and then both start.
  Only an exclusive lock makes "one at a time" true.
- **pnkit's `ps` scan for holders.** `/proc/locks` already names the pid holding this file's lock, so no scan of
  every process is needed.
