"""The catalog app end to end: a built site, ``srstudio serve`` on a loopback port and headless Chromium.

Skipped where Playwright or its browser is not installed, as the engine tests are where the engine is not.
The only clock in here is Playwright's own timeouts, which bound a wait and never pace a step.
"""

import json
import shutil
import subprocess
import threading
from pathlib import Path

import pytest

from srstudio import catalog_page as cp
from srstudio import catalog_server as server
from support import catalog as fx

sync_api = pytest.importorskip("playwright.sync_api")

BASE = fx.BASE.replace("const AUDIO_SRC = {};", "const AUDIO_SRC = {}; window.baseRuns = (window.baseRuns || 0) + 1;")


@pytest.fixture(scope="module")
def site(tmp_path_factory) -> Path:
    if not shutil.which("ffmpeg"):
        pytest.skip("needs ffmpeg")
    root = tmp_path_factory.mktemp("app")
    episodes, renders, cache = root / "episodes", root / "renders", root / "cache"
    renders.mkdir()
    cache.mkdir()
    fx.write_project(episodes, "camera-off", dur=4.0)
    fx.write_project(episodes, "the-router", kind="timeline", w=1080, h=1080, fps=24, dur=4.0)
    fx.write_project(episodes, "mushroom-training", kind="narration", fps=24, dur=4.0)
    fx.write_project(episodes, "take-home", dur=4.0)
    for slug in ("camera-off", "the-router", "mushroom-training", "take-home"):
        (renders / f"{slug}.mp4").write_bytes(slug.encode())
    video, poster = cache / "clip.mp4", cache / "clip.jpg"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=108x192:rate=10:duration=4",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(video)],
        check=True,
    )  # fmt: skip
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(video), "-frames:v", "1", str(poster)], check=True
    )  # fmt: skip
    base = root / "base.html"
    base.write_text(BASE, encoding="utf-8")
    notes = root / "notes.json"
    gallery = [*fx.GALLERY, fx.item(name="Mesa", parts=["soft-desk"])]
    notes.write_text(json.dumps({"schema": "1.1.0", "episodes": {}, "styles": {}, "gallery": gallery}))
    report = cp.Report(fx.USAGE.episodes, ("take-home", "the-code"))
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(cp, "web_video", lambda render, cache: (video, poster))
        patch.setattr(cp, "still", lambda render, shot, cache: poster)
        patch.setattr(cp, "pose_sheet", lambda engine, cache: [("stand", poster)])
        cp.build(
            base=base, episodes=episodes, renders=renders, site=root / "site", cache=cache, engine=Path("unused"),
            notes=cp.load_notes(notes), usage=report,
        )  # fmt: skip
    return root / "site"


@pytest.fixture(scope="module")
def origin(site):
    httpd = server.make_server(site, "127.0.0.1", 0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}/"
    httpd.shutdown()
    httpd.server_close()
    thread.join()


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        try:
            chromium = p.chromium.launch(headless=True)
        except sync_api.Error as exc:
            pytest.skip(f"no browser: {exc}")
        yield chromium
        chromium.close()


@pytest.fixture
def page(browser):
    tab = browser.new_page(viewport={"width": 1280, "height": 900})
    errors: list[str] = []
    tab.on("pageerror", lambda exc: errors.append(str(exc)))
    tab.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    yield tab
    tab.close()
    assert errors == []


def go(tab, origin: str, route: str) -> None:
    tab.goto(f"{origin}{route}", wait_until="load")


def nav(tab, label: str) -> None:
    tab.locator(f".nav-links a:text-is('{label}')").click()
    tab.wait_for_function("l => document.querySelector('.nav-links [aria-current]')?.textContent === l", arg=label)


def cards(tab, where: str = "#index") -> list[str]:
    return tab.eval_on_selector_all(
        f"{where} .card", "els => els.map(e => e.dataset.video || e.dataset.part || e.dataset.style)"
    )


def test_every_section_of_the_navigation_renders(page, origin, site):
    catalog = json.loads((site / "catalog.json").read_text())
    go(page, origin, "#/")
    kinds = {"Personagens": "character", "Locações": "location", "Objetos": "prop", "Gráficos": "graphic"}
    for label, kind in kinds.items():
        nav(page, label)
        assert len(cards(page)) == sum(p["kind"] == kind for p in catalog["parts"])
    nav(page, "Estilos")
    assert len(cards(page)) == len(catalog["styles"])
    nav(page, "Vídeos")
    assert len(cards(page)) == len(catalog["videos"])


