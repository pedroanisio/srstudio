---
pilot: further-north
main-trigger: recognition of being wrong
generated-by: claude-opus-5-5 in Claude Code
date: 2026-10-31
---

# Notes: Further North

[Back to the library README](../../../README.md)

## Main trigger

Recognition of being wrong. The viewer is asked a question they are sure about, is told to lock the answer in, and is
then shown a straight line that proves them wrong. Each new pair is a slightly harder version of the same mistake, until
the capital of Alaska sits south of Oslo. It ends on a hard return to the first frame and the question, so the second
watch starts on a viewer who now knows, and who wants to try it on someone.

A globe turns with pins on Rome and New York City. On "Rome" the globe falls towards Italy and cuts to a flat map, where
north is simply up. A line runs west from Rome and the camera flies along it to New York City, below the line. Three
more pairs do the same.

## What is claimed

Every figure on screen is the GeoNames point for the city, rounded to 0.1°: the stamp says so. The projections are named
in the caption. "By about fifty kilometers" is the sources' figure for London over Calgary. The climate line is in the
caption only, away from the Calgary beat, and the reel names no ocean current. `sources.md` gives each record, its id
and the status of each claim.

## Parts reused

The Toon stage and sketch build (`toon_sketch`, `sketch`, `scripting`), ElevenLabs takes and transcript check, foley
(`synth.write_whoosh`, `foley.write_bursts`), `Thumbnail`, signature marks, `mind_kit.check_copy`.

## Parts new (all proposed)

`map-globe`, `map-flat`, `map-equal-area`, `map-pin`, `map-parallel`, `map-population`, `map-ring`, `map-stamp`,
`map-captions`, and the look `MAPS` with its narrator Bella.

## What I would change

The Calgary frame is mostly empty land, because that is what is there. The gap is what the shot is about, and it holds
for 1.7 s, but it is the weakest picture in the reel.

## Standing rules

L15 was already met: the caption's first line is the reel's question. The other rules were not reviewed for this reel.

## Watch gate

Watch gate: Pedro, after delivery

## Enhancement

The engine's flash check names only the first bad frame, so this reel's flashes were found one encode at a time.
`srstudio craft --renders` now lists every window that flashes, measured on the master. Kind: checks.
