# ADR 0245: Final master voice measures

Delivery consumes `craft_bar.measure_voice(video, project) -> Result` before staging.
Every result carries the exact master SHA256, per-check measured value, bar and
verdict, per-line word levels, both pace clocks and retake lists. SHIP is accepted.
The independent reel pace ceiling is removed. Take pitch and ranking stay diagnostic.

`master-voice.json` is the offline alignment evidence: `master_sha256`, nonempty
`source`, and `lines` containing `id`, `start`, `duration`, and `words` with `text`,
`start`, `end` relative to that phrase. Phrase bounds retain edge silences. Every
recorded line must occur exactly once and match its recorded words. Missing, stale,
nonfinite, unordered or out-of-phrase timing refuses delivery. Replacing the master
invalidates evidence and results; no recording service is invoked here.

For three or more words phrase pace passes through 3.6, ships through 4.2 and fails
above it; span pace above 4.5 fails. Short lines are exempt from pace only. Every
line names its key words in existing direction stress metadata. Levels are sampled
from the master mix at the aligned intervals, with key margin at least +3 dB over
the line median and preceding margin at least -3 dB. No predecessor reports N/A.
Missing word levels or words below the existing prosody audibility floor fail. No human approval is introduced.

The checked-out SDK CLI has no `deliver` subcommand. Its delivery guide places
that command in the episodes repository. This change enforces voice checks in
`master_gate.read`, the existing SDK boundary consumed by that caller; it does not
add a new delivery command or edit the episodes caller. The pilot caller can use
the public function unchanged. Real-master reports require alignment evidence
that is not present in the inspected render and episode trees.
