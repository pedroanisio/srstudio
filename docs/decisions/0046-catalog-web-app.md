---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0046: The catalog is a small web app, not one file

- Status: proposed; implemented 2026-10-30 on `feat/catalog-site` (`srstudio.catalog_page`, `srstudio.catalog_server`,
  `srstudio page --site`, `srstudio serve`; `tests/test_catalog_page.py`, `tests/test_catalog_server.py`)
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Back to the [library README](../../README.md)

## Context

The catalog was one self-contained HTML file with every video and image embedded as a data URI, so that it opened
offline. It reached 125.5 MB: 105.6 MB of base64 video, 15.7 MB of JPEG, 1.5 MB of MP3, 1.0 MB of fonts and 0.5 MB of
PNG across 461 data URIs. The operator's browser no longer renders it. Everything else in the page is small, so the
root cause is the embedding and no amount of compression removes it: each new episode adds to a file the browser
must parse whole before it shows anything.

## Decision

1. **`srstudio page --site DIR` writes a folder**, `index.html` plus `media/<content-hash>.<ext>`, with relative
   URLs. `--site` replaces `--out`: the single-file mode is removed, because a mode that writes a page browsers cannot
   open is not an option worth keeping.
2. **No data URI remains**, including the 8 inside the frozen base page (2 fonts, 6 sounds), which become media
   files. A URL in CSS or in a script's string resolves against the document, so the text around them does not
   change. The build refuses a page that still holds one, in any encoding, and a page past `INDEX_LIMIT`.
3. **Names follow content.** A rebuild writes only what changed. Files are hard-linked from the cache, so the site
   costs no second copy of the videos; they are copied across devices, and when a link would have to change the
   mode of the cached file.
4. **A failed build leaves the previous site working.** Media are placed first, each through a temporary name;
   `index.html` is replaced last, atomically; files nothing references are removed only after that.
5. **`srstudio serve SITE`** is `ThreadingHTTPServer` with a handler of our own. It is read-only (GET and HEAD), serves
   only inside the folder, lists nothing, and answers ranges with 206 and `Content-Range`, or 416. Media are cached
   as immutable; everything else is revalidated. The default bind is loopback because there is no authentication.

## Rejected alternatives

- **Keeping one file, with lighter encodes.** Base64 adds a third to every byte, and the browser has to decode all of
  it before the first paint. Halving the video bitrate buys a few dozen more episodes and hurts the part of the page
  that matters. The catalog grows by a batch at a time, so the limit would come back.
- **Python's `http.server` (`SimpleHTTPRequestHandler`).** It has no Range support, and Chrome will not seek in a video
  without it, so clicking a line would fail. It also lists folders, follows symlinks out of the root and caches
  nothing usefully. Fixing those is most of the handler we wrote.
- **A web framework (Flask, FastAPI, Starlette) or a static server dependency.** The server is a read-only file
  server for one person on loopback. A framework would bring an install, an upgrade path and an attack surface to
  replace about 150 lines; `CLAUDE.md` allows a dependency only when it replaces code the project would otherwise
  have to maintain at a greater cost, and Range handling is the only hard part either way.
- **Opening `index.html` from disk with no server.** The media would load, but Chrome will not seek in a `file://`
  video in all cases, and the operator would lose the link that the path unit keeps current.

## Consequences

- The catalog needs a running server. `tools/systemd/srstudio-catalog-web.service` keeps one up; the operator installs
  it. The root `catalogo-scene-render.html` is no longer written and goes stale.
- A browser holding an old page can get a 404 for media a rebuild removed, until it reloads. The page is revalidated
  on every load, so a reload always fixes it.
- `generated/catalog/site` must stay on the same device as the cache for the hard links to save space; otherwise it
  costs a copy and nothing else.
