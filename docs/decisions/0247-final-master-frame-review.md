# 0247: Final-master frame review before staging

The final master is the frame authority. Scene geometry and the bug's first
corner cannot establish ownership, signature clearance or full-size review of
the encoded movie. Existing hand, cut-bust, number, bug, caption and map checks
continue to run; their success cannot substitute for final-master review.

`srstudio.final_frame_gate.check_master` is the shared SDK/pilot entry point.
It returns `FinalFrameResult`, with native dimensions, each decoded frame's
index, presentation timestamp and RGB hash, the master SHA256, and typed
`CheckResult` records containing verdict, measured value, limit, reason,
observations and human evidence. A refused result must stop staging.
Unreadable movies or malformed review files raise `FinalFrameError`.

Every encoded frame is decoded at native resolution with no resize or frame
sampling. The file hash is checked before and after decoding. This bounded
memory pass verifies the review's dimensions and exact frame count. It does
not pretend to perform visual recognition: a human supplies final-frame
identity and visible regions. The same equivalent human checker covers
formats the engine cannot evaluate; no medium implies an identity. Engine
geometry is never accepted by this entry point, so an unrelated render cannot
provide clearance. The existing scene checks remain supplementary.

Human evidence is a sequence of typed `Review` records keyed by master SHA256
and check. Delivery reads an existing `final-frame-review.json` list beside the
episode; this SDK never creates review or approval records. Required checks:
anatomy, show, captions, safe_areas, marks, staging, close_shot,
signature_clearance, signature_props, lessons.0034 and lessons.0035.
Each record names the reviewer, evidence, native dimensions, frame count,
disposition, reason and observations. Non-region checks require an explicit
nonnegative integer `defect_count`; a positive count fails even with a PASS
disposition. Missing, duplicate, stale, failed,
non-finite or incomplete records refuse, including legacy/advisory masters.
No waiver on a script clears these checks.

The two lessons always require full-size human review. Other checks may be
INAPPLICABLE only with an explicit format-specific explanation. That decision
is itself human evidence bound to this master. Region reviews enumerate all
visible signatures, story props and close-shot character parts, including
each punch-in. Every decoded frame needs an observation for these checks,
unless the entire check has justified inapplicability. A signature observation
with no counterpart uses `other=null`, empty mark/other IDs and an explicit
per-frame reason (for instance, no visible story props in that shot).
For a close-shot review, `focal` names the character and a nonempty `intruder`
confirms intrusion and refuses. Unknown ownership must be reviewed, never
cleared through an inferred character identity. The crop rectangle and evidence
identify the offending native-resolution region on the hash-bound frame.

`signature_clearance` measures the shortest Euclidean edge distance between
transformed visible signature and bug bounds on the final frame: at least
24 px is required by bar.craft.c6. `signature_props` independently refuses any
positive-area obstruction of a visible story-prop region. Bounds are a
conservative region representation: a reviewer may supply tighter visible
regions for a nonrectangular prop. Confirmed defects cannot be passed by a
human PASS disposition; the measured result still fails. Show scene checks
also measure the edge gap after transforms, and can accept explicit story-prop
node IDs from that same frame. Missing final-frame evidence always remains held.

`master_gate.read` runs this suite and `master_gate.refusals` holds its failures
before staging independently of the older prosody binding policy. Direct
`master_gate.judge` remains the existing audio/frozen diagnostic API; it cannot
replace `read` or the new shared suite for staging. `anatomy_gate.body_defects`
also accepts an explicit slug-to-final-master mapping to run its shared body,
staging and close-shot review alongside the existing hand/cut-bust checks.

The episodes repository's publish_pilots wiring is a separate task. Its caller
must pass existing typed reviews, report `result.lines()`, and refuse
`result.refused` or `FinalFrameError` before `outbox.stage`.
Call `check_master(master, slug=slug, review_path=project / 'final-frame-review.json')`
to load existing evidence in that same call, or pass a sequence of typed
records with `reviews=`. The two input forms are mutually exclusive.
