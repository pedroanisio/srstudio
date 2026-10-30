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
from srstudio import catalog_specimens as specimens
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
    inked = cache / "inked.jpg"  # the fox's second version looks different from its first
    inked.write_bytes(poster.read_bytes() + b"inked")
    work = root / "work" / "generated" / "character-proofs"
    (work / "fox").mkdir(parents=True)
    shutil.copyfile(video, work / "fox" / "fox-proof.mp4")
    (work / "critters").mkdir()
    (work / "critters" / "index.html").write_text('<!doctype html><video src="./goat.mp4"></video>')
    shutil.copyfile(video, work / "critters" / "goat.mp4")
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(cp, "web_video", lambda render, cache: (video, poster))
        patch.setattr(cp, "still", lambda render, shot, cache: poster)
        patch.setattr(cp, "pose_sheet", lambda engine, cache: [("stand", poster)])
        patch.setattr(cp.catalog_specimens, "render_all", lambda engine, cache, episodes: shelf(poster, inked))
        patch.setattr(cp.catalog_specimens, "poster", lambda packages, slug, engine, cache: poster)
        cp.build(
            base=base, episodes=episodes, renders=renders, site=root / "site", cache=cache, engine=Path("unused"),
            packages=Path("unused"), notes=cp.load_notes(notes), usage=report, proof_root=root / "work",
            pins={"camera-off": {"toon-fox": 2}, "the-router": {"toon-fox": 1}, "not-rendered": {"toon-fox": 2}},
        )  # fmt: skip
    return root / "site"


def shelf(picture: Path, inked: Path) -> specimens.Shelf:
    """Every part drawn but the captions, which say why they are not."""
    drawn = (x.name for x in cp.registry.entries() if x.name != "captions")
    done = {name: specimens.Specimen(name, inked if name == "toon-fox@2" else picture, 480, 480) for name in drawn}
    why = specimens.Refused(specimens.Reason.OVERLAY, "burned captions over a shot")
    return specimens.Shelf(done, {"captions": why}, 0)


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
        assert len(cards(page)) == sum(p["kind"] == kind and not p["version_of"] for p in catalog["parts"])
    nav(page, "Estilos")
    assert len(cards(page)) == len(catalog["styles"])
    nav(page, "Vídeos")
    assert len(cards(page)) == len(catalog["videos"])


def test_the_sidebar_stays_in_view_and_counts_every_section(page, origin, site):
    catalog = json.loads((site / "catalog.json").read_text())
    go(page, origin, "#/videos")
    page.wait_for_selector("#index .card")
    count = "href => document.querySelector(`.nav-links a[href='${href}']`).dataset.count"
    assert page.evaluate(count, "#/videos") == str(len(catalog["videos"]))
    characters = [p for p in catalog["parts"] if p["kind"] == "character" and not p["version_of"]]
    assert page.evaluate(count, "#/personagens") == str(len(characters))
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    assert page.locator("#nav").evaluate("n => n.getBoundingClientRect().top") == 0
    assert page.locator("#nav").evaluate("n => n.getBoundingClientRect().height") == 900


def test_the_home_view_is_a_dashboard_and_the_base_script_waits_for_its_route(page, origin, site):
    catalog = json.loads((site / "catalog.json").read_text())
    go(page, origin, "#/")
    page.wait_for_selector(".tiles-nav")
    assert page.locator(".hero").is_hidden() and page.locator("#motor").is_hidden()
    assert page.locator(".style-table tbody tr").count() == len(catalog["styles"])
    assert page.locator(".usage-bar").count() == 4
    assert page.locator("#app .specs .spec").count() > 0
    assert page.evaluate("document.querySelectorAll('video').length") == 0
    assert page.evaluate("document.querySelectorAll('img').length") <= len(catalog["styles"])  # one poster per style
    assert page.evaluate("window.baseRuns") is None
    go(page, origin, "#/")
    page.locator(".style-table a[href='#/videos?estilo=soft']").click()
    page.wait_for_function("document.querySelectorAll('#index .card').length === 1")
    nav(page, "Visão geral")
    page.wait_for_selector(".tiles-nav")
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


