---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0173: Caption breaks keep phrases whole

- Status: proposed (2026-11-01), on the operator's approval to port four ideas from pnkit; written by Claude Opus 5.5
  in Claude Code
- Source of the idea: pnkit, the operator's other kit, `pnkit/captions.py` at commit 7d935e5 (`WEAK`, `is_number`,
  `no_break`, `line_break`) and `tools/caption_gate.py`; rewritten here in srstudio's style rather than copied
- Builds on [ADR 0021](0021-engine-native-features.md) (the engine wraps a cue by characters) and stays compatible with
  rule 7 (ADR 0146, `a caption does not run across a sentence end`, on the unmerged `feat/sdk-rules`)
- Back to the [library README](../../README.md)

## Context

A viewer reads a caption one window at a time, and every break is a place where the reading stops. A break after
`the`, between `twenty` and `thousand`, or between `New` and `York` leaves half a phrase waiting for the next window.
srstudio breaks burned text in three places:

- **Cue cuts.** `native.cues_from_takes` splits a take that does not fit a cue (`_fit`), re-cuts a short tail
  (`_split`), and splits a cue whose last line would be an orphan (`_unorphan`).
- **The engine's wrap inside a cue.** The engine wraps a cue greedily by characters (ADR 0021), and `native.wrap`
  mirrors it. srstudio decides these breaks only by choosing what goes into each cue.
- **The kits' own lines.** These are text layers that each kit wraps itself: `look.wrap` (used by `saga_sets` and
  `gloss_sets`), `map_kit`, `mind_kit`, `news_kit` and `host_kit` `_wrap`, `collage.caption_lines`,
  `stick.word_cues` and `phrasing`.

## Decision

1. **`srstudio.breaks.forbidden(tokens)`** names each place where no break may fall, with the reason:
   - after a weak word: articles and determiners, prepositions, conjunctions, auxiliaries and modals, subject
     pronouns, and `to`;
   - inside a number: a number followed by a number or by a joining word, as in `twenty thousand`, `75 per cent` or
     `one in ten`;
   - inside a name: a capitalised word followed by a capitalised word or a digit, as in `New York` or `Apollo 12`. A
     word that only opens a sentence does not count, and text in capitals has no names.

   A word ending in `.` `?` `!` `;` `:` or `…` frees the break after it.
2. **The rule holds "while another break fits".** A forbidden break is taken only when no other cut or layout fits.
3. **Cue cuts.** `CaptionLook(keep_together=True)` replaces the greedy fill with a choice over every way to cut the
   take. It picks, in order:
   - the fewest cues that keep a sentence end and stop inside the next sentence (rule 7's `broken_off`);
   - then the fewest forbidden cuts;
   - then the fewest cues;
   - then the most even fill.

   The greedy fill is one of the ways it considers, so it is never worse on the first two counts. `_split` and
   `_unorphan` rank a forbidden cut after every allowed one.
4. **Kit lines.** `look.wrap(..., keep_together=True)`, which `saga_sets.wrap` and `gloss_sets.wrap` pass through, lays
   the words out with `breaks.lay_out`. It picks the fewest forbidden breaks, then the fewest lines, then the most even
   lines, within the box's `max_lines`. A text with explicit newlines keeps the author's breaks.
5. **Off by default, on for new work.** Every shipped look and wrap keeps its default. A published reel is frozen, and
   its rebuild must stay byte-identical. A new reel opts in through `CaptionLook(keep_together=True)` and through the
   `keep_together` argument of the wraps.
6. **Rule 7 stays whole.** A stop always frees the break after it, so the rule never pulls a cut away from a sentence
   end. The cue chooser counts rule 7's fault before its own, so it never trades a forbidden cut for a window that
   breaks off. A test holds both counts against the greedy fill on the same takes. This branch is built on `develop`,
   where `feat/sdk-rules` is not merged, so the chooser reads rule 7 from the cue's own punctuation rather than from
   `frame_gates.broken_off`.
7. **`srstudio.caption_breaks.audit(scene, lines)`** reads a built scene and lists each forbidden break, saying whether
   another break would have fitted. It checks cue cuts, the engine's wraps (mirrored) and the kits' text lines. It
   counts only breaks where the reel's lines say the two words in a row. A caption that has lost its stops gets them
   back from the lines.

## What it measures on the reels built so far

`caption_breaks.audit` was run read-only over the 237 reel scenes in `generated/episodes` (`<slug>/<slug>.scene.xml`,
compared with `frame_gates.sentences_of`). The 4 projects with no scene of that name were not read, and no delivered
file was changed.

| Break | Forbidden, another fits | Reels | Forbidden, nothing else fits | Reels |
|---|---|---|---|---|
| Cue cut | 35 | 18 | 0 | 0 |
| Engine wrap inside a cue | 52 | 29 | 22 | 16 |
| Kit text lines | 68 | 45 | 80 | 66 |

- 56 reels hold at least one forbidden break where another would have fitted.
- Almost all of these follow a weak word: 34 cue cuts, 51 wraps and 67 text lines. One break of each kind falls inside
  a name. None falls inside a number.
- Those reels are published and frozen, so the rule does not change them. The counts say how often new reels would
  otherwise repeat the pattern.

## Limits

- Weak-word lists are heuristic. `this` and `that` can close a phrase (`Is any of this / even real?`), and the list
  still marks the break after them. Over the reels, breaks after `this` or `that` are 8 of the 155 counted where
  another break fits. Breaks after `a` (24) and `the` (21) are the most common.
- For text layers, "fits" is measured in characters against the longer of the two lines already there, and only one
  pair of lines is re-cut at a time. A bubble that could be re-laid across three lines is counted as stuck.
- The engine's wrap inside a cue is still greedy. srstudio controls it only through what each cue holds. The chooser
  keeps cue cuts legal, but the engine can still wrap a cue's two lines after a weak word. That accounts for 52 of the
  breaks above.
- `map_kit`, `mind_kit`, `news_kit` and `host_kit` `_wrap`, `collage.caption_lines`, `stick.word_cues` and `phrasing`
  do not take the option yet. Each wraps with its own measure and its own published reels. That is 38 of the 68
  text-line breaks above, outside Saga and Gloss.

## Alternatives rejected

- **Turn the rule on in every shipped look.** It changes the cues of a published reel's rebuild, which the fidelity
  tests and the frozen-delivery rule refuse.
- **Bind words with a no-break space, so the engine cannot wrap between them.** It changes the text that is drawn and
  measured, the engine's handling of U+00A0 in its character wrap was not measured, and a font without the glyph would
  draw a box.
- **pnkit's weighted cost (`FAULT = 50` for each break where none may fall).** One weight turns a rule into a trade
  against evenness. An ordered comparison states the rule exactly: no forbidden break while an allowed layout fits.
- **Move a greedy cut back to the last allowed place.** This was tried first. It is local, and a test caught it
  shifting a later cut into a window that broke off inside a sentence. The whole-take choice cannot do that.
