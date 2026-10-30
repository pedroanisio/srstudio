"""``srstudio.catalog_page``: the catalog page rebuilt from the episode projects, their renders and the registry."""

import base64
import dataclasses
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

from srstudio import catalog_data, specimens
from srstudio import catalog_page as cp
from srstudio.cli import main
from support.catalog import (
    BASE,
    GALLERY,
    USAGE,
    fake_poster,
    fake_render_all,
    item,
    pictures,
    shot,
    still_of,
    write_project,
)  # fmt: skip


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
        ({"schema": "1.1.0", "episodes": {}, "styles": {}, "parts": {"pip": {"title": "T"}}}, "parts"),
        ({"schema": "1.2.0", "episodes": {}, "styles": {}, "parts": []}, "parts"),
        ({"schema": "1.2.0", "episodes": {}, "styles": {}, "parts": {"pip": {}}}, "title"),
        ({"schema": "1.2.0", "episodes": {}, "styles": {}, "parts": {"pip": {"title": 3}}}, "title"),
        ({"schema": "1.2.0", "episodes": {}, "styles": {}, "parts": {"pip": {"title": " "}}}, "title"),
        ({"schema": "1.2.0", "episodes": {}, "styles": {}, "parts": {"pip": {"title": "T", "colour": "x"}}}, "unknown"),
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


def url(seed: object, ext: str = "jpg") -> str:
    return f"media/{hashlib.sha256(str(seed).encode()).hexdigest()[:32]}.{ext}"


SHELL = {"stylesheet": url("css", "css"), "script": url("js", "js")}


def test_inject_makes_the_base_page_the_shell_of_the_app(tree):
    page = cp.inject(BASE, cards(tree), cp.Notes(), **SHELL)
    for label in ("Estilos", "Personagens", "Locações", "Objetos", "Gráficos", "Vídeos", "Motor"):
        assert f">{label}</a>" in page  # the labels stay in Portuguese, as the page is
    assert page.index('<nav id="nav"') < page.index('<div class="wrap" id="base">') < page.index('<main id="app"')
    assert page.index('<main id="app"') < page.index("<footer>")
    assert f'<link rel="stylesheet" href="{SHELL["stylesheet"]}">' in page
    assert f'<script src="{SHELL["script"]}" defer></script>' in page
    assert 'class="style-tag soft"' in page and 'class="style-tag cel"' in page  # every registered style
    assert page.count('class="style-tag cutout">Cutout</span><b>Recorte') == 1  # cards already there are kept
    assert "3 episódios novos" in page and "<b>9</b><span>estilos" in page
    assert f"<b>{len(cp.registry.entries())}</b><span>peças registradas" in page  # fills the ninth spec cell
    assert page.rstrip().endswith("</html>")


def test_the_shell_holds_no_media_and_runs_the_base_script_only_when_asked(tree):
    page = cp.inject(BASE, cards(tree), cp.Notes(), **SHELL)
    assert "<video" not in page and "<img" not in page  # the app renders them, a view at a time
    assert "window.srstudioBase = (function(){" in page and "});\n</script>" in page
    assert "})();\n</script>" not in page  # defined, not called


@pytest.mark.parametrize(
    "lost", ['<div class="wrap">', "<footer>", "(function(){\n'use strict';", "})();\n</script>", "const ENGINE = ["]
)
def test_inject_refuses_a_base_that_lost_an_anchor(tree, lost):
    with pytest.raises(cp.CatalogError, match="anchor"):
        cp.inject(BASE.replace(lost, "<!-- gone -->"), cards(tree), cp.Notes(), **SHELL)


def assembled(tree, notes=None, *, usage=None, packages=(), poses=(), engine=(), shown=None, refused=None):
    notes = notes or cp.Notes()
    return cp.assemble(
        cp.discover(*tree, notes, usage),
        notes,
        media=lambda r: url(r.name, "mp4"),
        poster=lambda r: url(r.name),
        poses=poses,
        stills=lambda s: url(f"{s.episode}@{s.at:g}"),
        usage=usage,
        packages=packages,
        engine=engine,
        pictures=pictures() if shown is None else shown,
        refused=refused or {},
        posters={p.slug: url(p.slug) for p in packages},
    )


def test_a_video_is_built_from_its_project_and_its_measured_parts(tree):
    catalog = assembled(tree, usage=USAGE)
    video = {v.slug: v for v in catalog.videos}["camera-off"]
    assert (video.title, video.lede, video.format, video.width) == (
        "camera-off title", "About camera-off & more", "9:16", 1080,
    )  # fmt: skip
    assert video.source == "library" and video.measured and video.style == "soft"
    assert video.parts == USAGE.episodes["camera-off"]
    assert video.src == url("camera-off.mp4", "mp4") and video.poster == url("camera-off.mp4")
    assert [x.t for x in video.lines] == [0.5, 1.0, 2.0] and video.effects == 1