def test_a_filter_shows_its_count_and_keeps_the_sort_and_the_view(page, origin):
    go(page, origin, "#/videos?ordem=titulo&ver=lista")
    page.wait_for_selector("#index .row")
    chip = page.locator(".filters a", has_text="Soft")
    assert chip.locator("small").inner_text() == "1"
    assert chip.get_attribute("href") == "#/videos?ordem=titulo&ver=lista&estilo=soft"


def test_the_list_view_is_a_table_and_a_link(page, origin, site):
    catalog = json.loads((site / "catalog.json").read_text())
    go(page, origin, "#/videos")
    page.wait_for_selector("#index .card")
    page.locator(".seg a:text-is('Lista')").click()
    page.wait_for_selector("#index tr.row")
    assert page.locator("#index tr.row").count() == len(catalog["videos"])
    assert page.evaluate("location.hash") == "#/videos?ver=lista"
    page.locator("#index tr.row[data-video='camera-off'] a").first.click()
    page.wait_for_selector("article[data-video='camera-off']")


def test_the_sort_orders_the_index(page, origin):
    go(page, origin, "#/videos")
    page.wait_for_selector("#index .card")
    page.locator("#sort").select_option(label="Título")
    page.wait_for_function("location.hash === '#/videos?ordem=titulo'")
    page.wait_for_selector("#index .card")
    titles = page.eval_on_selector_all("#index .card b", "els => els.map(e => e.textContent)")
    assert titles == sorted(titles, key=str.lower)


def test_the_usage_filter_narrows_parts(page, origin, site):
    catalog = json.loads((site / "catalog.json").read_text())
    go(page, origin, "#/personagens?uso=nao")
    page.wait_for_selector("#index .card")
    characters = [p for p in catalog["parts"] if p["kind"] == "character" and not p["version_of"]]
    unused = {p["name"] for p in characters if not p["videos"]}
    assert set(cards(page)) == unused
    assert page.locator(".seg a[aria-current='true']", has_text="Sem uso").count() == 1


def test_a_style_opens_in_tabs(page, origin, site):
    catalog = json.loads((site / "catalog.json").read_text())
    soft = next(s for s in catalog["styles"] if s["slug"] == "soft")
    go(page, origin, "#/estilos/soft")
    page.wait_for_selector("#style-videos .card")
    assert page.locator(".tabs a[aria-current='true']").inner_text().startswith("Vídeos")
    page.locator(".tabs a[href='#/estilos/soft?aba=personagens']").click()
    page.wait_for_selector("#style-parts .card")
    assert page.locator("#style-videos").count() == 0
    own = [n for n in soft["parts"] if next(p for p in catalog["parts"] if p["name"] == n)["kind"] == "character"]
    assert cards(page, "#style-parts") == own


def test_a_video_and_a_part_show_a_data_sheet(page, origin):
    go(page, origin, "#/videos/camera-off")
    sheet = page.wait_for_selector(".ficha").inner_text()
    assert "Duração" in sheet and "4,0 s" in sheet
    assert page.locator(".crumbs a[href='#/videos']").count() == 1
    go(page, origin, "#/personagens/pip")
    sheet = page.wait_for_selector(".ficha").inner_text()
    assert "pip" in sheet and "Aparece em" in sheet


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


def test_a_card_shows_the_part_itself_and_a_refused_part_says_why(page, origin):
    go(page, origin, "#/personagens")
    card = page.wait_for_selector("#index .card[data-part='juno']")
    picture = card.query_selector(".frame.specimen img")
    assert picture and picture.get_attribute("src").startswith("media/")  # juno is in no reel and no gallery
    assert "sem imagem" not in card.inner_text() and "sem still" not in card.inner_text()
    assert card.query_selector("b").inner_text() != "juno"
    go(page, origin, "#/graficos")
    refused = page.wait_for_selector("#index .card[data-part='captions']")
    assert not refused.query_selector("img")
    assert cp.REFUSAL_TEXT[specimens.Reason.OVERLAY] in refused.inner_text()


