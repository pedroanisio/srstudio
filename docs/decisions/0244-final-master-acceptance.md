# ADR 0244: Final-master acceptance

Accepted, 2026-11-05. Owner: codex-builder.

`master_gate.accept_master(master, project, approvals=(), crop=None)` is the
common, read-only acceptance entry point. It returns `MasterAcceptance`, including
the master SHA-256, individual `MasterCheck` verdicts, values, limits, evidence,
and any `MasterApproval` used. The file is hashed before and after measurement;
a changed master refuses. `master_gate.judge/read` use this result, so missing
legacy `prosody` markers no longer make master failures advisory. The SDK checkout
has no `srstudio deliver` command; delivery commands belong to srstudio-episodes
per `docs/authoring-delivery.md`. Its existing master-gate caller and the follow-up
pilot integration must consume this result before staging. No staging is performed
by the acceptance API.

Integrated loudness, LRA and true peak come from final-master
`ebur128=peak=true:framelog=quiet`. Raw stderr is retained alongside the SHA-256.
Integrated loudness passes at -16 through -14 LUFS inclusive; true peak must be
at most -1 dBTP, and LRA at least 4.5 LU. Missing and nonfinite values fail.
Only the lower extension through -16.6 LUFS is eligible for case-specific
approval/stress evidence. The proposed -12.5 ceiling is disabled: no authoritative
channel contract establishing it was available in this task.

C7 reads the existing offline recording adapters for timeline, flat dialogue,
or kept narration alignment. Word windows must be ordered, nonempty, finite,
within the placed clip and actual decoded audio. Each word must exceed the
-45 dBFS audibility floor in the mixed master. The first above-floor sample
inside the earliest aligned word gives first speech; it must be at or before
0.25 seconds. Missing speech/alignment fails. First sound remains a separate
diagnostic and never substitutes for speech. Evidence names placements, cached
word intervals, measured word RMS and audible times. This does not perform fresh
recognition or source separation: mislabeled sound or music inside an incorrect
speech alignment cannot be proven to be the claimed words. No provider requests
are made. Callers must supply the matching recording project.

C4 uses `freezedetect=n=0.003:d=1.5` on the content crop, replacing the old
pixel-share still exception. Runs over 1.5 seconds fail, including runs open at
EOF, closed at decoded video EOF reported by ffmpeg progress. No run reaching
the detector threshold is represented by an empty run list only after successful
decoding to EOF. Raw detector output, progress, crop and run times are retained.
For portrait 9:16 masters, the existing 1080x1340 content region is scaled from
1080x1920; content-only 1080:1340 masters use the whole frame. A small aspect
rounding tolerance permits integer-sized proxies. Other layouts must supply an
explicit validated `(width, height, x, y)` content crop. Dimensions are probed
from each actual master. Overlay movement outside this crop cannot hide a hold
inside it; overlays within content are not removed by this detector.

Exceptions are caller-supplied immutable `MasterApproval` records containing exact
master SHA-256, check, authorizer, reason and case evidence. The authorized owner
is arc4d3, as supplied by the task contract. Frozen and speech failures may be
approved; only the specified lower integrated band may be approved. Missing,
empty, wrong-check, wrong-authorizer or stale-hash evidence cannot waive a failure.
There is no approval creation, persistence, discovery or authentication workflow
here: callers are responsible for loading trusted records. Script waiver strings
are insufficient. Failed measurements stay separate per check; no approval can
turn a missing loudness measurement or a changed master into an accepted master.

`craft_bar.measure` consumes the same acceptance result for these bars while
retaining its existing pace, stress and music diagnostics. Its optional supplied
proof loudness is not used to substitute for measurements on the current master.
Tests use short synthetic clips and cached word records; no recording or delivery
is needed.
