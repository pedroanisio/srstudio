---
generated-by: Claude Code (Claude Opus 5.5)
---

# ADR 0232: A headless shift while the session is away, and the heavy gates at night

- Status: accepted (2026-11-04, arc4d3 under Pedro's mandate, Slack 1793804125.808629 in thread 1793803870.513729);
  the permission set is Pedro's to confirm when he installs the timers
- Back to the [library README](../../README.md)
- Builds on [ADR 0141](0141-gates-live-in-the-repository.md) and [ADR 0221](0221-a-five-minute-gate.md)

## Context

Slack requests, dispatches, merges and deliveries move only while the interactive orchestrator session is open. When
it is closed, posts wait for hours, even when the next step is already decided: an approved request to dispatch, a
passed gate to merge, a post that needs only a reply. The session's Slack hook touches
`generated/slack/heartbeat` while the session is alive, so the workstation can tell when nobody is at the desk.

The SDK gate and its full tier share the machine's cores with reel builds and renders, and the gate script holds one
lock for every gate on the machine (ADR 0141). A full-tier run by day stalls the reels behind it. arc4d3 asked that
the SDK and full-suite gates run between 01:00 and 05:00, "so the day stays clear for reels".

Both tools live in srstudio-episodes under `tools/ops/`, with their units under `tools/systemd/`. Pedro installs the
timers.

## Decision

### The headless shift (`tools/ops/shift.py`, `srstudio-shift.timer`)

1. **When.** The timer fires at :20 and :50, UTC-3 (America/Araguaina). A missed slot is not caught up.
2. **Skips.** A run is skipped, and the skip is logged and recorded, when:
   - the heartbeat is younger than 30 minutes (the interactive session is alive);
   - another shift holds `generated/ops/shift/lock` (`flock`, non-blocking);
   - today's (UTC-3) recorded spend plus $1 would pass $30.
3. **Bounds, all owned by ordinary code.** Each run is one `claude -p` with `--max-budget-usd 1` and
   `--max-turns 60`, stopped after 25 minutes. `TimeoutStartSec=28min` on the unit is the outer bound, and systemd's
   cgroup kill reaps whatever the run started.
4. **The ledger.** `generated/ops/shift/ledger.jsonl` (folder 700, file 600) is the only source of truth for the cap.
   It holds one line per slot, run or skip, with these fields:
   - `start`, `end`, `exit`, `cost_usd`, `skipped_reason`;
   - `session_id`, `subtype`, `is_error`, `num_turns`, `denials`, `unknown_fields`, `error`.

   The recorded cost follows four rules:
   - an unparseable output or a timeout is recorded at the per-run maximum ($1), never $0;
   - a reported cost above $1 is recorded as reported, because `--max-budget-usd` is checked between turns and a run
     can overshoot;
   - a `claude` that could not start records $0, since no request was made;
   - a ledger line that cannot be accounted stops the shift before it spends anything (exit 3).
5. **The output is parsed into a typed record.** `--output-format json` returns one result object. `parse_result`
   reads it into a frozen `ShiftResult` and checks each field:
   - `type` must be `result`, and `subtype` one of the five known values;
   - `is_error` must be a boolean, and every error subtype must carry `is_error: true`;
   - `total_cost_usd` must be a finite, non-negative number, not a boolean or a string;
   - `session_id` must be a canonical UUID;
   - `num_turns` must be a non-negative integer;
   - `permission_denials` must be a list of entries with a `tool_name`;
   - `result` must be text, and `errors` a list of text;
   - NaN and Infinity are refused.

   Any failure raises `OutputError`, and the run takes the recorded-at-maximum path. The model's own words (`result`)
   are printed to the journal, truncated, and never acted on.
6. **Unknown fields are named, not refused.** The result object of Claude Code 2.1.314 has about ninety top-level
   fields, most of them optional internal timings, and every release adds more. The module pins the full list of the
   2.1.314 fields. A field outside the list does not fail the parse: it is written by name to the ledger's
   `unknown_fields`, where review sees it. Every value the shift acts on is still validated strictly, and a renamed
   or retyped field it reads still fails the parse.

   This departs from the letter of CLAUDE.md's typed-parse rule ("rejects unknown fields"). The reason is that
   refusing an added field would turn each CLI update into runs recorded at $1 with their real cost unread. The cap
   would then end the shift's day at the 30th slot, and the cause would be a change outside the shift. Strictness
   belongs to the values the shift consumes. The full payload is not model output: the CLI writes it around the model.
7. **The prompt** (`tools/ops/shift-prompt.md`) states the scope.
   - In scope:
     - Slack triage, where each open post gets a reply, a mapping or a dismissal with a reason;
     - dispatching builders only on requests arc4d3 already approved;
     - merging and delivering only what passed its gate;
     - queueing SDK and full-suite gates for the night;
     - posting `blocked:` notes.
   - Never:
     - new formats or looks;
     - arc4d3's approvals;
     - anything that needs Pedro: any `git push` (the SDK's included), the auto-enhance mode, money, credentials,
       engine bugs, installing units;
     - Artifacts;
     - `protected/` or `authorial/`;
     - a second `claude`.
   - Every run ends with `govern note ops-indicators "shift HH:MM UTC-3: ..."`.
8. **Permissions.** A headless run cannot answer a permission prompt. The run uses these options:
   - `--permission-mode dontAsk` and `--permission-prompts none`, so anything not pre-approved is denied rather than
     asked;
   - `--settings tools/ops/shift-settings.json`, a dedicated allow and deny list;
   - `--strict-mcp-config` with no MCP configuration, so no connector loads.

   The permission mode is set on the command line, not in the settings file. A settings file that fails validation is
   silently ignored under `-p`, so this placement makes a broken file fail closed: everything is denied, and nothing
   is widened. The allow list contains:
   - the read tools, and Edit or Write under `_tmp/` only;
   - `govern`, by its absolute path;
   - the episodes gate script and the night queue's `add`;
   - the three delivery commands;
   - read-only git and `git merge`;
   - `ls` and `date`.

   The deny list contains:
   - Artifacts, WebFetch and WebSearch;
   - every `git push`, plus `--amend`, `reset --hard`, `stash` and branch deletion;
   - `sudo`, `systemctl`, `claude` and `rm`;
   - reading `.env` files, `~/.ssh` and the Claude credentials;
   - writing under `protected/` and `authorial/`.

   Each denial the run meets is recorded in the ledger (`denials`). Pedro widens the list from that evidence, not from
   guesses.

### Night gates (`tools/ops/night_gates.py`, `srstudio-night-gates.timer`)

1. **Adding an entry.** `add --repo sdk|episodes --sha SHA --name NAME [--kind gate|full]` resolves the SHA with
   `git rev-parse --verify` in that repository and stores the full SHA. It refuses the following, with exit 2:
   - a ref name, an unknown commit, or a commit from the other repository;
   - an unsafe name;
   - `--kind full` on the episodes gate, which already runs every test;
   - a commit and kind already waiting.

   The entry goes to `generated/ops/night-gates/queue.jsonl` (700/600).
2. **The run.** `run` (timer at 01:00 UTC-3) works as follows:
   - It takes the entries that no result names yet, oldest first, and re-reads the queue between gates.
   - Each entry runs through its repository's own script: `srstudio/tools/gate.sh [--full] SHA NAME`, or
     `srstudio-episodes/tools/gate.sh SHA NAME` with `GATE_WORKSPACE` and `SRSTUDIO_SDK` set.
   - It starts nothing outside 01:00–05:00 and nothing at or after 05:00.
   - Each gate's timeout is the time left until 05:00. At the timeout the gate's process group gets SIGINT (pytest
     stops cleanly on it), then SIGKILL after 30 s.
   - One lock allows one night run at a time.
3. **Results.** Each gate run is one line in `results.jsonl` with a status: passed, failed, stopped or error. The line
   also holds:
   - the exit code, start, end and duration;
   - the log of the script's output.

   A stopped entry is done; queue it again to retry. Entries the night did not reach wait for the next night.
4. **The summary.** One note goes out with `govern slack post --kind note --key night-gates-DATE`. A night that ran
   nothing posts nothing. A failed post exits 1, and the results are already recorded. The poster, the gate runner and
   the clock are injected, so the tests post nothing and run no gate.

## Rejected alternatives

- **`--dangerously-skip-permissions` or `--permission-mode bypassPermissions`.** Either one gives an unattended model
  every tool on a workstation that holds the Drive, Slack and Jira credentials and both repositories' pushable
  history. It also cannot keep the "never" list, which rests on the deny rules.
- **`--permission-mode auto`.** A model classifier decides each call. The bound would then sit with a model, and
  CLAUDE.md requires deterministic bounds to sit with ordinary code. Its decisions also leave no allow list that
  Pedro can review.
- **`acceptEdits` alone.** It approves edits anywhere in the workspace and still denies every command the shift needs.
- **Refusing unknown result fields.** See Decision 6: every CLI update would charge the cap $1 per run while the real
  cost went unread.
- **Trusting the CLI's cost when the output is unreadable, or recording $0.** The cap would undercount exactly the
  runs nobody can see into.
- **A queue rewritten as entries finish.** An `add` racing a rewrite could lose an entry. With an append-only queue,
  and results that name the ids they finished, there is no rewrite to race.
- **Leaving a stopped gate at the head of the queue.** A gate too long for the window would stop at 05:00 every night
  and hold everything behind it.
- **Running the full tier by day inside the 5-minute budget.** ADR 0221 already moved the full suite to a tier of its
  own, for this reason.

## Consequences

- With the session closed, Slack gets answers, and approved and gated work moves, within 30 minutes. The cost is at
  most $30 a day, recorded per run.
- The allow list will be too narrow at first. Denials show up in the ledger and in `blocked:` notes, not as silent
  skips.
- SDK and full-tier gates queued by day report at about 05:00 in one Slack note.
- Pedro installs and enables both timers. Nothing here installs a unit.
