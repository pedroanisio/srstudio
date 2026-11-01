---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0095: The gates live in the repository, and a reel leaves build on a review

- Status: accepted (2026-11-01)

## Context

Fifteen full gate runs in a row ended failed or killed. Most failures were faults a quick run would have found in
minutes, found after three quarters of an hour. The gate script lived in the scratch folder, so another checkout
could not run it, and the `reel` process said nobody reviews while the operator's process requires a frame review
and the comedy floor.

## Decision

- `tools/gate.sh SHA [NAME]` runs format, lint, types and the full suite on one commit in its own worktree under
  `generated/gates/NAME/`, keeps the log there and removes the worktree when the run passes.
- `tools/pregate.py` runs before it: format, lint, types, the tests named for each changed module, every changed test,
  and the contract tests merges most often break. It does not replace the full gate.
- The `reel` process's build stage leaves on the `reviewed` check: `lane.json` names the reels, and `reviews.json`
  records each one's author, a different reviewer, both comedy scores with the lower at the floor, and at least four
  frames read at full size. The check reads a record, as govern's role is (ADR 0058): it proves the review is
  written down, not that it was good.

## Rejected

- **Running the frame review inside the check.** The review is a reader's judgement, and govern is not a runner.
- **Choosing the quick gate's tests from coverage data.** It would be finer, and it would need a full run to refresh.
