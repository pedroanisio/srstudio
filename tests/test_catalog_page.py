"""``srstudio.catalog_page``: the catalog page rebuilt from the episode projects, their renders and the registry."""

import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

from srstudio import catalog_page as cp
from srstudio.cli import main

SCENE = """<?xml version="1.0" encoding="UTF-8"?>
<scene version="1.1">
  <project width="{w}" height="{h}" fps="{fps}" duration="{dur}" seed="1" background="#000000"/>
  <metadata title="{title}" description="{desc}" generator="test"/>
</scene>
"""

BASE = """<!doctype html>
<html lang="pt-BR"><head><style>
.a{ color:red }
</style></head><body>
<div class="eyebrow">scene-render · sr-core · srstudio · AudioForge · 6 pacotes .vpkg</div>
<p class="lede">Seis curtas reconstruídos, com <b>Cutout</b> e <b>Ink</b>.</p>
<div class="styles">
        <div class="style-card"><span class="style-tag cutout">Cutout</span><b>Recorte</b></div>
        <div class="style-card"><span class="style-tag ink">Ink</span><b>Traço</b></div>
      </div>
    </div>
    <div class="specs" aria-label="Especificações comuns">
      <div class="spec"><b>95,7 s</b><span>6 episódios</span></div>
    </div>
<section id="episodios"><div class="eyebrow">Parte 1</div></section>
<section id="elenco"><div class="eyebrow">Parte 2</div>
<p class="lede">Tudo que aparece nos seis vídeos, recortado do próprio desenho.</p>
  <div class="cast" id="cast"></div>
  <div class="locs" id="locs"></div>
  <div class="props" id="props"></div>
  <div class="props" id="graphics"></div>
</section>
<section id="usado"><div class="eyebrow">Parte 3</div></section>
<footer>
  <p>Fontes: os seis pacotes.</p>
</footer>
</body>
</html>
"""


def write_project(root: Path, slug: str, *, kind: str = "dialogue", w=1080, h=1920, fps=30, dur=4.0) -> Path:
    p = root / slug
    p.mkdir(parents=True)
    (p / f"{slug}.scene.xml").write_text(
        SCENE.format(w=w, h=h, fps=fps, dur=dur, title=f"{slug} title", desc=f"About {slug} &amp; more")
    )
    (p / f"{slug}.audio.scene.xml").write_text("<scene/>")  # the audio document is not the episode
    if kind == "dialogue":
        data = {
            "phrases": [
                {"role": "pip", "voice_name": "Will", "text": "Second line.", "start": 2.0},
                {"role": "boss", "voice_name": "Eric", "text": "First line.", "start": 0.5},
            ],
            "sound_effects": [{"name": "call-chime", "start": 1.0, "duration": 0.5}],
        }
    elif kind == "timeline":
        data = {
            "items": [
                {"actor": "human", "voice_name": "Chris", "text": "Load!", "start": 0.0},
                {"actor": "sfx", "text": "[BEEP]", "start": 1.0},
            ]
        }
    else:
        data = {"items": [{"text": "This module will take forty-five minutes.", "start": 0.08}]}
    (p / f"{kind if kind != 'narration' else 'narration'}.json").write_text(json.dumps(data))
    return p


@pytest.fixture
def tree(tmp_path) -> tuple[Path, Path]:
    episodes, renders = tmp_path / "episodes", tmp_path / "renders"
    renders.mkdir()
    write_project(episodes, "camera-off")
    write_project(episodes, "the-router", kind="timeline", w=1080, h=1080, fps=24)
    write_project(episodes, "mushroom-training", kind="narration", fps=24)
    write_project(episodes, "no-render-yet")
    for slug in ("camera-off", "the-router", "mushroom-training"):
        (renders / f"{slug}.mp4").write_bytes(b"not decoded here")
    return episodes, renders


# -- notes ------------------------------------------------------------------------------------------------
def test_notes_parse_into_typed_values(tmp_path):
    path = tmp_path / "notes.json"
    path.write_text(
        json.dumps(
            {
                "schema": "1.0.0",
                "episodes": {"camera-off": {"number": "08", "lede": "Câmera.", "highlights": ["Duas vozes."]}},
                "styles": {"soft": {"title": "Blob", "text": "Pose a pose."}},
            }
        )
    )
    notes = cp.load_notes(path)
    assert notes.episodes["camera-off"] == cp.EpisodeNote(number="08", lede="Câmera.", highlights=("Duas vozes.",))
    assert notes.styles["soft"] == cp.StyleNote(title="Blob", text="Pose a pose.")
    assert list(notes.order) == ["camera-off"]


