---
generated-by: Claude Sonnet 5.5 (claude-sonnet-5-5) in Claude Code
---

# ADR 0069: The cast bible

- Status: proposed
- Deciders: the operator (pedroanisio); the library is drafted by Claude Sonnet 5.5 in Claude Code and waits for the
  operator's reading
- Builds on [ADR 0065](0065-okayville-and-five-hashtags.md) (the Okayville account, and a gate that stops a first
  delivery) and [ADR 0032](0032-releases.md) (one release file per reel)
- Back to the [library README](../../README.md)

```
ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.
```

## Context

The channel has 131 published reels across Okayville, Saga and Gloss, made by many sessions at different times, and
nothing says who a character is. The cast cards name 14 characters, but the reels hold 47 names that come back, and the
same name is drawn, voiced or described differently from one reel to the next: the Toon rabbit and the Soft blob are
both Pip, one is a woman voiced by Alice and the other a man voiced by Will; Gary is a Collage dad, a Saga clerk and a
stick figure; Juno and Gus exist in two worlds. A new script written without the record repeats the clash.

## Decision

**A library, `bible/`.** Two data files share one semantic version: `cast.json` (characters, unnamed roles, places,
world rules, clashes) and `relationships.json` (one record per pair). `CHANGELOG.md` says what each version changed.
The first version, 1.0.0, has 43 characters with a sheet and 3 placeholders, 73 pairs, 27 places, 38 rules (14 are
proposals) and 51 clashes. Each file names the model and the tool that wrote it in `generated_by`.

**Source of truth: the published record only.** A reel is published when it is in the delivery manifest and has a
release. Every canon fact carries the slug of the reel that establishes it and a quotation, and it is one of four
kinds: `line` (a line, caption or post text of the reel), `voice` (the voice its project records), `drawn` (a registered
character its release pins) or `seen` (a frame a person looked at). Of the 2041 facts in 1.0.0, 1479 are lines, 287
voices and 190 drawings, and 85 are `seen`. A persona field with no fact behind it begins `open:` (not known) or
`proposal:` (a suggestion for a world rule or a never-list), and the loader refuses a field that is stated with no
fact, or marked and also backed.

**Recurring means 2 or more published reels**, counted by code (`srstudio bible inventory`) from four sources: the
release's recurring tags, the speakers of the project data, a name written with a capital in the post, and the
characters the release pins. All 14 cards stay; 27 characters with no card are added (Okayville 17, Saga 6, Gloss 4), as are
the Saga namesakes of two cards (`saga-gary`, `saga-juno`), and no card is dropped.

**Sealed worlds.** Saga and Gloss each have their own characters and share no canon with Okayville or with each other.
A character is keyed by the world of its reel, so the same name in two worlds is two characters (`juno` and
`saga-juno`), and the diagram draws one panel per world with no line between worlds.

**Clashes are recorded, not resolved.** Each of the 51 clashes (12 of name, 16 of drawing, 23 of voice; 37 inside one
world and 14 across worlds) has a proposed resolution in `open-decisions.md`. Published reels are frozen, so no
resolution renames or redraws one. Resolving a clash is the operator's decision.

**Placeholders.** Vera and Gus of the News Compiler show are placeholders until the polished look arrives with the
first of the six new news episodes. The host is a placeholder named Rafa until the operator approves his look. Lint,
whom Rafa replaces, was never published and is not canon. The delivery manifest this version reads holds no Mind or Maps reel and one News reel (`breaking-news`, a Collage
reel), so those shows have no character that recurs on a published reel and the bible holds none for them.

**The loader and the check are code.** `srstudio.bible` parses both files into frozen types and refuses unknown fields,
a canon character with no fact or no approved drawing, a pair that is not alphabetical or not unique, a relationship to
a character the bible lacks, and files that disagree on their version. `bible.verify` looks up every cited line, voice
and drawing in the published project (a `seen` fact is listed, never accepted by code). `srstudio bible check` is
deterministic and calls no model: it flags a release that names a character the bible lacks, or gives a known one
another drawing or voice, and a brief with no `Cast: slug, slug` line or with a slug the bible lacks.
`episodes/instagram_posts.write_all` runs it on a first delivery, after the hashtag cap, and a video already in the
manifest is never refused. A bible that cannot be read refuses the delivery.

