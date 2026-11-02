---
generated-by: Claude Fable 5.1 (claude-fable-5-1) in Claude Code
---

# ADR 0212: One choreography transcribed into a move library, under the operator's waiver

- Status: proposed (2026-11-02)
- Back to the [library README](../../README.md)

## Context

ADR 0203 settled that our dances learn style from a reference video, never choreography: statistics of how a body
moves against the beat, as ranges, from which no routine can be rebuilt. The operator's standing rule for the dance
SDK says the same, "measure, never copy".

On 2026-11-02 the operator ran a pose estimator over a second reference, a public choreography video for the song
FE!N (a dance class recording, two lead dancers and a crowd of students, 408.8 s at 23.976 pictures a second, the
song at 152 beats a minute), asked how many complete, unique moves it held, and then asked whether those moves could
enter the SDK and be composed from. Given the choice between a style record under ADR 0203 and a transcription that
contradicts it, the operator chose the transcription, with the waiver recorded here. The waiver covers this reference
and this library; ADR 0203 stays the rule for every other reference.

The people in the recording are real. The footage, its frames, stills, overlays and per-frame landmarks stay out of
the repository, Drive and Slack, as under ADR 0203. The estimator is a model whose output is wrong in ordinary ways
and is untrusted until it is parsed and bounded.

## Decision

Transcribe the moves confirmed by more than one dancer into `assets/dance/fein.json`, a `srstudio.dance-moves/1.0.0`
library of fitted pattern parameters, and compose from it through the same choreographer as the presets.

### What a transcribed move is

Each window of the reference becomes one `dance.Move` named `fein-NN`, `support` `feet`, both feet planted through a
loop of four beats: the measured span fills the first two beats as the strike onto the hit, the other two are the slow
return. Every moved joint carries one `sine` pattern of a quarter cycle a beat (bias, amplitude, phase and snap), on
the same canonical targets the presets use: hips, chest and neck on all three axes, each upper arm's lift, swing and
twist with the forearm's stretch, each upper leg's swing and spread with the lower leg's stretch. Nothing moves the
root: the estimator's metres start at the hips, so travel across the floor is not measured. The head is fitted at half
weight, since the estimator places it between the ears and the skeleton at the middle of the skull.

A transcription is lossy: four parameters a joint cannot hold every bend of a two-beat strike. The residual of the
fit, the root-mean-square distance between the fitted and the measured 13-point body in head radii, is written into
every move's description, with the move's track, seconds, and how often and by how many dancers it was seen.

### The tool: `tools/dance_transcribe.py`

The tool reads two documents strictly, every field named and bounded, a typed `TranscribeError` at a path for an
unknown or missing field, a repeated key, a non-finite number, a wrong format or version, frames out of order, a track
that is not a name, a joint list in another order, a 2D pose, or a record over its byte bound:

- a `dancepose.motion` record (format version 1), the estimator's output: per frame, per tracked person, the 15
  joints and 13 auxiliary landmarks in metres from the hips with the torso's yaw. It lives outside the repository.
- a `srstudio.dance-windows/1.0.0` list under `tools/data/`: the source named by its title, its YouTube id and the
  digest of the file read, with its picture rate, frame count, tempo and the estimator that read it (`extractor`);
  a sentence on how the windows were selected; and per move a name, a track, a start and an end in seconds (a
  quarter second to eight seconds), and how often and by how many dancers the move was seen. This list is the only footage-derived input the repository holds, and it holds no pose.

For a window the tool samples the track at sixteen times, taking a frame up to three frames away when the tracker
skipped one and refusing the window when the track is gone; keeps the study's thirteen points (hips, knees, ankles,
shoulders, elbows, wrists, the ears' middle as the head); turns the estimator's axes into the skeleton's; removes the
window's median facing by the torso's measured yaw; starts the body at the hips' middle; and scales it so the torso
is 4.8 head radii, as `dance_study.reference_body` does. A torso under 0.25 m or over 1.2 m is no person, and a
sample whose torso differs from the window's median by over 30% is a misread; either refuses the window.

The fit is `scipy.optimize.least_squares` through srstudio's own forward kinematics on the realistic preset, with the
hit and the far end of every target as parameters, bounded by the tightest delta every preset allows on top of its
own rest pose, for the move and its mirror alike, so a fitted move dances unclamped on every character. The snap is
bounded to 0.15..0.85 and the phase to half a cycle. The number of evaluations is a flag with a hard bound of 1,000.
Every written extreme is rounded to four places and then pulled inside its bound by at least 0.00001, so no rounding
lands a joint on a limit; a swing or hold under 0.02 rad is dropped. Each move is then proved on every preset,
mirrored too, at 32 samples a beat and at every pattern's own hit and far extreme, and the document written is read
back through `dance.parse_moves` before the tool returns. Windows run in parallel, each reported by name as it is
fitted or refused with its reason, and a refused window leaves the others standing. With `--resume`, the moves the
output already holds are kept, re-settled under the current rounding rule and proved again, and only the windows it
lacks are fitted; a kept move with a target the tool does not fit refuses the resume.

