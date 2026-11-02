---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0147: A caption does not run across a sentence end

- Status: accepted (2026-11-01), ordered by arc4d3, the narrower reading ruled by arc4d3 in Slack 1793579374.497809: "A
  window of whole sentences passes; a window that drops the stop or breaks off inside the next sentence is refused.";
  written by Claude Opus 5.5 in Claude Code
- Follows [ADR 0073](0073-frame-gates-and-standing-review.md) and
  [ADR 0146](0146-anatomy-is-a-build-error.md)
- Back to the [library README](../../README.md)

## Context

arc4d3: "Make structural errors impossible in the SDK and kit, not caught in review." Rule 7: "caption cues never run
across a sentence end (the 4 pulled queue reels)."

ADR 0073 made the unmarked case a first-delivery gate, `frame_gates.captions_run_together`: `Take it Whatever`. That gate
sits at the end of the work and lets a window pass once it has any stop. A window can keep the stop and still break off
in the middle of the next sentence: `Meetings have been reduced to one. It is`.

## Decision

1. **The rule is `caption-run`, the check `caption-grammar`.** A burned window, a text layer or a cue of a caption track,
   is at fault when it holds a sentence end of the reel's lines and either drops the stop
   (`frame_gates.run_together`, unchanged) or keeps it and ends inside the next sentence (`frame_gates.broken_off`).
2. **The window has to finish what it starts.** A last word that has a mark of its own, or that ends a sentence of the
   lines, makes a window of whole sentences, and it passes: `You're alive. She's holding line two.` is one spoken line on
   one pill, and `Love it. Evenings?` is the join `stick.word_cues` makes for a sentence too quick for a cue of its own.
3. **It is a build error.** `Episode.finish` refuses before it writes a scene (`text_rules.refuse_captions`), so a pilot
   and a reel never delivered are held too. The reel's subtitles and transcript are written before the build ends, which
   is what the rule reads.
4. **Delivery holds it too.** `text_rules.caption_defects` follows `captions_run_together` in the publish gate. On a
   first delivery a list excuses nothing.
5. **Published windows are rows, not a silent skip.** `assets/text_published.json` names each published window, read
   with the form of the anatomy list and closed to these rules; `srstudio anatomy` prints it with the anatomy rows.
   A second fault in a listed reel, or the same window in another reel, is refused.

## What it would have caught

Measured over the 237 built scenes in `generated/episodes`, each compared with its own lines:

- **37 reels, 58 windows.** 6 reels hold a window with no stop, the class ADR 0073 found. 31 reels only hold a window
  that breaks off.
- **Of the 4 pulled reels, 3.** `take-my-phone` (2 windows), `what-my-dad-does` (5) and `gloss-fewer-meetings` (1). The
  fourth, `text-me`, has no caption at fault: its only sentence end in a window is the whole-sentence pill above, and
  ADR 0073 names its third arm as the defect in that reel, which is rule 2's hand-no-arm.
- 30 reels are published and listed, 44 rows. The 3 pulled reels are not on the list, since they went back to be fixed,
  so a rebuild is refused until the windows are cut. `exciting-opportunity`, `first-sip`, `take-home` and `tell-us` are
  in no delivery manifest, so they are not on the list either: their 6 windows stop a rebuild, and that is the gap to
  close when any of them is next built.

The stricter reading, no window holds a sentence end at all, measures 128 reels: 123 hold a window that keeps the stop, 6 one that drops it, and 1 reel holds both kinds.

## Limits

- The sentences come from `voice-transcript.json` and the `.srt`. A silent reel has nothing to compare, and a reel whose
  subtitles are written after its build is only read at first delivery.
- A pair of words the lines also say inside a sentence is not a boundary, as in ADR 0073.
- A window that ends on a word which ends some other sentence of the reel reads as whole, so `broken_off` can miss one.
- Text in a signature, title or sign is read like a caption, and only faults if it repeats a pair of the lines.

## Alternatives rejected

- **No sentence end in any window.** It reads the words of the rule most literally, and it catches `text-me`'s pill,
  which the record gives a different defect. It would refuse every two-sentence line on one pill in every kit, which is
  the shape a line takes in Toon, Soft, Gloss and Saga, and 123 reels hold it. Nothing on the record calls that shape a
  defect, and the review's words were "captions that run two sentences together".
- **Keep the gate at delivery alone.** It leaves the fault to be found after the voice and the render are paid for.
- **Change `run_together` to fail on a kept stop.** `tests/test_run_together.py` holds the ADR 0073 class as it is, and
  its delivery message is exact. The new class is a second function beside it.
- **A flag that excuses a reel whole.** A row names the window, so a new fault in a published reel's rebuild is seen.
