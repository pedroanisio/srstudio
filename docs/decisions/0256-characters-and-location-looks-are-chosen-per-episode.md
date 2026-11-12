---
generated-by: Claude Fable 5.2 (claude-fable-5-2) in Claude Code
---

# ADR 0256: How a character is made and how a location looks are chosen per episode

- Status: accepted (2026-11-12), on the operator's word. The operator gave the rule for characters. For locations the
  operator said the condition must be corrected for the same reason and gave no wording: that wording is this record's
- Deciders: the operator; written by Claude Fable 5.2 in Claude Code
- Amends [ADR 0091](0091-hybrid-drawing-is-the-default.md), one clause of its decision, and
  [ADR 0179](0179-srlocations-location-bridge.md), the first condition of *What renders next to our figures*
- Back to the [library README](../../README.md)

## Context

Two sentences in this repository read as rules for all work.

1. [DRAWING.md](../../DRAWING.md), *The five layers*: "Characters stay on their style's rig: people, animals and
   creatures." ADR 0091 repeats it in its decision as "people stay on their rigs".
2. ADR 0179, *What renders next to our figures*: "These are arc4d3's conditions, and they bind every reel that uses the
   bridge", and the first of its three conditions: "A location rendered next to our figures is drawn in our cel/ink or
   clay look, never path-traced realism."

The question came up because a sibling library of the operator's builds its cast as 3D figures on srlocations'
mannequin skeleton, in plush, vinyl and low-poly families, and that cast is being connected to srstudio so it can
appear in episodes. Read as written, the first sentence forbids such a character in an episode, and the second forbids
any look but cel, ink or clay for the place it stands in.

On 2026-11-12 the operator ruled that srstudio is wrong in both: each sentence took one situation for a general rule.
Asked what the general rule for characters is, the operator answered that there is none, that the sentence goes, and
that each episode or style chooses whether a character is a drawn rig or a 3D model. The operator said the location
condition must be corrected for the same reason. This paragraph paraphrases the ruling; it does not quote it.

### Where the character sentence came from

- It entered with the first version of DRAWING.md (commit `c0bb94d4`, 2026-11-01), which was then a proposal: how the
  styles the library already had would take 3D proxies for rigid objects, painted environments and a shared light. The
  sentence opens the paragraph on the proposed `forms` module, which attaches shading to a drawn rig.
- ADR 0091 (commit `f69fad45`, the same day) made that method the default and shortened the sentence to "people stay on
  their rigs". It moved the rigid-object layer out of a study, now `examples/car_vibe`: a car modelled in 3D and drawn
  as cel plates, with the people of the scene drawn between the plates.
- In that situation the sentence says something true: a drawn style that takes a proxy for its car does not remodel
  its people. The *Video types* table says the same per type: Toon keeps its rigs, Collage its paper people, Stick and
  Soft their figures.
- It was not true of every character even then. The same paragraph says "Rafa stays on plates", and the table lists
  Host as "Rafa, modeled, on path-traced plates". Rafa (ADR 0068, accepted 2026-10-31) and Pedro (ADR 0072, accepted
  2026-11-01) are modelled characters. The README was corrected on 2026-11-05 (commit `c3270c63`) from "The library
  draws in 2D" to hybrid production with clay characters, after the 2D wording was read as a limit on the whole
  production. This record corrects the same kind of misreading.

### Where the location condition came from

- arc4d3 is the publishing side's bot in the shared Slack channel ([the Slack channel](../slack-channel.md)). Its posts
  count as requests, and the operator delegated approvals to it on 2026-10-31 (`srstudio.parts`, ADR 0060).
- ADR 0179 was written on 2026-11-02 (commit `dc579820`) for scripts that were about to stand srstudio's figures in
  locations rebuilt in 3D from reference photographs. As first written those were an airliner economy row, then a
  car's front seats (Slack 1793611091.520519). Half an hour later (commit `f84e85b0`) they became a starship bridge
  for Saga and a TV news studio study, with a supermarket to follow (Slack 1793611720.082919 and 1793612340.312069).
  The pin then moved to srlocations `be0aabc`, which holds those two locations "reworked to arc4d3's rulings and the
  News palette" (`tests/test_location_bridge.py`).
- The conditions answered those orders. The first one names the looks the library drew in that day: cel and ink for
  its drawn styles, clay for what `srstudio.clay` models. The record then wrote all three as binding every reel that
  uses the bridge. The Slack messages are not in this repository, so this record cannot say whether that reach was in
  arc4d3's words or was added when the record was written.