@pytest.mark.parametrize(
    "doc, match",
    [
        ({"schema": "1.0.0", "episodes": {}, "styles": {}, "extra": 1}, "unknown"),
        ({"schema": "1.0.0", "episodes": {"x": {"number": "1", "colour": "red"}}, "styles": {}}, "unknown"),
        ({"schema": "1.0.0", "episodes": {"x": {"number": 8}}, "styles": {}}, "number"),
        ({"schema": "1.0.0", "episodes": {"x": {"highlights": "one"}}, "styles": {}}, "highlights"),
        ({"schema": "1.0.0", "episodes": {}, "styles": {"soft": {"title": "T"}}}, "text"),
        ({"schema": "2.0.0", "episodes": {}, "styles": {}}, "schema"),
        ([], "object"),
    ],
)
def test_bad_notes_are_refused(tmp_path, doc, match):
    path = tmp_path / "notes.json"
    path.write_text(json.dumps(doc))
    with pytest.raises(cp.CatalogError, match=match):
        cp.load_notes(path)


def test_unreadable_notes_are_refused(tmp_path):
    path = tmp_path / "notes.json"
    path.write_text("{not json")
    with pytest.raises(cp.CatalogError, match="notes.json"):
        cp.load_notes(path)
    with pytest.raises(cp.CatalogError, match="missing"):
        cp.load_notes(tmp_path / "missing.json")


# -- discovery --------------------------------------------------------------------------------------------
def test_lines_come_from_whichever_script_the_project_has(tree):
    episodes, _ = tree
    lines, effects = cp.lines_of(episodes / "camera-off")
    assert [(x.t, x.who, x.sfx) for x in lines] == [(0.5, "boss", False), (1.0, "sfx", True), (2.0, "pip", False)]
    assert lines[1].text == "call chime" and effects == 1
    lines, effects = cp.lines_of(episodes / "the-router")
    assert [x.voice for x in lines] == ["Chris", ""] and lines[1].sfx and effects == 1
    lines, effects = cp.lines_of(episodes / "mushroom-training")
    assert lines[0].who == "narration" and effects == 0


def test_a_project_without_a_script_has_no_lines_and_a_broken_one_is_refused(tmp_path):
    (tmp_path / "silent").mkdir()
    assert cp.lines_of(tmp_path / "silent") == ([], 0)
    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "dialogue.json").write_text(json.dumps({"phrases": [{"role": "pip"}]}))
    with pytest.raises(cp.CatalogError, match="dialogue.json"):
        cp.lines_of(bad)


def test_discover_reads_every_rendered_project_in_note_order(tree):
    episodes, renders = tree
    notes = cp.Notes(episodes={"the-router": cp.EpisodeNote(number="I2", lede="Roteador.")})
    cards = cp.discover(episodes, renders, notes, USAGE)
    assert [c.slug for c in cards] == ["the-router", "camera-off", "mushroom-training"]  # noted first, then by name
    router, camera = cards[0], cards[1]
    assert (router.number, router.lede, router.fmt, router.fps) == ("I2", "Roteador.", "1:1", 24)
    assert (camera.number, camera.lede, camera.fmt) == ("", "About camera-off & more", "9:16")
    assert camera.title == "camera-off title" and camera.duration == 4.0
    assert camera.style == "soft" and router.style == "ink" and cards[2].style == "cel"  # from the measured parts


def test_a_project_without_a_scene_is_skipped_and_a_broken_scene_is_refused(tree):
    episodes, renders = tree
    (episodes / "empty").mkdir()
    (renders / "empty.mp4").write_bytes(b"")
    assert "empty" not in [c.slug for c in cp.discover(episodes, renders, cp.Notes())]
    (episodes / "camera-off" / "camera-off.scene.xml").write_text("<scene><project/>")
    with pytest.raises(cp.CatalogError, match="camera-off"):
        cp.discover(episodes, renders, cp.Notes())


