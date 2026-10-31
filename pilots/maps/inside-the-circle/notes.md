---
pilot: inside-the-circle
main-trigger: jaw-drop
generated-by: claude-opus-5-5 in Claude Code
date: 2026-10-31
---

# Notes: Inside the Circle

[Back to the library README](../../../README.md)

## Main trigger

Jaw-drop. The first frame is the claim: one ring, already full, and one line saying it holds nearly half of everyone
alive. A dot is a million people, the rest of the world's dots arrive round it, and a hamster shoves through them
apologising. The finding then gets bigger: the same ring slides over Australia, 44 dots fall in, the same hamster has
nobody to apologise to, and the first circle holds about ninety times as many. The reel ends on that map and cuts to the
full ring.

The ring never changes size and the map moves under it, so the comparison needs no explaining. The dots carry the
argument, and the voice only says what they are.

## What is claimed

The older claim, a majority inside 3,300 km of Mong Khet, fails on the 2025 grid at 48.3%, so the reel says "Nearly half"
and does not widen the circle. The stamp gives the rounded count, grid and year. "Almost four billion inside, and over
four billion outside" is the spoken form of that stamp: Bella read the digits "3.95" as "three point ninety-five", so
the line was rewritten in words and the exact figure stays on the stamp.

Both rings are Lambert equal-area maps re-centred on the ring's centre, at one scale, and measured at 429.9 px on the
frame. The caption states that Adelaide was chosen so the circle holds the country and largely misses Java. `sources.md`
gives each figure, the run it came from and the status of each claim. The 2013 circle is gone from the reel: the caption
says where the idea came from, and sources.md rows 14 and 15 carry that.

## Parts reused

The Toon stage and sketch build (`toon_sketch`, `sketch`, `scripting`), the rigged hamster at its version 1, ElevenLabs
takes and transcript check, foley (`synth.write_whoosh`, `map_kit.write_pops`), `Thumbnail`, signature marks,
`map-equal-area`, `map-pin`, `map-stamp`, `map-captions`, the look `MAPS` with its narrator Bella.

## Parts new (all proposed)

`map-ring` gains its tag and `map-population` gains its fade and a zone that is up from the first frame, all added for
this reel. `map_kit.glide` keeps the ring true during the slide. The rest of the staging is this reel's own: the crowd
and the ripples.

## What I would change

The cover's headline sits over the ring's tag. The two ripples outside the ring are faint under its veil. "Each dot is a
million people." wraps with "people." alone on its second line; only a new take would change that.

## Standing rules

Read as an explainer, under the Scope section of the rules: the map carries the idea and the cast comes in to react.

Taken: L4, the claim is on screen and spoken from frame 0, with the ring full. L5, the first line starts at 0.0 s. L7,
the world's dots start arriving at 0.5 s. L8, as an escalating finding: nearly half, then 3.95 bn against 4.24 bn, then
44 million in the same circle, then about ninety times as many. L10, the evidence is a stamp over the map. L11, the
surprise is the first line. L12, the reel ends on the second finding, 0.69 s after its last word, and cuts to frame 1
with no tail. L13, 20.2 s. L15, the caption's first line is a question. L16, the watch gate below.

Partly: L6, one short line on frame 0 over a full ring, read at a glance, but a map and not a reacting face. L9, held
framing, with the hamster for reactions in two shots.

Not taken: L17, `pilotcheck.py` is not on this branch and did not run.

## Watch gate

Watch gate: Pedro, after delivery

## Enhancement

Comparing each frame with the one before missed this reel's stills: a keyframe every two seconds broke them up, and a
picture that stood for nearly four seconds measured under two. `srstudio craft --renders` now lists every hold, each
frame compared with the first of the hold, so a slow change adds up and a keyframe does not. Kind: motion.