def test_every_style_lists_its_videos_and_its_parts(tree):
    catalog = assembled(tree, usage=USAGE)
    assert [s.slug for s in catalog.styles] == list(cp.STYLES)
    soft = {s.slug: s for s in catalog.styles}["soft"]
    assert soft.videos == ("camera-off",)
    assert set(soft.parts) == {x.name for x in cp.registry.entries() if x.style == "soft"}
    assert soft.text_html == cp.html.escape(cp.STYLES["soft"].summary)  # no note: the registered summary, escaped


def test_a_style_note_is_curated_markup():
    notes = cp.Notes(styles={"soft": cp.StyleNote("Blob", "Pose a <i>pose</i>.")})
    catalog = cp.assemble([], notes, media=str, poster=str, poses=[], pictures=pictures())
    soft = {s.slug: s for s in catalog.styles}["soft"]
    assert (soft.title, soft.text_html) == ("Blob", "Pose a <i>pose</i>.")


def test_every_registered_part_is_in_the_document_with_its_measured_videos(tree):
    catalog = assembled(tree, usage=USAGE)
    parts = {p.name: p for p in catalog.parts}
    assert set(parts) == {x.name for x in cp.registry.entries()}
    assert parts["pip"].videos == ("camera-off",) and parts["juno"].videos == ()  # used, and reachable though unused
    assert parts["juno"].gallery == ()  # no gallery still: not dropped either
    assert parts["pip"].specimen == still_of("pip")


def test_a_package_is_a_video_with_facts_and_no_file(tree):
    packages = cp.packages_of(BASE)
    assert [(p.slug, p.number, p.title, p.fmt) for p in packages] == [
        ("honesty-interview", "01", "Honestidade", "9:16"),
        ("printer-recreation", "06", "A impressora", "1:1"),
    ]
    assert packages[1].lede == "O estilo d'Ink."
    catalog = assembled(tree, usage=USAGE, packages=packages)
    videos = {v.slug: v for v in catalog.videos}
    honesty = videos["honesty-interview"]
    assert (honesty.source, honesty.measured, honesty.style, honesty.src) == ("package", True, "cutout", None)
    assert honesty.poster == url("honesty-interview")  # rendered from its spec
    assert honesty.parts == ("manager", "office-wide") and honesty.title == "Honestidade"
    assert "honesty-interview" in {p.name: p for p in catalog.parts}["manager"].videos
    printer = videos["printer-recreation"]
    assert (printer.measured, printer.parts) == (False, ())  # it is a package, and the report does not cover it


def test_a_package_without_a_poster_is_refused(tree):
    with pytest.raises(cp.CatalogError, match="honesty-interview.*poster"):
        cp.assemble([], cp.Notes(), media=str, poster=str, poses=[], packages=cp.packages_of(BASE), pictures=pictures())


def test_a_part_with_neither_a_specimen_nor_a_reason_stops_the_build_by_name(tree):
    shown = pictures()
    del shown["juno"], shown["soft-desk"]
    with pytest.raises(cp.CatalogError, match=r"\['juno', 'soft-desk'\]"):
        assembled(tree, shown=shown)


def test_a_part_with_both_a_specimen_and_a_reason_is_refused(tree):
    with pytest.raises(cp.CatalogError, match="both"):
        assembled(tree, refused={"juno": "Não."})


def test_a_refused_part_says_why_and_holds_no_picture(tree):
    shown = pictures()
    del shown["captions"]
    catalog = assembled(tree, shown=shown, refused={"captions": "Só existe sobre uma cena."})
    captions = {p.name: p for p in catalog.parts}["captions"]
    assert captions.specimen is None and captions.refused == "Só existe sobre uma cena."


def test_every_reason_has_its_words_in_the_catalog_language():
    assert set(cp.REFUSAL_TEXT) == set(cp.catalog_specimens.Reason)
    assert all(cp.REFUSAL_TEXT.values())


def test_a_part_with_no_curated_title_takes_its_registered_summary_and_a_curated_one_wins(tree, tmp_path):
    parts = {p.name: p for p in assembled(tree, usage=USAGE).parts}
    assert parts["juno"].title == cp.title_of(cp.registry.get("character", "juno"))
    assert parts["juno"].title != "juno"
    notes = gallery_notes(tmp_path)
    curated = {p.name: p for p in assembled(tree, notes, usage=SHOWN).parts}
    assert curated["pip"].title == "Pip"


