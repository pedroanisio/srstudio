# The catalog page

Back to the [library README](../../README.md) and the [workspace README](../../../README.md).

`srstudio page` writes the scene-render catalog, a single self-contained HTML file with every video and image embedded.
The page is the six original packages followed by *Parte 2: Os episódios novos da biblioteca*, which is rebuilt from
disk on every run:

- **Episodes**: every project in `--episodes` that has a `<slug>.scene.xml` and a render `<slug>.mp4` in `--renders`.
  The title, description, frame, fps and duration come from the scene. The lines come from the project's
  `dialogue.json`, `timeline.json` or `narration.json`. The style comes from the parts registry.
- **Styles**: one card for each registered style the base page does not already describe.
- **Pip's poses**: the Soft character drawn by the engine in every pose.
- **Registry**: every registered part with its style, kind, summary and episodes.
- **Used and unused parts** (with `--usage`): the characters, locations and props, each with the episodes that use
  it, then the ones no episode uses.

## Running it

From the workspace root, first measure which parts the episodes use (see the
[library README](../../README.md#the-parts)), then build the page:

```bash
(cd srstudio && ../.venv/bin/srstudio usage --episodes ../generated/episodes --packages ../generated/packages \
    --scripts episodes --work _tmp/usage-work --out ../generated/catalog/usage.json \
    --arg mushroom-training=--voice --arg employee-survey=--voice --arg the-report=--voice --arg logo-bigger=--voice)
.venv/bin/srstudio page \
    --base generated/catalog/packages-base.html \
    --episodes generated/episodes --renders generated/renders \
    --notes srstudio/docs/catalog/notes.json --usage generated/catalog/usage.json \
    --cache generated/catalog/cache --engine generated/bin/scene-render \
    --out catalogo-scene-render.html
```

- `--usage` is the report `srstudio usage` writes (schema `1.0.0`). With it, the registry table's episodes, the
  gallery chips and the gallery check below use the measured usage instead of the hand-declared `episodes=`. A report
  that cannot be read stops the build with exit code 2.

- `--base` is the frozen page of the six packages. If it no longer has the anchors the generator writes into, the
  command stops with `srstudio page: …` and exit code 2, and the old page is left as it was.
- `--cache` keeps the web encodes (540 px wide, 720 px when the render is wider than tall, so a square Ink render is 540; keyed by each render's size and modification time)
  and the pose images (keyed by the pose list). Unchanged renders are not encoded again.
- The page is written atomically with mode `600`.

## Notes

[`notes.json`](notes.json) holds the Portuguese text that cannot be read from disk: an episode's number, lede and
highlights, a style card's title and text, and the library's gallery. Noted episodes are listed first, in the file's
order; any other rendered episode follows by name with its scene description as the lede. Schema `1.1.0` (`1.0.0`
is still read, without a gallery): an unknown field, a missing field or a wrong type stops the build.

```json
{
  "schema": "1.1.0",
  "episodes": {"camera-off": {"number": "08", "lede": "…", "highlights": ["…"]}},
  "styles": {"soft": {"title": "Blob pose a pose", "text": "…"}},
  "gallery": [
    {"section": "cast", "name": "Pip", "parts": ["pip"], "voice": "Will", "text": "…",
     "shot": {"episode": "focus-mode", "at": 1.0, "box": [390, 560, 690, 920]},
     "poses": [{"label": "dança", "shot": {"episode": "focus-mode", "at": 9.5, "box": [260, 740, 820, 820]}}]}
  ]
}
```

The gallery fills Part 3, *Elenco, locações e props*. The six packages' cards come from the base page, and the
library's cards follow them in each grid. `section` is `cast`, `locations`, `props` or `graphics`. `parts` names the
registered parts the item shows. `shot` is a still cut from `generated/renders/<episode>.mp4` at `at` seconds,
cropped to `box` (`[x, y, w, h]` in frame pixels) when one is given; it is at most 480 px wide and cached like the
web encodes. Only the cast takes `poses`. The chips are the numbers of the library episodes the parts are
registered for, plus the episodes the stills come from.

When the notes have a gallery, the build also stops when:

- an item names an unregistered part;
- a still's episode has no render;
- a still's time is past the end;
- a box leaves the frame;
- a part that a rendered library episode is registered with (by slug or number), or with `--usage` a part its build
  calls, is shown by no item.

So a new episode cannot leave the gallery out of date.

## Keeping it up to date

[`tools/systemd/`](../../tools/systemd/) has a user path unit that runs the command above whenever one of these
changes:

- a file in `generated/renders`;
- a branch of this repository (a commit);
- `notes.json`;
- the base page.

The service first waits until no render has changed for 15 s, checking at most 60 times. Install it once:

```bash
cd srstudio/tools/systemd
systemctl --user link "$PWD/srstudio-catalog.path" "$PWD/srstudio-catalog.service"
systemctl --user enable --now srstudio-catalog.path
journalctl --user -u srstudio-catalog.service   # each rebuild and its episode list
```