### The library and the choreographer

`dance.library(name)` loads a shipped library by name from `assets/dance/<name>.json`; the name is checked against
the list of shipped libraries before any file is read, and `dance.moves()` is `library("moves")`.
`choreograph.palette_of(library)` makes a `Palette` over a whole library, its moves ranked by `energy` (the sum of
their amplitudes in size): the quieter half for low parts and the louder half for high ones. `srstudio choreograph
--library fein` draws from the library with that palette, and `tools/dance_views.py --library fein` reviews its
moves in three views.

### How the windows were chosen

The windows come from the estimator's record of the whole video, outside the repository: tracks at least five seconds
long and at least 0.45 of the picture high, cut into moves from one hold to the next (speed minima under 0.9 of the
median, at least 0.3 s apart, moves of 0.4 s to 3 s, gaps of up to eight frames bridged), each move described by the
path of the head, elbows, wrists, knees and ankles in the picture with the facing removed and the torso's length as
the unit, and clustered with complete linkage at the distance measured between the two lead dancers doing the same
move at the same moment in the duet shots (the 75th percentile of those pairs; the separation of same from different
pairs there has an area under the curve of 0.90 on few pairs). A cluster seen from two or more dancers is a confirmed
move: 78 of them. For each, the window is the first member whose track the estimator holds through the window with a
steady torso.

## Rejected alternatives

- **A style record only (ADR 0203).** The faithful reading of the standing rule. It yields no moves to compose from.
  The operator chose the transcription for this reference knowing that; the waiver is this record.
- **Every unique move (186) or every complete move (411).** The singletons are as likely a tracker's fragment as a
  move. Only moves two dancers were seen doing are transcribed.
- **Per-frame keyframes instead of patterns.** Faithful, and footage-derived pose of real people inside the
  repository. Refused on the same grounds as ADR 0203: only fitted parameters enter.
- **The `curve` waveform of moves 1.1.0, now.** It is on a sibling branch (`feat/dance-timing`, ADR 0204), not on
  the base of this one. A quarter-cycle sine with a snap is the closest shape 1.0.0 offers. The operator asked the
  same day for more natural acceleration and easing, and the reference agrees: on the 58 windows whose main stroke is
  readable at 24 pictures a second, the fastest moment lies after 0.6 of the stroke in 45% and before 0.4 in 28%,
  where a sine always puts it at 0.5. Fitting each pattern's cycle as a `curve` from the same measured bodies is the
  next change on this branch once 1.1.0 is under it; the tool's input and windows make that a rerun, not a redesign.
- **Fitting the root.** Unidentifiable in hip-centred data; it drifted to the bound in the prototype. Dropped.

## Consequences

- A named choreography's moves are in the library, by waiver. ADR 0203 is unchanged for every other reference.
- The repository holds the window list (tracks, seconds, counts) and the fitted parameters, never the record, the
  frames or the footage. The record can rebuild the library; the library cannot rebuild the record.
- The transcription's loss is visible: every move's description carries its residual, and the proof clip shows the
  moves on the three presets.
- The moves are read back from the file, so the estimator's output never reaches a routine unparsed.
- The library grows only by rerunning the tool over a record; nobody edits `fein.json` by hand.

## The reference, transcribed

The run over the whole record, 78 windows, ten workers:

| Measure | Value |
|---|---|
| Moves written | 78 of 78 windows |
| Fit residual, head radii (min / median / max) | 0.25 / 0.45 / 1.01 |
| Moves with a residual over 0.8 | 2 |
| Patterns per move | 23 (22 in four moves), one of them a hold at the median |
| Swing per moving pattern, radians (median / 90th percentile) | 0.26 / 0.76 |
| Times a move was seen (min / median / max) | 2 / 3 / 14 |
| Dancers seen doing it | 2 in 36 moves, 3 in 17, 4 in 15, 5 to 9 in 10 |
| Tracks the windows come from | 19, the two lead dancers' tracks holding 29 |

Thirteen windows (`fein-02`, `03`, `04`, `11`, `13`, `19`, `31`, `35`, `41`, `46`, `50`, `53`, `66`) are not the
cluster's first member: the estimator lost that member's track or misread its torso inside the window, and a later
member it holds throughout stands for the move.

The first run wrote 61 moves and refused 17 whose fitted extreme, rounded to four places, landed a hair past a
limit (by under 0.00005 radians) on one preset; the settling rule above replaced the one that rounded toward
the bound, the 17 were fitted again with `--resume`, and the 61 kept moves were re-settled under the new rule when
the library test found eight of them one rounding step past a limit at a sample time the prover's grid had missed.
The prover now reads every pattern's own extremes. A later record of the same estimator (its 0.2.0 and 0.3.0
releases add `hands` and `feet` per person) is outside the fields this tool accepts and is refused as unknown; the
0.1.0 record the library was built from is the one the windows name by digest.

The proof clip, `generated/character-proofs/fein-moves/views.mp4` with its page beside it, plays the 24 most-seen
moves two bars each at 152 BPM on the three presets in three views.

