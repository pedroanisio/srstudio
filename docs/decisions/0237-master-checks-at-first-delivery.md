---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0237: Master checks at first delivery

- Status: proposed (2026-11-04)
- Deciders: the operator; ordered by arc4d3's craft audit (Slack, 4 Nov); written by Claude Opus 5.5 in Claude Code
- Follows [ADR 0234](0234-voice-direction-per-line.md)
- Back to the [library README](../../README.md)

## Context

arc4d3's craft audit of the Okayville reels measured three faults on finished masters, beside the voice's prosody: a
picture that freezes, a reel that opens on silence, and a mix with too little loudness range. The audit's own scripts
are not on this host, so the checks are built from the definitions arc4d3 gave, not from its code. ADR 0234 (d) put
the prosody findings in every first-delivery report, refusing only reels recorded to the gate. These three follow the
same policy.

## Decision

`srstudio.master_gate` measures the finished master (`renders/<video>.mp4`) and reports three checks:

| Check | Measure | Fails |
| --- | --- | --- |
| `frozen` | Decoded at 10 frames a second in greyscale. Between two frames, the share of pixels whose level moves by 8 or more (of 255). A frame changing under 0.05% of its pixels is frozen. | A frozen run over 1.5 s |
| `opening` | The first sound after 0, from ffmpeg `silencedetect` at -45 dB (silences of 20 ms or more) | Over 0.25 s, or no sound at all |
| `lra` | The loudness range from ffmpeg `ebur128` | Under 4.5 LU |

Three more measures are reported as information and never fail:

- still runs (under 0.5% of pixels) over 2 s;
- a constant bed, where the reel's recorded music stem has no gap of at least 0.5 s that is 10 dB under its median
  level (100 ms windows). The stem is `music.file` in `timeline.json`, which `takes.record` writes for a script's bed,
  cut to the reel's length. Its fade-out (`music.fade`) is its ending, so it is not counted as a gap;
- the first word in `timeline.json`, when it starts inside the silence the master measured.

The policy is ADR 0234 (d)'s option A:

- The marker is the `prosody` section of the reel's `timeline.json`. Reels without it were recorded before the gate.
  Their findings are listed with "(recorded before the gate: advisory)" and never refuse.
- A reel recorded to the gate is refused on any finding not waived. It is also refused when its master cannot be
  measured: a missing file, a missing audio track, or a tool that fails.
- A waiver goes on `Script.waive` or `Reel.waive` (`frozen`, `opening`, `lra`). It needs a reason of at least three
  words and takes no bounds. `takes.record` writes it to the timeline, and the report lists it beside the finding.

The pixel step of 8 is an assumption that arc4d3's definition leaves open. On a held frame encoded with x264 at
default quality, noise moves up to 0.2% of pixels by 3 to 7 levels, which is over the 0.05% threshold. A step of 3
would never find a frozen frame on an x264 master.

## Consequences

- Every first-delivery report gains a `master` line per reel. Reels already recorded (J&P 4–6, the News pair) are
  listed and not refused.
- Each master is decoded once for the picture and twice for the sound. Three delivered reels of 16 to 26 s took 1.6
  to 1.8 s each on this host. Two of them would have been flagged: `two-percent` opens on 0.475 s of silence, and
  `cold-front` has a loudness range of 4.3 LU.
- The opening check reads the whole mix. A reel that opens on a sound effect or music passes even if the first word
  comes later; the first-word line shows that case.
- The constant-bed line needs the stem named in `timeline.json`'s `music.file`. A reel without one gets no line.
- Safe zones after punch-ins are out of scope.

## Rejected alternatives

- **ffmpeg `freezedetect`.** It thresholds a frame's mean difference, not the share of pixels that change, which is
  the measure arc4d3 defined.
- **A pixel step of 1 or 3.** Encoder noise on a held frame would hide every freeze.
- **The first word as the opening.** arc4d3 defined it as the first audible sound. The word is cross-checked, not
  used as the measure.
- **Waivers with bounds.** None of the three has a range a reel could move. A reel that needs a longer freeze waives
  the check with its reason.