def test_the_style_of_an_episode_is_the_style_of_the_parts_it_was_measured_using():
    assert cp.style_of("camera-off", USAGE) == "soft"
    assert cp.style_of("the-router", USAGE) == "ink"
    assert cp.style_of("honesty-interview", USAGE) == "cutout"
    assert cp.style_of("never-measured", USAGE) == ""
    assert cp.style_of("camera-off", None) == ""  # nothing measured, nothing claimed


def test_a_crossover_takes_the_style_most_of_its_parts_come_from():
    crossover = cp.Report({"mixed": ("pip", "soft-office", "talking-router")})
    assert cp.style_of("mixed", crossover) == "soft"
    tie = cp.Report({"tied": ("pip", "talking-router")})
    assert cp.style_of("tied", tie) == "ink"  # a tie goes to the first style by name, never to chance


# -- the page ---------------------------------------------------------------------------------------------
def cards(tree):
    episodes, renders = tree
    return cp.discover(episodes, renders, cp.Notes())


def test_inject_adds_the_library_section_style_cards_and_figures(tree):
    page = cp.inject(BASE, cards(tree), cp.Notes(), media=lambda p: p.name, poses=[("stand", "stand.png")])
    assert '<section id="biblioteca">' in page and page.index('id="biblioteca"') < page.index('id="elenco"')
    assert '<div class="eyebrow">Parte 2</div>' in page and '<div class="eyebrow">Parte 4</div>' in page
    assert page.count('<div class="eyebrow">Parte 3</div>') == 1
    for slug in ("camera-off", "the-router", "mushroom-training"):
        assert f'id="lib-{slug}"' in page and f'src="{slug}.mp4"' in page
    assert 'class="style-tag soft"' in page and 'class="style-tag cel"' in page  # every registered style
    assert page.count('class="style-tag cutout">Cutout</span><b>Recorte') == 1  # cards already there are kept
    assert "3 episódios novos" in page and "<b>9</b><span>estilos" in page
    assert f"<b>{len(cp.registry.entries())}</b><span>peças registradas" in page  # fills the ninth spec cell
    assert 'alt="Pip, pose stand"' in page and "pip" in page  # pose sheet and the registry table
    assert "About camera-off &amp; more" in page  # escaped once
    assert page.rstrip().endswith("</html>") and "lib-dialog" in page


def test_inject_refuses_a_base_that_lost_an_anchor(tree):
    with pytest.raises(cp.CatalogError, match="anchor"):
        cp.inject(BASE.replace('<section id="elenco">', "<section>"), cards(tree), cp.Notes(), media=str, poses=[])


# -- building ---------------------------------------------------------------------------------------------
def engine() -> Path:
    found = os.environ.get("SRSTUDIO_ENGINE") or shutil.which("scene-render")
    if not found or not Path(found).exists() or not shutil.which("ffmpeg"):
        pytest.skip("needs SRSTUDIO_ENGINE and ffmpeg")
    return Path(found).resolve()


def test_build_writes_a_private_standalone_page_and_reuses_its_cache(tree, tmp_path):
    episodes, renders = tree
    for slug in ("camera-off", "the-router", "mushroom-training"):
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=108x192:rate=10:duration=1",
             "-pix_fmt", "yuv420p", str(renders / f"{slug}.mp4")],
            check=True,
        )  # fmt: skip
    base = tmp_path / "base.html"
    base.write_text(BASE)
    out = tmp_path / "site" / "catalog.html"
    cache = tmp_path / "cache"
    args = ["page", "--base", str(base), "--episodes", str(episodes), "--renders", str(renders)]
    args += ["--out", str(out), "--cache", str(cache), "--engine", str(engine())]
    assert main(args) == 0
    page = out.read_text()
    assert page.count("data:video/mp4;base64,") == 3 and page.count("data:image/png;base64,") >= 18
    assert stat.S_IMODE(out.stat().st_mode) == 0o600 and stat.S_IMODE(out.parent.stat().st_mode) == 0o700
    cached = {p.name: p.stat().st_mtime_ns for p in cache.rglob("*") if p.is_file()}
    assert main(args) == 0
    assert {p.name: p.stat().st_mtime_ns for p in cache.rglob("*") if p.is_file()} == cached  # nothing re-encoded


