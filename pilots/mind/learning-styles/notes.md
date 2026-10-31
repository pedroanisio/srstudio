---
pilot: learning-styles
main-trigger: reversal
generated-by: claude-opus-5-5 in Claude Code
date: 2026-10-31
---

# Notes: The Meshing Hypothesis

## Main trigger

Reversal. A viewer who was told they have a learning style watches a hedgehog do what that idea allows: a page gone
entirely yellow, "I'm a visual learner", and no answer to "What's it say?". The reel names the idea, shows what the
preference does and does not track, then gives the review's verdict on screen. The ending repeats the first exchange
with the book shut, and this time "It's important." is true.

## What is claimed, and what is comedy

- The evidence card uses the words of the Pashler et al. abstract only. The full text was not accessed, as `sources.md`
  records, so the card names no page and quotes only "no adequate evidence base", with the abstract's limit to general
  teaching kept. The one page confirmed anywhere, p. 105, is secondary and is not shown.
- The reel never says disproved except as "Not disproved". The line under the card carries the 2024 meta-analysis: a
  small benefit, "too small and too infrequent" for widespread adoption. The caption prints g = 0.31, the abstract's
  figure; the paper's Results section gives 0.32. The 26% crossover figure is not on screen.
- 89.1% is labelled educators surveyed, on screen and in the caption. Most of those samples were convenience samples,
  which "surveyed" only hints at. It is read, not spoken, and it says "too" so the viewer and the teachers are in the
  same position: nobody here was foolish.
- "Many of us were told" is the wording `sources.md` allows. No source measures how many people were told this.
- The lens is comedy over a real result. Knoll et al. 2017 (abstract) relate style scores to judgments of learning, with
  "no association between VVQ scores and recall". The heights of the files are a picture of that, not a measurement.
- "Test yourself instead of rereading" rests on Dunlosky et al. 2013 (abstract), which rates practice testing high and
  rereading and highlighting low. "Match the format to the material" is Willingham's expert advice and is not in the
  reel.
- The quiz, its "Mostly A's" and the colour key on the page are invented. The hyper-specific detail is the key
  separating "important" from "very important", and the reel never explains it.
- The file labels were shortened to "How it felt" and "Recall" so the lens could pass under them.

## Parts reused

Hedgehog (version 2) and cat (version 1) from the Toon cast; the home room with its shelf and window, ledge and chair;
`mind-stage`, `mind-name-card`, `mind-evidence-card`, `mind-captions`, `mind-lens` and `mind-memory-shelf`; the channel
sting; the signature cactus and code. The hedgehog has no head rig and the cat is traced, so neither turns its head, the
cat has no frown and its mouth moves on word beats.

## Parts new (all proposed)

`toon-open-book`, `toon-shut-book`, `toon-highlighter`, `toon-study-page` and `toon-quiz-sheet`, in
`src/srstudio/toon_study.py`, catalogued in `docs/catalog/notes.json`. `srstudio.mind_kit` did not change. All effects
are synthesised.

## What I would change

- The name lands early: the catchphrase at 33% and the reveal at 35%, against a target near 40%. The reel is already at
  the 45 second limit, so holding the opening longer would need a cut after the name.
- The reel is exactly at the limit, 45.0 seconds. Dropping "Note the last word." would buy room, but the underline is what
  makes the name a joke and not a label.
- The narrator carries a lot in the middle. The evidence and its caveat are two long lines, and a viewer who only wants
  the joke waits from about 24 to 37 seconds for the hedgehog to come back.
- For the same reason sound is thin: speech and synthesised effects only, no music. The pauses at 4.05, 6.04 and 40.15
  seconds are digital silence on purpose, and I have not heard how they play.
- During the last highlight her fist passes over the first words of the row for a moment. It is the action, and the row
  is clear by the last frame, but a pen held from below would avoid it.
- A two-line caption sits over the tips of her spines at the turn. It covers no face, eye or text.
- `check_copy` catches OCD but not ADHD or autism, which a learning reel could easily reach for. That is a kit change,
  so I left it.