def test_the_home_view_loads_no_image_and_the_base_script_waits_for_its_route(page, origin):
    go(page, origin, "#/")
    page.wait_for_selector(".tiles-nav")
    assert page.locator(".hero").is_visible() and page.locator("#motor").is_hidden()
    assert page.evaluate("document.querySelectorAll('img, video').length") == 0
    assert page.evaluate("window.baseRuns") is None
    nav(page, "Motor")
    assert page.locator("#motor").is_visible() and page.locator(".hero").is_hidden()
    assert page.evaluate("window.baseRuns") == 1
    nav(page, "Pacotes")
    assert page.locator("#episodios").is_visible() and page.evaluate("window.baseRuns") == 1  # once


@pytest.mark.parametrize(
    "route, selector",
    [
        ("#/personagens/rosa", "article[data-part='rosa']"),
        ("#/estilos/soft", "article[data-style='soft']"),
        ("#/videos/camera-off", "article[data-video='camera-off']"),
    ],
)
def test_a_deep_link_opens_directly_on_a_fresh_load(page, origin, route, selector):
    go(page, origin, route)
    assert page.wait_for_selector(selector)


def test_video_to_part_to_video_and_back_and_forward(page, origin):
    go(page, origin, "#/videos")
    page.locator("#index .card[data-video='camera-off']").click()
    page.wait_for_selector("article[data-video='camera-off']")
    page.locator("article .pills a[data-part='pip']").click()
    page.wait_for_selector("article[data-part='pip']")
    page.locator("#part-videos .card[data-video='camera-off']").click()
    page.wait_for_selector("article[data-video='camera-off']")
    page.go_back()
    page.wait_for_selector("article[data-part='pip']")
    page.go_back()
    page.wait_for_selector("article[data-video='camera-off']")
    page.go_forward()
    page.wait_for_selector("article[data-part='pip']")
    assert page.evaluate("location.hash") == "#/personagens/pip"


def test_a_part_lists_the_videos_the_usage_report_measured(page, origin):
    go(page, origin, "#/personagens/manager")
    page.wait_for_selector("#part-videos")
    assert cards(page, "#part-videos") == ["honesty-interview"]


def test_the_style_filter_narrows_the_index_and_is_a_link(page, origin):
    go(page, origin, "#/videos")
    page.wait_for_selector("#index .card")
    total = len(cards(page))
    page.locator(".filters a[href='#/videos?estilo=soft']").click()
    page.wait_for_function("document.querySelectorAll('#index .card').length === 1")
    assert cards(page) == ["camera-off"] and len(cards(page)) < total
    page.go_back()
    page.wait_for_function("n => document.querySelectorAll('#index .card').length === n", arg=total)
    go(page, origin, "#/personagens?estilo=soft")
    page.wait_for_selector("#index .card")
    assert "pip" in cards(page) and "manager" not in cards(page)


def test_the_search_finds_by_name_across_sections_ignoring_accents(page, origin):
    go(page, origin, "#/videos")
    page.wait_for_selector("#index .card")
    page.locator("#search").fill("Rosa")
    page.wait_for_selector("#results .card[data-part='rosa']")
    assert "collage-rosa" in cards(page, "#results")
    page.locator("#search").fill("simulacao")
    page.wait_for_selector("#results .pills a[href='#/motor']")
    page.locator("#search").fill("no-such-name")
    page.wait_for_function("document.querySelector('#app .lede').textContent.startsWith('0 resultados')")
    page.locator("#search").fill("")
    page.wait_for_function("location.hash === '#/videos'")
    page.go_back()
    page.wait_for_function("location.hash === '#/busca/no-such-name'")
    page.go_back()  # three searches typed were one history entry
    page.wait_for_function("location.hash === '#/videos'")


def test_a_search_is_a_link(page, origin):
    go(page, origin, "#/busca/rosa")
    page.wait_for_selector("#results .card[data-part='rosa']")
    assert page.locator("#search").input_value() == "rosa"


