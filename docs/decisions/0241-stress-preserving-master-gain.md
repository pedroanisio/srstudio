# 0241 — Stress-preserving master gain

Status: amended 2026-11-06. The former whole-master gain cap is withdrawn.

The original headroom policy reduced jp-leftovers' requested -15 LUFS target
rather than retaining it. It contradicted the supplied arc4d3
`bar.audio.loudness` (canais store; `videos.craft.c7-loudness`):

> Loudness band for every master: -16 to -14 LUFS integrated, true peak at most
> -1 dBTP. Stress contrast comes from ducking bed and foley under stressed words
> and from limiter attack, never from lowering the whole master. -16.6 LUFS is
> the floor accepted case by case.

## Decision

For recorded named stress with integrated normalization, keep the authored
integrated target, true-peak ceiling and dialogue gain. Encode the authored
analysis mix without normalization or the final limiter and measure named
words using `craft_bar.measure_voice` and the cached placement/alignment.

Add -6 dB of gain automation to music, effects and ambience over each named
word's span. Use `emphasis.RAMP` (15 ms) on either side; merge overlapping
ramp extents. Composition-time additive gain automation preserves existing
faders and animations. Match words exactly as `prosody.measure` does: the
first normalized occurrence. The engine schema permits effect `attack` and
`release`, but the engine's effect limiter ignores attack, and the final
true-peak limiter has fixed lookahead/attack and a 50 ms release. Do not
invent master timing attributes or claim adjustable final limiter timing.

Measure each staged, encoded output before installing any output or report.
Every named word must reach `prosody.STRESS_DB` (3 dB above the line median);
`emphasis.MARGIN` remains the take's 0.5 dB production allowance, not a lower
acceptance bar. Failure raises `craft_bar.CraftError` with line, word, before
and after measurements and target. There is no quieter fallback and no lift
of the spoken word. A bad take or contrast lost to limiting needs a remix or
retake. Also refuse decoded loudness farther than 0.2 LU from target or true
peak more than 0.1 dB above the authored ceiling (ebur128 summary precision).
Report one line per output with target, decoded integrated loudness, true peak
and every named word's analysis/master contrast. Keep the whole report rather
than truncating it with the engine output tail.

Temporary sibling scenes retain relative asset references. Analysis products
stay outside the install stage. Source documents are unchanged; failures
clean stages and install nothing. Projects without recorded named stress keep
the existing engine command and bytes. Programme ranges and output segments
are refused for named stress until cached word timings can be remapped;
parameters, data, representations and thread arguments pass to analysis.

The synthetic peak-driving recording verifies target loudness and stress,
an unattainable target verifies refusal before install, duck-envelope checks
cover additive faders and overlapping words, and direct engine comparison
checks byte identity without named stress. Only scratch copies may be used
for real episode audio checks.

## Amendment, 2026-11-06: duck span and loudness band

The stress meter weighs a stressed word against the other words of its line on
the mixed master (`craft_bar.measure_voice`, `prosody.measure`). A duck under
the stressed word alone lowers that word's span and leaves the bed under the
others: on jp-leftovers "salt" fell from 2.86 dB to 1.96 dB. The duck now spans
the words of every line that names a stressed word.

A master is judged by the bar's band, not by the authored target to within a
tolerance. The engine's own AAC true-peak pass lowers a master by a few tenths
of a dB (jp-ready-in-five: target -16, measured -16.3), so the target check
refused masters the bar accepts. `loudness_verdict` passes -16 to -14 LUFS,
notes -16.6 to -16 LUFS as "accepted case by case", and refuses below -16.6,
above -14, or over the authored true-peak ceiling.

The engine's master limiter has no attack or release (scene-render 1.1 schema:
`limiter` is a boolean), so the bar's "limiter attack" lever is not available
on this engine. A word that the duck cannot keep above the stress bar is
refused, as before.