**What code cannot do.** The check reads names, drawings, voices and the cast line. It cannot tell that a paragraph
makes Rex a cat, or that a joke contradicts a canon fact in other words. That is for a reader, and the brief's cast
line exists so that a reader has the sheets in front of them.

**The readable folder.** `srstudio bible render` writes `generated/bible/`: `README.md`, `cast.json`,
`characters/<slug>.md` with the approved drawing beside each sheet, `relationships.json`, `relationships.png`,
`world.md`, `canon.md`, `open-decisions.md` and `CHANGELOG.md`, with directory mode 700 and file mode 600. The pages
are written from the data and never hold a fact it does not. The diagram is drawn through the engine in Fredoka and DM
Sans, with a layout found by code that keeps every name apart, splits each world into its connected groups and
prefers fewer lines through names and fewer crossings.

## Verification of what the models drafted

Models drafted the persona sheets from the published reels. They are untrusted, and the five controls hold:

1. A typed parse (`bible.load`) refuses unknown fields and every shape the schema forbids.
2. Semantic validation: backed-or-marked fields, the approved drawing, alphabetical unique pairs, places and pairs that
   name real characters.
3. A defined failure path: `BibleError`, `InventoryError`, `BibleBuildError` and `BibleCheckError`, each typed, and a
   delivery refused with a `DeliveryError`.
4. Tests that feed malformed and adversarial files to each (`tests/test_bible.py`, `test_bible_inventory.py`,
   `test_bible_check.py`, `test_bible_render.py`, `test_bible_diagram.py`, `test_bible_cli.py`, and the gate tests in
   `tests/test_social.py`).
5. Deterministic bounds: the layout tries a fixed number of seeds and the separation pass a fixed number of rounds.

Each model's fragment was verified by `bible_inventory.cite` before it was merged, and `bible.verify` ran over the
merged bible: 2041 facts, no failure. The 85 `seen` facts rest on a frame a person has to look at; code lists them and
does not confirm them.

## Rejected alternatives

- **One prose document.** A document has no gate: a new reel cannot be refused by it, and it drifts from the reels.
  Typed data with a loader can be.
- **A single canon for all worlds.** It would say Saga's Gloom and Okayville's manager are one person, or force a
  clash that is only a coincidence of names. Sealed worlds keep each canon small enough to check.
- **Resolving the clashes in this change.** Choosing which Pip is Pip is a creative decision, and every reel already
  published stays as it went out. The clashes are listed for the operator.
- **A model that judges a brief against the canon.** A reading of prose by a model is output nobody has verified, and a
  gate that depends on it cannot fail for the right reason. The gate stays on what code can prove.
- **An `aliases` field for the speaker keys of a project** (`customer` for Milo, `barista` for Ava). It would let the
  check follow a reel's own names, but each alias is one more fact to keep true. The bible lists the unnamed roles
  (`narrator`, `barista`, `pigeon` and others) instead, and a name with no sheet is flagged.

## Consequences

- Checked against the 131 published reels as a calibration (they are never refused), the check flags 13: six
  reels of the Toon Pip, who is drawn and voiced as another character than the Soft Pip, `market-rate` (the part the
  bible gives the manager is the candidate there), the Stick Gary of `the-viewing`, the Gloss Gus in
  `representative`, and one-off names (`brooke`, `theo`, `sam`, `remy`, `feld`) that
  have no sheet. Each is a clash or a name the bible does not yet hold, so a new reel that does the same is stopped.
- A one-reel name is not a character of the bible. A new reel that reuses it is refused until it gets a sheet; that is
  the intended pressure to decide who they are.
- Each new recurring character, pair or fact is a minor version of both files, with a line in `CHANGELOG.md`.
- The bible says nothing about reels not yet published. A reel becomes canon when it is published.