def test_page_reports_a_bad_base_as_an_error(tree, tmp_path, capsys):
    episodes, renders = tree
    base = tmp_path / "base.html"
    base.write_text("<html></html>")
    args = ["page", "--base", str(base), "--episodes", str(episodes), "--renders", str(renders)]
    args += ["--out", str(tmp_path / "o.html"), "--cache", str(tmp_path / "c"), "--engine", "missing-engine"]
    assert main(args) == 2
    assert "srstudio page:" in capsys.readouterr().err
    assert not (tmp_path / "o.html").exists()


# -- the galleries ----------------------------------------------------------------------------------------
def shot(episode="camera-off", at=1.0, box=None):
    return {"episode": episode, "at": at, **({"box": box} if box else {})}


GALLERY = [  # covers every part the tree's three episodes are registered with
    {"section": "cast", "name": "Pip", "parts": ["pip"], "voice": "Will", "text": "O <i>blob</i>.",
     "shot": shot(box=[0, 0, 300, 400]), "poses": [{"label": "dança", "shot": shot(at=2.0, box=[0, 0, 200, 200])}]},
    {"section": "cast", "name": "O roteador", "parts": ["talking-router", "ink-hand"], "text": "Fala.",
     "shot": shot("the-router")},
    {"section": "locations", "name": "Escritório & casa", "parts": ["soft-office"], "text": "Mesa.", "shot": shot()},
    {"section": "locations", "name": "Prateleira", "parts": ["ink-router-shot", "ink-router-wide"], "text": "Muro.",
     "shot": shot("the-router", 0.5)},
    {"section": "cast", "name": "Cogumelo", "parts": ["cel-traced"], "text": "Traçado.",
     "shot": shot("mushroom-training")},
    {"section": "locations", "name": "Sala", "parts": ["cel-room"], "text": "Piso.", "shot": shot("mushroom-training")},
    {"section": "graphics", "name": "Letreiro", "parts": ["cel-lettering"], "text": "Caixa.",
     "shot": shot("mushroom-training", 0.2, [0, 0, 1080, 300])},
]  # fmt: skip


def gallery_notes(tmp_path, gallery=GALLERY, schema="1.1.0") -> cp.Notes:
    path = tmp_path / "notes.json"
    path.write_text(json.dumps({"schema": schema, "episodes": {}, "styles": {}, "gallery": gallery}))
    return cp.load_notes(path)


def test_the_gallery_parses_into_typed_items(tmp_path):
    notes = gallery_notes(tmp_path)
    pip = notes.gallery[0]
    assert (pip.section, pip.name, pip.parts, pip.voice) == ("cast", "Pip", ("pip",), "Will")
    assert pip.shot == cp.Shot("camera-off", 1.0, (0, 0, 300, 400))
    assert pip.poses == (cp.Pose("dança", cp.Shot("camera-off", 2.0, (0, 0, 200, 200))),)
    assert notes.gallery[1].shot.box is None and notes.gallery[1].poses == ()
    assert cp.load_notes(write_notes(tmp_path, {"schema": "1.0.0", "episodes": {}, "styles": {}})).gallery is None


def write_notes(tmp_path, doc) -> Path:
    path = tmp_path / "doc.json"
    path.write_text(json.dumps(doc))
    return path


def item(**changes):
    return {**GALLERY[0], **changes}


@pytest.mark.parametrize(
    "entry, match",
    [
        (item(section="crowd"), "section"),
        (item(colour="red"), "unknown"),
        ({k: v for k, v in GALLERY[0].items() if k != "shot"}, "missing"),
        (item(name=""), "name"),
        (item(parts=[]), "parts"),
        (item(parts="pip"), "parts"),
        (item(shot=shot(at=-1)), "at"),
        (item(shot=shot(at="1")), "at"),
        (item(shot=shot(at=True)), "at"),
        (item(shot=shot(box=[0, 0, 0, 10])), "box"),
        (item(shot=shot(box=[0, 0, 10])), "box"),
        (item(shot=shot(box=[0, -1, 10, 10])), "box"),
        (item(shot=shot(box=[0, 0.5, 10, 10])), "box"),
        (item(shot={**shot(), "zoom": 2}), "unknown"),
        (item(poses=[{"label": "x"}]), "missing"),
        (item(poses="x"), "poses"),
        ({**GALLERY[2], "poses": [{"label": "x", "shot": shot()}]}, "poses"),
    ],
)
def test_a_bad_gallery_item_is_refused(tmp_path, entry, match):
    with pytest.raises(cp.CatalogError, match=match):
        gallery_notes(tmp_path, [entry])


