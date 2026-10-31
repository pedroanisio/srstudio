---
generated-by: Claude Sonnet 5.5 (claude-sonnet-5-5) in Claude Code
---

# ADR 0067: The catalog shows the pilots, plays the packages' renders, and lists only videos

- Status: proposed; implemented 2026-10-31 on `feat/catalog-pilots` (`srstudio.usage`, `srstudio.catalog_page`,
  `srstudio.catalog_data` schema 1.4.0, `assets/catalog/app.js`, `tools/systemd/srstudio-*.path`; tests in
  `tests/test_usage.py`, `test_catalog_page.py`, `test_catalog_data.py`, `test_catalog_app.py`, `test_systemd_units.py`).
  It builds on [ADR 0046](0046-catalog-web-app.md) and [ADR 0054](0054-pilots-have-their-own-road-to-drive.md).
- Deciders: worskpace-e5 (orchestrator), pending the operator's review; implementation drafted by Claude Sonnet 5.5
  in Claude Code
- Back to the [library README](../../README.md)

## Context

An inspection of the live catalog against what was produced (2026-10-31) found three gaps: the 11 pilots, rendered in
`generated/renders/pilots` from projects in `generated/episodes/pilots/<series>/<slug>`, were not in the catalog,
because the page builder scanned only the direct children of `generated/episodes` and read `pilots` as one project with
no scene; six original packages had a poster and no playable file, though their renders were in `generated/renders`;
and `the-code`, a folder with no scene and no render, showed as a "no render" card.

## Decision

1. **A pilot is an ordinary video with a series.** `usage.pilot_projects` reads `episodes/pilots/<series>/<slug>`, and
   `srstudio usage` measures each one with its script in `<scripts>/pilots/`, so its parts, its style and the gallery
   coverage check treat it like any episode. The catalog builds its card from the render in `renders/pilots`. The
   document gives the video `series` (the folder name), and the page tags it *piloto*. A pilot may not take a library
   slug. `pilots` itself is no longer a project, so it is no longer reported as unmeasured.
2. **A package plays its render.** `PACKAGE_RENDERS` names the file each original package was rendered as, because two
   carry the name of their recreation. A package with such a file on the machine gets a web encode as `src`, keeps the
   poster drawn from its spec and links to its SVG player; one without stays facts and a poster. The page does not
   guess a name from the slug.
3. **The catalog lists videos.** A project that was not measured and has no scene and render, and is no package, is a
   folder and not a video, so it has no card and is not in `unmeasured` (that list holds the videos whose parts were
   not measured). A measured project without a render keeps its "no render" card.
4. **Schema 1.4.0.** `series` is an optional field of a video; a package may carry `src`.
5. **The units watch the pilots' folders.** `srstudio-catalog.path` also watches `renders/pilots`, and
   `srstudio-usage.path` watches `episodes/pilots` and its series folders `mind`, `maps`, `news` and `host`. A new
   series needs its folder added there.

## Rejected alternatives

- **A separate pilots section.** The pilots are videos with parts, notes and a gallery; a section would copy each of
  those. A tag and a filter on the series keep one list.
- **Guess a package's render from its slug.** `printer-recreation` and `honesty-interview` do not match their files; a
  wrong guess would play the wrong video.
- **Keep a card for every folder.** A card for a folder that holds no video promises a video nobody can play.