@pytest.mark.parametrize(
    "summary, title",
    [
        ("Ava the barista: bun, apron, name tag", "Ava the barista"),
        ("Dr. Feld, a sixties therapist with a bun and glasses who has heard everything until now", "Dr. Feld"),
        ("The Handbook entry; dry", "The Handbook entry"),
        ("One caption per cue: centred text across the frame at :data:`CAPTION_Y`.", "One caption per cue"),
        ("An avocado standing on ``at``, ripe", "An avocado standing, ripe"),
        ("The gate podium at the right, from :data:`PODIUM_X` at :data:`PODIUM_TOP`", "The gate podium at the right"),
        ("A child's essay on ruled paper (:data:`SHEET`, centred on ``at``)", "A child's essay on ruled paper"),
        ("A plain sign.", "A plain sign"),
        ("Words " * 20, "Words " * 9 + "Words…"),
    ],
)
def test_a_summary_becomes_a_short_title(summary, title):
    entry = cp.registry.Entry("prop", "a-file-name", print, summary=summary)
    assert cp.title_of(entry) == title


def test_a_part_with_no_summary_is_named_not_shown_under_its_file_name():
    with pytest.raises(cp.CatalogError, match="a-file-name"):
        cp.title_of(cp.registry.Entry("prop", "a-file-name", print))


def test_every_registered_part_has_a_title_that_is_not_its_file_name():
    specimens.load_parts()
    titles = {x.name: cp.title_of(x) for x in cp.registry.entries()}
    assert not {name for name, title in titles.items() if title == name or len(title) > cp.TITLE_LIMIT + 1}


def test_a_base_page_with_bad_scene_data_is_refused():
    page = '<script id="scenes-data" type="application/json">[{"id": "x"}]</script>'
    with pytest.raises(cp.CatalogError, match="scene data"):
        cp.packages_of(page)
    assert cp.packages_of("<html></html>") == []


def test_the_engine_inventory_is_read_for_the_search():
    assert cp.engine_topics(BASE) == ("Animação e tempo", "Simulação física")
    assert cp.engine_topics("<html></html>") == ()


def test_a_measured_episode_with_no_card_is_kept_and_marked(tree):
    catalog = assembled(tree, usage=USAGE)
    honesty = {v.slug: v for v in catalog.videos}["honesty-interview"]  # no package data given here
    assert (honesty.source, honesty.measured, honesty.src) == ("no-render", True, None)


def test_an_unmeasured_episode_says_so_and_does_not_show_as_using_nothing(tree):
    report = cp.Report({"camera-off": USAGE.episodes["camera-off"]}, ("the-router", "the-code"))
    catalog = assembled(tree, usage=report)
    videos = {v.slug: v for v in catalog.videos}
    assert catalog.unmeasured == ("the-router", "the-code") and catalog.measured
    assert (videos["the-router"].source, videos["the-router"].measured) == ("library", False)
    assert (videos["the-code"].source, videos["the-code"].measured) == ("no-render", False)  # a project, no render


def test_a_card_the_report_never_mentions_is_not_measured(tree):
    partial = cp.Report({"camera-off": USAGE.episodes["camera-off"]})
    videos = {v.slug: v for v in assembled(tree, usage=partial).videos}
    assert (videos["the-router"].measured, videos["the-router"].parts, videos["the-router"].style) == (False, (), "")


def test_without_a_report_nothing_is_claimed(tree):
    catalog = assembled(tree)
    assert catalog.measured is False and all(not v.measured and not v.parts for v in catalog.videos)
    assert all(not p.videos for p in catalog.parts)


def test_a_report_naming_a_part_the_registry_lost_is_refused(tree):
    stale = cp.Report({"camera-off": ("pip", "a-removed-part")})
    with pytest.raises(cp.CatalogError, match="a-removed-part"):
        assembled(tree, usage=stale)


def test_the_pose_sheet_belongs_to_pip(tree):
    catalog = assembled(tree, poses=[("stand", url("stand", "png"))])
    pip = {p.name: p for p in catalog.parts}["pip"]
    assert pip.sheet == (cp.Still(url("stand", "png"), 300, 320, "stand"),)
    assert sum(1 for p in catalog.parts if p.sheet) == 1


def test_an_unregistered_pip_cannot_hold_the_pose_sheet(tree, monkeypatch):
    monkeypatch.setattr(cp.registry, "entries", lambda *a: [])
    with pytest.raises(cp.CatalogError, match="pip"):
        cp.assemble([], cp.Notes(), media=str, poster=str, poses=[("stand", url("stand", "png"))], pictures={})


# -- building ---------------------------------------------------------------------------------------------
def engine() -> Path:
    found = os.environ.get("SRSTUDIO_ENGINE") or shutil.which("scene-render")
    if not found or not Path(found).exists() or not shutil.which("ffmpeg"):
        pytest.skip("needs SRSTUDIO_ENGINE and ffmpeg")
    return Path(found).resolve()


