---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0053: The catalog shows a part's version history, and one card per part

- Status: proposed; implemented 2026-10-30 on `feat/catalog-versions` (`srstudio.catalog_versions`,
  `srstudio.catalog_page`, `srstudio.catalog_data` schema 1.2.0, `assets/catalog/app.js`;
  `tests/test_catalog_versions.py`, `tests/test_catalog_app.py`). It builds on
  [ADR 0047](0047-character-versions.md) and [ADR 0051](0051-catalog-pictures-come-from-the-spec.md).
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Back to the [library README](../../README.md)

## Context

The operator asked: "the catalog will hold the versions of the elements?". Version N of a character is registered as
`name@N`, so the catalog listed `toon-fox` and `toon-fox@2` as two unrelated characters and said nothing of what ADR
0047 records: the date, the note, the status, the approval, the proof, and which reels pin what. Versions are also
being extended to locations, props and graphics, with a richer record.

## Decision

1. **The document's history is per part, with no notion of kind.** `Part.versions` holds a `PartVersion` per version,
   oldest first, and a later version's own entry says `version_of`. Nothing in the document or the app asks whether a
   part is a character, so a location with a history adds data, not a redesign. `catalog.json` goes to schema 1.2.0;
   the fields are optional, so the change is a minor one.
2. **The record is read through the `characters` API.** `catalog_versions.history` uses `Version`, `Character.latest`
   and `characters.part_name`, never the JSON, so a richer record does not move this reader.
3. **One card per part, with every registered drawing kept.** An index, its counts and the search list a part once and
   answer for all its versions: the card shows the default's drawing, the version count and how many are proposed, and
   the videos are those of every version. The registry table and the 246 entries of the document stay complete, so
   `srstudio catalog` and the catalog still agree. A version's own route opens the part's page at that version.
4. **The default is computed once and checked again.** It comes from `Character.latest`, the highest approved version.
   `catalog_data` refuses a proposed version that is a default, or that carries an approval or a pin. A proposed
   version is marked *Proposta* on its page and counted on its card, and its picture never stands for the part.
5. **Pins come from the release files.** `srstudio page --releases` reads `Release.characters`. A pin to a version the
   record does not hold stops the build, by release. Without the option `Catalog.pinned` is false and the page says the
   pins were not read, since "no reel pins this" would be a claim nobody measured. A release with no video yet is
   named, with nothing to link to.
6. **A proof is placed in the site.** A proof is a local path outside the site, and a browser will not follow a
   `file:` link from a served page. A single file is a media file. A proof page goes in
   `proofs/<hash of its folder>/` with the files beside it, because some pages name their clips only in a script.
   Only files the server can type are placed, and they are hard-linked where possible. A proof that is not on the
   machine keeps its path on the page, with no link, and `--proof-root` (the working directory by default) is where
   the record's paths start from. Proof folders nothing links are removed after the index is replaced.
7. **The record's text is shown as written.** A note is the record's, and an approval is the operator's own words, so
   neither is translated in the page.

## Rejected alternatives

- **Drop `name@N` from the document and nest its data in the history.** The registry table would no longer be
  complete, and a video's measured parts would point at names the document lacks.
- **One card per version, labelled.** That is the problem the operator named: the fox would still read as two
  characters, and a proposed version would sit in the index beside the default.
- **Show the part's version 1 on its card.** The card would show a drawing no new reel gets.
- **Read `characters.json` in the catalog.** It would break on the record's next change.
- **Rewrite a proof page's links onto media files.** The critters and older-cast pages build their URLs in a script, so
  a rewrite cannot see them.
- **Serve a second root from `srstudio serve`.** The site would stop being one folder, and the server's one containment
  check would become two.
- **Copy the whole proof folder.** The folders hold scene documents and manifests the page does not need.
- **Fail the build on a missing proof.** ADR 0047 says the file may be absent on another checkout.
