---
generated-by: Claude Sonnet 5.5 (claude-sonnet-5-5) in Claude Code
---

# Changelog

`cast.json` and `relationships.json` share one semantic version. A new fact, character or pair is a minor version;
a fact corrected after a published reel disproved it, or a clash resolved by the operator, is a patch; a change to
the files' schema is a major version.

## 1.2.0

- Pair `milo` and `rosa` gains its family role: Cutout Rosa is Milo's mother. Published in `only-your-aunt` (#193), where he
  calls her Mom on the phone; the pair moves from `proposal` to `canon` and both characters list the reel. Collage Rosa
  remains Gary's mother; the two drawings stay the clash `rosa-two-drawings`.

## 1.1.1

- Roles `husband`, `wife`, `goat`, `fox` and `friend-fast` are added, and `neighbour` is treated as the role `neighbor`
  (`bible.ROLE_SPELLINGS`), not listed as a second one: published reels (`the-chirp`, `the-noise`, `voice-note`,
  `text-me`) key their speakers by them, and a role noun is not a missing character.
- The two rules from arc4d3's standing instructions are marked as decisions with the Slack messages that gave them
  (1793513568.110249 and 1793512208.441779). The schema has no status for a decision, so they stay `proposal`: no
  published reel establishes either. The rule about the base rig now says which Stick fields count as base rig.
- `srstudio bible rig` and the delivery gate hold a Stick reel's drawn looks to that rule (`srstudio.bible_rig`); the
  records are unchanged.

## 1.1.0

Written from the published record after batch C (163 published reels). Every new record rests on a delivered reel.

- Lewis (`lewis`): the Toon raccoon of `loaded-right`, voiced by Will. His name is credited ("Will (Lewis)") and the
  speaker key of the project data, and no line says it aloud. Pair `fern` and `lewis` is a proposal: the reel's post
  says Dad has a file on every boyfriend, and no line says in so many words that Lewis is Fern's.
- Gary of the Stick reels (`stick-gary`): Callum's voice in `the-viewing` and `third-snore`, the extra occupant who
  comes with the flat. He is a separate record from the Collage Gary (`gary`, Chris), as the Saga Gary is; the
  bible's check tells the two apart by voice and drawing. The clashes about the name stay recorded and unresolved.
- Keith (`keith`): the horse of `sorry-what`, named in a line and never heard. Drawn by `toon-horse`, which the
  registry lists as a prop.
- Across the road (`across`): the hedgehog of `sorry-what`, voiced by Jessica; the credit label and the speaker key
  are the only name.
- Feld (`feld`): Alice's voice on `nail-hole`, `therapy-session` and `book-a-table`; the Collage therapist
  (`collage-feld`) in the first two, a restaurant on the phone in the third.
- The role `mother` (Laura, `baby-monitor`).
- Two proposed rules from arc4d3's standing instructions: a recurring figure's base rig stays as published and only
  clothes and props change per reel (`base-rig-stays`); an unnamed figure with no line, recombined from existing
  options of an approved style, is background (`unnamed-figure-is-background`). Neither is enforced by code yet.
- `srstudio bible check` picks, among characters of one world that share a name, the one whose voice or drawing the
  reel has, so two Garys in one world do not flag each other's reels.

## 1.0.1

- The unnamed role is spelled `neighbor`, as the reels and the repository's EN-US default spell it, so a speaker keyed
  `neighbor` is a role and not an unknown name. No character, pair or fact changed.

## 1.0.0

The first cast bible, written from the 131 published reels.

- 43 characters with a sheet, 3 placeholders (Vera and Gus of the News Compiler, Rafa the host), 73 pairs, 27 places
  and 38 world rules (the rules marked proposal wait for the operator).
- Every character is a name on 2 or more published reels. All 14 cast cards are in; none is dropped. 27 more
  characters recur without a card (Okayville 17, Saga 6, Gloss 4), and Saga has the namesakes of two cards.
- 51 clashes are recorded and none is resolved: 12 of name, 16 of drawing, 23 of voice. Each has a proposed
  resolution in `open-decisions.md`.
- Saga and Gloss are sealed: each has its own characters and shares no canon with another world.
- Lint was never published and Rafa replaces him as the talking-head host; Lint is not canon.
- The Okayville account is `@okayville.tv`.