def rendered(renders: Path) -> None:
    for slug in ("camera-off", "the-router", "mushroom-training"):
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=108x192:rate=10:duration=1",
             "-pix_fmt", "yuv420p", str(renders / f"{slug}.mp4")],
            check=True,
        )  # fmt: skip


def page_args(tree, tmp_path, *, engine_path="missing-engine", base=None) -> list[str]:
    episodes, renders = tree
    args = ["page", "--base", str(base or tmp_path / "base.html"), "--episodes", str(episodes)]
    args += ["--renders", str(renders), "--site", str(tmp_path / "site"), "--cache", str(tmp_path / "cache")]
    return [*args, "--engine", str(engine_path), "--packages", str(tmp_path / "packages")]


def references(site: Path) -> set[str]:
    text = (site / "index.html").read_text() + (site / "catalog.json").read_text()
    return set(re.findall(r"media/[0-9a-f]+\.[a-z0-9]+", text))


def test_build_writes_a_private_site_and_reuses_its_cache(tree, tmp_path, monkeypatch):
    monkeypatch.setattr(cp.catalog_specimens, "render_all", fake_render_all)
    monkeypatch.setattr(cp.catalog_specimens, "poster", fake_poster)
    rendered(tree[1])
    (tmp_path / "base.html").write_text(BASE)
    args = page_args(tree, tmp_path, engine_path=engine())
    assert main(args) == 0
    site, cache = tmp_path / "site", tmp_path / "cache"
    page, document = (site / "index.html").read_text(), (site / "catalog.json").read_text()
    assert not cp.embedded(page) and not cp.embedded(document)  # no data URI of any kind
    catalog = catalog_data.load(site / "catalog.json")  # strict, and every media file it names is there
    assert sum(1 for v in catalog.videos if v.src) == 3
    assert {f"media/{p.name}" for p in (site / "media").iterdir()} == references(site)
    assert {p.suffix for p in (site / "media").iterdir()} == {".mp4", ".jpg", ".png", ".js", ".css"}
    for path in [site / "index.html", site / "catalog.json", *(site / "media").iterdir()]:
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    for folder in (site, site / "media"):
        assert stat.S_IMODE(folder.stat().st_mode) == 0o700
    cached = {p.name: p.stat().st_mtime_ns for p in cache.rglob("*") if p.is_file()}
    assert main(args) == 0
    assert {p.name: p.stat().st_mtime_ns for p in cache.rglob("*") if p.is_file()} == cached  # nothing re-encoded


@pytest.fixture
def fake_media(monkeypatch, tree, tmp_path):
    """Encoders replaced by small files with distinct contents, so a build needs neither ffmpeg nor the engine."""

    def web_video(render: Path, cache: Path) -> tuple[Path, Path]:
        cache.mkdir(parents=True, exist_ok=True)
        video, poster = cache / f"{render.stem}.mp4", cache / f"{render.stem}.jpg"
        video.write_bytes(f"video {render.stem} ".encode() + render.read_bytes())
        poster.write_bytes(f"poster {render.stem} ".encode() + render.read_bytes())
        return video, poster

    def pose_sheet(engine: Path, cache: Path) -> list[tuple[str, Path]]:
        png = cache / "stand.png"
        png.write_bytes(b"pose")
        return [("stand", png)]

    monkeypatch.setattr(cp, "web_video", web_video)
    monkeypatch.setattr(cp, "pose_sheet", pose_sheet)
    monkeypatch.setattr(cp.catalog_specimens, "render_all", fake_render_all)
    monkeypatch.setattr(cp.catalog_specimens, "poster", fake_poster)
    (tmp_path / "base.html").write_text(BASE)
    return page_args(tree, tmp_path)


def test_a_rebuild_writes_only_what_changed_and_removes_what_is_no_longer_referenced(tree, tmp_path, fake_media):
    site = tmp_path / "site"
    assert main(fake_media) == 0
    document = (site / "catalog.json").read_bytes()
    assert main(fake_media) == 0
    assert (site / "catalog.json").read_bytes() == document  # a rebuild of the same inputs is the same document
    before = {p.name: p.stat().st_ino for p in (site / "media").iterdir()}
    (site / "media" / ".abandoned.mp4.123").write_bytes(b"a partial write of a killed build")
    (tree[1] / "the-router.mp4").write_bytes(b"a new render")
    assert main(fake_media) == 0
    after = {p.name: p.stat().st_ino for p in (site / "media").iterdir()}
    assert {f"media/{name}" for name in after} == references(site)  # the old router files and the partial are gone
    assert len(before) == len(after) and len(set(before) & set(after)) == len(before) - 2  # its video and poster
    assert all(before[name] == after[name] for name in set(before) & set(after))  # the rest were left alone