def test_the_part_page_opens_with_the_specimen_and_keeps_the_reel_stills_under_seen_in(page, origin):
    go(page, origin, "#/personagens/pip")
    article = page.wait_for_selector("article[data-part='pip']")
    assert article.query_selector("#specimen img")
    assert article.evaluate("""a => {
        const seen = [...a.querySelectorAll('.sub')].find(s => s.textContent === 'Visto em');
        const specimen = a.querySelector('#specimen'), still = a.querySelector('.stills.lead:not(#specimen)');
        return specimen.compareDocumentPosition(seen) & 4 && seen.compareDocumentPosition(still) & 4;
    }""")


def test_a_refused_part_page_says_why(page, origin):
    go(page, origin, "#/graficos/captions")
    assert cp.REFUSAL_TEXT[specimens.Reason.OVERLAY] in page.wait_for_selector("#refused").inner_text()


def test_a_list_row_shows_the_part_itself_whole_and_a_refused_row_says_why(page, origin):
    go(page, origin, "#/personagens?ver=lista")
    picture = page.wait_for_selector("#index tr.row[data-part='juno'] .pic.specimen img")
    assert picture.evaluate("i => getComputedStyle(i).objectFit") == "contain"  # a square is not cropped to the cell
    go(page, origin, "#/graficos?ver=lista")
    refused = page.wait_for_selector("#index tr.row[data-part='captions']")
    assert not refused.query_selector("img")
    assert cp.REFUSAL_TEXT[specimens.Reason.OVERLAY] in refused.inner_text()


def test_a_card_never_crops_a_specimen(page, origin):
    go(page, origin, "#/personagens")
    picture = page.wait_for_selector("#index .card[data-part='juno'] .frame img")
    assert picture.evaluate("i => getComputedStyle(i).objectFit") == "contain"


def test_the_dashboard_counts_the_refused_parts_and_no_part_is_without_a_picture_or_a_reason(page, origin):
    go(page, origin, "#/")
    pending = page.wait_for_selector("details:has-text('Peças sem desenho isolado')")
    assert pending.query_selector("a[href='#/graficos/captions']")
    assert page.locator("details:has-text('Peças sem imagem')").count() == 0


def test_a_package_film_shows_the_poster_of_its_spec_and_keeps_its_player(page, origin):
    go(page, origin, "#/videos/honesty-interview")
    page.wait_for_selector("article a[href='#/pacotes/honesty-interview']")
    go(page, origin, "#/videos")
    card = page.wait_for_selector("#index .card[data-video='honesty-interview']")
    assert card.query_selector(".frame img") and "pacote em SVG" not in card.inner_text()


def test_marks_what_has_no_video_and_says_nothing_of_a_reel_still_it_lacks(page, origin):
    go(page, origin, "#/personagens/juno")
    page.wait_for_selector("#unused")
    article = page.locator("article").inner_text()
    assert "take-home" in article
    assert "Visto em" not in article and "Nenhum item da galeria" not in article
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


# -- versions ---------------------------------------------------------------------------------------------
def rewritten(tab, site, change) -> None:
    """Serve ``catalog.json`` as ``change`` leaves it, for a shape the shipped table does not hold."""
    doc = json.loads((site / "catalog.json").read_text())
    change(doc, {p["name"]: p for p in doc["parts"]})
    tab.route("**/catalog.json", lambda route: route.fulfill(json=doc))


def proposed_fox(doc, parts) -> None:
    """The fox as feat/older-cast leaves the rest of the cast: version 2 drawn and proposed, version 1 the default."""
    first, second = parts["toon-fox"]["versions"]
    first["default"] = True
    second.update(status="proposed", default=False, approval=None, pins=[])