def test_a_gallery_needs_schema_1_1_and_a_list(tmp_path):
    with pytest.raises(cp.CatalogError, match="gallery"):
        gallery_notes(tmp_path, schema="1.0.0")
    with pytest.raises(cp.CatalogError, match="gallery"):
        gallery_notes(tmp_path, gallery={"cast": []})


def stills(s: cp.Shot) -> str:
    return f"{s.episode}@{s.at:g}.jpg"


def test_the_galleries_are_injected_after_the_base_hosts(tree, tmp_path):
    notes = gallery_notes(tmp_path)
    numbered = cp.Notes(episodes={"camera-off": cp.EpisodeNote(number="08")}, gallery=notes.gallery)
    page = cp.inject(BASE, cp.discover(*tree, numbered), numbered, media=str, poses=[], stills=stills)
    cast = page.index('<div class="cast lib-gal" id="lib-cast">')
    assert (
        page.index('<div class="cast" id="cast"></div>') < cast < page.index('<div class="locs lib-gal" id="lib-locs">')
    )
    assert page.index('<div class="props" id="graphics"></div>') < page.index(
        '<div class="props lib-gal" id="lib-graphics">'
    )
    pip = page[cast : page.index("</p>", cast)]
    assert '<img src="camera-off@1.jpg" alt="Pip"' in pip and "<span>voz Will (ElevenLabs)</span>" in pip
    assert '<span class="chip on">08</span>' in pip  # the episode's number, the slug when it has none
    assert "O <i>blob</i>." in pip  # curated text is markup, as in the episode highlights
    assert '<img src="camera-off@2.jpg" alt="Pip, dança"' in page and "<small>dança</small>" in page
    assert "<h3>Escritório &amp; casa</h3>" in page
    assert '<span class="chip on">the-router</span>' in page
    assert 'style="aspect-ratio:1080/300"' in page  # a crop keeps its own shape
    assert "nos seis vídeos originais e nos 3 episódios da biblioteca" in page


def test_without_a_curated_gallery_the_base_galleries_are_left_alone(tree):
    page = cp.inject(BASE, cards(tree), cp.Notes(), media=str, poses=[])
    assert "lib-gal\"" not in page and "Tudo que aparece nos seis vídeos, recortado" in page


@pytest.mark.parametrize(
    "change, match",
    [
        (lambda g: g[:-1], "cel-lettering"),  # a part a library episode draws, shown by no item
        (lambda g: g + [item(name="X", parts=["no-such-part"])], "no-such-part"),
        (lambda g: g + [item(name="X", shot=shot("five-years"))], "five-years"),
        (lambda g: g + [item(name="X", shot=shot(at=4.0))], "at"),
        (lambda g: g + [item(name="X", shot=shot(box=[900, 0, 300, 300]))], "box"),
        (lambda g: g + [item(name="X", poses=[{"label": "y", "shot": shot(box=[0, 1800, 10, 200])}])], "box"),
    ],
)
def test_the_gallery_is_checked_against_the_registry_and_the_renders(tree, tmp_path, change, match):
    notes = gallery_notes(tmp_path, change(list(GALLERY)))
    with pytest.raises(cp.CatalogError, match=match):
        cp.inject(BASE, cards(tree), notes, media=str, poses=[], stills=stills, usage=SHOWN)


def test_a_gallery_needs_stills(tree, tmp_path):
    with pytest.raises(cp.CatalogError, match="stills"):
        cp.inject(BASE, cards(tree), gallery_notes(tmp_path), media=str, poses=[])


def test_a_still_is_cut_from_the_render_once(tmp_path):
    if not shutil.which("ffmpeg"):
        pytest.skip("needs ffmpeg")
    render = tmp_path / "ep.mp4"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=1080x1920:rate=10:duration=2",
         "-pix_fmt", "yuv420p", str(render)],
        check=True,
    )  # fmt: skip
    cache = tmp_path / "cache"
    crop = cp.still(render, cp.Shot("ep", 1.0, (100, 200, 600, 300)), cache)
    full = cp.still(render, cp.Shot("ep", 1.0), cache)

    def size(path):
        return subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, check=True,
        ).stdout.strip()  # fmt: skip

    assert size(crop) == "480,240" and size(full) == "480,854"  # cropped, then at most 480 wide
    mtime = crop.stat().st_mtime_ns
    assert cp.still(render, cp.Shot("ep", 1.0, (100, 200, 600, 300)), cache).stat().st_mtime_ns == mtime
    with pytest.raises(cp.CatalogError, match="ep.mp4"):
        cp.still(render, cp.Shot("ep", 9.0), cache)  # past the end: no frame, a clear error