- Nothing enforces the first condition. The bridge carries cameras, marks and blocking, no picture, and
  `srstudio.location_bridge` reads no look. ADR 0179 is still `proposed`.

## Decision

**Characters.** There is no general rule. "Characters stay on their style's rig" leaves DRAWING.md, and "people stay
on their rigs" in ADR 0091 is read as what it described: the drawn styles taking the rigid-object layer. It does not
bind other work. How a character is made is chosen per episode or style:

- a drawn rig of that style, as the drawn styles do today; or
- a 3D model. It is modelled in the library, as Rafa and Pedro are, or it is a figure built outside the library on
  srlocations' mannequin skeleton, such as the plush, vinyl and low-poly families of the sibling library. A figure
  built outside reaches an episode as rendered material through a bridge. No such bridge is in this repository yet;
  ADR 0179 and ADR 0187 show the pattern: srstudio never imports the other library and reads a pinned, checked
  record.

What DRAWING.md says about rigs as fact stays, because it still describes rigs: a rig declares the views and poses it
supports, and reusing its parts does not synthesize an unseen back or profile.

**Locations.** The first condition of ADR 0179 belongs to the locations ordered on 2026-11-02 and the figures that
were to stand in them. It is not a rule for every reel that uses the bridge. The look of what renders beside the
figures is chosen per episode.

The ruling is about that condition only. The other two stay in force as ADR 0179 states them: no brands, badges,
liveries or trade dress, and photographs are Pedro's only and never committed to this repository.

## What does not change

- Published reels stay frozen (ADR 0040).
- An approved drawing stays pinned, and a changed drawing is a new part version (ADR 0047). No style is moved off the
  characters it has: Toon, Collage, Stick and the others keep their rigs and figures until an episode or style chooses
  otherwise.
- A new look is still approved from a rendered, animated clip before a reel uses it (DRAWING.md, *Rules*; ADR 0091).
  That holds for a character made as a 3D model as for a drawn one. Who approves does not change either: DRAWING.md
  names the operator for a type's first use of a layer, and the [parts guide](../authoring-parts.md) names arc4d3 for a
  character version.
- A recurring figure of the cast bible keeps its base rig as published (`srstudio.bible_rig`, ADR 0069). That rule is
  about a figure that already exists, not about how a new one is made.
- The second and third conditions of ADR 0179, as above.
- No code, schema or test changes with this record. It changes DRAWING.md and the README's sentence on locations,
  and adds a pointer to ADR 0091 and to ADR 0179, whose text stays as written.

## Follow-ups

These places still state the old sentences, or assume that a character is a part of srstudio's registry. This record
changes none of them.

It still states the location condition as a present rule:

- The funny-reels skill carried the same condition when ADR 0220 moved it to srstudio-episodes: line 334 of
  `.claude/skills/funny-reels/SKILL.md` at the parent of commit `67bf9a38`. It is to be checked there.

They assume a character is a registered drawing:

- `src/srstudio/bible.py` lines 540-541: the loader refuses a canon character whose `look.drawing` is empty ("a canon
  character has no approved drawing"), and a `Drawing` (lines 163-173) is a part and version of srstudio's registry.
  Rafa can pass, being a registered part; a character built outside the library has none. `tests/test_bible.py` line 87
  holds the refusal, and [ADR 0069](0069-cast-bible.md) line 62 records it.
- `src/srstudio/export_toon.py` lines 133-148 (`cast_of`) and
  [ADR 0255](0255-build-export-draws-a-toon-export.md) lines 35-37: an export's speaker is drawn only when its first
  drawing is a `toon-` part of the Toon cast. Any other is heard and not drawn, and a pose that names it is refused
  (line 428). An export has no way yet to name a 3D model.
- [ADR 0184](0184-srlocations-mannequin-blocking.md) lines 94-95: "srlocations' mannequin is the fit test, not the
  character", written for a drawn figure of another size or shape. A figure built on that skeleton is a case it does
  not cover.

It stays as written, as each type's own choice:

- `DRAWING.md`, the *Video types* table (lines 164-176): what each type keeps is that type's default today. The line
  above the table now says so.

Not built or decided:

- The bridge that brings a 3D figure's rendered material into an episode, and how such a character is recorded,
  versioned and approved. Each needs its own record.