def test_the_site_holds_every_specimen_and_poster_and_a_page_says_what_it_rendered(tree, tmp_path, fake_media, capsys):
    assert main(fake_media) == 0
    catalog = catalog_data.load(tmp_path / "site" / "catalog.json")
    assert all(p.specimen for p in catalog.parts)
    assert all(v.poster for v in catalog.videos if v.source == "package")
    assert (
        f"{len(catalog.parts)} specimens: 0 rendered, {len(catalog.parts)} cached, 0 refused" in capsys.readouterr().out
    )


def test_a_refused_part_reaches_the_site_with_the_words_of_its_reason(tree, tmp_path, fake_media, monkeypatch):
    def one_refused(engine, cache, episodes):
        shelf = fake_render_all(engine, cache, episodes)
        done = {k: v for k, v in shelf.done.items() if k != "captions"}
        why = cp.catalog_specimens.Refused(cp.catalog_specimens.Reason.OVERLAY, "over a shot")
        return cp.catalog_specimens.Shelf(done, {"captions": why}, 0)

    monkeypatch.setattr(cp.catalog_specimens, "render_all", one_refused)
    assert main(fake_media) == 0
    parts = {p.name: p for p in catalog_data.load(tmp_path / "site" / "catalog.json").parts}
    assert parts["captions"].refused == cp.REFUSAL_TEXT[cp.catalog_specimens.Reason.OVERLAY]


def test_a_specimen_that_fails_stops_the_page_with_its_name(tree, tmp_path, fake_media, monkeypatch, capsys):
    def fails(engine, cache, episodes):
        raise cp.catalog_specimens.SpecimenRenderError("1 specimens failed:\nshrub: the recipe drew nothing")

    monkeypatch.setattr(cp.catalog_specimens, "render_all", fails)
    assert main(fake_media) == 2
    assert "shrub" in capsys.readouterr().err and not (tmp_path / "site" / "catalog.json").exists()


def test_a_package_poster_that_fails_stops_the_page_with_its_name(tree, tmp_path, fake_media, monkeypatch, capsys):
    def fails(packages, slug, engine, cache):
        raise cp.catalog_specimens.SpecimenRenderError(f"package {slug}: no scene spec")

    monkeypatch.setattr(cp.catalog_specimens, "poster", fails)
    assert main(fake_media) == 2
    assert "honesty-interview" in capsys.readouterr().err


def test_package_posters_need_the_packages_folder(tree, tmp_path, fake_media, monkeypatch):
    monkeypatch.delenv("SRSTUDIO_PACKAGES", raising=False)
    args = fake_media[: fake_media.index("--packages")]
    with pytest.raises(SystemExit):
        main(args)


def test_a_failed_build_leaves_the_previous_site_working(tree, tmp_path, fake_media, monkeypatch):
    site = tmp_path / "site"
    assert main(fake_media) == 0
    page = (site / "index.html").read_text()
    (tree[1] / "the-router.mp4").write_bytes(b"a new render")

    def no_space(*_args):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(cp.os, "replace", no_space)  # the first thing that fails is placing a media file
    assert main(fake_media) == 2
    monkeypatch.undo()
    assert (site / "index.html").read_text() == page
    assert all((site / ref).exists() for ref in references(site))


def test_the_index_is_replaced_last_and_what_it_needs_is_removed_only_after(tree, tmp_path, fake_media, monkeypatch):
    site = tmp_path / "site"
    assert main(fake_media) == 0
    page = (site / "index.html").read_text()
    old = references(site)
    (tree[1] / "the-router.mp4").write_bytes(b"a new render")
    write = cp._write_text

    def fail_on_the_index(path, text):
        if path.name == "index.html":
            raise cp.CatalogError("the index could not be written")
        write(path, text)

    monkeypatch.setattr(cp, "_write_text", fail_on_the_index)
    assert main(fake_media) == 2
    assert (site / "index.html").read_text() == page
    assert all((site / ref).exists() for ref in old | references(site))  # nothing of the old site was pruned


def test_a_file_at_the_site_path_is_reported(tree, tmp_path, fake_media, capsys):
    (tmp_path / "site").write_text("in the way")
    assert main(fake_media) == 2
    assert "srstudio page:" in capsys.readouterr().err


def test_an_index_past_its_bound_is_refused(tree, tmp_path, fake_media, monkeypatch, capsys):
    monkeypatch.setattr(cp, "INDEX_LIMIT", 100)
    assert main(fake_media) == 2
    assert "bytes" in capsys.readouterr().err and not (tmp_path / "site" / "index.html").exists()


