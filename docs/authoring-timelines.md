---
updated-by: OpenAI Codex (GPT-6)
---

# Load dialogue, takes and caption scripts

[Library README](../README.md) · [Authoring task index](authoring-reference.md)

Import `Timeline` and `TimelineError` from `srstudio.timeline`. Choose the format from the data shape, bind paths to the project root, and keep take-relative word times distinct from project times. The examples below load without provider access. On `TimelineError`, repair the named field before constructing the episode.

Run commands from the srstudio repository root.

## Timeline input formats

`Timeline.load(path)` reads JSON and selects a format by its top-level shape. The same data can be passed to
`Timeline.from_dict(data)`. Times are seconds on the project clock unless described otherwise. Invalid records raise
`TimelineError` with the field or file to correct. These examples describe timing only; an `Episode` also needs the
assets and font selected by its `EpisodeSpec` and style.

Choose one object format: `phrases` for dialogue or `items` for takes. An object containing both is rejected so
take audio cannot be silently ignored.

A dialogue object has a positive `duration` and a `phrases` list. Each phrase needs a nonempty `role` and `text`
and an ordered `start`/`end` inside the duration. Optional `camera_cuts` must have strictly increasing times inside
the duration; `angle` selects intervals through `timeline.shots("wide")`. Optional named beats such as
`reaction_start` and `end_card_start` must be within the duration. `sound_effects` may be omitted.

```json
{
  "duration": 3.0,
  "phrases": [
    {"role": "manager", "text": "Hello there.", "start": 0.3, "end": 1.5}
  ],
  "camera_cuts": [{"time": 0.0, "angle": "wide"}],
  "reaction_start": 1.8,
  "end_card_start": 2.4
}
```

A take timeline has `duration` and `items`. Each take needs `id`, `actor`, `shot`, `text`, `start`, and positive
`duration`. Takes must be contiguous from zero; include pauses in a take's duration. `words` and `phones`, when
present, use times relative to that take. `audio` is optional when parsing, but `ep.audio()` needs an existing file
for every take; paths are relative to the project root. An effect uses `actor: "sfx"`.

```json
{
  "duration": 2.0,
  "items": [
    {"id": "01", "actor": "speaker", "shot": "wide", "text": "Hello.",
     "start": 0.0, "duration": 1.0, "audio": "audio/take-01.wav"},
    {"id": "02", "actor": "speaker", "shot": "close", "text": "Goodbye.",
     "start": 1.0, "duration": 1.0, "audio": "audio/take-02.wav"}
  ]
}
```

A silent caption script is a nonempty list. Each caption needs `start`, `end`, and nonempty `text`; captions must
not overlap. Its duration is the final caption's end. An optional `caption` overrides displayed text.

```json
[
  {"start": 0.0, "end": 1.2, "text": "Hello there."},
  {"start": 1.2, "end": 2.4, "text": "Goodbye.", "caption": "Goodbye!"}
]
```

See [`Timeline.from_dict`, `from_takes`, and `from_captions`](../src/srstudio/timeline.py) for the supported fields
and [`srstudio.takes`](../src/srstudio/takes.py) for producing recorded take timelines.
