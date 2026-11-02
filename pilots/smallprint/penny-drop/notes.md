---
pilot: penny-drop
main-trigger: myth reversal
generated-by: claude-opus-5-5 in Claude Code
date: 2026-11-02
---

# Notes: Can a penny dropped from the Empire State Building kill you? — Small Print #1

[Back to the library README](../../../README.md)

## Main trigger

Myth reversal. The typed question is on screen from frame 0. Rafa lets one penny go off the clay tower on his worktop:
it tumbles down past the tower and lands on the worktop between 3.3 s and 4.1 s, and he says "Nope. It would sting."
The button turns the question round: what does hit that building is lightning, about 23 times a year, so up there the
penny is the safe one. The last beat is the first frame's picture, and the reel cuts back to it.

## Script

1. "Can a penny from up there kill you?" (the card: "Can a penny dropped from the Empire State Building kill you?")
2. "Okay. One penny." He lets it go, and it falls.
3. "Nope. It would sting."
4. "A penny is flat, so it tumbles. It tops out around 25 miles an hour." Stamp: TOPS OUT AT 25 MPH.
5. "MythBusters tried it in 2003. Busted." Stamp: BUSTED.
6. "Please don't check."
7. "What does hit that building? Lightning. About twenty-three times a year." Stamp: HIT 23 TIMES A YEAR.
8. "So up there, the penny's the safe one."

## What is claimed

Three stamps, each with a named source and its year on screen. The details are in `sources.md`. Nobody is ever drawn
below the drop: the penny lands only on the worktop. The reel and the post both ask the viewer not to test it.

## Parts reused

Rafa as he is (ADR 0068): his body, head rig, moods, mouths, room and worktop plates, all unchanged. Also reused: the
plate pipeline (`rafa_host`, `plates`, `rafa_reel.cut`), the `host_kit` karaoke captions, `toon_sketch` build, foley,
`Thumbnail`, the signature marks, and the ElevenLabs voice Will (`bIHbv24MWmeRgasZH58o`, `eleven_multilingual_v2`, seed
52026, stability 0.42, similarity 0.75, style 0.35).

## Parts new (all proposed)

`smallprint-tower` (a stepped clay tower with a penny: top, three tumbles, landed), `smallprint-card`,
`smallprint-stamp`, and the `penny-fall` and `lightning` panels.

## Measured

- **Master:** 22.7 s, 1080×1920, H.264/AAC at 30 fps, −15.4 LUFS, peak −1.9 dBFS, 2,223,801 bytes.
- **Strict render:** `--strict`, 0 findings.
- **Quiet:** no quiet of 1 s or more in the first 5 s. The darkest frame has a mean luma of 115.
- **Build wall times:** the first build took 1458 s, most of it path-tracing the plates. The final build took 55.9 s
  and the master 69.9 s.
- **Tokens and time:** the three pilots were made in one session, so neither can be split by reel. Measured from the
  session transcript's `usage` fields at 09:24 −03:00, the session used 994 input tokens, 322,219 output, 1,466,545
  cache-creation and 81,397,866 cache-read tokens. Its wall time from 07:11:15 to 09:24 −03:00 was 2 h 13 min.

## Craft score

14/20 (the author's score; no reviewer has scored it). The fall reads, and each stamp lands over a moving page. Three
lines follow the one before with almost no gap (`srstudio craft`: crowded lines at 6.30 s, 13.92 s and 19.90 s), so
the voice breathes less than it could.

## What I would change

Leave a short gap before each of the three crowded lines. The `SR-1028` signature is nearly invisible on the paper
panels.

## Standing rules (the brief's 1–10)

The question is typed on screen from 0.0 s. He tries it by 3.3 s. Each finding is a stamp line over a moving page. No
frame is dark. The button answers the opening another way, and the last frame cuts back to the first. The reel is
22.7 s. The caption's first line is a question, with five hashtags. It contains no politics or health advice, and
nothing anyone can copy from it.

## Watch gate

Watch gate: Pedro, after delivery.
