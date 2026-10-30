---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0047: Every part has numbered versions, and a reel pins the ones it draws

- Status: accepted (2026-10-30), amended the same day to cover every kind of part (see the amendment below; the
  decisions keep the names they had when written). Implemented: `srstudio.parts`, `srstudio.specimens`,
  `srstudio.catalog_specimens`, `assets/parts.json`, `Release.parts`, `releases.unpinned`,
  `usage.Report.pin_drift`, `sketch.drawer`, `toon_sketch.Staging.versions`, `srstudio parts`; `tests/test_parts.py`,
  `tests/test_specimens.py`, `tests/test_catalog_specimens.py`, `tests/test_releases.py`, `tests/test_social.py`,
  `tests/test_usage.py`, `tests/test_cli.py`.
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Extends [ADR 0044](0044-inked-toon-characters.md), and takes its digest from
  [ADR 0037](0037-the-cover-fingerprint-is-the-drawing.md)
- Back to the [library README](../../README.md)

## Context

The operator approved the inked fox and asked for versions: "approved, lets add version to the characters as we will
improve then frequently". Published reels are frozen, so a better drawing can only reach new reels. Until now the
only way to improve a character without touching a published reel was a second name beside it (`fox-inked`), and
nothing stopped an edit to a drawing a reel depends on, other than the rebuild proof someone had to remember to run.

## Decision

1. **Versions are plain integers per character.** Fox 1 is the brush fox and fox 2 the inked one. A drawing has no
   compatibility contract, so semver would claim something it cannot hold. Any visible change is a new version.
2. **The table is shared and typed.** `src/srstudio/assets/characters.json` holds every registered character of every
   style, and `characters.read` parses it into typed records that refuse unknown fields. Each version has a number,
   a date, a one-line note, a proof, a status, an approval and the digest of its drawing. Version 1 is the plain
   registered name, and version N is registered as `name@N`, so every version stays a drawing in the registry.
3. **`proof` is a local path.** It points under `generated/`, which git does not hold. It is a pointer for the
   operator and the catalog, not a file this repository ships, and it may be absent on another checkout.
4. **A reel gets the latest approved version by default and can ask for an older one.** A proposed version can be
   drawn for its proof by asking `characters.part` for it, but it is never the default and it cannot be pinned.
5. **Approval records whose it was.** An approved version above 1 must carry `proof` and `approval`, which holds the
   date and the operator's words or a reference to them. **An agent never writes `approval`, or sets a version to
   `approved`, without the operator's decision.** Version 1 needs neither, because it is the drawing the operator
   already published. Fox 2's approval quotes the words above.
6. **An approved look cannot be revised in place.** A test redraws every approved version and compares its digest.
   The failure says to restore the drawing and add a version. Changing a look always means adding a version.
7. **The digest is the drawing, as ADR 0037 says of a cover.** It must not teach anyone to ignore it, so a change
   that draws nothing different must not move it. `specimens.fingerprint` hashes only `<composition>`, with each
   effect or gradient it uses inlined where it is used. Ids are dropped, attributes are sorted, numbers are compared
   by value, and a group that draws and moves nothing dissolves. Order is kept, because what is drawn over what is
   the drawing. An element or attribute nobody classified raises, so a new one is decided once, not guessed at.
8. **Specimens are bounded.** There is one specimen per family, thirteen in all, and each shows every expression once.
   The vocabulary a specimen shows is fixed in `specimens.py`, not read from the style, so a new kind for new
   characters moves nobody's digest. Characters drawn since the vocabulary grew, and fox version 2, show the newer
   kinds too, in a family of their own.
9. **A release pins what it draws.** `Release.characters` maps a registered name to a version and is checked when
   the release loads: an unknown character, an unknown version or an unapproved one is refused by name. Every release
   carries its pins. The back catalogue's were generated from `srstudio usage`, measured on the commit before this
   change.
10. **Pins are mandatory at delivery.** "No pin means latest approved" suits a reel being written. After release it
    would mean a reel changes silently when a new version is approved. So `instagram_posts.py deliver` refuses and
    `check` reports any release with no `characters`, and any whose build drew something it does not pin at that
    version. `{}` declares a reel that draws no character. The gate reads files only, so `check` still runs no engine.
11. **Only Toon reads a pin.** `toon_sketch.Staging.versions` is required and `sketch.drawer` resolves every character
    through it, and each Toon build leaves `characters.json` in its project as the record the gate reads. Other
    styles have only version 1, so they have nothing to route, and `Character` refuses a second version on a style not
    in `characters.ROUTED` rather than let it draw for every reel. `srstudio characters --usage` compares measured
    parts with pins for every style.
