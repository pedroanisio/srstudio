# The catalog site

Back to the [library README](../../README.md) and the [workspace README](../../../README.md).

`srstudio page` writes the scene-render catalog as a small site, `index.html`, `catalog.json` and
`media/<content-hash>.<ext>`, and `srstudio serve` serves it ([ADR 0046](../decisions/0046-catalog-web-app.md)). The
page holds no data URI: every video, image, font and sound is a file it links to with a relative URL, and only the
current view loads its media. The app is plain JavaScript in `src/srstudio/assets/catalog/`, published as media like
everything else, and it renders every view from `catalog.json`.

## What is where

The navigation has a search box that finds names across all sections, and each view is a link. Back and forward work.

| Route | What it shows |
|---|---|
| `#/` | The opening of the base page: its summary, style cards and footer, with counts. |
| `#/estilos`, `#/estilos/<slug>` | Every style: description, videos and parts. |
| `#/personagens`, `#/locacoes`, `#/objetos`, `#/graficos` | The parts of each kind: name, image, video count. `?estilo=<slug>` filters by style, `?estilo=nenhum` lists the shared parts. |
| `#/personagens/<name>` (same for the other kinds) | The part alone, then its reel stills under *Visto em*, its text and every video it appears in. Pip also shows the pose sheet. |
| `#/videos`, `#/videos?estilo=<slug>` | Every video, filterable by style. |
| `#/videos/<slug>` | Player, facts, lines that seek the video, the style and every part. |
| `#/pacotes`, `#/pacotes/<id>` | The six packages with their players, inventories and comparison. |
| `#/motor` | The engine inventory, the pipeline and AudioForge. |
| `#/registro` | The parts registry and the used and unused lists. |
| `#/busca/<text>` | The search results. |

`catalog.json` is built from these sources, and it is never edited by hand:

- **Videos**: every project in `--episodes` that has a `<slug>.scene.xml` and a render `<slug>.mp4` in `--renders`.
  The title, description, frame, fps and duration come from the scene. The lines come from the project's
  `dialogue.json`, `timeline.json` or `narration.json`. The six packages are entries too, marked `pacote`, each with a
  poster the engine renders from its scene spec, and so is a measured project with no render. The style comes from the
  measured usage.
- **Styles**: every registered style, with the text of the notes, or its registered summary when it has none.
- **Parts**: every registered part with its style, kind and summary, its specimen, the stills the notes curate, and
  the videos `--usage` measured.

A specimen is the part alone, drawn by its own builder through the engine (ADR 0051), so a new part shows in the next
build with no note and no reel, titled from its registered summary until the notes name it. A part that cannot stand
alone has no specimen and says why; a registered part with neither stops the build. To add one, draw it with a recipe
in `catalog_specimens.RECIPES` when its builder needs data of its own, or give it a typed `REFUSED` reason.

Marks say what is missing. A part no video uses is marked *não usado*, and an episode
the usage report could not measure says *Não medido* instead of showing as using nothing.

A part with a version history to show (more than one version, or one that is proposed or carries an approval, a proof
or a pin) shows it on its page (ADR 0061): number, date, note, status, which version
new reels get, the operator's approval, the proof and the reels that pin it, with the drawing of every version. An
index lists the part once, showing its default's drawing, with a version count and how many are proposed; the registry
table keeps every drawing. A proposed version is marked as proposed and is never the default. A version's head rig, when it has one, is shown under it with its own approval and proof.

A pilot (a project in `generated/episodes/pilots/<series>/<slug>`, rendered into `generated/renders/pilots`) is an
ordinary video tagged with its series (ADR 0067). An original package whose render is in `generated/renders` plays it,
and links its SVG player. A folder with no scene and no render, such as `the-code`, is not a video and has no card.

The document is defined by `srstudio.catalog_data` (`schema_version` `1.4.0`). `catalog_data.load` rejects unknown
fields, unresolved references and missing media.

## Running it