def test_a_line_seeks_a_video_that_has_not_loaded(page, origin):
    go(page, origin, "#/videos/camera-off")
    video = page.wait_for_selector("#app video")
    assert video.get_attribute("preload") == "none" and video.get_attribute("poster")
    assert video.evaluate("v => v.readyState") == 0
    page.evaluate("document.querySelector('#app video').muted = true")
    page.locator(".line[data-t='2.000']").click()
    page.wait_for_function(
        "(() => { const v = document.querySelector('#app video'); return v.readyState >= 2 && v.currentTime >= 2 })()"
    )
    page.locator(".line[data-t='0.500']").click()  # and one that has
    page.wait_for_function(
        "(() => { const v = document.querySelector('#app video'); return !v.seeking && v.currentTime < 2 })()"
    )
    page.evaluate("location.hash = '#/videos'")
    page.wait_for_selector("#index .card")
    assert page.evaluate("document.querySelectorAll('video').length") == 0


@pytest.mark.parametrize("slug", ["take-home", "the-code"])
def test_an_unmeasured_episode_says_so(page, origin, slug):
    go(page, origin, f"#/videos/{slug}")
    assert "Não medido" in page.wait_for_selector("#not-measured").inner_text()


def test_marks_on_what_has_no_video_or_no_still(page, origin):
    go(page, origin, "#/personagens/juno")
    page.wait_for_selector("#unused")
    assert page.wait_for_selector("#no-still") and "take-home" in page.locator("article").inner_text()
    go(page, origin, "#/personagens")
    assert "não usado" in page.wait_for_selector("#index .card[data-part='juno']").inner_text()


def test_a_package_links_to_its_player_and_a_project_says_it_has_no_render(page, origin):
    go(page, origin, "#/videos/honesty-interview")
    page.wait_for_selector("a[href='#/pacotes/honesty-interview']")
    assert page.locator("article video").count() == 0
    go(page, origin, "#/videos/the-code")
    assert "não tem render" in page.wait_for_selector("article").inner_text()


def test_the_pose_sheet_the_registry_and_the_usage_lists_are_reachable(page, origin, site):
    go(page, origin, "#/personagens/pip")
    assert page.wait_for_selector("#pose-sheet figure img").get_attribute("loading") == "lazy"
    nav(page, "Registro")
    rows = len(json.loads((site / "catalog.json").read_text())["parts"])
    assert page.locator(".lib-registry tbody tr").count() == rows
    assert page.locator("#lib-usage .lib-usage-kind").count() == 4
    assert "take-home" in page.locator("#lib-usage").inner_text()


@pytest.mark.parametrize("route", ["#/nada", "#/videos/nada", "#/personagens/nada", "#/objetos/pip", "#/estilos/nada"])
def test_an_unknown_route_says_so(page, origin, route):
    go(page, origin, route)
    page.wait_for_function("document.querySelector('#app h2')?.textContent === 'Não encontrado'")


def test_markup_in_a_route_is_shown_as_text(page, origin):
    go(page, origin, "#/busca/" + "%3Cimg%20src=x%20onerror=window.hacked=1%3E")
    page.wait_for_selector("#results", state="attached")
    assert page.locator("#app img").count() == 0 and page.evaluate("window.hacked") is None


@pytest.mark.parametrize(
    "route", ["#/videos", "#/personagens", "#/videos/camera-off", "#/personagens/pip", "#/registro"]
)
def test_a_phone_width_has_no_horizontal_scroll(browser, origin, route):
    tab = browser.new_page(viewport={"width": 400, "height": 800})
    go(tab, origin, route)
    tab.wait_for_selector("#app > *")
    assert tab.evaluate("document.documentElement.scrollWidth") == 400
    tab.close()


@pytest.mark.parametrize(
    "answer, shown",
    [
        ({"status": 500, "body": "no"}, "HTTP 500"),
        ({"status": 200, "body": "{not json"}, "Não foi possível"),
        ({"status": 200, "body": '{"schema_version": "2.0.0"}'}, "schema 2.0.0"),
    ],
)
def test_a_document_the_app_cannot_read_is_reported_on_the_page(browser, origin, answer, shown):
    tab = browser.new_page()
    tab.route("**/catalog.json", lambda route: route.fulfill(**answer))
    go(tab, origin, "#/videos")
    assert shown in tab.wait_for_selector("#load-error").inner_text()
    tab.close()