# -- measured usage ---------------------------------------------------------------------------------------
USAGE = cp.Report(
    {
        "camera-off": ("pip", "soft-office", "soft-desk"),
        "the-router": ("talking-router", "ink-hand", "ink-router-shot", "ink-router-wide"),
        "mushroom-training": ("cel-traced", "cel-room", "cel-lettering"),
        "honesty-interview": ("manager", "office-wide"),  # a package episode: no card, not in the gallery
    }
)


# the measured usage less soft-desk: every part it names is shown by an item of GALLERY
SHOWN = cp.Report({slug: tuple(p for p in parts if p != "soft-desk") for slug, parts in USAGE.episodes.items()})


def test_the_registry_table_and_the_usage_lists_come_from_the_measured_usage(tree):
    page = cp.inject(BASE, cards(tree), cp.Notes(), media=str, poses=[], usage=USAGE)
    table = page[page.index('<table class="lib-registry">') : page.index("</table>")]
    assert "<td><code>soft-desk</code></td>" in table
    row = table[table.index("<code>soft-desk</code>") :]
    assert row[: row.index("</tr>")].endswith("<td>camera-off</td>")  # declared nowhere, measured in camera-off
    juno = table[table.index("<code>juno</code>") :]
    assert juno[: juno.index("</tr>")].endswith("<td>—</td>")

    def block(kind):
        start = page.index(f'id="usage-{kind}"')
        return page[start : page.index("</div>", start)]

    chars = block("character")
    used, unused = chars.split("Não usados")
    assert "Personagens" in chars and "<b>4</b> usados" in chars  # pip, talking-router, cel-traced, manager
    assert "<code>manager</code> <small>honesty-interview</small>" in used and "<code>juno</code>" in unused
    assert "<code>pip</code>" in used and "<code>pip</code>" not in unused
    assert f"<b>{len(cp.registry.entries('character')) - 4}</b> não usados" in chars
    assert "<code>soft-desk</code> <small>camera-off</small>" in block("prop") and "Locações" in block("location")
    assert 'id="usage-graphic"' not in page  # characters, locations and props


def test_without_usage_the_table_claims_no_episodes_and_no_list_is_added(tree):
    page = cp.inject(BASE, cards(tree), cp.Notes(), media=str, poses=[])
    assert 'id="lib-usage"' not in page
    table = page[page.index('<table class="lib-registry">') : page.index("</table>")]
    row = table[table.index("<code>pip</code>") :]
    assert row[: row.index("</tr>")].endswith("<td>—</td>")


def test_with_usage_the_gallery_must_show_every_part_a_rendered_episode_uses(tree, tmp_path):
    notes = gallery_notes(tmp_path)
    with pytest.raises(cp.CatalogError, match="soft-desk"):  # measured in camera-off, shown by no item
        cp.inject(BASE, cards(tree), notes, media=str, poses=[], stills=stills, usage=USAGE)
    covered = gallery_notes(tmp_path, [*GALLERY, item(name="Mesa", parts=["soft-desk"])])
    page = cp.inject(BASE, cards(tree), covered, media=str, poses=[], stills=stills, usage=USAGE)
    assert 'id="lib-usage"' in page  # manager (honesty-interview, no card) needs no gallery item


def test_page_reports_an_unreadable_usage_report_as_an_error(tree, tmp_path, capsys):
    episodes, renders = tree
    bad = tmp_path / "usage.json"
    bad.write_text(json.dumps({"schema": "0.1.0"}))
    args = ["page", "--base", str(tmp_path / "base.html"), "--episodes", str(episodes), "--renders", str(renders)]
    args += ["--out", str(tmp_path / "o.html"), "--cache", str(tmp_path / "c"), "--usage", str(bad)]
    assert main(args) == 2
    assert "schema" in capsys.readouterr().err and not (tmp_path / "o.html").exists()
