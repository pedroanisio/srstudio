---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0058: Batches and pilot sets run as govern lanes, for state and cost

- Status: accepted (2026-10-31), from the operator's "ok, so use where it can help" after a review of what govern does
  and does not do for this process
- Deciders: the operator (pedroanisio), recorded by Claude Opus 5.5 in Claude Code
- Back to the [library README](../../README.md)

## Context

The state of running work lived in one orchestrator's conversation and memory files, so a context limit cost a long
summary and any other session started blind. Nobody could say what a reel cost in model tokens. `govern`, in the
operator's super-tools repository, keeps a lane's state in files, prints a short brief, and attributes Claude Code and
Codex tokens to lanes and stages, subagents included.

## Decision

1. One lane per batch or pilot set, not per reel: a stage is shared by every reel in it, and a lane per reel would be
   overhead with no reader.
2. `govern.config.json` sits at the workspace root, the one folder every worktree is under, so all sessions share one
   state. Lanes, queue and run state live under `generated/govern/`; the processes are source, in `tools/govern/processes/`:

   ```json
   {"projects": "generated/govern/projects", "queue": "generated/govern/queue", "state": "generated/govern/state",
    "processes": "srstudio/tools/govern/processes", "tuningLog": "generated/govern/tuning.jsonl"}
   ```

3. Two processes, `reel` and `pilot`. Both run plan, build, merge, deliver, done, and `pilot` adds `watch` after
   delivery. Merge and deliver require a check, so a note cannot pass them.
4. The checks are `tools/govern/lane_check.py`, thin over what already decides these things: `git merge-base` for the
   branch in develop, the publish check, `rclone check` for pilots on Drive. Each lane's `lane.json` names its branch
   and series. govern adds no judgement of its own.
5. `reel` has no owner gate, because the operator does not review these videos. A pilot's `watch` stage leaves on a note
   quoting the operator's words. That note records the verdict and is not the approval: parts stay approved in
   `parts.json`, tied to their drawings.
6. The commands are used from this library. govern's agent manual is not installed, because it forbids subagents and
   messages between sessions, which this process uses.

## Rejected alternatives

- **govern's built-in `video` process.** It requires owner approval of the script and the final cut.
- **`.govern/` inside this repository.** A tracked state folder gives each worktree its own copy of the state.
- **`govern approve` for parts and pilots.** Inside a Claude Code session it accepts only words typed in that session,
  while the operator also approves on Slack, and it cannot tie an approval to a drawing as `parts.json` does.
- **The task queue in place of subagents.** It runs each message in a fresh headless session, which does not suit a
  long build. `--verify` on its replies stays unused until a job is sent that way.
- **Resource locks on merges.** They bind only the sessions that use them, and the Codex session commits on its own.
- **Capability profiles as the guard on Drive.** They limit an agent's tools, not what a test run inside a permitted
  tool does. The rclone guard in `tests/conftest.py` is that guard.

## Consequences

- `govern usage` reports tokens per lane. ElevenLabs is not in it: resources are priced by time, and takes are not.
- A delivery still goes through the publishing and pilot tools with all their gates. A lane records and checks that it
  happened, and no delivery depends on govern being present.
- Develop races, worktree traps and judging a video are outside what this changes.
