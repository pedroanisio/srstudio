---
pilot: most-time-zones
main-trigger: surprise
generated-by: claude-opus-5-5 in Claude Code
date: 2026-11-01
---

# Notes: Most Time Zones — Maps #4

[Back to the library README](../../../README.md)

## Main trigger

Surprise. The first line answers a trivia question with the wrong-sounding country: "Most time zones on Earth? France."
The hamster objects that it is tiny, and the map answers him by going to Tahiti, then Reunion, then a land border with
Brazil that he did not expect. Twelve clocks fill the frame, all reading one moment, and seven towns light up in turn so
the sun never sets on them. The reel ends on the hamster's "So what time is lunch?", a flat "Yes.", and a cut to frame 1.

## What is claimed

Twelve is the July count from tz database 2026c and it is a July count: in January France and Russia tie at eleven, so
the stamp says July and the caption says the tie. `validate` refuses the build unless the twelve clocks show twelve
different times.

"The sun never sets on France" rests on seven towns checked at every five minutes of 2026. The lowest sun over the
seven is 19.7° on 18 June, the day the reel runs. `validate` stops the build if a five-minute step of that day leaves no
town lit. The pins for Guiana and Brazil are positions chosen inside each country, to mark the border, and are not
measured places.

"Tahiti is France" rests on Natural Earth's country data. The French constitutional text could not be reached, and
`sources.md` does not cite it.

## Parts reused

The Toon stage and sketch build (`toon_sketch`, `sketch`, `scripting`), the rigged hamster, ElevenLabs takes and
transcript check, foley, `Thumbnail`, signature marks, `map-stamp`, `map-captions`, `map-pin`, the look `MAPS` with its
narrator Bella.

## Parts new (all proposed)

`map_kit.clock`, registered as `map-clock`, and `map_kit.daylight`, registered as `map-daylight`, with `sun_altitude`
and `lit` behind them. No letters on a clock face, so it needs no language.

## What I would change

Some clocks in the ring sit behind the hamster and the floor. The twelve are all drawn and the count is in the line, but
a viewer cannot count twelve there.

## Standing rules

Read as an explainer, under the Scope section of the rules.

Taken: L4, the claim is spoken from frame 0. L5, the first line starts at 0.0 s. L7, the map moves in the first second.
L8, as an escalating finding: islands, a border with Brazil, twelve clocks, the sun. L10, the evidence is a stamp over
the map. L11, the surprise is the first line. L12, the reel ends on the hamster's last question and cuts to frame 1. L13,
23.4 s. L15, the caption's first line is a question. L16, the watch gate below.

Partly: L6, the opening reads through its caption.

L18: two voices, short silences between the lines, and no music bed.

Not taken: L17, `pilotcheck.py` is not on this branch and did not run.

## Watch gate

Watch gate: not watched yet.
