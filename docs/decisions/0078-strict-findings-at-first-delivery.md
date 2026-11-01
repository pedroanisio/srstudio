---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0078: Strict findings at first delivery, and records that clear a false one

- Status: proposed (2026-11-01), on arc4d3's post of that day: "A reel whose findings are all proven false ships. A
  finding counts as proven false only when it's measured on the rendered frames, not argued: the text's real time on
  screen from the frames (first to last frame it's legible) against the rule's minimum, and contrast measured on the
  composited frame. Each one goes in the `delivered:` post with its frame evidence, signed off by a reviewer who isn't
  the author. Real findings still get fixed." On `TXT-FIT`, arc4d3's acceptance of `ill-get-this` the same day: "the
  proof holds. The card touches the edge only while it's thrown in (f0505), and at rest GARY is fully inside it (f0517,
  f0528)."
- Deciders: arc4d3, the publishing side, for the rule; written by Claude Opus 5.5 in Claude Code
- Follows [ADR 0073](0073-frame-gates-and-standing-review.md) and [ADR 0040](0040-frozen-releases-at-an-accepted-drawing.md)
- Back to the [library README](../../README.md)

## Context

`scene-render encode --strict` exits 1 on a finding and writes the master all the same. Delivery never read the result,
so "a reel that fails it does not ship" was a line in the skill and not a control: a reel with findings could ship.

Some findings are false. The engine measures each text layer on its own, so a card carried across a cut is new layers
and each is timed alone ([ADR 0030](0030-gloss-style.md) noted it, and
[the bug report](../engine-bug-legibility-across-cuts.md) reproduces it). `no-thanks` shows one: the engine measures a
card at 0.333 s, and the master shows it from frame 184 to frame 241, 2.417 s. A gate that only refused would hold true
work on an engine error. A gate that took an agent's word would be no gate.

Published content is frozen, so nothing here may ask a delivered reel to change.

## Decision

1. **Every new reel's report is read at first delivery.** `write_all` calls `strict_gate.strict_defects` beside the
   frame gates, on `first`, the videos delivering and not in the manifest. A refusal is a `FrameGateError` naming the
   reel and the finding, before anything is written. `check` does not run it: a delivered reel owes nothing.
2. **`--strict` decides what counts.** Every finding that is not `info` counts, as the engine counts it, so a new
   severity counts by default.
3. **No report is not a clean report.** A reel with no `qa/render-report.json`, a report it cannot read, one of another
   scene, or one of part of the running time is refused. `encode --start --end` rewrites the report, so a short preview
   would otherwise clear what it never rendered.
4. **A finding is cleared by a record and nothing else**: `episodes/strict/<slug>.json`, version 1.0.0, tracked with the
   release. The frames it cites sit in the project, under `qa/strict/`.
5. **Only `LEG-SHORT`, `LEG-CONTRAST` and `TXT-FIT` can be cleared.** The rule says how to measure the first two, and
   arc4d3's acceptance of `ill-get-this` gives the third. Anything else is a real finding and gets fixed.
6. **`srstudio strict` lists the reels shipped under the rule**, with their numbers and frames, and how many of the
   delivered reels that is: the post asks to see how often it happens, and a `delivered:` post carries the reel's lines.

## The record

```json
{
  "schema_version": "1.0.0",
  "slug": "no-thanks",
  "scene_sha256": "<the report's scene>",
  "video_sha256": "<the master the frames came from>",
  "fps": 24,
  "author": "<who measured>",
  "reviewer": "<who signed it off>",
  "cleared": [
    {
      "code": "LEG-SHORT",
      "node": "c1849-layer",
      "at": 7.583,
      "measurement": {"first_frame": 184, "last_frame": 241, "seconds": 2.4167, "minimum": 0.8333},
      "frames": [
        {"frame": 184, "path": "qa/strict/frame-0184.png"},
        {"frame": 241, "path": "qa/strict/frame-0241.png"}
      ]
    }
  ]
}
```

`LEG-CONTRAST` measures `first_frame`, `last_frame`, `lowest_frame`, `fill`, `back`, `ratio` and `minimum`: the worst
frame of the run, on the composited master.

`TXT-FIT` measures `first_frame`, the first frame the box is on screen, `rest_frame`, the first it stays still, and
`last_frame`, with `text` and `box` as `[left, top, right, bottom]` in frame pixels at rest, and the report's `limit`.
It proves a text cut only while it comes in. The record of `ill-get-this` would carry
`{"first_frame": 504, "rest_frame": 517, "last_frame": 539, "text": [429, 1389, 675, 1479], "box": [211, 1095, 866, 1541], "limit": 0}`.

A finding has no id in the report, so `code`, `node` and `at`, its start to
the millisecond, name it. One caption track can repeat a code on one node.

A record is written by agents, so it is model output and gets the five controls CLAUDE.md asks for. The numbers are also
checked against the files, because a record of correct shape can still be invented:

| A record is refused when | Because |
|---|---|
| it has an unknown or a missing field, or another version | a typed parse |
| the reviewer is the author | the rule; compared without case or outer spaces |
| its seconds are not its frames over its frame rate | the numbers must agree with each other |
| its ratio is not what its two colours compute to | the same, within 0.05 for the rounding of a median |
| the measurement does not reach the minimum | it did not prove anything; equal to it passes, as the engine counts it |
| its minimum is not the report's | the rule's minimum is not the author's to choose |
| it names a finding the report does not have | stale |
| it covers a finding but measured frames from another part of the reel | a true number about another text |
| its text reaches past its box at rest by more than the limit | the text is cut; the gate computes the overhang from the two boxes |
| the report has the text cut after `rest_frame` | a text cut at rest, or leaving, is cut: the proof is "only while it's thrown in" |
| its text leaves the frame | the frame cuts a text as a box does |
| its scene is not the report's, or its master's hash is not the video's | it was measured on something else |
| its frame rate is not the file's | at 12 fps, 48 frames read twice as long |
| a cited frame is missing, or is not that frame of the master | it is an argument, not a measurement |

A cited picture is compared with the frame decoded from the master, byte for byte. `LEG-SHORT` must cite its first and
last frames and `LEG-CONTRAST` its worst, `TXT-FIT` its first, rest and last.

## Proof on real findings

Batch B's evidence ran through the real gate on its own reports, masters and frames. All 18 of its findings, 12
`LEG-SHORT` and 6 `LEG-CONTRAST` on `four-coats`, `no-thanks`, `arrive-early` and `left-at-door`, clear. The ratio slack
holds on all six.

Pointed by mistake at earlier masters of `arrive-early` and `four-coats`, built from the same scenes, the gate refused
their frames, down to one that differed by at most 10 levels of 255. That is the check doing its work, and a re-encode
after measuring means measuring again.

The proof arc4d3 accepted on `ill-get-this` ran the same way, on its report, its master and its frames, and clears. The
report's cut is `c7202-layer`, 20.917 to 21 s. Boxes recomputed from frames decoded from the master, with thresholds of
their own, put GARY within 1 px and the card within 4 px of the record's numbers, with 218 px of box left of the text, 191
right of it, 294 above and 62 below. Seven tampered copies of the record were refused, among them a rest
frame before the cut ends, a limit of 700 and a report that has the text cut into its rest.

## Consequences

- The published reels are untouched, because `first` leaves them out. Run over all 145 as if they were new, the gate
  would refuse 102: 13 on findings, 1 whose report is of an older scene, 81 with no report and 7 with no scene. The other
  43 pass. None of this is acted on.
- Only Toon, Collage and Stick declare `report=` on their output. The next reel in any other style is refused until it
  is encoded with `--report <project>/qa/render-report.json`. Declaring it in those styles would change scenes a
  published reel rebuilds from.
- `episodes/publish_pilots.py` runs none of the frame gates, and so not this one. The rule and ADR 0073 both name reels
  through `deliver`. A pilot with findings still ships unread.
- Re-encoding a reel voids its record, even from the same scene, because the frames are that master's.
- First delivery decodes each record's cited frames, so a record costs one pass over its master.

## What the gate cannot see

It holds the numbers to the files and no further. It does not see that the text is legible in the frames it is shown,
that the text stayed up between two cited frames, that a contrast figure was measured on the glyphs, or that the two
boxes of a `TXT-FIT` are where the record says. A box is upright, so around a tilted card it holds some of the table
too, and the frames are what show the text on the card. The engine samples a `TXT-FIT` (71 of 576 frames on `ill-get-this`), so
a cut outside the sampled frames is not in the report. Those are the
reviewer's, and arc4d3 spot-checks each `delivered:` post. It cannot see who the reviewer was: that they are not the
author is a rule of the process, as with the comedy floor (ADR 0064).

## Rejected

- **Re-measuring in the gate.** Finding a text in a frame needs a template and a box for each text, and the report gives
  neither, so the gate would be running a second author's measurement with its own thresholds. Binding each number to
  the master's own frames, for a reviewer to read, is what the rule asks.
- **Encoding without `--strict`, or lowering findings to warnings.** [ADR 0025](0025-saga-style.md) refused this, and it
  would hide real findings with the false ones.
- **Clearing `LEG-SPEED` or anything else.** A kind can be cleared once the publishing side has said how it is measured,
  as it did for `TXT-FIT`. Another needs the same, and a measure of its own.
- **Clearing a `TXT-FIT` by saying the cut is brief.** arc4d3 accepted a text that rests whole, not a short cut, so the
  measure is the rest, and a text cut as it leaves is still real.
- **A new record version for `TXT-FIT`.** No record had been written at 1.0.0, so the kind joined it.
- **A line in the release file.** A release says what a reel is. A record is bound to one master and is replaced with it.
- **Records in `generated/`.** The listing has to answer for what shipped, and that belongs in history. Only the frames
  stay beside the build, as they are the size of frames.
- **Stopping at the engine.** The bug report goes to the engine, and the listing shows how often it costs a reel, but
  until a release fixes it a false finding would hold a true reel.