def test_the_single_file_mode_is_gone(tree, tmp_path):
    with pytest.raises(SystemExit) as exit_:
        main([*page_args(tree, tmp_path)[:-4], "--out", str(tmp_path / "o.html"), "--cache", str(tmp_path / "c")])
    assert exit_.value.code == 2


def test_page_reports_a_bad_base_as_an_error(tree, tmp_path, capsys):
    (tmp_path / "base.html").write_text("<html></html>")
    assert main(page_args(tree, tmp_path)) == 2
    assert "srstudio page:" in capsys.readouterr().err
    assert not (tmp_path / "site").exists()


# -- media ------------------------------------------------------------------------------------------------
def test_media_are_named_by_their_content_and_linked_from_the_cache(tmp_path):
    source = tmp_path / "cached.MP4"
    source.write_bytes(b"bytes")
    source.chmod(0o600)
    store = cp.MediaStore(tmp_path / "media")
    url = store.add(source)
    assert re.fullmatch(r"media/[0-9a-f]{32}\.mp4", url)
    assert (tmp_path / url).read_bytes() == b"bytes" and (tmp_path / url).stat().st_ino == source.stat().st_ino
    twin = tmp_path / "twin.mp4"
    twin.write_bytes(b"bytes")
    assert store.add(twin) == url  # same content, same name


def test_a_cache_file_on_another_device_is_copied(tmp_path, monkeypatch):
    source = tmp_path / "cached.jpg"
    source.write_bytes(b"bytes")
    source.chmod(0o600)

    def cross_device(*_args):
        raise OSError(18, "Invalid cross-device link")

    monkeypatch.setattr(cp.os, "link", cross_device)
    url = cp.MediaStore(tmp_path / "media").add(source)
    copied = tmp_path / url
    assert copied.read_bytes() == b"bytes" and copied.stat().st_ino != source.stat().st_ino
    assert stat.S_IMODE(copied.stat().st_mode) == 0o600


def test_a_cache_file_with_another_mode_is_copied_so_the_cache_is_only_read(tmp_path):
    source = tmp_path / "cached.jpg"
    source.write_bytes(b"bytes")
    source.chmod(0o644)
    copied = tmp_path / cp.MediaStore(tmp_path / "media").add(source)
    assert stat.S_IMODE(copied.stat().st_mode) == 0o600 and stat.S_IMODE(source.stat().st_mode) == 0o644


def test_a_damaged_media_file_is_rewritten(tmp_path):
    source = tmp_path / "cached.jpg"
    source.write_bytes(b"bytes")
    store = cp.MediaStore(tmp_path / "media")
    target = tmp_path / store.add(source)
    target.unlink()
    target.write_bytes(b"by")
    assert (tmp_path / store.add(source)).read_bytes() == b"bytes"


def test_a_document_or_page_with_a_data_uri_is_never_written(tree, tmp_path, fake_media, monkeypatch):
    real = cp.registry.entries

    def embedded_summary(*args):
        return [dataclasses.replace(x, summary="data:image/png;base64,AAAA") for x in real(*args)]

    monkeypatch.setattr(cp.registry, "entries", embedded_summary)
    assert main(fake_media) == 2
    assert not (tmp_path / "site" / "catalog.json").exists() and not (tmp_path / "site" / "index.html").exists()


def test_the_uris_of_the_base_page_become_media_files(tmp_path):
    font, song = base64.b64encode(b"font bytes").decode(), base64.b64encode(b"song bytes").decode()
    page = f"""<style>@font-face{{ src:url("data:font/ttf;base64,{font}") format("truetype") }}</style>
<script>const A = {{"one": "data:audio/mpeg;base64,{song}", "two": "data:audio/mpeg;base64,{song}"}};</script>
<p>metadata: kept, and so is data: alone in prose</p>"""
    store = cp.MediaStore(tmp_path / "media")
    out = cp.extract_embedded(page, store)
    assert not cp.embedded(out) and "metadata: kept" in out
    fonts = re.findall(r'url\("(media/[0-9a-f]+\.ttf)"\)', out)
    songs = re.findall(r'"(media/[0-9a-f]+\.mp3)"', out)
    assert len(fonts) == 1 and len(songs) == 2 and songs[0] == songs[1]
    assert (tmp_path / fonts[0]).read_bytes() == b"font bytes" and (tmp_path / songs[0]).read_bytes() == b"song bytes"


@pytest.mark.parametrize(
    "uri, match",
    [
        ("data:application/x-unknown;base64,AAAA", "application/x-unknown"),  # no extension to serve it under
        ("data:font/ttf;base64,AAAAA", "base64"),  # a bad length
    ],
)
def test_a_base_page_uri_that_cannot_become_a_file_is_refused(tmp_path, uri, match):
    with pytest.raises(cp.CatalogError, match=match):
        cp.extract_embedded(f'<a href="{uri}">', cp.MediaStore(tmp_path / "media"))


