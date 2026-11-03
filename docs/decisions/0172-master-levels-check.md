---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0172: The master's levels check

- Status: proposed (2026-11-01), on the operator's approval to port four ideas from pnkit; written by Claude Opus 5.5
  in Claude Code. The check exists; the refusal at delivery is not wired, for the reason under *Measured*.
- Source of the idea: pnkit, the operator's other kit, `tools/scopes_check.py` at commit 7d935e5, rewritten here in
  srstudio's style rather than copied
- Back to the [library README](../../README.md)

## Context

A master can carry samples that a broadcast chain or a phone's display pipeline handles differently from the
preview:

- luma or chroma codes outside the legal range of a limited-range source (`illegal`);
- colours that no RGB display can show (`out_of_gamut`);
- chroma past the engine's limit (`oversaturated`).

Nothing in srstudio measured them. The engine does, with `scene-render scopes <video> --format json`. It reads the
video only and opens no GPU device (measured under `strace`, ADR 0171).

## Decision

1. **`srstudio.scopes`** runs `scene-render scopes <master> --step 5 --format json` and parses the answer into
   `Levels`. Any answer outside the known shape is a `ScopesError` (code `scopes.*`), never a pass. That covers:
   - JSON that does not parse, or is not an object;
   - another envelope `format` than `scene-render-cli/1`, or another `command`;
   - a failed run (`ok` false or a non-zero `exit_code`);
   - another `schema` than `scene-render-scopes/1`;
   - a missing measure, or a value that is not a finite number in `[0, 1]`;
   - fewer than one analysed frame.
2. **`judge(levels, limits)`** fails on `illegal`, `out_of_gamut` and `oversaturated` above their limits, which are
   all 0 by default. A single sample fails. `illegal` is `None` for a source with no legal range (full range or
   float), and is then not judged. **Clipping** is the largest share of any channel at either end. It is reported but
   never gated, because a white wall or a black frame is clipped by design.
3. **`srstudio scopes <video>...`** prints one line per master and exits 0 when it is clean, 1 on a finding, and 2
   when the master cannot be measured.
4. **`scopes.scope_defects(renders, first, engine)`** is the function the delivery gate can call. It has the shape of
   the other first-delivery checks: slug to video name in, `Drift` rows out. It returns one row per failing master,
   one per master it cannot measure, and one per missing master. It reads only reels on their first delivery, so a
   published reel stays frozen.
5. **The refusal is not wired into `episodes/instagram_posts.py`.** No threshold is loosened to make it pass, for the
   reason below.

## Measured

Every master in `generated/renders/*.mp4` was read with `scene-render scopes --step 5 --format json` and parsed with
`srstudio.scopes.parse`. All 240 parsed and none had an engine error.

| Measure | Masters above 0 | Median | Largest |
|---|---|---|---|
| illegal | 240 | 0.0681 % | 0.795 % |
| out_of_gamut | 232 | 0.0329 % | 0.378 % |
| oversaturated | 8 | 0.0000044 % | 0.00043 % |
| clipped (reported only) | 240 | 2.17 % | 91.5 % |

**0 of 240 masters pass at the default limit of 0.** Every one has illegal samples, and every master the house has
delivered would be refused. Wiring the refusal now would block every new reel built the same way. The defect sits
upstream of the check, in how the masters are encoded and graded, and this decision does not find it. That is the
next step, and it is the operator's to order.

## Consequences

- `srstudio scopes` measures a master on demand. `scope_defects` is ready for the gate, and wiring it takes one line
  in `publish` beside `strict_defects` once the masters can pass.
- The numbers above are the baseline for whoever investigates the encode and grade. The check's limits stay at 0.

## Alternatives rejected

- **Wire the refusal with a limit above today's worst master.** That would loosen a threshold to make a check pass,
  and the check would then fail on nothing it was built to find.
- **Gate clipping.** Clipping is often by design, as in a white card or a fade to black, and pnkit reports it without
  gating it for the same reason.
- **Measure with ffmpeg's `signalstats`.** It measures per frame without the engine's gamut and saturation model, and
  the engine's `scopes` is the same measure the renderer itself reports.
- **Sample every frame (`--step 1`).** It is five times slower. Every fifth frame (128 frames of a 26 s reel at 24
  fps) already finds samples in all 240 masters.
