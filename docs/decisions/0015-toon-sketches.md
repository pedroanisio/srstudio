---
generated-by: Claude Fable 5.1 (claude-fable-5-1) in Claude Code
---

# ADR 0015: Toon sketches — comedy as data, cut between two coworkers, voiced per speaker, with props that carry the gag

- Status: accepted and implemented, 2026-10-28 (`srstudio.sketch`, `srstudio.toon_props`, `foley.buzz`/`foley.tones`,
  `toon_cast.sticky_note` and `stickers=`, `toon.captions(tints=)`, `episodes/_toon_sketch.py`,
  `episodes/the_report*.py`, `episodes/logo_bigger*.py`, their tests)
- Deciders: the operator (pedroanisio), implementation drafted by Claude Fable 5.1 in Claude Code
- Back to the [library README](../../README.md); follows [ADR 0014](0014-toon-brush-characters.md)

## Context

The operator asked for episodes that use the new Toon characters, props and locations and are "very funny", and
judged the character sheet ([ADR 0014](0014-toon-brush-characters.md)) not funny at all. A review of that sheet
against the voiced episodes scored it 5/20 on a comedy rubric (hook, premise, setup–turn–punchline, surprise,
escalation, the gag shown, timing, a clear speaker, sound, an ending) and recommended: one joke with Rex and Fern
playing off each other, the gag shown on screen rather than captioned, a real turn, a hold before the punchline with
a sting or voices, and a hook that poses a question in the first two seconds. The silent sheet also left the viewer
guessing who was talking.

## Decision

1. **A sketch is data: speakers, lines, beats.** `srstudio.sketch.Sketch` names its speakers (an ElevenLabs premade
   voice each, and the Toon character one plays on screen, or none for a voice heard on a speaker), the lines (one
   request each) and the beats: every change of caption, on-screen character, expression or prop event at its
   scripted time, a spoken beat naming the line and the word it starts on. `check` refuses an inconsistent sketch
   (unknown characters or expressions, beats held under 0.15 s, lines without a starting beat or out of order,
   a last beat without room before the end). `cues`, `appearances` and `events` are the only derivations the
   build draws from, and `cues` carries the line's speaker so the caption pill is tinted by who says it.
2. **Shot / reverse shot, not a split screen.** The picture cuts between the characters: consecutive beats of one
   character are one appearance, a group on screen from its entrance to its exit holding its set, its props and
   the character on its poses (`toon_cast.dog`/`frog` and `toon.cat` take `enter=`). Two coworkers on one desk at
   the frame's width would need both scaled down and mirrored; a cut keeps each at the size the style draws them,
   and a call badge (`toon-badge`) says who is on the line.
3. **Recorded per speaker, placed on the words, verified.** `sketch.record` says each line in its speaker's
   voice through `srstudio.voice` (typed parse, alignment and audio checks), confirms each voice id by name,
   hears every take back with speech-to-text and refuses the recording when any line is misheard, places the
   lines at the speakers' own pace (`narration.plan_relaxed`) and moves the beats onto the heard words
   (`sketch.place`, the survey's placement generalised: silent beats a moment after the line before them, a
   caption held at least 0.85 s). The placed beats are written to `voiced/beats.json` with their events and read
   back typed (`load_beats`), so the voiced build draws from a file the operator can diff, never from a rerun.
4. **Props carry the gag.** `srstudio.toon_props` adds the meeting room (a whiteboard where the window was), a
   mug with steam, a wall clock whose hands jump to listed times, sticky notes lettered on the laptop lid, phone
   toasts that slide in and shake with a synthesised buzz, marker text on the board, a sun logo that scales about
   its centre to each asked size (linear 0.3 s ramps, held between) with a drop shadow for "make it pop", and the
   call badge. `toon_cast.sticky_note` and the `stickers=` parameter put a note on a character's forehead that
   follows its sigh and lean. Every measure is in the reference screen pixels of the style, every prop refuses
   out-of-range data (`ToonDataError`), and each is registered with the episodes that use it.
5. **Sound between the lines.** `foley.buzz` (two pulses of a hum shaken by the rattle of a phone on a desk),
   `foley.tones` with `STING` (two sagging notes) and `CHIME`, and the keyboard only in the typing beats outside
   the spoken spans; all deterministic, listed in `narration.json` as effects, mixed under the voices.
6. **Two sketches.** *The Report* (T3): Fern asks where the report is, Rex has never heard of it, his own
   reminders buzz in, the notes on his laptop and the one on his forehead have been on screen since the first
   frame; the hold, "...What report?", the sting, the clock past nine. *Logo Bigger* (T4): a client on speaker
   wants the logo bigger until it is the size of the building, then popping, then smaller; the original pops;
   "Invoice sent." / "Can you make the invoice smaller?" / "No." Both open on a question, cut between the two
   coworkers, hold at least 1.2 s before the punchline, and end on the sting. A caption that would not fit the
   frame in one pill is refused at build time (`fit_captions`); a long line is captioned in two beats.

## Rejected alternatives

- **Scoring the jokes with an LLM gate.** A model-scored "funny gate" would need the full verification layer
  CLAUDE.md requires of every model consumer and would still measure a model's taste, not the audience's. The
  rubric's points are enforced where they are mechanical (a question hook, a hold before the punchline, a sting
  after it, both characters on screen, tinted pills) by `tests/test_toon_sketches.py`; the rest is the operator's
  judgement on the rendered video.
- **Both characters in one frame.** See decision 2.
- **Drawing the toasts and the clock as captions.** The rubric's point was that the gag has to be seen; a toast
  that buzzes in with Rex's own words is evidence the audience reads before Rex does.
- **One narrator for every part.** Distinct premade voices per speaker (Charlie, Matilda, George) make the
  speaker clear by ear as the tints do by eye.

## Consequences

- A new Toon sketch is a data module (speakers, lines, beats, `validate` for its events, `dress` for its shots)
  plus two thin scripts; `_toon_sketch.build` and `record_episode` do the rest.
- The sheet episode (T2) stays as the characters' reference; T3 and T4 are the episodes that use them.
- Every recording is one request per line, never retried; a misheard line stops the run with the list of
  mismatches, and the operator decides whether to reword.