def test_a_character_is_one_card_with_its_version_count_showing_its_default(page, origin, site):
    parts = {p["name"]: p for p in json.loads((site / "catalog.json").read_text())["parts"]}
    go(page, origin, "#/personagens")
    page.wait_for_selector("#index .card")
    assert "toon-fox" in cards(page) and "toon-fox@2" not in cards(page)
    card = page.locator("#index .card[data-part='toon-fox']")
    assert "2 versões" in card.inner_text()
    assert card.locator("img").get_attribute("src") == parts["toon-fox@2"]["specimen"]["src"]
    assert "versões" not in page.locator("#index .card[data-part='pip']").inner_text()
    go(page, origin, "#/personagens?ver=lista")
    row = page.wait_for_selector("#index tr.row[data-part='toon-fox']")
    assert "2 versões" in row.inner_text()
    assert page.locator("#index tr.row[data-part='toon-fox@2']").count() == 0


def test_the_counts_follow_the_cards_and_the_registry_stays_complete(page, origin, site):
    catalog = json.loads((site / "catalog.json").read_text())
    characters = [p for p in catalog["parts"] if p["kind"] == "character" and not p["version_of"]]
    go(page, origin, "#/personagens")
    page.wait_for_selector("#index .card")
    assert len(cards(page)) == len(characters)
    assert page.evaluate("document.querySelector(\".nav-links a[href='#/personagens']\").dataset.count") == str(
        len(characters)
    )
    go(page, origin, "#/")
    toon = page.wait_for_selector(".style-table a[href='#/personagens?estilo=toon']", state="attached")
    assert toon.inner_text() == str(sum(p["style"] == "toon" for p in characters))
    go(page, origin, "#/registro")
    page.wait_for_selector(".lib-usage-kind")
    assert page.locator("a[href='#/personagens/toon-fox%402'] code").count() >= 1
    assert page.locator("article, #app").first.inner_text().count("toon-fox@2") >= 1


def test_a_part_page_shows_its_whole_history(page, origin, site):
    parts = {p["name"]: p for p in json.loads((site / "catalog.json").read_text())["parts"]}
    go(page, origin, "#/personagens/toon-fox")
    page.wait_for_selector("#versions")
    assert page.locator("#versions .version").count() == 2
    first, second = page.locator("#versions .version[data-version='1']"), page.locator(".version[data-version='2']")
    for v, name in ((first, "toon-fox"), (second, "toon-fox@2")):
        assert v.locator("img").get_attribute("src") == parts[name]["specimen"]["src"]
    text = second.inner_text()
    record = parts["toon-fox"]["versions"][1]
    assert "Versão 2" in text and "Aprovada" in text and "Padrão para novos reels" in text
    assert record["note"] in text and "30/10/2026" in text
    assert f"“{record['approval']['words']}”" in text
    assert "Padrão para novos reels" not in first.inner_text() and "Aprovada" in first.inner_text()
    assert page.locator("#specimen img").get_attribute("src") == parts["toon-fox@2"]["specimen"]["src"]


def test_a_version_links_its_proof_and_the_reels_that_pin_it(page, origin):
    go(page, origin, "#/personagens/toon-fox")
    second = page.wait_for_selector(".version[data-version='2']")
    proof = second.query_selector("a.proof")
    assert page.request.get(origin + proof.get_attribute("href")).status == 200
    pins = page.locator(".version[data-version='2'] .pins")
    assert pins.locator("a").get_attribute("href") == "#/videos/camera-off"
    assert "not-rendered" in pins.inner_text()  # a pin with no video yet is named, with nothing to link to
    assert page.locator(".version[data-version='1'] .pins a").get_attribute("href") == "#/videos/the-router"
    assert page.locator(".version[data-version='1'] a.proof").count() == 0


def test_a_page_proof_opens_with_the_files_beside_it(page, origin):
    go(page, origin, "#/personagens/toon-goat")
    link = page.wait_for_selector(".version a.proof").get_attribute("href")
    assert link.startswith("proofs/") and link.endswith("/index.html")
    assert page.request.get(origin + link.replace("index.html", "goat.mp4")).status == 200


def test_a_single_version_is_listed_without_repeating_the_picture(page, origin):
    go(page, origin, "#/personagens/toon-goat")
    page.wait_for_selector("#versions")
    version = page.locator("#versions .version")
    assert version.count() == 1 and version.locator("img").count() == 0
    assert "“all approved”" in version.inner_text() and "Padrão para novos reels" in version.inner_text()