From the workspace root, first measure which parts the episodes use (see the
[library README](../../README.md#the-parts)), then build the page:

```bash
(cd srstudio && ../.venv/bin/srstudio usage --episodes ../generated/episodes --packages ../generated/packages \
    --scripts episodes --work _tmp/usage-work --out ../generated/catalog/usage.json)
.venv/bin/srstudio page \
    --base generated/catalog/packages-base.html \
    --episodes generated/episodes --renders generated/renders \
    --notes srstudio/docs/catalog/notes.json --usage generated/catalog/usage.json \
    --releases srstudio/episodes/posts \
    --cache generated/catalog/cache --engine generated/bin/scene-render --packages generated/packages \
    --site generated/catalog/site
.venv/bin/srstudio serve generated/catalog/site   # http://127.0.0.1:8765/
```

`srstudio serve SITE [--host 127.0.0.1] [--port 8765]` is read-only and has no authentication, so it binds to
loopback unless told otherwise. It answers the byte ranges a browser needs to seek a video. Opening `index.html`
from disk is not supported.

- `--releases` is the folder of release files (`srstudio/episodes/posts`), which says which reels pin which version.
  Without it the page says the pins were not read.
- `--proof-root` is where a version record's proof paths start, by default the working directory. A proof that is not
  on the machine keeps its path on the page, with no link.
- `--usage` is the report `srstudio usage` writes (schema `1.0.0`). Each part's videos, each video's parts and the
  gallery check below come from it; without it no part is claimed by any video and every video is marked as not
  measured. Notes with a gallery need it: the build stops with exit code 2 without one, since the gallery check could
  not fail. A report that cannot be read, or that names a part no longer registered, stops the build with exit code 2.

- `--packages` is the folder of `<name>-<version>` packages, or `SRSTUDIO_PACKAGES`. Each package's poster is rendered
  from its scene spec; packages are only read.
- `--base` is the frozen page of the six packages. If it no longer has the anchors the generator writes into, the
  command stops with `srstudio page: …` and exit code 2, and the old page is left as it was.
- `--cache` keeps the web encodes (540 px wide, 720 px when the render is wider than tall, so a square Ink render is 540; keyed by each render's size and modification time)
  and the pose images (keyed by the pose list). Unchanged renders are not encoded again. It also keeps the specimens
  (keyed by each part's drawing) and the package posters (keyed by spec, moment and package version), so a rebuild
  renders only the parts that changed. `srstudio page` prints how many it rendered, took from the cache and refused.
- `--site` is written with folders `700` and files `600`. Media are named by their content, so a rebuild writes only
  what changed. They are hard-linked from the cache where possible and copied otherwise. Media go first, then
  `catalog.json`, and `index.html` is replaced last, so a failed build leaves the previous site working. Files nothing references are
  removed only after that. The build stops if the page would hold a data URI or pass `INDEX_LIMIT`.

## Notes

[`notes.json`](notes.json) holds the Portuguese text that cannot be read from disk: an episode's number, lede and
highlights, a style card's title and text, a part's title, and the library's gallery. Noted episodes are listed
first, in the file's order; any other rendered episode follows by name with its scene description as the lede. Schema
`1.3.0` (`1.1.0` is still read, without part titles, and `1.0.0` without a gallery either): an unknown field, a missing
field or a wrong type stops the build.

```json
{
  "schema": "1.2.0",
  "episodes": {"camera-off": {"number": "08", "lede": "…", "highlights": ["…"]}},
  "styles": {"soft": {"title": "Blob pose a pose", "text": "…"}},
  "parts": {"bean-jar": {"title": "Pote de grãos de café"}},
  "gallery": [
    {"section": "cast", "name": "Pip", "parts": ["pip"], "voice": "Will", "text": "…",
     "shot": {"episode": "focus-mode", "at": 1.0, "box": [390, 560, 690, 920]},
     "poses": [{"label": "dança", "shot": {"episode": "focus-mode", "at": 9.5, "box": [260, 740, 820, 820]}}]}
  ]
}
```

The gallery fills the detail view of each part it names; the cards of the six packages stay under `#/pacotes`.
`section` is `cast`, `locations`, `props` or `graphics`. `parts` names the registered parts the item shows. `shot` is a still cut from `generated/renders/<episode>.mp4` at `at` seconds,
cropped to `box` (`[x, y, w, h]` in frame pixels) when one is given; it is at most 480 px wide and cached like the
web encodes. Only the cast takes `poses`.

A part's title is its `parts` entry, or else the `name` of a gallery item that shows that part alone. An item that
shows several parts names a shot, so its name stays under "Visto em" and titles none of them. A part with neither takes
the first clause of its registered summary, in English, until someone writes its entry; a character with no curated
name gets a plain description here, because a name is the operator's to choose. The build stops when an entry names an
unregistered part, or when two parts of a kind share a curated title.

When the notes have a gallery, the build also stops when:

- an item names an unregistered part;
- a still's episode has no render;
- a still's time is past the end;
- a box leaves the frame;
- a part that a rendered library episode's build calls, as `--usage` measured it, is shown by no item.

So a new episode cannot leave the gallery out of date.

That check needs the measured usage, which takes minutes, so it cannot run before a merge. A cheaper one does:
`tests/test_catalog_coverage.py` requires every registered part to be shown by a gallery item or listed there, with the
reason, as not shown (no project builds it, only a package does, its reels are not rendered yet). A branch that
registers a part therefore fails its own tests until it adds a gallery item or declares the part, instead of the site
stopping after the merge. It cannot see a declared part that a new episode starts to use: the build above still stops
for that, `srstudio-catalog.service` shows as failed, and `journalctl --user -u srstudio-catalog.service` names the
parts. Remove a part from the list when its item is added; the test fails on an entry that is shown or not registered.

## Keeping it up to date

[`tools/systemd/`](https://github.com/pedroanisio/srstudio-episodes/tree/develop/tools/systemd) has a user path unit that runs the command above whenever one of these
changes:

- a file in `generated/renders`;
- a branch of this repository (a commit);
- `notes.json`;
- the base page;
- `generated/catalog/usage.json`, the report below.

The service first waits until no render has changed for 15 s, checking at most 60 times. A second unit,
`srstudio-catalog-web.service`, keeps `srstudio serve` running on `127.0.0.1:8765`.

The page only reads the usage report, so a third pair of units keeps it current: `srstudio-usage.path` starts
`srstudio-usage.service` when an episode is added or removed, or a branch of this repository changes, and the service
runs `srstudio usage` over every episode (minutes, since each is built on a copy). The report is written only after
every episode was tried. An episode with a `voiced/` recording whose script takes `--voice` is built from it, the build
its delivered master came from. One whose build fails is listed as not measured (the page marks it *Não medido*) and
the run exits 1, so the unit shows as failed with the episode named in the journal; if every build fails nothing is
written and the previous report stays. When the report changes, `srstudio-catalog.path` rebuilds the site. Install
them once:

```bash
cd srstudio/tools/systemd
systemctl --user link "$PWD/srstudio-catalog.path" "$PWD/srstudio-catalog.service" "$PWD/srstudio-catalog-web.service" \
    "$PWD/srstudio-usage.path" "$PWD/srstudio-usage.service"
systemctl --user enable --now srstudio-catalog.path srstudio-catalog-web.service srstudio-usage.path
journalctl --user -u srstudio-catalog.service   # each rebuild and its episode list
journalctl --user -u srstudio-usage.service     # each measure; a failure names the episode
```
