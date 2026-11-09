---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# 0255 — build-export draws a toon export

Date: 2026-11-09

Status: accepted

## Context

ADR 0254 gave `srstudio build-export` one default staging: a plain stage, the
takes' audio, captions and the cactus. It drew no cast and no set, so a video
rendered through sreditor showed only words on a coloured background.

sreditor's export now carries what a Toon sketch needs, as data:
- `bible/cast.json`, where each character names the rig that draws it under
  `look.drawing` (such as `toon-lyra`);
- `assets/poses.json`, the beats: per appearance, the eyes, mouth and arms
  over time;
- `assets/events.json`, the prop events;
- `assets/staging.json`, the set rig of each take and the rig of each prop
  slug.

The worker still never runs code from a job, so the drawing has to come from
srstudio's own registry and the Toon sketch builder.

## Decision

An export in the `toon` style with at least one beat is built as a Toon
sketch (`srstudio.export_toon`); every other export keeps ADR 0254's default
staging. The command's name and arguments do not change.

- **Cast:** each bible character whose rig is `toon-<name>`, with `<name>` in
  the toon cast, is drawn by that rig. A character with any other rig is left
  out of the beats.
- **Recording:** the takes become the voiced recording `toon_sketch.build`
  reads: `audio/vo-NN.wav`, `narration.json` in the export's language,
  `voiced/script.json`, `voiced/speech.json`, and mouths from each word's
  letters spread evenly over the word.
- **Captions:** each take is cut into pill captions that fit the narrower of
  the pill and the centred width inside the safe area. The cut is chosen so
  that the fewest captions are read under their least time (CAPTION_MIN),
  each waiting at most CAPTION_LAG for the one before. The episode is held
  until the last caption has been read.
- **Beats:** a beat stands on every caption. A pose change or prop event
  closer than MIN_STEP to a beat joins it; otherwise it becomes a silent beat
  that keeps the caption on screen. Two events on one beat are refused.
- **Sets and props:** each take stands in the location rig staging names for
  it, behind the cast; a prop is drawn in front from its event to the end of
  its take. Both come from srstudio's registry, and an unknown rig is refused
  with the path into the export that names it.
- **Signature:** both the cactus and the code are drawn, so the scene passes
  the signature check (ADR 0250).

## Consequences

A sreditor episode in the toon style now renders with its cast, sets, props,
mouth movement and captions, from data alone.

The pills use DejaVu Sans Bold, because the Toon font is not bundled. The
episode spec's language stays the sketch's default; only `narration.json`
carries the export's language. A take with no set plays on the sketch's plain
room.

## Rejected alternatives

- **Greedy caption cuts:** they let a short caption be replaced before it was
  read, which the engine's legibility check flags.
- **Pushing captions after silent beats:** it delayed every following caption
  and broke the lag limit.
- **A new command for toon exports:** the worker calls one command, so the
  choice belongs inside it.