12. **`fox-inked` is fox version 2.** It is registered as `toon-fox@2`. No alias is kept, because no episode, release
    or script names it. Saga's cast stays as drawn, at version 1.

## Alternatives rejected

- **SHA-256 of the whole specimen document.** It is simple, but it moves when sr-core's scene output or
  `version="auto"` changes, and then a test says "add a version" when no drawing changed.
- **A hash of the drawing's source.** Source can move without the drawing changing, and a shared helper can change
  the drawing without its source changing. ADR 0037 rejected the same thing for covers.
- **Routing pins through every style.** It would touch every builder to pin characters that have one version. The
  cost is that a second version of another style's character needs its style routed first, and the table refuses
  until then.
- **Semver.** See decision 1.
- **Pins written once, with no gate.** That covers the back catalogue and leaves every later reel exposed.
- **Every expression × every character in the specimens.** It adds nothing a specimen per family does not catch, at
  the cost of thousands of tests.
- **Keeping `fox-inked` as an alias.** Nothing needs it, and two names for one drawing is what this replaces.

## Consequences

- A new version adds a record, a registered `name@N`, a specimen entry and its digest from
  `srstudio characters --digest name@N`. Until the operator approves it, it stays `proposed`.
- A shared code change that moves an approved drawing fails the digest test on purpose. The fix is to keep the old
  drawing reachable for version N and add a version, not to refresh the digest.
- A kind added to the vocabulary for new characters is not shown by older specimens, so the digest does not protect
  an older version's drawing of that kind.
- A Toon script must pass `versions`, so it cannot forget its pins. A script that calls `toon_cast` directly instead
  of `toon_sketch.build` draws version 1 by code and leaves no record, so only its pins and the digest cover it.
- A project built before records has no `characters.json`. The gate then has only its pins to read, and the rebuild
  proof covers it.

## Amendment (2026-10-30): every kind of part

The operator asked "the catalog will hold the versions of the elements ?" and the answer was yes, for every kind of
part, not only characters.

1. **One record per registered part.** `assets/parts.json` (schema 2.0.0) replaces `assets/characters.json` and holds
   245 parts: 100 props, 61 locations, 50 characters and 34 graphics, each with the fields and rules above plus its
   `kind`. `srstudio.characters` became `srstudio.parts`, `Character` became `Part`, `Release.characters` became
   `Release.parts`, and `srstudio characters` became `srstudio parts`. No alias is kept: a table named for characters
   that holds locations would mislead, and no built project held a record to migrate.
2. **A release pins every part it draws.** All 109 releases were migrated in one commit, 1,160 pins in all, from
   `srstudio usage` measured on the commit before this change. Every character pin they held survived unchanged.
3. **A digest comes from the catalog's recipes.** `catalog_specimens.digest` draws a location, a prop or a graphic
   through the recipe its catalog picture uses, so each part has one drawing and no second recipe. The fingerprint
   classifies what those parts draw: masks, blends, expressions and text animators. An expression's body and a text
   asset's letters count, and a font asset does not. Parts lettered from a project's font or traced data need that
   project, so their redraw test runs where `SRSTUDIO_EPISODES` is set, as the catalog's own tests do.
4. **A part with no drawing of its own records why.** `Part.refused` holds a typed `Reason` and one line, and such a
   part has no digest: 21 parts (10 locations, 5 graphics, 4 props, 2 characters), the same 21 the catalog refuses.
   Their reasons are 10 `character-shot`, 7 `overlay`, 2 `placeholder`, 1 `worn` and 1 `motion`. `stick-figure` and
   `cel-traced` had digests of placeholder data, which said nothing about their characters, so those were dropped. A
   refused part is still pinned, and `srstudio parts --refused` lists them.
5. **A second version is refused by name until it is routed.** `parts.ROUTED` holds `(kind, style)` pairs and starts
   with Toon's characters. No build reads a pin for a prop or a location yet, so a second version of one would draw
   for every reel.
6. **Version 1 of a part no reel has drawn says so.** Seven parts were in the library when versions began and no reel
   had drawn them: `toon-clipboard`, `toon-counter`, `toon-lounge`, `toon-phone`, `toon-receipt`, `toon-speaker` and
   `toon-take-a-number`. Their notes say that, and they are `approved` like every other version 1, so a new reel may
   use them. `approved` on a version 1 means the baseline a reel may pin, not a look the operator judged.