def test_a_proof_not_on_this_machine_says_so(page, origin, site):
    def gone(doc, parts):
        parts["toon-fox"]["versions"][1]["proof"] = ""

    rewritten(page, site, gone)
    go(page, origin, "#/personagens/toon-fox")
    version = page.wait_for_selector(".version[data-version='2']")
    assert "não está nesta máquina" in version.inner_text() and not version.query_selector("a.proof")


def test_a_proposed_version_shows_as_proposed_and_never_as_the_default(page, origin, site):
    rewritten(page, site, proposed_fox)
    parts = {p["name"]: p for p in json.loads((site / "catalog.json").read_text())["parts"]}
    go(page, origin, "#/personagens")
    card = page.wait_for_selector("#index .card[data-part='toon-fox']")
    assert "1 proposta" in card.inner_text()
    assert card.query_selector("img").get_attribute("src") == parts["toon-fox"]["specimen"]["src"]
    go(page, origin, "#/personagens/toon-fox")
    second = page.wait_for_selector(".version[data-version='2']")
    assert "Proposta" in second.inner_text() and "Padrão para novos reels" not in second.inner_text()
    assert "Aprovada" not in second.inner_text()
    assert "Padrão para novos reels" in page.locator(".version[data-version='1']").inner_text()
    assert second.query_selector("img").get_attribute("src") == parts["toon-fox@2"]["specimen"]["src"]
    assert page.locator("#specimen img").get_attribute("src") == parts["toon-fox"]["specimen"]["src"]


def test_a_proposed_version_with_no_drawing_says_so(page, origin, site):
    def undrawn(doc, parts):
        proposed_fox(doc, parts)
        parts["toon-fox"]["versions"][1]["part"] = ""

    rewritten(page, site, undrawn)
    go(page, origin, "#/personagens/toon-fox")
    assert "Ainda sem desenho" in page.wait_for_selector(".version[data-version='2']").inner_text()


def test_a_version_s_own_route_opens_the_history_at_that_version(page, origin):
    go(page, origin, "#/personagens/toon-fox%402")
    current = page.wait_for_selector(".version.current")
    assert current.get_attribute("data-version") == "2"
    assert page.locator("article").get_attribute("data-part") == "toon-fox"
    assert page.locator(".version").count() == 2


def test_a_character_counts_the_videos_of_every_version(page, origin, site):
    def used(doc, parts):
        parts["toon-fox@2"]["videos"] = ["camera-off"]

    rewritten(page, site, used)
    go(page, origin, "#/personagens")
    card = page.wait_for_selector("#index .card[data-part='toon-fox']")
    assert "1 vídeo" in card.inner_text() and "não usado" not in card.inner_text()
    go(page, origin, "#/personagens/toon-fox")
    assert page.wait_for_selector("#part-videos .card[data-video='camera-off']")


def test_the_search_finds_a_character_by_a_version_once(page, origin):
    go(page, origin, "#/busca/toon-fox%402")
    page.wait_for_selector("#results .card")
    assert cards(page, "#results") == ["toon-fox"]


def test_pins_that_were_not_read_are_not_shown_as_none(page, origin, site):
    def unread(doc, parts):
        doc["pinned"] = False
        for v in parts["toon-fox"]["versions"]:
            v["pins"] = []

    rewritten(page, site, unread)
    go(page, origin, "#/personagens/toon-fox")
    text = page.wait_for_selector(".version[data-version='2']").inner_text()
    assert "não lidas" in text and "Nenhum reel" not in text


def test_a_version_no_reel_pins_says_so(page, origin, site):
    def none(doc, parts):
        for v in parts["toon-fox"]["versions"]:
            v["pins"] = []

    rewritten(page, site, none)
    go(page, origin, "#/personagens/toon-fox")
    assert "Nenhum reel" in page.wait_for_selector(".version[data-version='2']").inner_text()


def test_a_part_with_no_history_shows_no_version_section(page, origin):
    go(page, origin, "#/objetos/soft-desk")
    page.wait_for_selector("article.detail")
    assert page.locator("#versions").count() == 0