@pytest.mark.parametrize(
    "uri",
    ["data:image/svg+xml,%3Csvg%3E", "data:text/plain;charset=utf-8,hello", "DATA:IMAGE/PNG;base64,AAAA", "data:,x"],
)
def test_a_uri_of_any_other_form_still_counts_as_embedded(tmp_path, uri):
    assert cp.embedded(f'<img src="{uri}">')
    with pytest.raises(cp.CatalogError, match="data URI"):
        cp.require_no_embedded(f'<img src="{uri}">')


# -- the galleries ----------------------------------------------------------------------------------------
def gallery_notes(tmp_path, gallery=GALLERY, schema="1.1.0", parts=None) -> cp.Notes:
    path = tmp_path / "notes.json"
    doc = {"schema": schema, "episodes": {}, "styles": {}, "gallery": gallery}
    if parts is not None:
        doc |= {"schema": "1.2.0", "parts": {name: {"title": title} for name, title in parts.items()}}
    path.write_text(json.dumps(doc))
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
        (item(shot=shot(at=float("nan"))), "at"),  # json reads NaN and Infinity
        (item(shot=shot(at=float("inf"))), "at"),
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


def test_a_gallery_item_reaches_every_part_it_shows(tree, tmp_path):
    notes = gallery_notes(tmp_path)
    catalog = assembled(tree, notes, usage=SHOWN)
    parts = {p.name: p for p in catalog.parts}
    pip = parts["pip"]
    assert (pip.title, pip.gallery[0].voice) == ("Pip", "Will")
    assert pip.gallery[0].note_html == "O <i>blob</i>."  # curated text is markup, as in the episode highlights
    assert pip.gallery[0].still == cp.Still(url("camera-off@1"), 300, 400, "", "camera-off")
    assert pip.gallery[0].poses == (cp.Still(url("camera-off@2"), 200, 200, "dança", "camera-off"),)
    assert parts["talking-router"].gallery == parts["ink-hand"].gallery
    assert parts["ink-hand"].gallery[0].name == "O roteador"
    assert parts["cel-lettering"].gallery[0].still.height == 300  # a crop keeps its own shape
    assert parts["soft-office"].gallery[0].still.width == 1080  # a whole frame has the episode's


def test_a_gallery_title_names_a_part_only_when_the_item_shows_that_part_alone(tree, tmp_path):
    parts = {p.name: p for p in assembled(tree, gallery_notes(tmp_path), usage=SHOWN).parts}
    assert parts["pip"].title == "Pip"  # the item shows pip alone
    for name in ("talking-router", "ink-hand"):  # "O roteador" names a shot of the two
        assert parts[name].title == cp.title_of(cp.registry.get(parts[name].kind, name))
        assert parts[name].title != "O roteador"


def test_a_part_note_titles_the_part_whatever_the_gallery_calls_it(tree, tmp_path):
    notes = gallery_notes(tmp_path, parts={"ink-hand": "A mão de tinta", "pip": "O blob"})
    assert notes.parts["ink-hand"] == cp.PartNote(title="A mão de tinta")
    parts = {p.name: p for p in assembled(tree, notes, usage=SHOWN).parts}
    assert (parts["ink-hand"].title, parts["pip"].title) == ("A mão de tinta", "O blob")
    assert parts["ink-hand"].gallery[0].name == "O roteador"  # the shot keeps its own name


def test_part_notes_need_no_gallery(tree, tmp_path):
    doc = {"schema": "1.2.0", "episodes": {}, "styles": {}, "parts": {"juno": {"title": "A Juno"}}}
    notes = cp.load_notes(write_notes(tmp_path, doc))
    assert {p.name: p for p in assembled(tree, notes, usage=USAGE).parts}["juno"].title == "A Juno"


def test_a_note_for_an_unregistered_part_is_refused_by_name(tree, tmp_path):
    notes = gallery_notes(tmp_path, parts={"no-such-part": "Nada"})
    with pytest.raises(cp.CatalogError, match="no-such-part"):
        assembled(tree, notes, usage=SHOWN)


def test_curated_titles_that_repeat_within_a_kind_are_refused_by_name(tree, tmp_path):
    for repeated in (
        {"juno": "Pip"},  # a note against a solo gallery item
        {"juno": "Outra", "manager": "Outra"},  # two notes
    ):
        with pytest.raises(cp.CatalogError, match="juno") as caught:
            assembled(tree, gallery_notes(tmp_path, parts=repeated), usage=SHOWN)
        assert "pip" in str(caught.value) or "manager" in str(caught.value)


