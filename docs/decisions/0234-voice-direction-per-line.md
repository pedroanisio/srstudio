---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0234: Voice direction per line

- Status: proposed (2026-11-04). Slice (a): the model, the direction schema and the holds. Text to Dialogue (b) and
  the take ranking and gate (c) follow in their own commits.
- Deciders: the operator; ordered by arc4d3 (Slack, 4 Nov); written by Claude Opus 5.5 in Claude Code
- Follows [ADR 0031](0031-shared-look-and-caption-primitives.md) and [ADR 0170](0170-approved-files-are-write-once.md)
- Back to the [library README](../../README.md)

## Context

Pedro's note on Between Friends: the voices lack intonation and pauses. The focal word "discipline" gets no pause and
no weight, one listener heard "dog food" as "doctor's", and a reply comes with no room to breathe. Every take so far
is one `eleven_multilingual_v2` request with plain text. The kit gave a director only the voice settings, the pace
and a hold after a take. Any markup written into a line would reach the captions and the speech check.

We read the ElevenLabs documentation and checked each claim we build on with a short real request on 2026-11-04:

| Claim | Source | Real request |
| --- | --- | --- |
| `eleven_v4` exists and is recommended over v3 for audio tags | help centre, "How do audio tags work with Eleven v3 and v4" | `GET /v1/models` lists `eleven_v4`, `eleven_v4_turbo`, `eleven_v3` |
| v3 and v4 perform tags such as `[sighs]` | best-practices guide | v3 and v4: the tag is not spoken; scribe reports `[sighs]` as an event |
| A tag on multilingual v2 | not documented | spoken aloud: "[sighs] Allergies." was heard as "Size allergies?" |
| The alignment of a tagged request | not documented | it spells the sent text, tags included, and the tag letters span the sigh |
| `<break time="x.xs" />` up to 3 s; v3 and v4 take none | controls guide | v2: a 1.0 s break gave 1.07 s of silence; v4: ignored, no pause, not spoken |
| v4 has no style and no speed | Eleven v4 page | v4: speed 0.7 and 1.0 gave the same 2.273 s clip |
| previous_text and next_text | TTS API reference | accepted on v2 and v4; v3 answers HTTP 400 "not yet supported" |
| Capitals stress a word, an ellipsis adds a pause (v3, v4) | best-practices guide | "Just..." gave a 0.41 to 0.44 s pause on v3 and v4 |
| v3 stability is discrete (Creative, Natural, Robust) | not found in the current docs | v3 accepted 0.3: kept as 0..1 |

## Decision

`srstudio.direction` adds a typed `Direction` per line. `takes.Take`, `series.line` and
`ElevenLabsClient.synthesize` take it as a keyword argument.

- **Model.** `Direction.model` sets the model for one line. `Script.models` and `Series.models` set it for each
  voice. The checked models are `eleven_multilingual_v2`, `eleven_v3` and `eleven_v4`, each with a `ModelSpec` of
  what it takes. Without a direction, a take is sent as before.
- **Tags.** `tags` are names from the documented allow-list `AUDIO_TAGS`, or `strong X accent`. A described quality,
  such as `quality="quietly, holding back"`, adds one more tag. Tags are refused on multilingual v2, which speaks
  them.
- **Emphasis.** `emphasis` names words of the line. Each one is sent in capitals, as a whole word, wherever it occurs
  in the line. Only v3 and v4 take emphasis. A word the line does not have is refused.
- **Pauses.** `pauses` are break tags after a named word, 0.1 to 3 s, three at most, on multilingual v2 only. On v3 and
  v4 a pause is a cut: the line becomes two takes with a `post_hold` or a `pre_hold`. An ellipsis in the words marks a
  hesitation.
- **Holds.** `pre_hold` is exact digital silence cut into the take before its speech, and the take's words move later
  by the same amount. `post_hold` is the silence after the take and replaces `hold`. Setting both is refused.
- **Speed.** `speed` is 0.7 to 1.2, only on a model where it takes effect.
- **Continuity.** `context=True` sends the previous and next spoken lines of the script as `previous_text` and
  `next_text`. It is refused on v3.
- **Takes.** `takes=N` records N takes on seeds `seed, seed+1, ...`, each cached under its own key. Every take is heard
  back. With more than one take, the recording stops until `pick=k` names the one to keep. The takes stay cached, so
  naming the pick costs no request. `timeline.json` records the model, seed, direction, every take with its seed and
  hearing, and the pick.
- **Settings.** v3 and v4 take only stability and similarity. Their settings come from
  `VoiceSettings.expressive(stability, similarity_boost)`. A style or pace that the model would drop is refused.
- **The line's own letters.** `render` keeps a source index for each sent letter, and `spoken` maps the provider's
  alignment back to the line. It drops tag and break letters, undoes stress capitals, keeps the timings, and raises
  `VoiceOutputError` when the alignment spells anything else. Captions, word timings and lip sync read only the
  line's words.
- **The speech check** compares the spoken words. On a tagged line only, the recogniser's bracketed events
  (`[sighs]`) are dropped. A tag spoken aloud is heard as words and still fails.

Every refusal is a `DirectionError`, a `VoiceRequestError`, raised before any request.

## Consequences

- Every published take keeps its request and cache key. A test pins two keys computed before this change.
- The A/B clips are in `generated/voice-ab/`, 42 clips: 7 voices, 3 lines, v2 against v4. The speech check caught two
  v4 takes that stuttered ("Is, is this about the breakup?"), which is why a key line gets several takes.
- The premade voices do not list `eleven_v4` in `high_quality_base_model_ids`, but they synthesise on it. Whether they
  sound as good there is a listening question for Pedro.
- `sketch.record`, the Toon sketch recorder, takes no direction yet. A sketch line is said as before.

## Rejected alternatives

- **Markup inside the line's text** (`"[sighs] Just... discipline."` as the line). The tags would reach the captions,
  the speech check and the lip sync, which is what kept Between Friends off tags.
- **Switching every reel to v4.** Every cache key and every take would change, and published reels are frozen.
- **Break tags on v4,** as the claim that "v4 takes SSML" suggests. The docs say no, and a real request ignored them.
- **Stripping tags with a regular expression over the alignment.** That cannot tell a tag from a bracket in a line,
  and it loses the mapping for stress capitals. The source index is exact, and it is checked.
- **Keeping the first take that passes the speech check.** The point of several takes is a choice made by ear. A silent
  default would hide it.
- **Room tone for the holds.** Exact silence is measurable and the mix has its own bed. Room tone can come later as a
  mix decision.
