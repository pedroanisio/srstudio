---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0051: A catalog card shows the part itself, rendered from its definition

- Status: proposed; implemented 2026-10-30 on `feat/catalog-specimens` (`srstudio.catalog_specimens`,
  `srstudio.catalog_page`, `srstudio.catalog_data` schema 1.1.0, `assets/catalog/app.js`;
  `tests/test_catalog_specimens.py`). It amends decision 9 of ADR 0046.
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Back to the [library README](../../README.md)

## Context

A card's picture was a still that `notes.json` cut from a reel. So five objects of one café all showed that café, and
a part in no curated item showed "sem imagem": seven Toon characters did, with nothing wrong with them except that nobody
had written a note. The six package films showed a blank card although their scene specs are on disk.

The definition of a part is its registered builder, and the engine can draw it. A picture that depends on a reel and
a note can only lag behind the registry.

## Decision

1. **Every registered part is drawn alone by the real builder through the real engine**, on a neutral ground, and the
   catalog's cards, list rows and part pages open with that specimen. Reel stills stay on the part page under *Visto
   em*.
2. **Characters have one recipe, `srstudio.specimens.SPECIMENS`.** It is ADR 0047's digest drawing, so a character
   looks the same here as in its version record; this module adds only the framing. A second recipe would drift.
3. **A new part needs no entry.** A builder that needs only a place and a clock is drawn from its signature
   (`catalog_specimens.auto`). One that needs data of its own has a recipe in `RECIPES`, whose sample text is the
   only invented content, and it never reaches a reel. A registered part with neither stops `srstudio page` by name.
4. **A part that cannot stand alone says why.** `REFUSED` holds a typed `Reason`: a layer over a shot, a motion, a
   thing worn by a character, a shot whose builder draws a character, or a player of project data the shared recipe
   only has placeholders for. The card shows the reason in the catalog's language. A refusal is not a fallback, and
   the document has no third state: a part with neither a specimen nor a reason, or both, is refused by the schema.
5. **A set shows nobody.** The tests trace which registered parts a set's build calls, so a character cannot be
   hidden in one. `office-wide` is refused because its builder draws the candidate's back.
6. **Framing is measured.** A first render at half scale, with room around the frame, finds what the part covers; the
   second scales the composition to fill a square. The project stays at its own size, as symbols render offscreen at
   document size. Sets are not trimmed, since their edges belong to them, and they keep their style's stage colour.
7. **A rebuild renders only what changed.** A file is named by the digest of the drawing: `specimens.fingerprint` for a
   character, so engine noise such as ids does not count; the document's bytes for everything else, whose ids come from
   a fresh counter per part. `FRAMING` is in the key, to raise when the framing itself changes.
8. **A package's poster is a frame of its own spec**, at 35% of its length, keyed by spec, moment and package version.
   Packages are only read. `srstudio page` gains `--packages`; a package with no poster stops the build by name.
9. **A part with no curated title takes the first clause of its registered summary** (`catalog_page.title_of`), the
   only display text a registry entry offers, with code references removed. Curated titles still win, and no name is
   invented. Such a title is in English and reads as a description until the notes name the part.

## Rejected alternatives

- **Keep reel stills and add a specimen only where none exists.** A card would mean two different things, and a
  picture of a whole scene would still stand for a salt shaker. It also keeps "sem imagem" as a reachable state.
- **Fall back to a reel frame for a refused part.** It hides the one fact the mark exists to state, that the part has
  no drawing of its own.
- **Draw refused shots with their character removed.** The builders have no empty variant, and masking the character
  out would be a picture the library cannot produce.
- **Crop in `ffmpeg` only, without scaling the composition.** A small prop would be a few upscaled pixels, and blurred
  symbols would stay blurred. Scaling the document draws the part at the size shown.
- **A project sized to the output.** Symbols render offscreen at document size, so a 480 px project clips them.
- **One digest for every part.** `specimens.fingerprint` classifies what a character draws, and raises on elements
  only other parts use. Widening it would change a character's digest contract for a cache key that the document's
  bytes already give.
- **Render posters at a time curated per film.** That is a note to maintain per package. One fixed fraction lands
  inside the sketch on all six.
