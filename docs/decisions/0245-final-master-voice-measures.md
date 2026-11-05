# ADR 0245: Final master voice measures

Accepted, 2026-11-05. Owner: codex-builder.

`master_gate.accept_master(master, project)` returns `MasterAcceptance` with
hash-bound pace/stress MasterChecks, VoiceLine reports, and SHIP/FAIL retake lists.
Delivery through judge/read and craft_bar.measure consumes this common result.
The follow-up episodes caller can call this same public function unchanged.
The SDK has no deliver command; the episodes delivery boundary is documented in
ADR 0244. No new alignment file or provider request is introduced.

Timing uses the existing offline timeline, flat dialogue and kept narration
adapters used by first_speech. Placements retain edge silences; word levels are
sampled from the current master mix. Phrase count/duration passes through 3.6,
ships through 4.2, fails above 4.2; count/first-to-last-word span fails above 4.5.
Lines under three words are pace exempt only. Missing, invalid, nonfinite or
out-of-audio timing refuses. SHIP remains acceptable and names a future retake.
The independent prosody reel ceiling is removed. Take pitch/ranking diagnostics
remain separate from final-master level enforcement.

Every line must identify a key word. Each word must be audible above the existing
-45 dBFS master floor. Key words require at least +3 dB over the line word median;
the immediately preceding word requires at least -3 dB. No predecessor is N/A.
Reports include words, levels, median, margins, timing source, verdicts and master
SHA256. Hashes before and after measurement detect replacement during measurement;
results identify only those exact bytes and must be recomputed after replacement.
No human approval or waiver is introduced for pace or stress.

As in ADR 0244, offline alignment is not fresh recognition or source separation:
incorrectly labelled speech windows containing effects/music cannot establish
lexical identity. Callers must supply the matching recording project.