def test_a_curated_title_may_repeat_across_kinds(tree, tmp_path):
    notes = gallery_notes(tmp_path, parts={"juno": "Cena", "soft-office": "Cena"})
    parts = {p.name: p for p in assembled(tree, notes, usage=SHOWN).parts}
    assert parts["juno"].title == parts["soft-office"].title == "Cena"


def test_the_library_notes_title_registered_parts_shortly_and_never_twice_in_a_kind():
    specimens.load_parts()
    notes = cp.load_notes(Path(__file__).parents[1] / "docs" / "catalog" / "notes.json")
    titles = cp.curated_titles(notes)
    cp.check_titles(titles)  # raises on an unregistered part or a repeated title
    assert notes.parts and not [t for t in titles.values() if len(t) > cp.TITLE_LIMIT]


def test_without_a_curated_gallery_no_part_has_a_still(tree):
    assert all(not p.gallery for p in assembled(tree).parts)


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
        assembled(tree, notes, usage=SHOWN)


def test_a_gallery_without_a_usage_report_is_refused(tree, tmp_path):
    # its coverage check counts the parts the rendered episodes use, which only a usage report measures
    with pytest.raises(cp.CatalogError, match="usage report"):
        assembled(tree, gallery_notes(tmp_path))


def test_a_gallery_needs_stills(tree, tmp_path):
    with pytest.raises(cp.CatalogError, match="stills"):
        cp.assemble(
            cards(tree), gallery_notes(tmp_path), media=str, poster=str, poses=[], usage=SHOWN, pictures=pictures()
        )


HALF_WRITER = """#!/bin/sh
# writes part of its output (the file after -o, else the last argument), then fails like a killed encode
out=""; prev=""; last=""
for a in "$@"; do [ "$prev" = "-o" ] && out="$a"; prev="$a"; last="$a"; done
[ -z "$out" ] && out="$last"
printf partial > "$out"
exit 1
"""


@pytest.mark.parametrize("make", ["web_video", "still", "pose_sheet"])
def test_a_failed_encode_leaves_nothing_a_later_run_would_take_as_cached(tmp_path, monkeypatch, make):
    tools = tmp_path / "bin"
    tools.mkdir()
    for name in ("ffmpeg", "engine"):
        (tools / name).write_text(HALF_WRITER)
        (tools / name).chmod(0o700)
    monkeypatch.setenv("PATH", f"{tools}{os.pathsep}{os.environ['PATH']}")
    render, cache = tmp_path / "ep.mp4", tmp_path / "cache"
    render.write_bytes(b"not a video")
    call = {
        "web_video": lambda: cp.web_video(render, cache),
        "still": lambda: cp.still(render, cp.Shot("ep", 1.0), cache),
        "pose_sheet": lambda: cp.pose_sheet(tools / "engine", cache),
    }[make]
    for _ in range(2):
        with pytest.raises(cp.CatalogError, match="failed"):
            call()
    assert [p for p in cache.rglob("*") if p.is_file() and not p.name.endswith(".scene.xml")] == []


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
# the measured usage less soft-desk: every part it names is shown by an item of GALLERY
SHOWN = cp.Report({slug: tuple(p for p in parts if p != "soft-desk") for slug, parts in USAGE.episodes.items()})


def test_with_usage_the_gallery_must_show_every_part_a_rendered_episode_uses(tree, tmp_path):
    notes = gallery_notes(tmp_path)
    with pytest.raises(cp.CatalogError, match="soft-desk"):  # measured in camera-off, shown by no item
        assembled(tree, notes, usage=USAGE)
    covered = gallery_notes(tmp_path, [*GALLERY, item(name="Mesa", parts=["soft-desk"])])
    assert assembled(tree, covered, usage=USAGE).measured  # manager (honesty-interview, no card) needs no gallery item


def test_page_reports_an_unreadable_usage_report_as_an_error(tree, tmp_path, capsys):
    episodes, renders = tree
    bad = tmp_path / "usage.json"
    bad.write_text(json.dumps({"schema": "0.1.0"}))
    args = ["page", "--base", str(tmp_path / "base.html"), "--episodes", str(episodes), "--renders", str(renders)]
    args += ["--site", str(tmp_path / "site"), "--cache", str(tmp_path / "c"), "--usage", str(bad)]
    assert main(args) == 2
    assert "schema" in capsys.readouterr().err and not (tmp_path / "site").exists()


@pytest.mark.parametrize(
    "docstring, shown",
    [
        ("Centred at :data:`CAPTION_Y` by default", "Centred at CAPTION_Y by default"),
        ("See :func:`srstudio.word_cues`, then ``at``", "See srstudio.word_cues, then at"),
        ("One line with no markup", "One line with no markup"),
    ],
)
def test_a_part_summary_shows_no_docstring_markup(docstring, shown):
    assert cp.plain(docstring) == shown
