---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0234: Voice direction per line

- Status: proposed (2026-11-04). Slice (a): the model, the direction schema and the holds. Slice (b): Text to
  Dialogue, cut back into one take per line. Slice (c): the takes measured and ranked, and the prosody gate. Slice
  (d): the gate at first delivery.
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
| Text to Dialogue takes v3 and v4 only | Text to Dialogue API reference | v4 and v3 answer; multilingual v2 answers HTTP 400 |
| A dialogue's alignment and `voice_segments` | Text to Dialogue API reference | the alignment spells the inputs joined with nothing between; segments meet end to start and hold their letters |
| Dialogue settings | API reference: `stability`, `similarity` | an unknown key (`similarity_boost`) is accepted without a word |

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

**Exchanges (slice b).** `srstudio.dialogue.say` sends two or more turns as one Text to Dialogue request
(`/v1/text-to-dialogue/with-timestamps`, v4 by default, v3 allowed). It parses the answer into typed segments and
an alignment, rejects unknown fields, and checks that the alignment spells the sent turns. It also checks that each
turn's segments meet end to start, cover exactly that turn's letters, are said by that turn's voice, and hold their
letters' times. It then cuts the audio into one take per turn, each with its own words' alignment on the cut's
clock. A silent turn or an audio length that does not fit is a `VoiceOutputError`, and nothing is cached on failure.
A script opts in per exchange with `Script.exchanges` (or `Reel.exchanges`) of
`takes.Exchange(first, last, model, settings, takes, pick)`. Every other run of lines stays one request per line, so
the script chooses per exchange which reads better. Inside an exchange:

- Each turn is heard back on its own cut, and bracketed events count only on tagged turns.
- A turn's direction is limited to tags, a quality and emphasis, because the dialogue keeps its own timing.
- Every take but the last holds 0, and no take has its own pace. A take lasts until the next turn's speech starts on
  the dialogue's clock. The timeline records that gap with the cut's place in the dialogue. The last take keeps its
  hold.
- `takes=N` records N dialogues on seeds `seed, seed+1, ...`. With more than one, the recording stops until `pick`
  names the kept dialogue. Every candidate's hearing is recorded on the exchange's first take.

**Measures, ranking and the gate (slice c).** `srstudio.prosody` measures every recorded take on its own clip. It
takes the word times from speech-to-text. For each word it measures the RMS level in dB and the pitch: the 90th
percentile of a YIN fundamental-frequency track over the word's voiced frames (40 ms frames, 10 ms hop, 70 to 400 Hz).
A stressed word is one in `emphasis`, or the word named by the new `Direction.punchline`. Per line it also measures
the pitch of the voiced frames inside its words: their median, and their spread (the interquartile range in
semitones). A word's weight is its level over the line's median word, in dB; its lift is its pitch over the line's
median pitch, in semitones. A one-word line has neither. `timeline.json` keeps, per take, the heard words with their
numbers, the line's median pitch and spread, the first and last word on the take's clock, the words per second, and
each stressed word's place and margins. When a line or an exchange has several takes, they are ranked best first in
the order the voice analysis gives: the speech check, then the stressed word's weight and lift (every one landing,
then the weakest margin), then the pace against the line's bound. A line with no stressed word is weighed on its
loudest word. The ranking goes into the "pick one" failure, the transcript report and the timeline. The pick stays
the builder's.

