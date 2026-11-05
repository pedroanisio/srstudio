# ADR 0239: The project craft bar belongs to proof

Accepted, 2026-11-05. Reserved as `proof-project-craft-bar` on the measure-bar branch.

`srstudio proof VIDEO --project DIR` adds the C4/C7 table to the existing master
report. Without the option, the report, flags and status retain their behavior.
Each library `Measure` is an immutable dataclass with a name, typed value, bar,
pass verdict and evidence source. `Result` collects these measures. JSON adds
`craft_bar.measures` and `craft_bar.passed` to the existing report. Any failed bar
or measurement error returns failure. Waivers do not change this craft table.

Integrated LUFS and LRA come from the existing `proof.measure` ebur128 summary.
LRA uses `master_gate.MIN_LRA`. The requested bar specifies no integrated-LUFS
range, so that row explicitly requires a finite reading; it does not invent a
delivery target. Pace uses `prosody.Measure.pace`: heard words divided by the
first-to-last word span. Every line above the pace bar fails; the higher retake
threshold is named in that line's bar. This differs from scratch phrase-duration
counts, which can include silence and count punctuation differently.

Recording adapters read timeline word records, flat `dialogue.json` speech
placements with content-addressed cached transcripts, or narration's kept
`voiced/speech.json` character alignment. Narration stress names come from the
take's direction or matching narration item. Flat stress names come from the
recorded stress list or clip direction. A gain-only emphasized clip may reuse
its recorded source transcript only after both source and emphasized file hashes
match the emphasis record. No voice client is constructed. Missing caches fail
closed; there is no network fallback.

Every line is cut from the supplied master, converted to mono PCM, and measured
by `prosody.measure`; take-level stress numbers are never copied into the result.
Missing/empty word timing, silent word windows and absent stress words raise
`WordsNotHeard`; empty projects raise `NoRecordedLines`; absent master audio
raises `NoAudio`. Other tool/input failures raise `CraftError`.

First-word timing is the cached word start mapped through the clip trim and
placement. The signal check rejects empty or digitally silent word windows; it
is not speech recognition. It cannot prove the same words were spoken over
music, or establish that a supplied project made a supplied master. In particular,
a retaken project supplied with an older master can produce incorrect placements,
pace and stress windows. Callers must quote that limitation when versions differ.

C4 runs the exact cropped `freezedetect` filter printed in the result. It closes
a run continuing to EOF at the container duration. Zero means no run reached
the detector's minimum duration, rather than a measurement of shorter holds.
`master_gate.changes/runs` use pixel-share thresholds and do not mean the same
thing, so C4 does not reuse them.

Music uses `master_gate.constant_bed` on declared music stems, honoring declared
fade duration. This is a stem continuity check, not source separation on a mix.
No declared music is reported explicitly; undeclared music cannot be identified
by this check. Ambient effects are not assumed to be music.

Tests use synthetic masters, word caches and both recording layouts, without
network access. They cover CLI success/failure, legacy proof behavior, trim
mapping, missing evidence, silence, music continuity and freezes through EOF.


## Revision — 2026-11-05

The C7 pace ruling supersedes the word-span pace bar above:

> B. C7 pace, measured on the phrase: <=3.6 w/s PASS, 3.6–4.2 SHIP (reported, and listed for the next re-takes), over
> 4.2 FAIL. Lines of 3+ words also fail over 4.5 on the word span, and lines under 3 words have no pace bar.

For lines with at least three heard words, `pace:ID` divides the heard word count
by the kept phrase duration, including edge silences. Rates `<= 3.6 words/s`
are PASS, `3.6 < rate <= 4.2` are SHIP, and rates `> 4.2` are FAIL. A separate
`pace_span:ID` divides the same count by the cached first-to-last word span,
with PASS `<= 4.5 words/s` and FAIL above it. Comparisons use unrounded rates.
Each row names its method. Lines with fewer than three heard words emit neither
pace row, while retaining audibility, stress and other craft checks.

`Measure.status` names PASS, SHIP or FAIL. `Measure.passed` and `Result.passed`
remain strict: SHIP is not PASS. `Measure.ok` and `Result.ok` express shipping
eligibility (no FAIL rows). Proof uses `Result.ok` for its exit code, so a SHIP
row alone does not fail proof, while any FAIL row, including the span guard,
still does. `Result.retakes()` returns every SHIP measure for the next re-takes.
The text report prints `SHIP pace:ID: ...` and a `Next re-takes:` list; JSON
includes each status, strict `passed`, shipping `ok`, and the `retakes` names.
Local caller inspection found only `srstudio.cli._proof` consuming craft verdicts;
the repository gate scripts do not consume `craft_bar.Measure` directly.
