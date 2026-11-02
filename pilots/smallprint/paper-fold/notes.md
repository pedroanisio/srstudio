---
pilot: paper-fold
main-trigger: challenge
generated-by: claude-opus-5-5 in Claude Code
date: 2026-11-02
---

# Notes: Can you fold a paper in half more than 7 times? — Small Print #2

[Back to the library README](../../../README.md)

## Main trigger

Challenge. The reel opens with Rafa already folding. The sheet on his worktop gets smaller and thicker at 0.8 s and
1.6 s, and at 3.1 s it reaches its seventh fold and stalls: "Seven. And... nope." The button is that, yes, you can, and
he will need a longer kitchen. A tissue roll's sheet runs off his worktop and out of the frame. Then he starts again
at fold four, the first frame's picture, and the reel cuts back to it.

## Script

1. "Can you fold paper in half eight times?" (the card: "Can you fold a paper in half more than 7 times?")
2. "Seven. And... nope."
3. "Every fold doubles the layers. Seven folds is 128." Stamp: 7 FOLDS = 128 LAYERS.
4. "Each fold needs about four times the paper." Stamp: 4x THE PAPER, EVERY FOLD.
5. "In 2002, a high school student did twelve. One sheet of tissue, 4,000 feet long." Stamp: 12 FOLDS, 2002.
6. "So yes, you can. I'll need a longer kitchen."
7. "Right. Eight."

## What is claimed

The 128 is arithmetic. "About four times" comes from Gallivan's formula (2001), and the record and its 4,000 ft
sheet come from Guinness World Records (2002). The details are in `sources.md`.

The layers page keeps a ledger: every count lands with its fold and stays up. When the page turns to "four times the
paper", five sheets appear from one corner, each twice as wide and twice as tall as the last.

## Parts reused

Rafa as he is (ADR 0068), all unchanged. Also reused: the plate pipeline, the `host_kit` captions (including the fix
that captions "4,000" as one word), `toon_sketch` build, foley, `Thumbnail`, the signature marks, and the ElevenLabs voice
Will with the brief's settings.

## Parts new (all proposed)

`smallprint-paper` (a sheet folded 1 to 7 times) and `smallprint-roll` (a tissue roll whose sheet runs out of frame),
`smallprint-card`, `smallprint-stamp`, and the `fold-layers` and `long-strip` panels.

## Measured

- **Master:** 22.0 s, 1080×1920, H.264/AAC at 30 fps, −15.1 LUFS, peak −1.9 dBFS, 2,127,160 bytes.
- **Strict render:** `--strict`, 0 findings.
- **Quiet:** no quiet of 1 s or more in the first 5 s. The darkest frame has a mean luma of 116.
- **Build wall times:** the first build failed at 279.7 s on a caption of "4,000" and was fixed in `host_kit`. The
  final build took 90.8 s and the master 44.1 s.
- **Tokens and time:** the three pilots were made in one session, so neither can be split by reel. Measured from the
  session transcript's `usage` fields at 09:24 −03:00, the session used 994 input tokens, 322,219 output, 1,466,545
  cache-creation and 81,397,866 cache-read tokens. Its wall time from 07:11:15 to 09:24 −03:00 was 2 h 13 min.

## Craft score

13/20 (the author's score; no reviewer has scored it). The two pages carry the reel. The folding is shown only by
replacement states of the sheet, not by his hands, and `srstudio craft` finds no pause between the lines.

## What I would change

Show his hands folding, and leave the voice one breath before "So yes, you can."

## Standing rules (the brief's 1–10)

The question is typed on screen from 0.0 s. He tries it by 3.1 s. Each finding is a stamp line over a moving page. No
frame is dark. The button answers the opening another way and cuts back to the first frame. The reel is 22.0 s. The
caption's first line is a question, with five hashtags. It contains no politics or health advice, and nothing harmful
to copy.

## Watch gate

Watch gate: Pedro, after delivery.