The targets and their definitions are arc4d3's, from 126 Okayville reels (1,745 lines, all on multilingual v2), in
the voice analysis of 4 Nov. Key lines are the punchline (`Direction.punchline`), the button (the reel's last line,
marked or not) and an answer (the other speaker's reply to a line ending in "?"). A key line with no stressed word
named is held to the stress target on its loudest word.

| Check | Target |
| --- | --- |
| `reel_pace` | at most 3.6 words a second of speech over the reel |
| `line_pace` | at most 4.3 words a second on any line, unless the rush is the joke (a waiver) |
| `first_word` | the first word by 0.25 s |
| `turn_median` | the reel's median gap at a change of speaker 0.3 to 0.65 s |
| `turn_gap` | no default gap at a change of speaker over 0.7 s |
| `answer_gap` | 0.4 to 0.9 s from a question to its answer; once per reel up to 1.5 s (the emotional hold) |
| `punch_gap` | before a punchline or the button: aim 1.0 to 1.8 s, flagged under 0.5 s or over 2.0 s |
| `end_breath` | 0.3 to 1.2 s from the last word to the end |
| `stress` | each stressed word heard, at least +3 dB weight and +2 semitones lift; on a key line, its loudest word too |
| `spread` | a key line's pitch spread at least 3.2 semitones |
| `flat` | any line's pitch spread at least 1.5 semitones, under it a flat take to retake |
| `delivery` | the punchline's and the button's lift and weight at least +1 semitone and +1 dB over the median of the reel's other lines |
| `hold` | the measured silence keeps the direction's `pre_hold` and `post_hold` (50 ms slack) |

The median at a change of speaker counts the turn and answer gaps that keep their own target and are not waived: a
gap already flagged, the emotional hold and a punchline's hold are not default gaps. The gate computes every margin
again from the recorded words, so a stale margin in the record cannot pass it.

`prosody.gate(timeline)` returns every finding, and `python -m srstudio.prosody PROJECT` exits 1 on any finding that
is not waived. Recording writes the targets and findings into `timeline.json`, but does not stop on them. A line
overrides a target only through `Direction.waive`, a `Waiver(check, reason, bounds)` whose reason is a sentence. With
bounds, the waiver moves a ranged target; without them, the check is off for that take. A waived finding stays listed
with its reason. `reel_pace` and `turn_median` are waived on `Script.waive` or `Reel.waive`. `punchline` and `waive` change nothing in
the request: a take whose direction only carries them is sent as an undirected take, with the same cache key.

**At first delivery (slice d).** arc4d3 ruled on 4 Nov that the prosody findings are advisory from the day the
gate lands, listed in every first-delivery report, and refuse only scripts started after it. `srstudio.prosody_gate`
reads `episodes/<slug>/timeline.json` for each first delivery:

- **Unmeasured.** A timeline with no `prosody` section, or no timeline, reads "unmeasured" and is listed, never
  refused. `takes.record` writes the section since slice (c) and nothing before it did, so the section is the marker
  for a reel recorded to the gate. Reels recorded on an earlier library, such as the Juno & Pip episodes 4 to 6 and
  the News pair arc4d3 named, carry none.
- **Refused.** A reel with the section is refused on any finding no stated reason waives. The gate runs
  `prosody.gate` again with today's targets and does not trust the recorded `passed`, which can be stale or edited.
  A section or timeline it cannot read refuses the reel.
- **Waived.** A waived finding is listed with its reason. `deliver` prints the report, and the delivery post to the
  reviewer quotes it. The Instagram caption (`ig.txt`) is public and never carries a waiver.
- **Pilots.** A pilot reaches Drive as a package, and its build project has no fixed place. `prosody_gate.judge`
  reads the `project/timeline.json` its package carries. No package carries one today, so every pilot reads
  "unmeasured" until its package does.

## Consequences

- Every published take keeps its request and cache key. A test pins two keys computed before this change.
- The A/B clips are in `generated/voice-ab/`, 42 clips: 7 voices, 3 lines, v2 against v4. The speech check caught two
  v4 takes that stuttered ("Is, is this about the breakup?"), which is why a key line gets several takes.
- The premade voices do not list `eleven_v4` in `high_quality_base_model_ids`, but they synthesise on it. Whether they
  sound as good there is a listening question for Pedro.
- `sketch.record`, the Toon sketch recorder, takes no direction yet. A sketch line is said as before.
- A dialogue costs one request for all of its turns. Its cache key is the whole request, so changing one turn
  re-records the exchange.
- Pace is measured over speech, from each line's first word to its last, summed over the reel; arc4d3 confirmed
  this reading (words per second of speech, not of running time). The targets and definitions were checked against
  the voice analysis itself (Slack file F0CESR11JFM, 4 Nov). That check moved the change-of-speaker target to the
  reel's median with a 0.7 s ceiling per gap, the punchline flag to 0.5 and 2.0 s with the button counted as a
  punchline, the stress margins to the line's median word and median pitch, and added the spread, flat and delivery
  checks and the loudest word on key lines.
- A reel recorded before the gate and recorded again after it carries the section and is judged; the marker is the
  recording, not the date the script was written.
- On the real three-turn dialogue, Christopher's emphasised "discipline" measured -0.8 dB against his line's median
  word and -3.3 semitones against its median pitch, so the capitals did not lift it. "What do you feed him?" ran at
  6.8 words a second. All three lines measured a pitch spread of 1.2 to 1.5 semitones, two of them under the 1.5
  floor for a flat take. The ranking and the gate exist for exactly these cases.
- A real three-turn v4 dialogue (Will, Christopher, Will, 72 characters) went through `say` on 2026-11-04. Each cut
  was heard as written ("What do you feed him?", "Dog food and discipline", "Just discipline?").

## Rejected alternatives

- **Markup inside the line's text** (`"[sighs] Just... discipline."` as the line). The tags would reach the captions,
  the speech check and the lip sync, which is what kept Between Friends off tags.
- **Switching every reel to v4.** Every cache key and every take would change, and published reels are frozen.
- **Break tags on v4,** as the claim that "v4 takes SSML" suggests. The docs say no, and a real request ignored them.
- **Stripping tags with a regular expression over the alignment.** That cannot tell a tag from a bracket in a line,
  and it loses the mapping for stress capitals. The source index is exact, and it is checked.
- **Keeping the first take that passes the speech check.** The point of several takes is a choice made by ear. A silent
  default would hide it.
- **Splitting a dialogue at the alignment's word boundaries** instead of at `voice_segments`. The silence between turns
  would have no owner. Segments are the API's own turn boundaries, and they are checked against the letters.
- **`previous_text` on a dialogue.** The API accepts it, but an exchange already carries its own context.
- **Ranking on pitch alone.** A word shouted on the same note, or sung higher at the same level, is not the stress
  the analysis measured. The targets ask for both.
- **Stopping the recording on a gate finding.** The builder needs the numbers to pick a take or write a waiver, and
  the cached takes cost nothing to re-measure.
- **Room tone for the holds.** Exact silence is measurable and the mix has its own bed. Room tone can come later as a
  mix decision.
